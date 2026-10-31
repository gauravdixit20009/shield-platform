"""
SHIELD Platform — Admin / CMS Routes
Central Management for DGP/Commissioner level.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.auth.dependencies import get_current_officer, require_rank, require_sp_or_above, require_dgp_or_above
from app.models.officer import Officer, OfficerRank
from app.models.case import Case, CaseStatus
from app.models.audit import AuditLog, ThreatReport
from app.auth.auth_service import AuthService

router = APIRouter()


class CreateOfficerRequest(BaseModel):
    badge_number: str
    full_name: str
    email: str
    phone: str
    rank: OfficerRank
    department: str
    state: Optional[str] = None
    district: Optional[str] = None
    station_code: Optional[str] = None
    superior_officer_id: Optional[str] = None
    initial_password: str


class SuspendOfficerRequest(BaseModel):
    reason: str
    escalate_cases: bool = True


# ─── Dashboard ─────────────────────────────────────────────
@router.get("/dashboard")
async def get_dashboard(
    officer: Officer = Depends(require_sp_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Central management dashboard stats."""
    # Active cases
    active_cases = await db.execute(
        select(func.count(Case.id)).where(
            Case.status == CaseStatus.OPEN,
            Case.is_deleted == False,
        )
    )
    # Officers on duty
    on_duty = await db.execute(
        select(func.count(Officer.id)).where(Officer.is_on_duty == True)
    )
    # Threat reports
    high_threats = await db.execute(
        select(func.count(ThreatReport.id)).where(
            ThreatReport.threat_level.in_(["HIGH", "CRITICAL"]),
            ThreatReport.is_reviewed == False,
        )
    )

    return {
        "active_cases": active_cases.scalar(),
        "officers_on_duty": on_duty.scalar(),
        "unreviewed_high_threats": high_threats.scalar(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# ─── Officer Management ────────────────────────────────────
@router.post("/officers", summary="Register new officer")
async def create_officer(
    body: CreateOfficerRequest,
    officer: Officer = Depends(require_dgp_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Register a new officer. DGP+ only."""
    # Check badge number uniqueness
    existing = await db.execute(
        select(Officer).where(Officer.badge_number == body.badge_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Badge number already exists")

    hashed_pw = AuthService.hash_password(body.initial_password)
    totp_secret = AuthService.generate_totp_secret()

    new_officer = Officer(
        badge_number=body.badge_number,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        rank=body.rank,
        department=body.department,
        state=body.state,
        district=body.district,
        station_code=body.station_code,
        hashed_password=hashed_pw,
        totp_secret=totp_secret,
        is_mfa_enabled=True,
        created_by=officer.id,
    )
    if body.superior_officer_id:
        import uuid
        new_officer.superior_officer_id = uuid.UUID(body.superior_officer_id)

    db.add(new_officer)
    await db.commit()
    await db.refresh(new_officer)

    totp_uri = AuthService.generate_totp_uri(new_officer.email, totp_secret)

    return {
        "officer_id": str(new_officer.id),
        "badge_number": new_officer.badge_number,
        "mfa_setup_uri": totp_uri,
        "message": "Officer created. Share MFA QR code with the officer securely.",
    }


@router.post("/officers/{officer_id}/suspend")
async def suspend_officer(
    officer_id: str,
    body: SuspendOfficerRequest,
    current_officer: Officer = Depends(require_sp_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Suspend an officer. SP+ only."""
    import uuid
    result = await db.execute(
        select(Officer).where(Officer.id == uuid.UUID(officer_id))
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Officer not found")

    target.is_suspended = True
    target.suspension_reason = body.reason

    from app.models.audit import AuditAction
    audit = AuditLog(
        officer_id=current_officer.id,
        action=AuditAction.OFFICER_SUSPENDED,
        resource_type="officer",
        resource_id=uuid.UUID(officer_id),
        timestamp=datetime.now(timezone.utc).isoformat(),
        details={"reason": body.reason, "suspended_officer": target.badge_number},
    )
    db.add(audit)
    await db.commit()

    return {"status": "SUSPENDED", "officer": target.badge_number}


# ─── Threat Reports ────────────────────────────────────────
@router.get("/threat-reports")
async def get_threat_reports(
    officer: Officer = Depends(require_sp_or_above),
    db: AsyncSession = Depends(get_db),
):
    """View all unreviewed threat reports."""
    result = await db.execute(
        select(ThreatReport).where(ThreatReport.is_reviewed == False)
        .order_by(ThreatReport.created_at.desc())
    )
    reports = result.scalars().all()

    return {
        "reports": [
            {
                "id": str(r.id),
                "officer_id": str(r.officer_id),
                "threat_level": r.threat_level,
                "threat_score": r.threat_score,
                "ai_analysis": r.ai_analysis,
                "recommended_action": r.recommended_action,
                "created_at": str(r.created_at),
            }
            for r in reports
        ]
    }


# ─── Audit Logs ────────────────────────────────────────────
@router.get("/audit-logs")
async def get_audit_logs(
    officer_id: Optional[str] = None,
    limit: int = 100,
    current_officer: Officer = Depends(require_sp_or_above),
    db: AsyncSession = Depends(get_db),
):
    """View audit logs. SP+ only."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if officer_id:
        import uuid
        query = query.where(AuditLog.officer_id == uuid.UUID(officer_id))

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(l.id),
                "officer_id": str(l.officer_id),
                "action": l.action,
                "resource_type": l.resource_type,
                "ip_address": l.ip_address,
                "timestamp": l.timestamp,
                "is_anomalous": l.is_anomalous,
            }
            for l in logs
        ]
    }
