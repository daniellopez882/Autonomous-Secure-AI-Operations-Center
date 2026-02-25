from typing import List, Optional, Dict, Any
from agents.base.agent import BaseAgent
from agents.base.message import ASOCMessage, MessageType, Priority
from core.config.settings import settings

class SupervisorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SupervisorAgent",
            description="Enforces policies, manages approval gates, and coordinates agents"
        )
        self.active_incidents: Dict[str, Any] = {}

    async def evaluate_action(self, agent_name: str, action: Dict[str, Any], risk_score: float) -> bool:
        """
        Evaluate if an action is allowed based on risk score and policy.
        Queries OPA (Open Policy Agent) if available, otherwise falls back to local rules.
        """
        import httpx
        
        self.logger.info(f"Evaluating action from {agent_name}: {action.get('type')} with risk {risk_score}")

        # Construct OPA Input
        opa_input = {
            "input": {
                "action": {
                    "type": action.get("type", "unknown"),
                    "risk_score": risk_score,
                    "agent": agent_name
                },
                "user": action.get("user", "system"),
                "resource": action.get("target", "unknown")
            }
        }

        try:
            # Query OPA
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.OPA_URL}/v1/data/asoc/actions/allow",
                    json=opa_input,
                    timeout=2.0
                )
                
                if response.status_code == 200:
                    result = response.json().get("result", False)
                    self.logger.info(f"OPA Policy Decision: {'ALLOWED' if result else 'DENIED'}")
                    return result
                else:
                    self.logger.warning(f"OPA returned status {response.status_code}")
                    
        except Exception as e:
            self.logger.warning(f"Could not query OPA ({settings.OPA_URL}): {e}. Falling back to local policy.")

        # Fallback Local Policy:
        # Destructive actions with risk > 0.7 always require human approval (return False to block auto-execution)
        if risk_score > 0.7 and action.get('is_destructive', False):
            self.logger.warning("ACTION BLOCKED (Local Policy): High risk destructive action")
            return False
            
        return True

    async def process_message(self, message: ASOCMessage) -> Optional[ASOCMessage]:
        """
        The Supervisor handles routing and high-level decisions.
        """
        if message.message_type == MessageType.ALERT:
            # New threat from Detection Agent
            incident_id = message.correlation_id or message.message_id
            self.active_incidents[incident_id] = message.payload
            
            self.logger.info(f"New incident recorded: {incident_id}")
            
            # Decide next step: Send to Forensics
            return ASOCMessage(
                message_type=MessageType.COMMAND,
                source_agent=self.name,
                target_agent="ForensicsAgent",
                payload={"incident_id": incident_id, "data": message.payload},
                correlation_id=incident_id,
                priority=message.priority
            )
            
        return None
