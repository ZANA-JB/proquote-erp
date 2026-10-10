"""Définit les cotations, leurs statuts et leurs relations persistées."""

import uuid

from sqlalchemy import Column, String, Date, Enum, ForeignKey, Numeric, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from datetime import date, datetime


class QuotationStatus(enum.Enum):
    BROUILLON = "BROUILLON"
    ENVOYEE = "ENVOYEE"
    ACCEPTEE = "ACCEPTEE"
    REFUSEE = "REFUSEE"
    EXPIREE = "EXPIREE"


class Incoterm(enum.Enum):
    CLIENT = "CLIENT"
    ENI = "ENI"


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    reference = Column(String, unique=True, index=True, nullable=True)
    client_name = Column(String, nullable=False, index=True)
    client_email = Column(String, nullable=False)
    client_address = Column(String, nullable=True)
    client_reference = Column(String, nullable=True)
    creation_date = Column(Date, default=date.today, nullable=False, index=True)
    validity_date = Column(Date, nullable=True)
    delivery_duration = Column(String, nullable=True)
    incoterm = Column(String, nullable=True)
    special_conditions = Column(Text, nullable=True)
    status = Column(Enum(QuotationStatus), nullable=False, default=QuotationStatus.BROUILLON, index=True)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    is_paid = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    articles = relationship("Article", back_populates="quotation", cascade="all, delete-orphan")

    @property
    def purchase_indicator(self) -> str:
        return "VERT" if self.status == QuotationStatus.ACCEPTEE else "ROUGE"
