"""Applique les transitions de statut autorisées par le processus métier."""

import os
from typing import Optional

from sqlalchemy.orm import Session

from app.models.quotation import Quotation, QuotationStatus
from app.services.pdf_service import get_pdf_path


class StatusTransitionError(Exception):
    """Signale une transition de statut interdite."""


_ALLOWED_TRANSITIONS = {
    QuotationStatus.BROUILLON: [QuotationStatus.ENVOYEE],
    QuotationStatus.ENVOYEE: [QuotationStatus.ACCEPTEE, QuotationStatus.REFUSEE, QuotationStatus.EXPIREE],
    QuotationStatus.ACCEPTEE: [],
    QuotationStatus.REFUSEE: [],
    QuotationStatus.EXPIREE: [],
}


def change_status(quotation: Quotation, new_status: QuotationStatus, db: Session, *, email_sent: bool = False) -> Quotation:
    current = quotation.status
    if current == new_status:
        return quotation

    allowed = _ALLOWED_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise StatusTransitionError(f"Transition from {current.value} to {new_status.value} is not allowed")

    # Une cotation est validée uniquement lorsqu'elle passe explicitement à ACCEPTEE.
    # Sa création ou son envoi par email ne suffit pas à la considérer comme validée.
    if current == QuotationStatus.BROUILLON and new_status == QuotationStatus.ENVOYEE:
        pdf_path = get_pdf_path(quotation.reference)
        if not os.path.exists(pdf_path):
            raise StatusTransitionError("Cannot mark as ENVOYEE: PDF file not found")
        if not email_sent:
            raise StatusTransitionError("Cannot mark as ENVOYEE: email send confirmation required")

    quotation.status = new_status
    db.add(quotation)
    db.commit()
    db.refresh(quotation)
    return quotation
