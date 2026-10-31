"""
SHIELD Platform — Officers & CCTV stub routes
"""
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_officer, require_sp_or_above
from app.models.officer import Officer

# Officers router
router = APIRouter()

@router.get("/")
async def list_officers(officer: Officer = Depends(require_sp_or_above)):
    """List officers under this supervisor's command."""
    return {"message": "Officers list — implement full pagination here"}

@router.get("/{officer_id}")
async def get_officer(officer_id: str, officer: Officer = Depends(get_current_officer)):
    return {"message": f"Officer profile {officer_id}"}
