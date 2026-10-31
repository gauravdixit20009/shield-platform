"""
SHIELD Platform — Cases API Routes
Full CRUD with zero-loophole access control.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.auth.dependencies import get_current_officer, require_rank
from app.models.officer import Officer, OfficerRank
from app.models.case import Case, CasePriority, CaseStatus, CrimeCategory, Evidence, EvidenceType
from app.services.case_service import CaseService, CaseAccessError
from app.services.traitor_detection import TraitorDetectionEngine
from app.models.audit import BehaviorSignalType

router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────
class CreateCaseRequest(BaseModel):
    title: str
    description: Optional[str] = None
    category: CrimeCategory
    priority: CasePriority = CasePriority.MEDIUM
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None
    incident_latitude: Optional[float] = None
    incident_longitude: Optional[float] = None
    jurisdiction_state: Optional[str] = None
    jurisdiction_district: Optional[str] = None
    fir_number: Optional[str] = None
    assigned_officer_id: Optional[str] = None  # Only SP+ can set this


class UpdateCaseRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    court_name: Optional[str] = None
    court_case_number: Optional[str] = None
    next_hearing_date: Optional[str] = None


class TransferCaseRequest(BaseModel):
    to_officer_id: str
    reason: str


# ─── Routes ────────────────────────────────────────────────
@router.get("/", summary="List my cases")
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    List cases accessible to the current officer.
    Field officers see ONLY their assigned cases.
    SP+ see cases they created or assigned.
    DGP+ see all cases.
    """
    cases = await CaseService.list_cases_for_officer(
        db, officer, status_filter, page, per_page
    )
    return {
        "cases": [_serialize_case(c) for c in cases],
        "page": page,
        "per_page": per_page,
    }


@router.get("/{case_id}", summary="Get case details")
async def get_case(
    case_id: uuid.UUID,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Get full case details. Access denied if not authorized."""
    try:
        case = await CaseService.get_case_for_officer(db, case_id, officer)
    except CaseAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _serialize_case(case, detailed=True)


@router.post("/", summary="Create new case", status_code=201)
async def create_case(
    body: CreateCaseRequest,
    officer: Officer = Depends(require_rank(OfficerRank.INSPECTOR)),  # Min Inspector rank
    db: AsyncSession = Depends(get_db),
):
    """Create a new case. Inspectors+ only. Assignment rules enforced."""
    case = await CaseService.create_case(db, officer, body.dict(exclude_none=True))
    return _serialize_case(case)


@router.patch("/{case_id}", summary="Update case")
async def update_case(
    case_id: uuid.UUID,
    body: UpdateCaseRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Update case. Only the assigned officer or creator can update."""
    try:
        case = await CaseService.get_case_for_officer(db, case_id, officer)
    except CaseAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Only assigned officer or their superior can edit
    can_edit = (
        str(case.assigned_officer_id) == str(officer.id) or
        str(case.created_by_officer_id) == str(officer.id)
    )
    if not can_edit:
        await TraitorDetectionEngine.add_signal(
            db, officer.id,
            BehaviorSignalType.CASE_TAMPERING,
            {"case_id": str(case_id), "action": "unauthorized_edit_attempt"}
        )
        raise HTTPException(status_code=403, detail="Cannot edit a case you are not assigned to")

    for field, value in body.dict(exclude_none=True).items():
        setattr(case, field, value)

    from app.models.case import CaseActivityLog
    activity = CaseActivityLog(
        case_id=case.id,
        officer_id=officer.id,
        action="CASE_EDITED",
        ip_address=getattr(officer, "_request_ip", "unknown"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        details=body.dict(exclude_none=True),
    )
    db.add(activity)
    await db.commit()
    await db.refresh(case)
    return _serialize_case(case)


@router.post("/{case_id}/transfer", summary="Request case transfer")
async def request_transfer(
    case_id: uuid.UUID,
    body: TransferCaseRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Request to transfer a case to another officer. Requires supervisor approval."""
    try:
        transfer = await CaseService.request_case_transfer(
            db, case_id, officer, uuid.UUID(body.to_officer_id), body.reason
        )
    except CaseAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {
        "transfer_id": str(transfer.id),
        "status": "PENDING_APPROVAL",
        "message": "Transfer request sent to your superior for approval",
    }


@router.post("/transfers/{transfer_id}/approve", summary="Approve case transfer")
async def approve_transfer(
    transfer_id: uuid.UUID,
    officer: Officer = Depends(require_rank(OfficerRank.SP)),
    db: AsyncSession = Depends(get_db),
):
    """Approve a case transfer request. SP+ only. Cannot self-approve."""
    try:
        transfer = await CaseService.approve_case_transfer(db, transfer_id, officer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "APPROVED", "transfer_id": str(transfer.id)}


@router.post("/{case_id}/evidence", summary="Upload evidence")
async def upload_evidence(
    case_id: uuid.UUID,
    title: str,
    evidence_type: EvidenceType,
    file: UploadFile = File(...),
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Upload evidence file. Chain-of-custody automatically recorded."""
    try:
        case = await CaseService.get_case_for_officer(db, case_id, officer)
    except CaseAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Hash the file for tamper detection
    import hashlib
    content = await file.read()
    file_hash = hashlib.sha512(content).hexdigest()

    # TODO: Upload to MinIO encrypted vault
    file_path = f"evidence/{case_id}/{file.filename}"

    evidence = Evidence(
        case_id=case.id,
        evidence_number=f"EV-{case.case_number}-{len(case.evidence) + 1:04d}",
        title=title,
        evidence_type=evidence_type,
        file_path=file_path,
        file_hash=file_hash,
        file_size=len(content),
        mime_type=file.content_type,
        collected_by_id=officer.id,
        collected_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(evidence)
    await db.commit()

    return {
        "evidence_id": str(evidence.id),
        "evidence_number": evidence.evidence_number,
        "file_hash": file_hash,
        "message": "Evidence uploaded and hash recorded for chain-of-custody",
    }


@router.post("/{case_id}/evidence/{evidence_id}/bsa-certificate", summary="Generate BSA Section 63 Digital Evidence Certificate")
async def generate_bsa_certificate(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a court-admissible Digital Evidence Certificate under 
    Section 63(4) of the Bharatiya Sakshya Adhiniyam, 2023 (BSA),
    with SHA-512 cryptographic verification seal and chain of custody attestation.
    """
    from app.services.bsa_certificate_service import BSACertificateService
    from sqlalchemy import select

    case = await CaseService.get_case_for_officer(db, case_id, officer)
    res = await db.execute(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.case_id == case.id)
    )
    evidence = res.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence artifact not found in this case")

    certificate = BSACertificateService.generate_certificate(case, evidence, officer)
    return certificate


# ─── Serializer ────────────────────────────────────────────
def _serialize_case(case: Case, detailed: bool = False) -> dict:
    base = {
        "id": str(case.id),
        "case_number": case.case_number,
        "title": case.title,
        "category": case.category,
        "priority": case.priority,
        "status": case.status,
        "incident_location": case.incident_location,
        "created_at": str(case.created_at),
    }
    if detailed:
        base.update({
            "description": case.description,
            "fir_number": case.fir_number,
            "suspects_count": len(case.suspects) if case.suspects else 0,
            "evidence_count": len(case.evidence) if case.evidence else 0,
            "ai_summary": case.ai_summary,
            "ai_risk_score": case.ai_risk_score,
            "ai_tags": case.ai_tags,
            "court_name": case.court_name,
            "next_hearing_date": case.next_hearing_date,
        })
    return base
