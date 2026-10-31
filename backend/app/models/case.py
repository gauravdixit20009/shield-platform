"""
SHIELD Platform — Case Management Models
Full case lifecycle with zero-loophole access control.
"""
from sqlalchemy import Column, String, Enum, Integer, Float, Boolean, ForeignKey, Text, LargeBinary, Uuid, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class CasePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"    # Terrorism, kidnapping, etc.
    TOP_SECRET = "TOP_SECRET"  # National security


class CaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    AWAITING_COURT = "AWAITING_COURT"
    TRANSFERRED = "TRANSFERRED"
    CLOSED_SOLVED = "CLOSED_SOLVED"
    CLOSED_UNSOLVED = "CLOSED_UNSOLVED"
    ARCHIVED = "ARCHIVED"


class CrimeCategory(str, enum.Enum):
    MURDER = "MURDER"
    RAPE = "RAPE"
    KIDNAPPING = "KIDNAPPING"
    ROBBERY = "ROBBERY"
    THEFT = "THEFT"
    FRAUD = "FRAUD"
    CYBERCRIME = "CYBERCRIME"
    TERRORISM = "TERRORISM"
    DRUG_TRAFFICKING = "DRUG_TRAFFICKING"
    CORRUPTION = "CORRUPTION"
    MONEY_LAUNDERING = "MONEY_LAUNDERING"
    DOMESTIC_VIOLENCE = "DOMESTIC_VIOLENCE"
    ORGANIZED_CRIME = "ORGANIZED_CRIME"
    HUMAN_TRAFFICKING = "HUMAN_TRAFFICKING"
    OTHER = "OTHER"


class Case(BaseModel):
    """
    Core case model. Row-Level Security (RLS) enforced at DB level.
    Policy: assigned_officer_id = current_user OR creating_officer_id superior_chain.
    """
    __tablename__ = "cases"

    # Identification
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    fir_number = Column(String(50), nullable=True)          # First Information Report #
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)               # Encrypted at field level

    # Classification
    category = Column(Enum(CrimeCategory), nullable=False)
    priority = Column(Enum(CasePriority), default=CasePriority.MEDIUM, nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.OPEN, nullable=False)
    is_sensitive = Column(Boolean, default=False)           # Extra access restrictions

    # Incident Details
    incident_date = Column(String(50), nullable=True)       # ISO8601
    incident_location = Column(String(500), nullable=True)
    incident_latitude = Column(Float, nullable=True)
    incident_longitude = Column(Float, nullable=True)
    jurisdiction_state = Column(String(100), nullable=True)
    jurisdiction_district = Column(String(100), nullable=True)
    police_station = Column(String(200), nullable=True)

    # Access Control (The Core of Zero-Loophole Design)
    assigned_officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=False)
    created_by_officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=False)
    department = Column(String(100), nullable=False)
    access_level_required = Column(Integer, default=1)      # Minimum rank level needed

    # AI Analysis
    ai_summary = Column(Text, nullable=True)               # ARIA generated
    ai_risk_score = Column(Float, nullable=True)
    ai_tags = Column(JSON, default=list)
    ai_connections = Column(JSON, default=dict)           # Links to other cases

    # Court Information
    court_name = Column(String(255), nullable=True)
    court_case_number = Column(String(100), nullable=True)
    next_hearing_date = Column(String(50), nullable=True)
    judge_name = Column(String(255), nullable=True)

    # Closure
    closure_reason = Column(Text, nullable=True)
    closure_date = Column(String(50), nullable=True)
    final_report_id = Column(Uuid(as_uuid=True), nullable=True)

    # Relationships
    assigned_officer = relationship("Officer", foreign_keys=[assigned_officer_id], back_populates="cases_assigned")
    creating_officer = relationship("Officer", foreign_keys=[created_by_officer_id], back_populates="cases_created")
    suspects = relationship("Suspect", back_populates="case")
    victims = relationship("Victim", back_populates="case")
    evidence = relationship("Evidence", back_populates="case")
    reports = relationship("CaseReport", back_populates="case")
    transfer_history = relationship("CaseTransfer", back_populates="case")
    activity_logs = relationship("CaseActivityLog", back_populates="case")


class Suspect(BaseModel):
    __tablename__ = "suspects"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    aliases = Column(JSON, default=list)
    date_of_birth = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)
    nationality = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    phone_numbers = Column(JSON, default=list)
    email_addresses = Column(JSON, default=list)
    aadhar_number = Column(String(20), nullable=True)  # Encrypted
    pan_number = Column(String(20), nullable=True)     # Encrypted
    passport_number = Column(String(20), nullable=True)
    photo_url = Column(String(512), nullable=True)
    face_encoding = Column(LargeBinary, nullable=True) # AI face embedding
    criminal_history = Column(JSON, default=list)
    is_arrested = Column(Boolean, default=False)
    is_chargesheeted = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    case = relationship("Case", back_populates="suspects")


class Victim(BaseModel):
    __tablename__ = "victims"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)
    phone = Column(String(15), nullable=True)
    address = Column(Text, nullable=True)
    statement = Column(Text, nullable=True)         # Encrypted
    is_witness = Column(Boolean, default=False)
    is_protected = Column(Boolean, default=False)   # Witness protection
    notes = Column(Text, nullable=True)

    case = relationship("Case", back_populates="victims")


class EvidenceType(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    PHOTOGRAPH = "PHOTOGRAPH"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FORENSIC_REPORT = "FORENSIC_REPORT"
    DIGITAL = "DIGITAL"       # Digital forensics
    PHYSICAL = "PHYSICAL"     # Tagged physical item
    WITNESS_STATEMENT = "WITNESS_STATEMENT"
    CCTV_FOOTAGE = "CCTV_FOOTAGE"
    CALL_RECORDS = "CALL_RECORDS"
    BANK_RECORDS = "BANK_RECORDS"
    OTHER = "OTHER"


class Evidence(BaseModel):
    """
    Every piece of evidence has chain-of-custody tracking.
    Files stored in encrypted MinIO vault.
    """
    __tablename__ = "evidence"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    evidence_number = Column(String(100), nullable=False)    # Unique per case
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    evidence_type = Column(Enum(EvidenceType), nullable=False)

    # Storage
    file_path = Column(String(1024), nullable=True)         # MinIO path
    file_hash = Column(String(128), nullable=True)          # SHA-512 for tamper detection
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    is_encrypted = Column(Boolean, default=True)

    # Chain of Custody
    collected_by_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=True)
    collected_at = Column(String(50), nullable=True)       # ISO8601
    collection_location = Column(String(500), nullable=True)
    custody_chain = Column(JSON, default=list)            # Array of transfers

    # AI Analysis
    ai_analysis = Column(Text, nullable=True)
    ai_tags = Column(JSON, default=list)

    case = relationship("Case", back_populates="evidence")


class CaseTransfer(BaseModel):
    """Records every case transfer — requires 2-officer approval."""
    __tablename__ = "case_transfers"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    from_officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=False)
    to_officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=False)
    approved_by_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=True)
    transfer_reason = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=False)
    approved_at = Column(String(50), nullable=True)

    case = relationship("Case", back_populates="transfer_history")


class CaseActivityLog(BaseModel):
    """Immutable activity log for every case action."""
    __tablename__ = "case_activity_logs"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    officer_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=False)
    action = Column(String(100), nullable=False)      # view | edit | add_evidence | etc.
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    device_fingerprint = Column(String(512), nullable=True)
    timestamp = Column(String(50), nullable=False)    # ISO8601

    case = relationship("Case", back_populates="activity_logs")


class CaseReport(BaseModel):
    __tablename__ = "case_reports"

    case_id = Column(Uuid(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    title = Column(String(500), nullable=False)
    report_type = Column(String(100), nullable=False)  # progress | final | court
    content = Column(Text, nullable=True)
    file_path = Column(String(1024), nullable=True)
    submitted_by_id = Column(Uuid(as_uuid=True), ForeignKey("officers.id"), nullable=True)
    is_watermarked = Column(Boolean, default=True)

    case = relationship("Case", back_populates="reports")
