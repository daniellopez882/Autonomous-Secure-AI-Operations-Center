import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    ALERT = "alert"
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    LOG = "log"


class Priority(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class SecurityContext(BaseModel):
    tenant_id: str
    resource_id: str | None = None
    risk_score: float = 0.0


class ASOCMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # utcnow() is deprecated since 3.12 and returns a naive datetime,
    # which silently compares wrong against aware timestamps elsewhere.
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_type: MessageType
    source_agent: str
    target_agent: str | None = None
    payload: dict[str, Any]
    priority: Priority = Priority.LOW
    security_context: SecurityContext | None = None
    correlation_id: str | None = None

    class Config:
        use_enum_values = True
