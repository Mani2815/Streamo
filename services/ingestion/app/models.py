from pydantic import BaseModel, Field
from typing import Any, Dict
import datetime
import uuid

class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    ingested_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    payload: str
