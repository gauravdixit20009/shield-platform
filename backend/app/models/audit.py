"""
SHIELD Platform — Audit & Threat Detection Models
Immutable logs + behavioral signals for traitor detection.
"""
from sqlalchemy import Column, String, Enum, Integer, Float, Boolean, ForeignKey, Text, Uuid, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class AuditAction(str, enum.Enum):
    # Auth
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    MFA_BYPASS_ATTEMPT = "MFA_BYPASS_ATTEMPT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    # Case
    CASE_VIEWED = "CASE_VIEWED"
    CASE_EDITED = "CASE_EDITED"
    CASE_TRANSFERRED = "CASE_TRANSFERRED"
    CASE_EXPORTED = "CASE_EXPORTED"
    CASE_PRINTED = "CASE_PRINTED"
    CASE_DELETED_ATTEMPT = "CASE_DELETED_ATTEMPT"
    # Evidence
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    EVIDENCE_DOWNLOADED = "EVIDENCE_DOWNLOADED"
    EVIDENCE_VIEWED = "EVIDENCE_VIEWED"
    # Admin
    OFFICER_SUSPENDED = "OFFICER_SUSPENDED"
    OFFICER_CREATED = "OFFICER_CREATED"
    PERMISSIONS_CHANGED = "PERMISSIONS_CHANGED"
    # Duty
    DUTY_START = "DUTY_START"
    DUTY_END = "DUTY_END"
    PANIC_BUTTON = "PANIC_BUTTON"
    # Security
    UNAUTHORIZED_ACCESS_ATTEMPT = "UNAUTHORIZED_ACCESS_ATTEMPT"
    BULK_DOWNLOAD_ATTEMPT = "BULK_DOWNLOAD_ATTEMPT"
    SCREENSHOT_ATTEMPT = "SCREENSHOT_ATTEMPT"
    VPN_DETECTED = "VPN_DETECTED"


class AuditLog(BaseModel):
    """
    Immutable audit log. This table has NO UPDATE / DELETE permissions at DB level.
    Enforced via PostgreSQL trigger: DENY UPDATE DELETE ON audit_logs.
    """
    __tablename__ = "audit_logs"

    officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)   # case | evidence | officer
    resource_id = Column(Uuid(as_uuid=True), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    device_fingerprint = Column(String(512), nullable=True)
    user_agent = Column(String(512), nullable=True)
    geo_location = Column(JSON, nullable=True)          # From IP geolocation
    timestamp = Column(String(50), nullable=False, index=True)
    is_anomalous = Column(Boolean, default=False, index=True)
    anomaly_score = Column(Float, nullable=True)
    anomaly_reason = Column(Text, nullable=True)

    officer = relationship("Officer", back_populates="audit_logs")


class BehaviorSignalType(str, enum.Enum):
    OFF_HOURS_ACCESS = "OFF_HOURS_ACCESS"
    UNUSUAL_CASE_ACCESS = "UNUSUAL_CASE_ACCESS"
    BULK_DOWNLOAD = "BULK_DOWNLOAD"
    LOCATION_SPOOF_SUSPECT = "LOCATION_SPOOF_SUSPECT"
    VPN_USAGE = "VPN_USAGE"
    FAILED_AUTH_SPIKE = "FAILED_AUTH_SPIKE"
    CASE_TAMPERING = "CASE_TAMPERING"
    EVIDENCE_DELETION_ATTEMPT = "EVIDENCE_DELETION_ATTEMPT"
    UNUSUAL_COMMUNICATION = "UNUSUAL_COMMUNICATION"
    PEER_BEHAVIOR_DEVIATION = "PEER_BEHAVIOR_DEVIATION"
    GEOGRAPHIC_ANOMALY = "GEOGRAPHIC_ANOMALY"
    CREDENTIAL_SHARING_SUSPECT = "CREDENTIAL_SHARING_SUSPECT"


class BehaviorSignal(BaseModel):
    """
    Raw behavioral signals for the traitor detection engine.
    Aggregated hourly to update officer threat_score.
    """
    __tablename__ = "behavior_signals"

    officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_type = Column(Enum(BehaviorSignalType), nullable=False)
    severity = Column(Integer, default=1)                # 1-10
    score_contribution = Column(Integer, default=0)      # Added to threat score
    details = Column(JSON, default=dict)
    timestamp = Column(String(50), nullable=False, index=True)
    is_processed = Column(Boolean, default=False)
    reviewed_by_id = Column(Uuid(as_uuid=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    is_false_positive = Column(Boolean, default=False)

    officer = relationship("Officer", back_populates="behavior_signals")


class ThreatReport(BaseModel):
    """Full threat report generated when officer crosses threshold."""
    __tablename__ = "threat_reports"

    officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=False)
    threat_level = Column(String(20), nullable=False)    # MEDIUM/HIGH/CRITICAL
    threat_score = Column(Integer, nullable=False)
    signals_summary = Column(JSON, default=dict)        # AI narrative
    ai_analysis = Column(Text, nullable=True)            # ARIA generated
    recommended_action = Column(Text, nullable=True)
    is_reviewed = Column(Boolean, default=False)
    reviewed_by_id = Column(Uuid(as_uuid=True), nullable=True)
    action_taken = Column(Text, nullable=True)
    is_escalated = Column(Boolean, default=False)
    escalated_to = Column(String(100), nullable=True)    # IB / CBI etc.
