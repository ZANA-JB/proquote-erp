"""Expose les opérations API de gestion des cotations et de leurs PDF."""

from datetime import date
from typing import List, Optional

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from app.core.database import get_db
from app.core.deps import get_current_user, require_quotation_access, require_role
from app.models.article import Article
from app.models.audit_log import AuditLog
from app.models.quotation import Incoterm, Quotation, QuotationStatus
from app.models.user import UserRole
from app.schemas.article import ArticleCreate
from app.schemas.audit_log import AuditLogOut
from app.schemas.pagination import PaginatedResponse
from app.schemas.quotation import QuotationCreate, QuotationListItem, QuotationOut, QuotationUpdate
from app.services.calculation_service import calculate_line_total, calculate_quotation_total
from app.services.pdf_service import generate_pdf
from app.core.config import settings
from app.services.reference_service import generate_reference
from app.services.email_service import send_quotation_email
from app.services.status_service import change_status, StatusTransitionError
from app.schemas.quotation import StatusChangeRequest

router = APIRouter()


def _build_article(article_data: ArticleCreate, quotation_id: str) -> Article:
    return Article(
        designation=article_data.designation,
        quantity=article_data.quantity,
        unit=article_data.unit,
        unit_price=article_data.unit_price,
        line_total=calculate_line_total(article_data.quantity, article_data.unit_price),
        quotation_id=quotation_id,
    )


@router.post(
    "/",
    response_model=QuotationOut,
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def create_quotation(
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not payload.articles:
        raise HTTPException(status_code=400, detail="A quotation must have at least one article")

    quotation = Quotation(
        client_name=payload.client_name,
        client_email=payload.client_email,
        client_address=payload.client_address,
        client_reference=payload.client_reference,
        validity_date=payload.validity_date,
        delivery_duration=payload.delivery_duration,
        incoterm=payload.incoterm.strip() if payload.incoterm else None,
        special_conditions=payload.special_conditions,
        vat_mode=payload.vat_mode,
        vat_code=payload.vat_code.strip() if payload.vat_mode == "avec_tva" else None,
        vat_rate=payload.vat_rate if payload.vat_mode == "avec_tva" else None,
        payment_method=(
            payload.payment_method.strip() or None if payload.payment_method else None
        ),
        payment_terms=(
            payload.payment_terms.strip() or None if payload.payment_terms else None
        ),
        created_by=current_user.id,
    )
    db.add(quotation)
    db.flush()

    quotation.reference = generate_reference(db, creation_date=quotation.creation_date)

    articles_to_add = []
    for article_data in payload.articles:
        articles_to_add.append(_build_article(article_data, quotation.id))
        db.add(articles_to_add[-1])

    db.flush()  # Rend les articles disponibles avant le calcul du total.
    
    quotation.total_amount = calculate_quotation_total(articles_to_add)
    db.add(quotation)

    audit = AuditLog(
        user_id=current_user.id,
        action="quotation.created",
        entity_type="Quotation",
        entity_id=quotation.id,
        details={
            "reference": quotation.reference,
            "client_name": quotation.client_name,
            "total_amount": float(quotation.total_amount),
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(quotation)
    return quotation


@router.get(
    "/",
    response_model=PaginatedResponse[QuotationListItem],
    dependencies=[Depends(get_current_user)],
)
def list_quotations(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=500),
    reference: Optional[str] = Query(None, max_length=100),
    client_name: Optional[str] = Query(None, max_length=250),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Quotation)

    if current_user.role == UserRole.COLLABORATEUR:
        query = query.filter(Quotation.created_by == current_user.id)

    if reference:
        # Recherche partielle et insensible à la casse sur la référence.
        query = query.filter(Quotation.reference.ilike(f"%{reference}%"))
    if client_name:
        query = query.filter(Quotation.client_name.ilike(f"%{client_name}%"))
    if status:
        try:
            query = query.filter(Quotation.status == QuotationStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if date_from:
        query = query.filter(Quotation.creation_date >= date_from)
    if date_to:
        query = query.filter(Quotation.creation_date <= date_to)

    total = query.count()
    items = query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()

    for quotation in items:
        if not quotation.reference:
            quotation.reference = generate_reference(db, creation_date=quotation.creation_date)
            db.add(quotation)
    if any(not item.reference for item in items):
        db.commit()

    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


@router.get("/{quotation_id}", response_model=QuotationOut, dependencies=[Depends(get_current_user)])
def get_quotation(quotation_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)
    return quotation


@router.get("/{quotation_id}/history", response_model=List[AuditLogOut], dependencies=[Depends(get_current_user)])
def get_quotation_history(quotation_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)
    # Récupère l'historique de la cotation et de ses articles.
    query = db.query(AuditLog).filter(
        (
            AuditLog.entity_type.ilike("quotation")
            & (AuditLog.entity_id == quotation_id)
        )
        | (
            AuditLog.entity_type.ilike("article")
            & AuditLog.details.contains({"quotation_id": quotation_id})
        )
    )
    results = query.order_by(AuditLog.created_at.desc()).all()
    return results


@router.put(
    "/{quotation_id}",
    response_model=QuotationOut,
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def update_quotation(
    quotation_id: str,
    payload: QuotationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    if payload.client_name is not None:
        quotation.client_name = payload.client_name
    if payload.client_email is not None:
        quotation.client_email = payload.client_email
    if payload.client_address is not None:
        quotation.client_address = payload.client_address
    if payload.client_reference is not None:
        quotation.client_reference = payload.client_reference
    if payload.validity_date is not None:
        quotation.validity_date = payload.validity_date
    if payload.delivery_duration is not None:
        quotation.delivery_duration = payload.delivery_duration
    if payload.incoterm is not None:
        quotation.incoterm = payload.incoterm.strip() or None
    if payload.special_conditions is not None:
        quotation.special_conditions = payload.special_conditions
    if payload.vat_mode == "sans_tva":
        quotation.vat_mode = "sans_tva"
        quotation.vat_code = None
        quotation.vat_rate = None
    elif payload.vat_mode == "avec_tva":
        quotation.vat_mode = "avec_tva"
        quotation.vat_code = payload.vat_code
        quotation.vat_rate = payload.vat_rate
    elif payload.vat_code is not None or payload.vat_rate is not None:
        if quotation.vat_mode != "avec_tva":
            raise HTTPException(
                status_code=422,
                detail="Set vat_mode to avec_tva before updating VAT code or rate",
            )
        quotation.vat_code = payload.vat_code
        quotation.vat_rate = payload.vat_rate
    if "payment_method" in payload.model_fields_set:
        quotation.payment_method = (
            payload.payment_method.strip() or None if payload.payment_method else None
        )
    if "payment_terms" in payload.model_fields_set:
        quotation.payment_terms = (
            payload.payment_terms.strip() or None if payload.payment_terms else None
        )

    if quotation.vat_mode == "avec_tva" and (not quotation.vat_code or quotation.vat_rate is None):
        raise HTTPException(
            status_code=422,
            detail="A VAT code and rate are required when VAT applies",
        )

    if payload.articles is not None:
        if not payload.articles:
            raise HTTPException(status_code=400, detail="A quotation must have at least one article")
        for article in list(quotation.articles):
            db.delete(article)
        quotation.articles = []
        db.flush()
        for article_data in payload.articles:
            quotation.articles.append(_build_article(article_data, quotation.id))

    quotation.total_amount = calculate_quotation_total(quotation.articles)
    db.add(quotation)

    audit = AuditLog(
        user_id=current_user.id,
        action="quotation.updated",
        entity_type="Quotation",
        entity_id=quotation.id,
        details={"reference": quotation.reference, "total_amount": float(quotation.total_amount)},
    )
    db.add(audit)
    db.commit()
    db.refresh(quotation)
    return quotation


@router.delete(
    "/{quotation_id}",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    db.delete(quotation)
    audit = AuditLog(
        user_id=current_user.id,
        action="quotation.deleted",
        entity_type="Quotation",
        entity_id=quotation.id,
        details={"reference": quotation.reference},
    )
    db.add(audit)
    db.commit()
    return {"detail": "Quotation deleted"}


@router.post(
    "/{quotation_id}/generate-pdf",
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def generate_quotation_pdf(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    pdf_path = generate_pdf(quotation)
    audit = AuditLog(
        user_id=current_user.id,
        action="quotation.pdf_generated",
        entity_type="Quotation",
        entity_id=quotation.id,
        details={
            "reference": quotation.reference,
            "pdf_path": pdf_path,
        },
    )
    db.add(audit)
    db.commit()
    return {"detail": "PDF generated", "pdf_path": pdf_path}


@router.post(
    "/{quotation_id}/send",
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def send_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    pdf_path = generate_pdf(quotation)

    # Vérifie explicitement la configuration SMTP et renvoie une erreur claire.
    if not settings.SMTP_HOST:
        raise HTTPException(status_code=400, detail="SMTP host is not configured; set SMTP_HOST in environment")
    if not settings.MAIL_FROM:
        raise HTTPException(status_code=400, detail="Mail sender is not configured; set MAIL_FROM in environment")

    sent = send_quotation_email(quotation, pdf_path)

    audit = AuditLog(
        user_id=current_user.id,
        action="quotation.sent",
        entity_type="Quotation",
        entity_id=quotation.id,
        details={
            "reference": quotation.reference,
            "success": sent,
            "pdf_path": pdf_path,
        },
    )
    db.add(audit)
    db.commit()

    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send quotation email")

    try:
        # Marque la cotation comme envoyée après confirmation de la règle métier.
        updated = change_status(quotation, QuotationStatus.ENVOYEE, db, email_sent=True)
    except StatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"detail": "Email sent and status updated to ENVOYEE", "quotation": updated}


@router.get("/{quotation_id}/pdf", dependencies=[Depends(get_current_user)])
def get_quotation_pdf(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    path = generate_pdf(quotation)

    return FileResponse(path, media_type="application/pdf", filename=os.path.basename(path))


@router.patch(
    "/{quotation_id}/status",
    response_model=QuotationOut,
    dependencies=[Depends(require_role(UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def patch_quotation_status(
    quotation_id: str,
    payload: StatusChangeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    # Empêche de forcer ENVOYEE ou EXPIREE via cet endpoint.
    if payload.new_status in (QuotationStatus.ENVOYEE, QuotationStatus.EXPIREE):
        raise HTTPException(status_code=400, detail="This transition cannot be performed via this endpoint")

    if quotation.status == payload.new_status:
        return quotation

    try:
        updated = change_status(quotation, payload.new_status, db)
    except StatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    audit = AuditLog(
        user_id=current_user.id,
        action="quotation.status_changed",
        entity_type="Quotation",
        entity_id=quotation.id,
        details={
            "reference": quotation.reference,
            "new_status": updated.status.value,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(updated)
    return updated
