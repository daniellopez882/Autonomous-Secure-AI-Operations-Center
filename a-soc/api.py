"""
api.py
A-SOC backend: HTTP probes plus a WebSocket that streams a SOC incident
simulation to the dashboard.

What this service actually is, stated plainly because the code did not say so:
it **replays scripted attack scenarios**. The agent classes under ``agents/``
return hardcoded findings and are not wired to an LLM. What is real, and what
this revision makes real, is the **guardrail**: whether a proposed remediation
may execute is now decided by ``guardrails.decision.evaluate_action`` from the
action type and its context.

Previously that decision was ``if risk_score > 0.6:  # Threshold for demo`` --
a magic number that ignored ``RiskScorer`` and the rego policy, both of which
were dead code.

Other fixes in this revision:

* ``ConnectionManager`` moved to ``core.realtime`` and made fault-tolerant. A
  single dead client used to abort the whole broadcast loop, which permanently
  killed the background telemetry task the first time anyone closed a tab.
* ``@app.on_event("startup")`` replaced with a lifespan handler, and the
  background task is now cancelled on shutdown instead of leaking.
* ``datetime.utcnow()`` (deprecated since 3.12) replaced with aware timestamps.
* CORS origins and the optional WebSocket token come from configuration rather
  than being hardcoded to localhost.
* Agent imports are deferred, so the service starts without boto3 installed --
  it previously required the AWS SDK to serve a simulation that never calls AWS.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import secrets
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from core.config.settings import settings
from core.logging_config import get_logger, setup_logging
from core.realtime.connection_manager import ConnectionManager
from core.simulation.scenarios import BENIGN_TELEMETRY, SCENARIOS
from guardrails.decision import ActionRequest, Decision, evaluate_action

logger = get_logger("asoc.api")

manager = ConnectionManager()
_background_task: asyncio.Task | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the ambient telemetry feed, and stop it cleanly on shutdown."""
    global _background_task
    setup_logging(level=settings.LOG_LEVEL, json_output=settings.JSON_LOGS)
    logger.info("service_starting", environment=settings.ENVIRONMENT)
    _background_task = asyncio.create_task(background_telemetry())
    try:
        yield
    finally:
        logger.info("service_stopping")
        if _background_task is not None:
            _background_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _background_task
        await manager.close_all()


app = FastAPI(
    title="A-SOC API",
    description="Agentic security operations centre - incident simulation and guardrails.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ----------------------------------------------------------------- HTTP probes
@app.get("/health", tags=["ops"])
async def health_check() -> dict[str, Any]:
    """Liveness. Deliberately touches no dependency."""
    return {
        "status": "healthy",
        "service": "asoc-backend",
        "version": app.version,
        "active_connections": len(manager),
    }


@app.get("/ready", tags=["ops"])
async def readiness() -> dict[str, Any]:
    """
    Readiness. The simulation has no external dependencies, so this reports
    configuration health rather than pretending to check a database.
    """
    checks = {
        "telemetry_task": {
            "ok": _background_task is not None and not _background_task.done(),
            "required": True,
        },
        "guardrails": {"ok": _guardrails_self_test(), "required": True},
        "ws_auth_configured": {
            "ok": bool(settings.WS_AUTH_TOKEN) or not settings.is_production,
            "required": True,
        },
    }
    ready = all(c["ok"] for c in checks.values() if c["required"])
    return {"ready": ready, "checks": checks}


def _guardrails_self_test() -> bool:
    """Confirm the policy engine answers, so /ready fails if it is broken."""
    try:
        verdict = evaluate_action(ActionRequest("LOG_QUERY", "self-test"))
        return verdict.decision is Decision.ALLOW
    except Exception:
        logger.error("guardrail_self_test_failed", exc_info=True)
        return False


@app.get("/api/v1/policy/evaluate", tags=["guardrails"])
async def evaluate_policy(
    action_type: str = Query(..., max_length=64),
    target: str = Query("unspecified", max_length=256),
    production: bool = Query(False),
    irreversible: bool = Query(False),
) -> dict[str, Any]:
    """
    Evaluate a proposed action against the guardrail without executing it.

    Exposed so the policy can be inspected and tested directly, rather than
    only being observable by watching the simulation.
    """
    verdict = evaluate_action(
        ActionRequest(
            action_type=action_type,
            target=target,
            context={"production_environment": production, "irreversible": irreversible},
        )
    )
    return verdict.to_dict()


# -------------------------------------------------------------------- WebSocket
def _ws_token_ok(supplied: str | None) -> bool:
    """Constant-time check of the optional WebSocket token."""
    expected = settings.WS_AUTH_TOKEN
    if not expected:
        # No token configured: open in development, refused in production
        # (the readiness probe reports this as unready).
        return not settings.is_production
    return bool(supplied) and secrets.compare_digest(supplied, expected)


@app.websocket("/ws/threat-feed")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(None)) -> None:
    if not _ws_token_ok(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="unauthorized")
        logger.warning("ws_rejected_unauthorized")
        return

    await manager.connect(websocket)
    permission_event = asyncio.Event()
    current_task: asyncio.Task | None = None

    try:
        while True:
            data = await websocket.receive_text()

            if data == "START_SIMULATION":
                if current_task is not None:
                    current_task.cancel()
                permission_event.clear()
                current_task = asyncio.create_task(run_simulation(permission_event))

            elif data == "APPROVE_ACTION":
                permission_event.set()
                await manager.broadcast(
                    {
                        "id": str(uuid.uuid4()),
                        "timestamp": _now(),
                        "agent": "System",
                        "status": "approved",
                        "message": "Human operator authorized action.",
                        "severity": "low",
                    }
                )

    except WebSocketDisconnect:
        logger.info("ws_client_disconnected")
    finally:
        manager.disconnect(websocket)
        if current_task is not None:
            current_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await current_task


# ------------------------------------------------------------- background feed
async def background_telemetry() -> None:
    """
    Ambient benign log flow.

    The loop body is guarded: broadcast no longer raises, but an unexpected
    error here would otherwise silently end the feed for the whole process,
    which is exactly the failure the old implementation had.
    """
    while True:
        try:
            await manager.broadcast(
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": _now(),
                    "agent": "Telemetry",
                    "status": "scanning",
                    "message": random.choice(BENIGN_TELEMETRY),  # noqa: S311 - demo content
                    "severity": "low",
                    "is_background": True,
                }
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("telemetry_broadcast_failed", exc_info=True)
        await asyncio.sleep(random.uniform(2, 5))  # noqa: S311 - demo pacing


# ------------------------------------------------------------------ simulation
async def run_simulation(permission_event: asyncio.Event) -> None:
    """Replay one attack scenario, gating remediation on the guardrail."""
    incident_id = str(uuid.uuid4())

    async def stream(agent: str, status_: str, message: str, severity: str = "low") -> None:
        await manager.broadcast(
            {
                "id": str(uuid.uuid4()),
                "timestamp": _now(),
                "agent": agent,
                "status": status_,
                "message": message,
                "severity": severity,
                "incident_id": incident_id,
            }
        )
        await asyncio.sleep(settings.SIMULATION_STEP_SECONDS)

    scenario = random.choice(SCENARIOS)  # noqa: S311 - demo content
    logger.info("simulation_started", incident_id=incident_id, scenario=scenario.name)

    await stream("System", "active", "A-SOC Protocol Initiated")
    await stream("System", "monitoring", f"Scenario Active: {scenario.name}")

    # 1. Ingest
    await stream("Telemetry", "scanning", f"Ingesting Logs: {scenario.telemetry}")
    await stream("Telemetry", "alert", scenario.alert, "medium")

    # 2. Detect
    await stream("Detection", "analyzing", "Correlating events with Threat Intel...")
    await stream(
        "Detection",
        "detected",
        f"Threat Confirmed: detection confidence {scenario.detection_confidence:.2f}",
        "high",
    )

    # 3. Supervise -- the real guardrail, not a magic threshold.
    await stream("Supervisor", "evaluating", "Evaluating proposed action against policy...")

    verdict = evaluate_action(
        ActionRequest(
            action_type=scenario.action,
            target=scenario.target,
            context=scenario.action_context,
        )
    )
    logger.info(
        "guardrail_verdict",
        incident_id=incident_id,
        action=verdict.action_type,
        decision=verdict.decision.value,
        risk_score=verdict.risk_score,
    )
    await manager.broadcast(
        {
            "type": "POLICY_VERDICT",
            "incident_id": incident_id,
            "timestamp": _now(),
            **verdict.to_dict(),
        }
    )

    if verdict.decision is Decision.DENY:
        await stream(
            "Supervisor",
            "denied",
            f"Action {verdict.action_type} DENIED by policy "
            f"(risk {verdict.risk_score:.2f}). Escalating to human operators.",
            "critical",
        )
        logger.info("simulation_halted_by_policy", incident_id=incident_id)
        return

    if verdict.decision is Decision.REQUIRE_APPROVAL:
        await stream(
            "Supervisor",
            "blocked",
            f"{verdict.action_type} requires authorization "
            f"(risk {verdict.risk_score:.2f}, {verdict.risk_level.value}). Awaiting operator...",
            "critical",
        )
        await manager.broadcast(
            {
                "type": "APPROVAL_REQUIRED",
                "incident_id": incident_id,
                "action": verdict.action_type,
                "target": scenario.target,
                "risk_score": verdict.risk_score,
                "reasons": list(verdict.reasons),
            }
        )
        await permission_event.wait()
        await stream("Supervisor", "authorized", "Action Authorized. Proceeding...")
    else:
        await stream(
            "Supervisor",
            "authorized",
            f"{verdict.action_type} auto-approved (risk {verdict.risk_score:.2f}, below threshold).",
        )

    # 4. Forensics
    await stream("Forensics", "investigating", "Reconstructing blast radius...", "medium")
    await manager.broadcast(
        {
            "type": "BLAST_RADIUS_UPDATE",
            "incident_id": incident_id,
            "graph": scenario.graph,
            "root_cause": scenario.name,
        }
    )
    await stream("Forensics", "complete", "Root cause execution trace mapped.", "high")

    # 5. Response
    await stream("Response", "actuating", f"Executing {verdict.action_type}...", "critical")
    await stream("Response", "notifying", "Sending alert to #sec-ops...", "medium")
    await stream("Response", "success", "Threat Neutralized. Infrastructure Secure.")

    # 6. Compliance
    await stream("Compliance", "auditing", "Mapping to SOC2 & ISO 27001 controls...")
    if verdict.audit_required:
        await stream("Compliance", "logged", f"Audit record sealed for incident {incident_id[:8]}.")
    logger.info("simulation_complete", incident_id=incident_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host=settings.BIND_HOST, port=settings.PORT)
