import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from app.core.constants import NotificationType


class NotificationPublic(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    title: str
    message: str
    notification_type: NotificationType
    data: dict[str, Any]
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
