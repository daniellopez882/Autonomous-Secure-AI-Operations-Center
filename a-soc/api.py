from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import uuid
import sys
from pathlib import Path
from typing import List
from datetime import datetime

# Add the a-soc directory (parent of api.py) to sys.path
sys.path.append(str(Path(__file__).parent))

from agents.telemetry.telemetry_agent import TelemetryAgent
from agents.detection.detection_agent import DetectionAgent
from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.forensics.forensics_agent import ForensicsAgent
from agents.response.response_agent import ResponseAgent
from agents.compliance.compliance_agent import ComplianceAgent
from agents.base.message import ASOCMessage, MessageType, Priority

app = FastAPI(title="A-SOC API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    return {
        "status": "healthy",
        "service": "asoc-backend",
        "active_connections": len(manager.active_connections)
    }

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_telemetry())

@app.websocket("/ws/threat-feed")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    permission_event = asyncio.Event() # Used to pause execution
    
    try:
        current_task = None
        
        while True:
            # Keep connection alive and listen for commands from UI
            data = await websocket.receive_text()
            
            if data == "START_SIMULATION":
                # Create a new simulation task
                if current_task: current_task.cancel()
                permission_event.clear() # Reset approval status
                current_task = asyncio.create_task(run_simulation(permission_event))
            
            elif data == "APPROVE_ACTION":
                # User clicked 'Approve'
                permission_event.set() 
                await manager.broadcast({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "agent": "System",
                    "status": "approved",
                    "message": "Human operator authorized action.",
                    "severity": "low"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if current_task: current_task.cancel()

import random

async def background_telemetry():
    """Simulate continuous benign log flow."""
    benign_messages = [
        "VPC Flow: Traffic allowed from 10.0.0.5 to 10.0.0.8 (Port 443)",
        "IAM: User 'dev-operator' assumed role 'ReadOnlyAccess'",
        "CloudTrail: GetBucketEncryption on 'assets-prod'",
        "CloudWatch: Metric 'CPUUtilization' within threshold for 'web-server-01'",
        "K8s: Pod 'auth-api-5f8d' healthy heart-beat received",
        "S3: PutObject to 'audit-logs' by 'system-service'",
        "GuardDuty: No new threats detected in last 5 minutes",
        "Config: Resource 'sg-0abc123' compliant with policy 'restricted-ssh'"
    ]
    while True:
        await manager.broadcast({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": "Telemetry",
            "status": "scanning",
            "message": random.choice(benign_messages),
            "severity": "low",
            "is_background": True
        })
        await asyncio.sleep(random.uniform(2, 5))

async def run_simulation(permission_event: asyncio.Event):
    """Run a randomized secure SOC cycle and stream updates to the UI, pausing for approval."""
    
    # helper to stream status
    async def stream_status(agent, status, message, severity="low"):
        await manager.broadcast({
            "id": str(uuid.uuid4()),
            "timestamp":  datetime.utcnow().isoformat() + "Z",
            "agent": agent,  
            "status": status,
            "message": message,
            "severity": severity
        })
        await asyncio.sleep(1.5) # Pacing for demo

    await stream_status("System", "active", "A-SOC Protocol Initiated", "low")

    # DEFINE SCENARIOS
    scenarios = [
        {
            "name": "IAM Privilege Escalation",
            "telemetry": {"event": "ConsoleLogin", "user": "admin", "ip": "192.168.1.50"},
            "alert": "Suspicious ConsoleLogin detected (Brute Force)",
            "risk_score": 0.85,
            "action": "IAM_REVOKE",
            "target": "admin-user",
            "graph": {
                 "nodes": [
                    {"id": "attacker-ip", "type": "threat_actor", "label": "IP: 192.168.1.50", "risk": "critical"},
                    {"id": "user", "type": "identity", "label": "User: admin", "risk": "high"},
                    {"id": "policy", "type": "resource", "label": "IAM: FullAccess", "risk": "medium"}
                ],
                "edges": [
                    {"source": "attacker-ip", "target": "user", "label": "Brute Force"},
                    {"source": "user", "target": "policy", "label": "Policy Attach"}
                ]
            }
        },
        {
            "name": "Ransomware Data Encrypted",
            "telemetry": {"event": "FileWrite", "path": "/data/db.enc", "process": "encrypt.exe"},
            "alert": "High-velocity file encryption detected on DB Server",
            "risk_score": 0.95,
            "action": "ISOLATE_INSTANCE",
            "target": "i-098f6bcd4621d373c",
            "graph": {
                 "nodes": [
                    {"id": "c2-server", "type": "threat_actor", "label": "C2: 45.33.2.1", "risk": "critical"},
                    {"id": "host", "type": "resource", "label": "EC2: DB-Prod", "risk": "critical"},
                    {"id": "file", "type": "resource", "label": "File: sensitive.db", "risk": "high"}
                ],
                "edges": [
                    {"source": "c2-server", "target": "host", "label": "Command & Control"},
                    {"source": "host", "target": "file", "label": "Encryption Process"}
                ]
            }
        },
        {
            "name": "S3 Data Exfiltration",
            "telemetry": {"event": "GetObject", "bucket": "customer-data", "bytes": 5000000000},
            "alert": "Anomalous Data Transfer (5GB) to external IP",
            "risk_score": 0.75,
            "action": "BLOCK_IP",
            "target": "203.0.113.42",
            "graph": {
                 "nodes": [
                    {"id": "insider", "type": "identity", "label": "User: analyst-bob", "risk": "medium"},
                    {"id": "bucket", "type": "resource", "label": "S3: customer-data", "risk": "high"},
                    {"id": "dest-ip", "type": "threat_actor", "label": "IP: 203.0.113.42", "risk": "critical"}
                ],
                "edges": [
                    {"source": "insider", "target": "bucket", "label": "Bulk Read"},
                    {"source": "bucket", "target": "dest-ip", "label": "Exfiltration"}
                ]
            }
        }
    ]
    
    scenario = random.choice(scenarios)
    incident_id = str(uuid.uuid4())
    
    await stream_status("System", "monitoring", f"Scenario Active: {scenario['name']}", "low")

    # 2. Ingest
    await stream_status("Telemetry", "scanning", f"Ingesting Logs: {scenario['telemetry']}", "low")
    
    alert_msg = ASOCMessage(
        message_type=MessageType.ALERT,
        source_agent="TelemetryAgent",
        payload=scenario['telemetry'],
        correlation_id=incident_id,
        priority=Priority.MEDIUM
    )
    await stream_status("Telemetry", "alert", scenario['alert'], "medium")

    # 3. Detect
    await stream_status("Detection", "analyzing", "Correlating events with Threat Intel...", "low")
    # Simulate detection processing
    detection_report = ASOCMessage(
        message_type=MessageType.REPORT,
        source_agent="DetectionAgent",
        payload={"risk_score": scenario['risk_score'], "analysis": "Confirmed Malicious"},
        correlation_id=incident_id
    )
    
    await stream_status("Detection", "detected", f"Threat Confirmed: Risk Score {scenario['risk_score']}", "high")

    # 4. Supervise
    await stream_status("Supervisor", "evaluating", "Checking policy guardrails...", "low")
    
    risk_score = scenario['risk_score']
    
    if risk_score > 0.6: # Threshold for demo
        # PAUSE FOR HUMAN APPROVAL
        await stream_status("Supervisor", "blocked", f"High Risk Action Proposed: {scenario['action']}. Awaiting Authorization...", "critical")
        
        # Send explicit approval request to UI
        await manager.broadcast({
            "type": "APPROVAL_REQUIRED",
            "action": scenario['action'],
            "target": scenario['target'],
            "risk_score": risk_score
        })
        
        # Wait until frontend sends "APPROVE_ACTION" which sets the event
        await permission_event.wait()
        
        await stream_status("Supervisor", "authorized", "Action Authorized. Proceeding...", "low")

    # 5. Forensics
    await stream_status("Forensics", "investigating", "Reconstructing blast radius...", "medium")
    
    # Broadcast Scenario Graph
    await manager.broadcast({
        "type": "BLAST_RADIUS_UPDATE",
        "graph": scenario['graph'],
        "root_cause": scenario['name']
    })

    await stream_status("Forensics", "complete", "Root cause execution trace mapped.", "high")

    # 6. Response
    await stream_status("Response", "actuating", f"Executing {scenario['action']}...", "critical")
    
    # Simulate Slack Notification
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    await stream_status("Response", "notifying", f"Sending Slack Alert to #sec-ops at {timestamp}...", "medium")
    await asyncio.sleep(0.5)

    remediation = ASOCMessage(
            message_type=MessageType.COMMAND,
            source_agent="SupervisorAgent",
            target_agent="ResponseAgent",
            payload={"action": scenario['action'], "target": scenario['target']},
            correlation_id=incident_id
    )
    
    await stream_status("Response", "success", "Threat Neutralized. Infrastructure Secure.", "low")

    # 7. Compliance
    await stream_status("Compliance", "auditing", "Mapping to SOC2 & ISO 27001...", "low")
    log = ASOCMessage(
        message_type=MessageType.LOG,
        source_agent="ResponseAgent",
            payload={"event_type": "remediation", "details": {"action": scenario['action']}},
            correlation_id=incident_id
    )
    # await compliance.process_message(log) # skip actual storage call for speed in multi-scenario
    await stream_status("Compliance", "logged", f"Audit record #{random.randint(1000,9999)} sealed.", "low")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
