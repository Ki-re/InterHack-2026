from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    agent_id: int | None
    alert_id: str
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}
