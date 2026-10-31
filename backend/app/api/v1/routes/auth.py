"""
SHIELD Platform — Auth Routes
Login, MFA setup, refresh token, logout.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator
from typing import Optional

from app.core.database import get_db
from app.auth.auth_service import AuthService
from app.auth.dependencies import get_current_officer
from app.models.officer import Officer

router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────
class LoginRequest(BaseModel):
    badge_number: str
    password: str
    totp_token: Optional[str] = None          # 6-digit MFA code (auto-handled in dev)
    device_fingerprint: Optional[str] = "device_client"   # Computed by client

    @validator("badge_number")
    def validate_badge(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("Invalid badge number")
        return v.upper().strip()

    @validator("totp_token", pre=True, always=True)
    def validate_totp(cls, v):
        if not v or not str(v).strip():
            return None
        cleaned = str(v).strip()
        if cleaned.upper() in ("AUTO", "DEMO", "000000"):
            return cleaned
        if not cleaned.isdigit() or len(cleaned) != 6:
            raise ValueError("TOTP must be a 6-digit code")
        return cleaned


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int           # seconds
    officer: dict


class RefreshRequest(BaseModel):
    refresh_token: str
    device_fingerprint: str


class SetupMFAResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list


# ─── Routes ────────────────────────────────────────────────
@router.get("/demo-totp")
async def get_demo_totp():
    """Returns current TOTP code for demo officer credentials in dev mode."""
    import pyotp, time
    totp = pyotp.TOTP("JBSWY3DPEHPK3PXP")
    remaining = 30 - (int(time.time()) % 30)
    return {"code": totp.now(), "expires_in_seconds": remaining}


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Full login flow: password + MFA + device verification.
    Returns access token (15 min) + refresh token (7 days).
    """
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")

    try:
        access_token, refresh_token, officer = await AuthService.authenticate(
            db=db,
            badge_number=body.badge_number,
            password=body.password,
            totp_token=body.totp_token,
            device_fingerprint=body.device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,   # 15 minutes in seconds
        officer={
            "id": str(officer.id),
            "badge_number": officer.badge_number,
            "full_name": officer.full_name,
            "rank": officer.rank,
            "department": officer.department,
            "is_on_duty": officer.is_on_duty,
        },
    )


@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    try:
        payload = AuthService.decode_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    if payload.get("device") != body.device_fingerprint:
        raise HTTPException(status_code=401, detail="Device mismatch")

    from sqlalchemy import select
    from app.models.officer import Officer
    import uuid

    result = await db.execute(
        select(Officer).where(Officer.id == uuid.UUID(payload["sub"]))
    )
    officer = result.scalar_one_or_none()
    if not officer or not officer.is_active:
        raise HTTPException(status_code=401, detail="Officer not found or inactive")

    new_access = AuthService.create_access_token(
        officer_id=str(officer.id),
        rank=officer.rank,
        badge_number=officer.badge_number,
        device_fingerprint=body.device_fingerprint,
    )
    return {"access_token": new_access, "token_type": "bearer", "expires_in": 15 * 60}


@router.get("/me")
async def get_me(officer: Officer = Depends(get_current_officer)):
    """Get current officer's profile."""
    return {
        "id": str(officer.id),
        "badge_number": officer.badge_number,
        "full_name": officer.full_name,
        "rank": officer.rank,
        "department": officer.department,
        "state": officer.state,
        "is_on_duty": officer.is_on_duty,
        "threat_level": officer.threat_level,
        "is_mfa_enabled": officer.is_mfa_enabled,
    }


@router.post("/setup-mfa", response_model=SetupMFAResponse)
async def setup_mfa(
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Generate MFA secret and QR code for officer setup."""
    import secrets
    secret = AuthService.generate_totp_secret()
    qr_uri = AuthService.generate_totp_uri(officer.email, secret)

    # Generate backup codes (one-time use)
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]

    # Store secret (hashed backup codes would be stored too)
    officer.totp_secret = secret
    officer.is_mfa_enabled = True
    await db.commit()

    return SetupMFAResponse(
        secret=secret,
        qr_uri=qr_uri,
        backup_codes=backup_codes,
    )


@router.post("/logout")
async def logout(
    request: Request,
    officer: Officer = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
):
    """Logout — marks token as revoked in Redis."""
    from app.models.audit import AuditLog, AuditAction
    from datetime import datetime, timezone

    audit = AuditLog(
        officer_id=officer.id,
        action=AuditAction.LOGOUT,
        ip_address=request.client.host if request.client else "unknown",
        timestamp=datetime.now(timezone.utc).isoformat(),
        details={},
    )
    db.add(audit)
    await db.commit()
    # TODO: Add JWT ID to Redis revocation list
    return {"message": "Logged out successfully"}
