"""
SHIELD Platform — Base SQLAlchemy Models
All models include audit fields and soft-delete.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class TimestampMixin:
    """Adds created_at, updated_at, deleted_at to every model."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft-delete
    is_deleted = Column(Boolean, default=False, nullable=False)


class AuditMixin:
    """Adds who created/updated/deleted a record."""
    created_by = Column(Uuid(as_uuid=True), nullable=True)
    updated_by = Column(Uuid(as_uuid=True), nullable=True)
    deleted_by = Column(Uuid(as_uuid=True), nullable=True)


class BaseModel(Base, TimestampMixin, AuditMixin):
    """Abstract base for all SHIELD models."""
    __abstract__ = True

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
