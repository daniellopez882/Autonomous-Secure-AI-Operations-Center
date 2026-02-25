from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

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
    resource_id: Optional[str] = None
    risk_score: float = 0.0

class ASOCMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: MessageType
    source_agent: str
    target_agent: Optional[str] = None
    payload: Dict[str, Any]
    priority: Priority = Priority.LOW
    security_context: Optional[SecurityContext] = None
    correlation_id: Optional[str] = None

    class Config:
        use_enum_values = True
