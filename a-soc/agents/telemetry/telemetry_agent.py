import asyncio

import boto3

from agents.base.agent import BaseAgent
from agents.base.message import ASOCMessage, MessageType, Priority
from core.config.settings import settings


class TelemetryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TelemetryAgent",
            description="Pulls logs from AWS CloudTrail, VPC Flow Logs, and K8s audit logs",
        )
        # Strong references to background tasks. Without this, asyncio may
        # garbage-collect a running task and polling stops silently.
        self._tasks: set[asyncio.Task] = set()
        # Try to initialize AWS client, but don't fail if credentials aren't available
        try:
            self.cloudtrail = boto3.client("cloudtrail", region_name=settings.AWS_REGION)
        except Exception as e:
            self.logger.warning(f"AWS credentials not configured, using mock mode: {e}")
            self.cloudtrail = None

    async def poll_cloudtrail(self):
        """Mock polling CloudTrail for events."""
        self.logger.info("Polling CloudTrail for new events...")
        # In a real scenario, we'd use LookupEvents with a StartTime
        try:
            # response = self.cloudtrail.lookup_events(MaxResults=10)
            # mock event for now
            mock_event = {
                "eventID": "12345",
                "eventName": "ConsoleLogin",
                "userIdentity": {"type": "IAMUser", "userName": "test-user"},
                "eventTime": "2026-02-08T16:50:00Z",
                "sourceIPAddress": "1.2.3.4",
            }

            message = ASOCMessage(
                message_type=MessageType.ALERT,
                source_agent=self.name,
                payload={"event": mock_event, "provider": "aws_cloudtrail"},
                priority=Priority.MEDIUM,
            )
            await self.send_message(message)
            await self.log_event("log_ingestion", {"event_id": "12345", "source": "cloudtrail"})

        except Exception as e:
            self.logger.error(f"Error polling CloudTrail: {e!s}")

    async def process_message(self, message: ASOCMessage) -> ASOCMessage | None:
        # Telemetry Agent mostly sends messages, but might receive configuration updates
        if message.message_type == MessageType.COMMAND:
            if message.payload.get("action") == "start_polling":
                # A bare create_task() keeps no reference, so the event loop
                # may garbage-collect the task mid-flight and polling stops
                # silently. Hold it, and drop it when it finishes.
                task = asyncio.create_task(self.poll_cloudtrail())
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
        return None


if __name__ == "__main__":
    agent = TelemetryAgent()
    asyncio.run(agent.poll_cloudtrail())
