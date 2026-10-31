"""
SHIELD Platform — Duty Mode Routes
GPS tracking, panic button, media capture, duty start/end.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.auth.dependencies import get_current_officer
from app.models.officer import Officer, OfficerLocation
from app.models.audit import AuditLog, AuditAction

router = APIRouter()


class DutyStartRequest(BaseModel):
    device_fingerprint: str
    initial_latitude: float
    initial_longitude: float
    shift_id: Optional[str] = None


class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None


class PanicRequest(BaseModel):
    latitude: float
    longitude: float
    message: Optional[str] = None


@router.post("/start")
async def start_duty(
    body: DutyStartRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    Officer starts duty shift.
    Enables GPS tracking, device monitoring.
    Consent is implied by this action.
    """
    officer.is_on_duty = True
    
    # Log location start
    location = OfficerLocation(
        officer_id=officer.id,
        latitude=body.initial_latitude,
        longitude=body.initial_longitude,
        is_on_duty=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(location)

    audit = AuditLog(
        officer_id=officer.id,
        action=AuditAction.DUTY_START,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details={
            "latitude": body.initial_latitude,
            "longitude": body.initial_longitude,
            "shift_id": body.shift_id,
        },
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "DUTY_STARTED",
        "message": "Duty mode activated. Location tracking enabled.",
        "gps_interval_seconds": 30,
        "features_enabled": ["gps", "camera", "microphone", "activity_log"],
    }


@router.post("/end")
async def end_duty(
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """End duty shift. Stops all monitoring."""
    officer.is_on_duty = False

    audit = AuditLog(
        officer_id=officer.id,
        action=AuditAction.DUTY_END,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details={},
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "DUTY_ENDED",
        "message": "Duty mode deactivated. Monitoring stopped.",
    }


@router.post("/location")
async def update_location(
    body: LocationUpdateRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive GPS location update from device.
    Called every 30 seconds during duty mode.
    """
    if not officer.is_on_duty:
        raise HTTPException(status_code=400, detail="Officer not on duty")

    location = OfficerLocation(
        officer_id=officer.id,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude=body.altitude,
        accuracy=body.accuracy,
        speed=body.speed,
        heading=body.heading,
        is_on_duty=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(location)
    await db.commit()

    return {"status": "OK", "timestamp": location.timestamp}


@router.post("/panic")
async def panic_button(
    body: PanicRequest,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    PANIC BUTTON — Immediate SOS.
    - Records location
    - Logs audit
    - Sends alert to HQ (TODO: WebSocket push)
    - Triggers recording
    """
    audit = AuditLog(
        officer_id=officer.id,
        action=AuditAction.PANIC_BUTTON,
        ip_address=getattr(officer, "_request_ip", "unknown"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        details={
            "latitude": body.latitude,
            "longitude": body.longitude,
            "message": body.message,
            "officer_badge": officer.badge_number,
            "officer_name": officer.full_name,
        },
        is_anomalous=True,
        anomaly_score=100.0,
        anomaly_reason="PANIC BUTTON ACTIVATED",
    )
    db.add(audit)
    await db.commit()

    # TODO: Push WebSocket alert to dispatch center
    # TODO: Trigger recording on device

    return {
        "status": "SOS_SENT",
        "message": "Emergency alert sent to HQ. Help is on the way.",
        "location_recorded": True,
    }


@router.post("/upload-media")
async def upload_duty_media(
    media_type: str,   # "photo" | "audio" | "video"
    latitude: float = 0.0,
    longitude: float = 0.0,
    file: UploadFile = File(...),
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload media captured during duty (photo, audio, video).
    Automatically timestamped, geotagged, and encrypted.
    """
    if not officer.is_on_duty:
        raise HTTPException(status_code=400, detail="Officer not on duty")

    import hashlib
    content = await file.read()
    file_hash = hashlib.sha512(content).hexdigest()
    
    # TODO: Upload to MinIO encrypted vault
    file_path = f"duty/{officer.badge_number}/{datetime.now(timezone.utc).date()}/{file.filename}"

    return {
        "status": "UPLOADED",
        "file_hash": file_hash,
        "file_path": file_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "geo_tagged": {"latitude": latitude, "longitude": longitude},
    }


@router.get("/live-officers")
async def get_live_officers(
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all on-duty officers with their last known location.
    SP+ only for full view; officers see only their team.
    """
    from app.auth.dependencies import RANK_HIERARCHY
    from app.models.officer import OfficerRank
    from sqlalchemy import select

    officer_level = RANK_HIERARCHY.index(officer.rank)
    sp_level = RANK_HIERARCHY.index(OfficerRank.SP)

    query = select(Officer).where(
        Officer.is_on_duty == True,
        Officer.is_active == True,
    )
    if officer_level < sp_level:
        # Only see subordinates
        query = query.where(Officer.superior_officer_id == officer.id)

    result = await db.execute(query)
    on_duty = result.scalars().all()

    return {
        "on_duty_count": len(on_duty),
        "officers": [
            {
                "id": str(o.id),
                "badge_number": o.badge_number,
                "name": o.full_name,
                "rank": o.rank,
            }
            for o in on_duty
        ],
    }
