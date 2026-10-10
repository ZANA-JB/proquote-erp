"""Expose les statistiques et graphiques des cotations."""

from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.dashboard import DashboardSummary, ChartDataPoint
from app.services.dashboard_service import get_summary, get_chart_data

router = APIRouter()


def _authorization_context(current_user):
    role = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    user_id = current_user.id if role == 'COLLABORATEUR' else None
    return role, user_id


@router.get('/summary', response_model=DashboardSummary, dependencies=[Depends(get_current_user)])
def dashboard_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    role, user_id = _authorization_context(current_user)
    summary = get_summary(db, user_id=user_id, role=role)
    return summary


@router.get('/charts', response_model=List[ChartDataPoint], dependencies=[Depends(get_current_user)])
def dashboard_charts(
    type: str = Query('by_month', pattern='^(by_month|by_status|by_period)$'),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role, user_id = _authorization_context(current_user)
    data = get_chart_data(db, chart_type=type, user_id=user_id, role=role, date_from=date_from, date_to=date_to)
    return data
 
