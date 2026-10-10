"""Définit les demandes d'accès et leurs états de traitement."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, String

from app.core.database import Base
from app.schemas.access_request import AccessProfile


class AccessRequestStatus(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    ACCEPTEE = "ACCEPTEE"
    REFUSEE = "REFUSEE"


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    nomComplet = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    password_hash = Column("motDePasse", String, nullable=False)
    profilSouhaite = Column(SAEnum(AccessProfile, native_enum=False), nullable=False)
    status = Column(SAEnum(AccessRequestStatus, native_enum=False), nullable=False, default=AccessRequestStatus.EN_ATTENTE, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
