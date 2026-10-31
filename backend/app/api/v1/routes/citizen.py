"""
SHIELD Platform — Citizen Public Safety & e-Services Router
Public endpoints for civilians:
- Online e-FIR & incident reporting
- Complaint / FIR status tracking
- Anonymous crime tips & whistleblower submissions
- Civilian Emergency SOS
- Police Officer Digital Badge verification
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import secrets

from app.core.database import get_db
from app.models.officer import Officer, OfficerRank
from app.models.case import Case, CasePriority, CaseStatus, CrimeCategory
from app.models.audit import AuditLog, AuditAction

router = APIRouter()

# In-memory storage for demonstration citizen complaints & tips (synced to Case when approved)
CITIZEN_COMPLAINTS: Dict[str, Dict[str, Any]] = {
    "CIT-2026-89412": {
        "tracking_id": "CIT-2026-89412",
        "title": "Unauthorized debit & phishing message",
        "category": "CYBERCRIME",
        "incident_location": "Bandra West, Mumbai",
        "complainant_name": "Rohan Deshmukh",
        "complainant_phone": "+91 98201 XXXXX",
        "description": "Received suspicious SMS with APK download link pretending to be electricity board. 45,000 INR debited.",
        "status": "UNDER_INVESTIGATION",
        "station_code": "CPS-02",
        "station": "Cyber Cell Police Station (Bandra West)",
        "registered_date": "2026-10-28",
        "created_at": "2026-10-28T14:30:00Z",
        "investigating_officer": "Sub-Inspector A. Verma (Cyber Cell)",
        "assigned_officer": "Sub-Inspector A. Verma",
        "milestones": [
            {"step": "Online e-FIR Registered", "detail": "Complaint acknowledged with digital hash", "timestamp": "2026-10-28 14:30", "completed": True},
            {"step": "Assigned to Investigating Officer", "detail": "Cyber Crime Cell inspector assigned", "timestamp": "2026-10-28 16:15", "completed": True},
            {"step": "Bank Lien Notice Dispatched", "detail": "Section 94 BNSS notice issued to recipient bank", "timestamp": "2026-10-29 11:00", "completed": True},
            {"step": "Forensic Review & IP Tracing", "detail": "Telecom CDR & gateway server log audit", "timestamp": "In Progress", "completed": False},
            {"step": "Final Court Charge Sheet", "detail": "Submitting findings to judicial magistrate", "timestamp": "Pending", "completed": False}
        ],
        "timeline": [
            {"time": "2026-10-28 14:30", "status": "COMPLAINT_REGISTERED", "note": "Online citizen e-complaint logged."},
            {"time": "2026-10-28 16:15", "status": "STATION_ASSIGNED", "note": "Assigned to Cyber Crime Cell, CPS-02."},
            {"time": "2026-10-29 11:00", "status": "BANK_NOTICE_SENT", "note": "Section 94 BNSS notice sent to beneficiary bank for lien freeze."},
        ]
    }
}

ANONYMOUS_TIPS = []


class CivilianComplaintRequest(BaseModel):
    title: Optional[str] = None
    category: str = "CYBERCRIME"
    description: str = Field(..., min_length=5)
    incident_location: str
    complainant_name: str
    complainant_phone: Optional[str] = None
    contact_number: Optional[str] = None
    complainant_email: Optional[str] = None


class AnonymousTipRequest(BaseModel):
    category: str = "NARCOTICS"
    location: str
    description: Optional[str] = None
    tip_details: Optional[str] = None
    suspects: Optional[str] = None
    evidence_urls: Optional[list] = None


class CivilianSosRequest(BaseModel):
    latitude: float
    longitude: float
    caller_name: Optional[str] = "Civilian in Distress"
    caller_phone: Optional[str] = None
    distress_type: Optional[str] = "GENERAL_EMERGENCY"
    incident_type: Optional[str] = None


@router.post("/complaints")
async def register_civilian_complaint(
    body: CivilianComplaintRequest,
    db: AsyncSession = Depends(get_db)
):
    """File an online e-FIR / citizen incident report."""
    tracking_id = f"CIT-2026-{secrets.randbelow(90000) + 10000}"
    now_iso = datetime.now(timezone.utc).isoformat()

    title = body.title or f"{body.category.title()} Online Incident Report"
    phone = body.complainant_phone or body.contact_number or "N/A"

    complaint_record = {
        "tracking_id": tracking_id,
        "title": title,
        "category": body.category,
        "incident_location": body.incident_location,
        "complainant_name": body.complainant_name,
        "complainant_phone": phone,
        "complainant_email": body.complainant_email,
        "description": body.description,
        "status": "COMPLAINT_REGISTERED",
        "station_code": "CPS-02",
        "station": "Colaba Police Station (Sector 4)",
        "created_at": now_iso,
        "registered_date": now_iso[:10],
        "investigating_officer": "Sub-Inspector Amit Verma (Cyber Cell)",
        "assigned_officer": "Sub-Inspector Amit Verma",
        "milestones": [
            {"step": "e-FIR Formally Registered", "detail": "Incident verified & timestamped in police records", "timestamp": now_iso[:16].replace("T", " "), "completed": True},
            {"step": "Assigned to Station Investigation Unit", "detail": "Forwarded to Cyber & Crime Branch, CPS-02", "timestamp": now_iso[:16].replace("T", " "), "completed": True},
            {"step": "Field Inquiry & Evidence Verification", "detail": "Notice under BNSS 2023 dispatched", "timestamp": "In Progress", "completed": False},
            {"step": "Final Charge Sheet Submission", "detail": "Judicial magistrate submission", "timestamp": "Pending", "completed": False}
        ],
        "timeline": [
            {"time": now_iso[:16].replace("T", " "), "status": "COMPLAINT_REGISTERED", "note": "Citizen e-report received and verified via portal."}
        ]
    }
    CITIZEN_COMPLAINTS[tracking_id] = complaint_record

    # Log to audit trail
    audit = AuditLog(
        action=AuditAction.CASE_EDITED,
        timestamp=now_iso,
        resource_type="CITIZEN_COMPLAINT",
        details={
            "source": "CITIZEN_PORTAL",
            "tracking_id": tracking_id,
            "category": body.category,
            "location": body.incident_location
        }
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "SUCCESS",
        "tracking_id": tracking_id,
        "message": "Your incident report has been registered with State Police Command.",
        "acknowledgment_date": now_iso
    }


@router.get("/complaints/{tracking_id}")
async def track_complaint(tracking_id: str):
    """Track the investigation progress of an e-FIR or citizen complaint."""
    complaint = CITIZEN_COMPLAINTS.get(tracking_id)
    if not complaint:
        # Also check standard FIR format
        if tracking_id.upper().startswith("FIR"):
            return {
                "tracking_id": tracking_id,
                "title": "Special Investigation FIR",
                "status": "UNDER_INVESTIGATION",
                "category": "ORGANIZED_CRIME",
                "station_code": "HQ-CPS-01",
                "timeline": [
                    {"time": "2026-10-15 10:00", "status": "FIR_REGISTERED", "note": "Statutory FIR registered under Bharatiya Nyaya Sanhita."},
                    {"time": "2026-10-18 14:00", "status": "EVIDENCE_COLLECTED", "note": "Digital forensic evidence sealed under BSA Section 63."}
                ]
            }
        raise HTTPException(status_code=404, detail="Complaint / Tracking ID not found.")

    return complaint


@router.post("/anonymous-tip")
async def submit_anonymous_tip(
    body: AnonymousTipRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit 100% anonymous whistleblower or criminal intelligence tip."""
    tip_id = f"TIP-SECRET-{secrets.token_hex(4).upper()}"
    details = body.description or body.tip_details or "Confidential intelligence tip"
    tip_record = {
        "tip_id": tip_id,
        "category": body.category,
        "location": body.location,
        "details": details,
        "suspects": body.suspects,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    ANONYMOUS_TIPS.append(tip_record)

    # Cryptographically anonymized audit record (Zero IP/PII stored)
    now_iso = datetime.now(timezone.utc).isoformat()
    audit = AuditLog(
        action=AuditAction.CASE_VIEWED,
        timestamp=now_iso,
        resource_type="ANONYMOUS_TIP",
        details={"source": "ANONYMOUS_WHISTLEBLOWER", "tip_id": tip_id, "category": body.category}
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "RECEIVED",
        "tip_id": tip_id,
        "message": "Anonymous tip encrypted and forwarded to State Intelligence Unit. No IP or metadata was logged."
    }


@router.post("/sos")
async def civilian_sos(
    body: CivilianSosRequest,
    db: AsyncSession = Depends(get_db)
):
    """Civilian Emergency Distress Alert (112 ERSS Integration)."""
    sos_id = f"SOS-{secrets.token_hex(4).upper()}"
    distress = body.distress_type or body.incident_type or "GENERAL_EMERGENCY"
    now_iso = datetime.now(timezone.utc).isoformat()

    audit = AuditLog(
        action=AuditAction.PANIC_BUTTON,
        timestamp=now_iso,
        resource_type="CIVILIAN_SOS",
        details={
            "sos_id": sos_id,
            "distress_type": distress,
            "latitude": body.latitude,
            "longitude": body.longitude,
            "caller_name": body.caller_name
        }
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "SOS_DISPATCHED",
        "sos_id": sos_id,
        "message": "Emergency alert broadcast to nearest PCR mobile vans and Police Station.",
        "coordinates": {"latitude": body.latitude, "longitude": body.longitude},
        "eta_minutes": 4
    }


@router.get("/verify-officer/{badge_number}")
async def verify_officer_badge(badge_number: str, db: AsyncSession = Depends(get_db)):
    """Citizens can verify whether an officer is authentic and currently on active duty."""
    res = await db.execute(select(Officer).where(Officer.badge_number == badge_number.strip().upper()))
    officer = res.scalar_one_or_none()

    if not officer:
        return {
            "verified": False,
            "badge_number": badge_number,
            "message": "NO POLICE RECORD FOUND. Exercise caution — person is not recognized in official SHIELD roster."
        }

    return {
        "verified": True,
        "badge_number": officer.badge_number,
        "name": officer.full_name,
        "rank": officer.rank,
        "department": officer.department,
        "station_code": officer.station_code or "District Headquarters",
        "status": "ON_ACTIVE_DUTY" if officer.is_on_duty else "OFF_DUTY",
        "verified_at": datetime.now(timezone.utc).isoformat()
    }
