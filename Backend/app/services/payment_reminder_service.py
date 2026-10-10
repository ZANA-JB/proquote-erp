"""Calcule et enregistre les relances liées aux cotations acceptées."""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.payment_reminder import PaymentReminder, ReminderStatus
from app.models.quotation import Quotation, QuotationStatus
from app.models.audit_log import AuditLog
from app.services.email_service import send_payment_reminder_email


def _get_next_due_date(quotation: Quotation, today: date) -> date:
    expiration = quotation.validity_date
    if expiration is None:
        raise ValueError("Quotation does not have a validity date")

    delta = today - expiration
    if delta.days < 7:
        raise ValueError("Quotation is not yet eligible for a payment reminder")

    full_weeks = delta.days // 7
    return expiration + timedelta(days=full_weeks * 7)


def _reminder_period_exists(db: Session, quotation_id: str, due_date: date) -> bool:
    return (
        db.query(PaymentReminder)
        .filter(PaymentReminder.quotation_id == quotation_id)
        .filter(PaymentReminder.due_date == due_date)
        .filter(PaymentReminder.reminder_status == ReminderStatus.ENVOYE)
        .count()
        > 0
    )


def send_reminder_for_quotation(db: Session, quotation: Quotation, today: date) -> Optional[PaymentReminder]:
    due_date = _get_next_due_date(quotation, today)

    if _reminder_period_exists(db, quotation.id, due_date):
        return None

    reminder = PaymentReminder(
        quotation_id=quotation.id,
        due_date=due_date,
        reminder_status=ReminderStatus.PLANIFIE,
    )
    db.add(reminder)
    db.flush()

    email_ok = send_payment_reminder_email(quotation, reminder)
    reminder.sent_date = datetime.utcnow()
    reminder.reminder_status = ReminderStatus.ENVOYE if email_ok else ReminderStatus.ECHEC
    db.add(reminder)

    audit = AuditLog(
        user_id=quotation.created_by,
        action="payment_reminder.sent" if email_ok else "payment_reminder.failed",
        entity_type="PaymentReminder",
        entity_id=reminder.id,
        details={
            "quotation_id": quotation.id,
            "due_date": due_date.isoformat(),
            "status": reminder.reminder_status.value,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(reminder)
    return reminder


def get_due_quotations(db: Session, today: date):
    threshold = today - timedelta(days=7)
    return (
        db.query(Quotation)
        .filter(Quotation.status == QuotationStatus.ACCEPTEE)
        .filter(Quotation.is_paid == False)
        .filter(Quotation.validity_date != None)
        .filter(Quotation.validity_date <= threshold)
        .all()
    )
