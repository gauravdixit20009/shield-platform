"""
SHIELD Platform — FastAPI Dependency Injection
Handles: DB sessions, current officer extraction, role enforcement.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.core.database import get_db
from app.auth.auth_service import AuthService
from app.models.officer import Officer, OfficerRank
from app.models.audit import AuditLog, AuditAction
from app.utils.logger import logger
from datetime import datetime, timezone

bearer_scheme = HTTPBearer()

# Rank hierarchy (higher index = more senior)
RANK_HIERARCHY = [
    OfficerRank.CONSTABLE,
    OfficerRank.HEAD_CONSTABLE,
    OfficerRank.ASI,
    OfficerRank.SI,
    OfficerRank.INSPECTOR,
    OfficerRank.DSP,
    OfficerRank.ASP,
    OfficerRank.SP,
    OfficerRank.DIG,
    OfficerRank.IGP,
    OfficerRank.ADGP,
    OfficerRank.DGP,
    OfficerRank.IPS,
    OfficerRank.IAS,
    OfficerRank.AUDITOR,
    OfficerRank.SYSTEM_ADMIN,
]


async def get_current_officer(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Officer:
    """Extract and validate officer from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = AuthService.decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    officer_id = payload.get("sub")
    device_fingerprint = payload.get("device")

    if not officer_id:
        raise credentials_exception

    # Fetch officer from DB (always fresh — no stale cached data)
    result = await db.execute(
        select(Officer).where(
            Officer.id == uuid.UUID(officer_id),
            Officer.is_deleted == False,
        )
    )
    officer = result.scalar_one_or_none()

    if not officer:
        raise credentials_exception

    if not officer.is_active or officer.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated",
        )

    # Attach request metadata to officer for downstream use
    officer._request_ip = request.client.host if request.client else "unknown"
    officer._request_device = device_fingerprint

    return officer


def require_rank(minimum_rank: OfficerRank):
    """Factory dep: enforce minimum rank. Below rank → 403."""
    async def checker(officer: Officer = Depends(get_current_officer)) -> Officer:
        if officer.rank not in RANK_HIERARCHY:
            raise HTTPException(status_code=403, detail="Insufficient rank")
        officer_level = RANK_HIERARCHY.index(officer.rank)
        required_level = RANK_HIERARCHY.index(minimum_rank)
        if officer_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Minimum rank required: {minimum_rank}. Your rank: {officer.rank}",
            )
        return officer
    return checker


def require_any_rank(*ranks: OfficerRank):
    """Dep: officer must have one of the specified ranks."""
    async def checker(officer: Officer = Depends(get_current_officer)) -> Officer:
        if officer.rank not in ranks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission for this action",
            )
        return officer
    return checker


# Pre-built common dependencies
require_sp_or_above = require_rank(OfficerRank.SP)
require_dgp_or_above = require_rank(OfficerRank.DGP)
require_inspector_or_above = require_rank(OfficerRank.INSPECTOR)
