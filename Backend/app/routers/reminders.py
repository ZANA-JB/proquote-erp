"""Expose la consultation et l'envoi des relances de paiement."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_quotation_access, require_role
from app.models.payment_reminder import PaymentReminder, ReminderStatus
from app.models.quotation import Quotation, QuotationStatus
from app.models.user import UserRole
from app.schemas.pagination import PaginatedResponse
from app.schemas.payment_reminder import PaymentReminderOut
from app.services.payment_reminder_service import send_reminder_for_quotation
from app.core.config import settings

router = APIRouter()


@router.get("/quotations/{quotation_id}/reminders", response_model=PaginatedResponse[PaymentReminderOut])
def get_reminders(
    quotation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)
    query = db.query(PaymentReminder).filter(PaymentReminder.quotation_id == quotation_id)
    total = query.count()
    items = query.order_by(PaymentReminder.due_date.desc()).offset(skip).limit(limit).all()
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


@router.post("/quotations/{quotation_id}/reminders/send")
def send_reminder(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(UserRole.RESPONSABLE, UserRole.ADMIN)),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != QuotationStatus.ACCEPTEE or quotation.is_paid:
        raise HTTPException(status_code=400, detail="Quotation is not eligible for a payment reminder")

    if not settings.SMTP_HOST:
        raise HTTPException(status_code=400, detail="SMTP host is not configured; cannot send reminders")
    if not settings.MAIL_FROM:
        raise HTTPException(status_code=400, detail="Mail sender is not configured; cannot send reminders")

    reminder = send_reminder_for_quotation(db, quotation, date.today())
    if reminder is None:
        raise HTTPException(status_code=400, detail="A reminder for the current period has already been sent")

    return {"detail": "Reminder sent", "reminder_id": reminder.id}


@router.get("/reminders", response_model=PaginatedResponse[PaymentReminderOut], dependencies=[Depends(require_role(UserRole.RESPONSABLE, UserRole.ADMIN))])
def list_reminders(
    status: Optional[ReminderStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(PaymentReminder)
    if status is not None:
        query = query.filter(PaymentReminder.reminder_status == status)
    total = query.count()
    items = query.order_by(PaymentReminder.due_date.desc()).offset(skip).limit(limit).all()
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)
