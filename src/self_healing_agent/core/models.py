from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def utc_now_string() -> str:
    return datetime.now(timezone.utc).isoformat()

class IncidentPayload(BaseModel):
    incident_details: str = Field(
        ...,
        description="Raw incident details received from the source system.",
    )


class HitlResponsePayload(BaseModel):
    request_id: str
    status: Literal["APPROVED", "REJECTED"]
    reviewer: str
    reason: str
    timestamp_utc: str = Field(default_factory=utc_now_string)

    @field_validator("timestamp_utc", mode="before")
    @classmethod
    def set_timestamp_if_blank(cls, value: str | None) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return utc_now_string()
        return value

    
