from pydantic import BaseModel
from datetime import datetime

class TimerEntity(BaseModel):
    id: int | None = None
    name: str
    message: str
    interval_minutes: int
    min_lines: int
    enabled: int = 1
    last_executed_at: datetime | None = None
    created_at: datetime | None = None
