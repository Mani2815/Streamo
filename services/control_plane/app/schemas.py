from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime

class SourceBase(BaseModel):
    name: str
    url: HttpUrl
    poll_interval: Optional[int] = 60

class SourceCreate(SourceBase):
    pass

class Source(SourceBase):
    id: int
    schema_: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SourceValidateRequest(BaseModel):
    name: str
    url: HttpUrl

class SourceValidateResponse(BaseModel):
    valid: bool
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    error: Optional[str] = None
    detected_fields: Optional[Dict[str, str]] = None
