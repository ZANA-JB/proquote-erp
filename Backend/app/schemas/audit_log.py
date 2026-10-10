from datetime import datetime
from typing import Any
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    user_id: str | None
    details: dict[str, Any] | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
