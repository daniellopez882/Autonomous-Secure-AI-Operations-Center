import abc
import logging
from typing import Any, Dict, List, Optional
from .message import ASOCMessage, MessageType
import asyncio

class BaseAgent(abc.ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"asoc.agents.{name}")
        self._setup_logging()

    def _setup_logging(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    @abc.abstractmethod
    async def process_message(self, message: ASOCMessage) -> Optional[ASOCMessage]:
        """Process an incoming message and optionally return a response."""
        pass

    async def send_message(self, message: ASOCMessage):
        """Simulate sending a message to the orchestrator/bus."""
        self.logger.info(f"Sending message {message.message_id} from {self.name}")
        # In a real implementation, this would push to a message bus like Redis/RabbitMQ
        pass

    async def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log a security event to the immutable audit store (EventStore)."""
        log_msg = ASOCMessage(
            message_type=MessageType.LOG,
            source_agent=self.name,
            payload={"event_type": event_type, "details": details}
        )
        self.logger.info(f"Audit Log: {event_type} - {details}")
        
        # Persist to disk
        try:
            from core.memory.event_store import event_store
            await event_store.append_event(event_type, details, self.name)
        except ImportError:
            # Fallback for when running in diverse environments
            pass
        except Exception as e:
            self.logger.error(f"Failed to persist event: {e}")

        await self.send_message(log_msg)

    def __repr__(self):
        return f"Agent(name={self.name}, type={self.__class__.__name__})"
