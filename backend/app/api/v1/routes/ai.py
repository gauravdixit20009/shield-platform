"""
SHIELD Platform — AI (ARIA) Routes
Case analysis, document OCR, suspect network mapping.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import uuid

from app.core.database import get_db
from app.auth.dependencies import get_current_officer
from app.models.officer import Officer
from app.services.case_service import CaseService, CaseAccessError
from app.ai.aria_service import ARIAService

router = APIRouter()


class AnalyzeCaseRequest(BaseModel):
    case_id: str


class AnalyzeDocumentRequest(BaseModel):
    document_text: str
    document_type: str = "FIR"


class ChatRequest(BaseModel):
    message: str
    case_id: Optional[str] = None     # Optional context


@router.post("/analyze-case")
async def analyze_case(
    body: AnalyzeCaseRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Run ARIA AI analysis on a case. Officer must be authorized for the case."""
    try:
        case = await CaseService.get_case_for_officer(
            db, uuid.UUID(body.case_id), officer, log_action=True
        )
    except CaseAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Prepare case data for ARIA
    suspects_data = [
        {"name": s.full_name, "aliases": s.aliases, "is_arrested": s.is_arrested}
        for s in (case.suspects or [])
    ]
    evidence_list = [f"{e.evidence_type}: {e.title}" for e in (case.evidence or [])]

    case_summary = f"""
Case: {case.case_number}
Category: {case.category}
Priority: {case.priority}
Status: {case.status}
Location: {case.incident_location}
Date: {case.incident_date}
Description: {case.description or 'Not provided'}
"""

    result = await ARIAService.analyze_case(case_summary, evidence_list, suspects_data)

    # Save AI summary back to case
    case.ai_summary = result.get("analysis", "")
    await db.commit()

    return result


@router.post("/analyze-document")
async def analyze_document(
    body: AnalyzeDocumentRequest,
    officer: Officer = Depends(get_current_officer),
):
    """Analyze a document (FIR, charge sheet, etc.) with ARIA."""
    result = await ARIAService.analyze_document(body.document_text, body.document_type)
    return result


@router.post("/chat")
async def chat_with_aria(
    body: ChatRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with ARIA AI assistant.
    If case_id provided, ARIA has context from that case (access-controlled).
    """
    context = ""
    if body.case_id:
        try:
            case = await CaseService.get_case_for_officer(
                db, uuid.UUID(body.case_id), officer
            )
            context = f"\nCurrent case context: {case.case_number} - {case.title} ({case.category})\n"
        except CaseAccessError:
            context = ""  # No context — officer not authorized

    full_prompt = context + body.message
    response = await ARIAService._query(full_prompt)
    return {"response": response, "has_case_context": bool(context)}


@router.post("/suggest-investigation-steps")
async def suggest_steps(
    body: AnalyzeCaseRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-suggested investigation steps for a case."""
    try:
        case = await CaseService.get_case_for_officer(db, uuid.UUID(body.case_id), officer)
    except CaseAccessError as e:
        raise HTTPException(status_code=403, detail=str(e))

    steps = await ARIAService.suggest_investigation_steps({
        "case_number": case.case_number,
        "category": case.category,
        "description": case.description,
        "evidence_count": len(case.evidence or []),
        "suspects_count": len(case.suspects or []),
    })
    return {"steps": steps}
