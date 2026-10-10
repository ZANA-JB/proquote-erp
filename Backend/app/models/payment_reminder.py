"""Définit les relances de paiement liées aux cotations."""

import uuid

from sqlalchemy import Column, String, Date, DateTime, Enum, ForeignKey
from app.core.database import Base
from datetime import datetime
import enum


class ReminderStatus(enum.Enum):
    PLANIFIE = "PLANIFIE"
    ENVOYE = "ENVOYE"
    ECHEC = "ECHEC"


class PaymentReminder(Base):
    __tablename__ = "payment_reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    quotation_id = Column(String(36), ForeignKey("quotations.id"), nullable=False)
    due_date = Column(Date, nullable=False)
    sent_date = Column(DateTime, nullable=True)
    reminder_status = Column(Enum(ReminderStatus), nullable=False, default=ReminderStatus.PLANIFIE)
