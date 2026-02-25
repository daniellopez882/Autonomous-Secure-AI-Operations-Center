from typing import Optional, List, Dict, Any
from agents.base.agent import BaseAgent
from agents.base.message import ASOCMessage, MessageType, Priority

class ComplianceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ComplianceAgent",
            description="Checks security events against SOC2, ISO 27001, and HIPAA frameworks"
        )
        self.framework_mappings = {
            "revoked_access": ["SOC2.CC6.1", "ISO.A.9.2.6"],
            "unauthorized_login": ["SOC2.CC6.8", "NIST.AC-2"],
            "data_exfiltration": ["GDPR.Art.33", "HIPAA.164.308"]
        }

    async def map_incident(self, event_type: str, details: Dict[str, Any]) -> List[str]:
        """Map a security event to specific compliance controls."""
        findings = self.framework_mappings.get(event_type, ["GENERAL_SECURITY_ALERT"])
        self.logger.info(f"Compliance Mapping for {event_type}: {findings}")
        return findings

    async def process_message(self, message: ASOCMessage) -> Optional[ASOCMessage]:
        if message.message_type == MessageType.LOG:
            event_type = message.payload.get("event_type")
            controls = await self.map_incident(event_type, message.payload.get("details", {}))
            
            # Record compliance finding
            await self.log_event("compliance_finding", {
                "original_event": event_type,
                "mapped_controls": controls
            })
            
        return None
