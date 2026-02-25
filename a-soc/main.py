import asyncio
import uuid
import sys
from pathlib import Path

# Add the a-soc directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from agents.telemetry.telemetry_agent import TelemetryAgent
from agents.detection.detection_agent import DetectionAgent
from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.forensics.forensics_agent import ForensicsAgent
from agents.response.response_agent import ResponseAgent
from agents.compliance.compliance_agent import ComplianceAgent
from agents.base.message import ASOCMessage, MessageType, Priority

async def simulate_threat_cycle():
    print("\n--- 🕵️ A-SOC AUTONOMOUS SECURITY CYCLE STARTING ---\n")
    
    # 1. Initialize Agents
    telemetry = TelemetryAgent()
    detection = DetectionAgent()
    supervisor = SupervisorAgent()
    forensics = ForensicsAgent()
    response = ResponseAgent()
    compliance = ComplianceAgent()

    # 2. Simulate Log Ingestion (Telemetry)
    print("[1] Telemetry Agent: Ingesting AWS CloudTrail logs...")
    incident_id = str(uuid.uuid4())
    alert_msg = ASOCMessage(
        message_type=MessageType.ALERT,
        source_agent="TelemetryAgent",
        payload={"event": "ConsoleLogin", "user": "admin", "ip": "1.2.3.4"},
        correlation_id=incident_id,
        priority=Priority.MEDIUM
    )

    # 3. Threat Analysis (Detection)
    print("[2] Detection Agent: Analyzing threat with LLM reasoning...")
    detection_report = await detection.process_message(alert_msg)
    
    # 4. Policy Enforcement (Supervisor)
    if detection_report:
        print(f"[3] Supervisor Agent: Evaluating risk ({detection_report.payload['risk_score']})...")
        command_to_forensics = await supervisor.process_message(detection_report)
        
        # 5. Root Cause Analysis (Forensics)
        if command_to_forensics:
            print("[4] Forensics Agent: Reconstructing attack timeline...")
            forensics_report = await forensics.process_message(command_to_forensics)
            
            # 6. Automated Remediation (Response)
            print("[5] Response Agent: Executing remediation (IAM_REVOKE)...")
            remediation_cmd = ASOCMessage(
                message_type=MessageType.COMMAND,
                source_agent="SupervisorAgent",
                target_agent="ResponseAgent",
                payload={"action": "IAM_REVOKE", "target": "admin-user"},
                correlation_id=incident_id
            )
            await response.process_message(remediation_cmd)
            
            # 7. Compliance Audit (Compliance)
            print("[6] Compliance Agent: Mapping incident to SOC2 controls...")
            audit_log = ASOCMessage(
                message_type=MessageType.LOG,
                source_agent="ResponseAgent",
                payload={"event_type": "revoked_access", "details": {"user": "admin-user"}},
                correlation_id=incident_id
            )
            await compliance.process_message(audit_log)

    print("\n--- ✅ THREAT NEUTRALIZED & AUDITED ---\n")

if __name__ == "__main__":
    asyncio.run(simulate_threat_cycle())
