from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from app.models.payment_reminder import ReminderStatus


class PaymentReminderOut(BaseModel):
    id: str
    quotation_id: str
    due_date: date
    sent_date: Optional[datetime]
    reminder_status: ReminderStatus

    model_config = {
        "from_attributes": True,
    }
