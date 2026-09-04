"""
core/simulation/scenarios.py
Attack scenarios the demo replays.

These were inline dictionaries inside ``api.py``'s ``run_simulation``. Moving
them here keeps the transport layer free of content, and lets the test suite
assert that every scenario's proposed action is one the guardrail actually
recognises -- previously ``ISOLATE_INSTANCE`` and ``BLOCK_IP`` appeared here but
in no scoring table, so they silently took a default score.

Note on ``risk_score``: it is the *detection* confidence that the telemetry
represents a real threat. It is deliberately **not** the action risk score.
Action risk is computed by ``guardrails.decision.evaluate_action`` from the
action type and its context. Conflating the two is what let the old
``if risk_score > 0.6`` gate stand in for a policy engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    telemetry: dict[str, Any]
    alert: str
    detection_confidence: float
    action: str
    target: str
    action_context: dict[str, Any] = field(default_factory=dict)
    graph: dict[str, Any] = field(default_factory=dict)


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="IAM Privilege Escalation",
        telemetry={"event": "ConsoleLogin", "user": "admin", "ip": "192.168.1.50"},
        alert="Suspicious ConsoleLogin detected (Brute Force)",
        detection_confidence=0.85,
        action="IAM_REVOKE",
        target="admin-user",
        action_context={"production_environment": True, "irreversible": False},
        graph={
            "nodes": [
                {
                    "id": "attacker-ip",
                    "type": "threat_actor",
                    "label": "IP: 192.168.1.50",
                    "risk": "critical",
                },
                {"id": "user", "type": "identity", "label": "User: admin", "risk": "high"},
                {"id": "policy", "type": "resource", "label": "IAM: FullAccess", "risk": "medium"},
            ],
            "edges": [
                {"source": "attacker-ip", "target": "user", "label": "Brute Force"},
                {"source": "user", "target": "policy", "label": "Policy Attach"},
            ],
        },
    ),
    Scenario(
        name="Ransomware Data Encrypted",
        telemetry={"event": "FileWrite", "path": "/data/db.enc", "process": "encrypt.exe"},
        alert="High-velocity file encryption detected on DB Server",
        detection_confidence=0.95,
        action="ISOLATE_INSTANCE",
        target="i-098f6bcd4621d373c",
        action_context={"production_environment": True, "affects_multiple_resources": False},
        graph={
            "nodes": [
                {
                    "id": "c2-server",
                    "type": "threat_actor",
                    "label": "C2: 45.33.2.1",
                    "risk": "critical",
                },
                {"id": "host", "type": "resource", "label": "EC2: DB-Prod", "risk": "critical"},
                {"id": "file", "type": "resource", "label": "File: sensitive.db", "risk": "high"},
            ],
            "edges": [
                {"source": "c2-server", "target": "host", "label": "Command & Control"},
                {"source": "host", "target": "file", "label": "Encryption Process"},
            ],
        },
    ),
    Scenario(
        name="S3 Data Exfiltration",
        telemetry={"event": "GetObject", "bucket": "customer-data", "bytes": 5_000_000_000},
        alert="Anomalous Data Transfer (5GB) to external IP",
        detection_confidence=0.75,
        action="BLOCK_IP",
        target="203.0.113.42",
        action_context={"production_environment": True},
        graph={
            "nodes": [
                {
                    "id": "insider",
                    "type": "identity",
                    "label": "User: analyst-bob",
                    "risk": "medium",
                },
                {"id": "bucket", "type": "resource", "label": "S3: customer-data", "risk": "high"},
                {
                    "id": "dest-ip",
                    "type": "threat_actor",
                    "label": "IP: 203.0.113.42",
                    "risk": "critical",
                },
            ],
            "edges": [
                {"source": "insider", "target": "bucket", "label": "Bulk Read"},
                {"source": "bucket", "target": "dest-ip", "label": "Exfiltration"},
            ],
        },
    ),
)

BENIGN_TELEMETRY: tuple[str, ...] = (
    "VPC Flow: Traffic allowed from 10.0.0.5 to 10.0.0.8 (Port 443)",
    "IAM: User 'dev-operator' assumed role 'ReadOnlyAccess'",
    "CloudTrail: GetBucketEncryption on 'assets-prod'",
    "CloudWatch: Metric 'CPUUtilization' within threshold for 'web-server-01'",
    "K8s: Pod 'auth-api-5f8d' healthy heart-beat received",
    "S3: PutObject to 'audit-logs' by 'system-service'",
    "GuardDuty: No new threats detected in last 5 minutes",
    "Config: Resource 'sg-0abc123' compliant with policy 'restricted-ssh'",
)
