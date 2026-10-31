"""
SHIELD Platform — API v1 Router
All routes organized by domain.
"""
from fastapi import APIRouter
from app.api.v1.routes import auth, cases, officers, ai, duty, admin, cctv, citizen, interagency

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(officers.router, prefix="/officers", tags=["Officers"])
router.include_router(cases.router, prefix="/cases", tags=["Cases"])
router.include_router(ai.router, prefix="/ai", tags=["ARIA AI"])
router.include_router(duty.router, prefix="/duty", tags=["Duty Mode"])
router.include_router(admin.router, prefix="/admin", tags=["Admin / CMS"])
router.include_router(cctv.router, prefix="/cctv", tags=["CCTV Management"])
router.include_router(citizen.router, prefix="/citizen", tags=["Citizen Public Safety"])
router.include_router(interagency.router, prefix="/interagency", tags=["Inter-Agency Grid"])
