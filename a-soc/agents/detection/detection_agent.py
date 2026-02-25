from typing import Optional
from agents.base.agent import BaseAgent
from agents.base.message import ASOCMessage, MessageType, Priority
from core.config.settings import settings

class DetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="DetectionAgent",
            description="Anomaly detection + LLM reasoning over security logs"
        )
        self.provider = settings.LLM_PROVIDER

    async def analyze_threat(self, event_data: dict) -> ASOCMessage:
        """Analyze event data using LLM reasoning."""
        self.logger.info(f"Analyzing threat with {self.provider}...")
        
        # In a real implementation, we would call the LLM here
        # prompt = f"Analyze this AWS event for security threats: {json.dumps(event_data)}"
        
        # Mock analysis result
        threat_detected = True
        risk_score = 0.85
        reasoning = "Suspicious ConsoleLogin from unusual IP address (1.2.3.4)"
        
        if threat_detected:
            return ASOCMessage(
                message_type=MessageType.ALERT,
                source_agent=self.name,
                payload={
                    "risk_score": risk_score,
                    "reasoning": reasoning,
                    "original_event": event_data
                },
                priority=Priority.HIGH
            )
        return None

    async def process_message(self, message: ASOCMessage) -> Optional[ASOCMessage]:
        if message.message_type == MessageType.ALERT and message.source_agent == "TelemetryAgent":
            analysis_result = await self.analyze_threat(message.payload.get("event"))
            if analysis_result:
                await self.send_message(analysis_result)
                await self.log_event("threat_detected", {"risk_score": 0.85, "reasoning": "Suspicious login"})
                return analysis_result
        return None
