"""Calcule les indicateurs depuis les données réelles de la base."""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date

from app.models.quotation import Quotation, QuotationStatus
from app.schemas.dashboard import DashboardSummary, ChartDataPoint


def get_summary(db: Session, user_id: Optional[str] = None, role: Optional[str] = None) -> DashboardSummary:
    if user_id and role == 'COLLABORATEUR':
        total = db.query(func.count(Quotation.id)).filter(Quotation.created_by == user_id).scalar() or 0
    else:
        total = db.query(func.count(Quotation.id)).scalar() or 0

    def count_status(status: QuotationStatus):
        if user_id and role == 'COLLABORATEUR':
            return (
                db.query(func.count(Quotation.id)).filter(Quotation.status == status, Quotation.created_by == user_id).scalar() or 0
            )
        return db.query(func.count(Quotation.id)).filter(Quotation.status == status).scalar() or 0

    sent = count_status(QuotationStatus.ENVOYEE)
    accepted = count_status(QuotationStatus.ACCEPTEE)
    refused = count_status(QuotationStatus.REFUSEE)
    expired = count_status(QuotationStatus.EXPIREE)
    draft = count_status(QuotationStatus.BROUILLON)

    if user_id and role == 'COLLABORATEUR':
        total_amount = db.query(func.coalesce(func.sum(Quotation.total_amount), 0)).filter(Quotation.created_by == user_id).scalar() or 0
    else:
        total_amount = db.query(func.coalesce(func.sum(Quotation.total_amount), 0)).scalar() or 0

    issued = sent + accepted + refused + expired
    if issued > 0:
        conversion_rate = accepted / issued
    else:
        conversion_rate = 0.0

    return DashboardSummary(
        total_quotations=int(total),
        sent_count=int(sent),
        accepted_count=int(accepted),
        refused_count=int(refused),
        expired_count=int(expired),
        draft_count=int(draft),
        total_amount=float(total_amount),
        conversion_rate=float(conversion_rate),
    )


def _get_month_label_expr(db: Session):
    dialect_name = db.bind.dialect.name if db.bind is not None else "sqlite"
    if dialect_name == 'postgresql':
        return func.date_trunc('month', Quotation.creation_date)
    return func.strftime('%Y-%m', Quotation.creation_date)


def get_chart_data(db: Session, chart_type: str, user_id: Optional[str] = None, role: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[ChartDataPoint]:
    results: List[ChartDataPoint] = []
    # by_month : compte les cotations par année et par mois.
    if chart_type == 'by_month':
        label_expr = _get_month_label_expr(db)
        q = db.query(label_expr.label('label'), func.count(Quotation.id).label('value'))
        if user_id and role == 'COLLABORATEUR':
            q = q.filter(Quotation.created_by == user_id)
        if date_from:
            q = q.filter(Quotation.creation_date >= date_from)
        if date_to:
            q = q.filter(Quotation.creation_date <= date_to)
        q = q.group_by('label').order_by('label')
        for label, value in q.all():
            if hasattr(label, 'strftime'):
                label = label.strftime('%Y-%m')
            results.append(ChartDataPoint(label=str(label), value=float(value)))

    elif chart_type == 'by_status':
        q = db.query(Quotation.status, func.count(Quotation.id))
        if user_id and role == 'COLLABORATEUR':
            q = q.filter(Quotation.created_by == user_id)
        q = q.group_by(Quotation.status)
        for status, cnt in q.all():
            label = status.value if hasattr(status, 'value') else str(status)
            results.append(ChartDataPoint(label=label, value=float(cnt)))

    elif chart_type == 'by_period':
        # Additionne les montants par mois ou dans la période demandée.
        label_expr = _get_month_label_expr(db)
        q = db.query(label_expr.label('label'), func.coalesce(func.sum(Quotation.total_amount), 0).label('value'))
        if user_id and role == 'COLLABORATEUR':
            q = q.filter(Quotation.created_by == user_id)
        if date_from:
            q = q.filter(Quotation.creation_date >= date_from)
        if date_to:
            q = q.filter(Quotation.creation_date <= date_to)
        q = q.group_by('label').order_by('label')
        for label, value in q.all():
            if hasattr(label, 'strftime'):
                label = label.strftime('%Y-%m')
            results.append(ChartDataPoint(label=str(label), value=float(value)))

    return results
