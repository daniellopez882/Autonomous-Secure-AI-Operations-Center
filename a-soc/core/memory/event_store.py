import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import uuid

class EventStore:
    def __init__(self, storage_path: str = "data/events.jsonl"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def append_event(self, event_type: str, payload: Dict[str, Any], agent: str):
        """Append an event to the immutable log."""
        event_record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "agent": agent,
            "payload": payload,
            # "signature": self._sign_event(payload) # TODO: Implement HMAC signature
        }
        
        async with self._lock:
            with open(self.storage_path, "a") as f:
                f.write(json.dumps(event_record) + "\n")
        
        return event_record

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent events from the log."""
        events = []
        if not self.storage_path.exists():
            return events
            
        try:
            with open(self.storage_path, "r") as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    events.append(json.loads(line))
        except Exception as e:
            print(f"Error reading event store: {e}")
            
        return events

# Singleton instance
event_store = EventStore()
