from pydantic import BaseModel
from typing import List


class ChartDataPoint(BaseModel):
    label: str
    value: float


class DashboardSummary(BaseModel):
    total_quotations: int
    sent_count: int
    accepted_count: int
    refused_count: int
    expired_count: int
    draft_count: int
    total_amount: float
    conversion_rate: float

