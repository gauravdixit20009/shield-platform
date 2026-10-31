"""
SHIELD Platform — CCTV Management Routes
Connects to secure media gateway, verifies zone authorization, and proxies feeds.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.auth.dependencies import get_current_officer, require_rank
from app.models.officer import Officer, OfficerRank
from app.services.cctv_service import CCTVService

router = APIRouter()


class AddCameraRequest(BaseModel):
    camera_name: str
    location: str
    stream_url: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    station_code: Optional[str] = None
    zone: Optional[str] = None
    has_ptz: Optional[bool] = False


@router.get("/cameras")
async def list_cameras(
    zone: Optional[str] = Query(None),
    officer: Officer = Depends(get_current_officer),
):
    """
    List CCTV cameras.
    Enforces zone permissions:
    General officers see only their jurisdiction.
    Armory & Sensitive vaults require Senior clearance (SP/DGP/IPS).
    """
    cameras = CCTVService.list_cameras(officer.rank, zone)
    return {
        "cameras": cameras,
        "total": len(cameras),
    }


@router.get("/cameras/{camera_id}/stream")
async def get_stream_token(
    camera_id: str,
    officer: Officer = Depends(get_current_officer),
):
    """
    Get ephemeral authenticated stream token (15-min TTL).
    Direct RTSP credentials are never exposed to browser or mobile apps.
    """
    try:
        token_info = CCTVService.generate_stream_token(camera_id, officer.badge_number)
        return token_info
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/cameras")
async def add_camera(
    body: AddCameraRequest,
    officer: Officer = Depends(require_rank(OfficerRank.SP)),
):
    """Add a new CCTV camera feed to the grid. SP+ only."""
    cam = CCTVService.register_camera(body.dict())
    return {
        "status": "REGISTERED",
        "camera_id": cam["id"],
        "camera_name": cam["name"],
        "message": f"Camera '{cam['name']}' securely integrated into police grid.",
    }


@router.get("/alerts")
async def get_ai_alerts(
    officer: Officer = Depends(get_current_officer),
):
    """Get AI computer vision alerts (perimeter breach, crowd spike, loitering)."""
    return {
        "alerts": CCTVService.get_vision_alerts()
    }
