"""Expose la création, la modification et la suppression des articles."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_quotation_access, require_role
from app.models.quotation import Quotation
from app.models.article import Article
from app.models.user import UserRole
from app.models.audit_log import AuditLog
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleOut
from app.services.calculation_service import calculate_line_total, calculate_quotation_total

router = APIRouter()


@router.post(
    "/quotations/{quotation_id}/articles",
    response_model=ArticleOut,
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def create_article(
    quotation_id: str,
    payload: ArticleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    article = Article(
        designation=payload.designation,
        quantity=payload.quantity,
        unit=payload.unit,
        unit_price=payload.unit_price,
        line_total=calculate_line_total(payload.quantity, payload.unit_price),
        quotation_id=quotation.id,
    )
    db.add(article)
    db.flush()

    quotation.total_amount = calculate_quotation_total(quotation.articles)
    db.add(quotation)

    audit = AuditLog(
        user_id=current_user.id,
        action="article.created",
        entity_type="Article",
        entity_id=article.id,
        details={"quotation_id": quotation.id, "designation": article.designation, "line_total": float(article.line_total)},
    )
    db.add(audit)
    db.commit()
    db.refresh(article)
    return article


@router.put(
    "/quotations/{quotation_id}/articles/{article_id}",
    response_model=ArticleOut,
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def update_article(
    quotation_id: str,
    article_id: str,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    article = db.query(Article).filter(Article.id == article_id, Article.quotation_id == quotation_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    if payload.designation is not None:
        article.designation = payload.designation
    if payload.quantity is not None:
        article.quantity = payload.quantity
    if payload.unit is not None:
        article.unit = payload.unit
    if payload.unit_price is not None:
        article.unit_price = payload.unit_price

    article.line_total = calculate_line_total(article.quantity, article.unit_price)
    db.add(article)

    quotation.total_amount = calculate_quotation_total(quotation.articles)
    db.add(quotation)

    audit = AuditLog(
        user_id=current_user.id,
        action="article.updated",
        entity_type="Article",
        entity_id=article.id,
        details={"quotation_id": quotation.id, "line_total": float(article.line_total)},
    )
    db.add(audit)
    db.commit()
    db.refresh(article)
    return article


@router.delete(
    "/quotations/{quotation_id}/articles/{article_id}",
    dependencies=[Depends(require_role(UserRole.COLLABORATEUR, UserRole.RESPONSABLE, UserRole.ADMIN))],
)
def delete_article(
    quotation_id: str,
    article_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    require_quotation_access(quotation, current_user)

    if len(quotation.articles) <= 1:
        raise HTTPException(status_code=400, detail="A quotation must contain at least one article")

    article = db.query(Article).filter(Article.id == article_id, Article.quotation_id == quotation_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article)
    db.flush()

    quotation.total_amount = calculate_quotation_total(quotation.articles)
    db.add(quotation)

    audit = AuditLog(
        user_id=current_user.id,
        action="article.deleted",
        entity_type="Article",
        entity_id=article.id,
        details={"quotation_id": quotation.id},
    )
    db.add(audit)
    db.commit()
    return {"detail": "Article deleted"}
