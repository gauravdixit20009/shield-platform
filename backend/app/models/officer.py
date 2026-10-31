"""
SHIELD Platform — Officer & User Models
Handles all officer roles, biometrics, and device management.
"""
from sqlalchemy import Column, String, Enum, Integer, Float, Boolean, ForeignKey, Text, LargeBinary, Uuid, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class OfficerRank(str, enum.Enum):
    DGP = "DGP"                    # Director General of Police — highest
    ADGP = "ADGP"                  # Additional DGP
    IGP = "IGP"                    # Inspector General
    DIG = "DIG"                    # Deputy Inspector General
    SP = "SP"                      # Superintendent of Police
    ASP = "ASP"                    # Asst. Superintendent
    DSP = "DSP"                    # Deputy Superintendent
    INSPECTOR = "INSPECTOR"
    SI = "SI"                      # Sub-Inspector
    ASI = "ASI"                    # Asst. Sub-Inspector
    HEAD_CONSTABLE = "HEAD_CONSTABLE"
    CONSTABLE = "CONSTABLE"
    IAS = "IAS"                    # Indian Administrative Service
    IPS = "IPS"                    # Indian Police Service
    AUDITOR = "AUDITOR"            # Internal auditor — read-only
    SYSTEM_ADMIN = "SYSTEM_ADMIN"  # No case access


class Department(str, enum.Enum):
    STATE_POLICE = "STATE_POLICE"
    CBI = "CBI"
    NIA = "NIA"
    ED = "ED"               # Enforcement Directorate
    INCOME_TAX = "INCOME_TAX"
    CUSTOMS = "CUSTOMS"
    BSF = "BSF"
    CRPF = "CRPF"
    CISF = "CISF"
    NSG = "NSG"
    RAW = "RAW"             # Research and Analysis Wing
    IB = "IB"               # Intelligence Bureau


class Officer(BaseModel):
    __tablename__ = "officers"

    # Identity
    badge_number = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    rank = Column(Enum(OfficerRank), nullable=False, index=True)
    department = Column(Enum(Department), nullable=False)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    station_code = Column(String(50), nullable=True)

    # Credentials
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(15), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    totp_secret = Column(String(64), nullable=True)      # MFA TOTP secret
    is_mfa_enabled = Column(Boolean, default=True)
    webauthn_credentials = Column(JSON, default=list)   # Hardware key data

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_on_duty = Column(Boolean, default=False, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)
    suspension_reason = Column(Text, nullable=True)

    # Hierarchy
    superior_officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=True)
    superior = relationship("Officer", remote_side="Officer.id", foreign_keys=[superior_officer_id])

    # Traitor Detection Score
    threat_score = Column(Integer, default=0, nullable=False)  # 0-100
    threat_level = Column(String(20), default="LOW", nullable=False)  # LOW/MEDIUM/HIGH/CRITICAL
    last_threat_analysis = Column(String(50), nullable=True)

    # Biometrics (stored as encrypted blobs)
    face_encoding = Column(LargeBinary, nullable=True)  # Encrypted face embedding
    fingerprint_hash = Column(String(255), nullable=True)

    # Relationships
    devices = relationship("RegisteredDevice", back_populates="officer")
    cases_assigned = relationship("Case", foreign_keys="Case.assigned_officer_id", back_populates="assigned_officer")
    cases_created = relationship("Case", foreign_keys="Case.created_by_officer_id", back_populates="creating_officer")
    audit_logs = relationship("AuditLog", back_populates="officer")
    locations = relationship("OfficerLocation", back_populates="officer")
    behavior_signals = relationship("BehaviorSignal", back_populates="officer")

    def __repr__(self):
        return f"<Officer {self.badge_number} - {self.rank}>"


class RegisteredDevice(BaseModel):
    """Only whitelisted devices can access the system."""
    __tablename__ = "registered_devices"

    officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id", ondelete="CASCADE"), nullable=False)
    device_fingerprint = Column(String(512), nullable=False, index=True)
    device_name = Column(String(255), nullable=True)
    device_os = Column(String(50), nullable=True)    # Android / iOS / Web
    device_os_version = Column(String(50), nullable=True)
    push_token = Column(String(512), nullable=True)  # FCM push token
    is_trusted = Column(Boolean, default=False)      # Approved by admin
    last_seen = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)

    officer = relationship("Officer", back_populates="devices")


class OfficerLocation(BaseModel):
    """Real-time GPS track — stored during duty mode only."""
    __tablename__ = "officer_locations"

    officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    is_on_duty = Column(Boolean, default=True)
    timestamp = Column(String(50), nullable=False)   # ISO8601

    officer = relationship("Officer", back_populates="locations")
