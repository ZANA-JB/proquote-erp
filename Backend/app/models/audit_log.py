"""Définit la journalisation des actions réalisées dans le système."""

import uuid

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey
from app.core.database import Base
from datetime import datetime
import enum


class AuditAction(enum.Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    SENT = "sent"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String(36), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
