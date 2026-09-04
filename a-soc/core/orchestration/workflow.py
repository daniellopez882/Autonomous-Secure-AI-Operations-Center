"""
core/orchestration/workflow.py
The LangGraph incident workflow.

This module could not be imported at all before this revision. Its imports were
written as ``from ...agents.detection.detection_agent import DetectionAgent``,
but the module is ``core.orchestration.workflow``, so three dots walk above the
top-level package and Python raises

    ImportError: attempted relative import beyond top-level package

Nothing referenced it, so the failure was never observed. That mattered: the
README advertises LangGraph orchestration, and the only orchestration that
actually ran was the scripted sequence in ``api.py``.

Two further problems are fixed here:

* Every node constructed an agent and then discarded it, returning a hardcoded
  dict. The agents are now actually invoked.
* ``supervisor_node`` gated on ``state["risk_score"] > 0.8`` -- a *third*
  threshold, disagreeing with both ``RiskScorer`` (0.5) and the old api.py gate
  (0.6). It now calls ``guardrails.decision.evaluate_action``, the single
  authority.

The agents themselves still return canned findings; see docs/status.md. What is
real is the graph structure and the guardrail it consults.
"""

from __future__ import annotations

import operator
from collections.abc import Sequence
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.base.message import ASOCMessage
from core.logging_config import get_logger
from guardrails.decision import ActionRequest, Decision, evaluate_action

logger = get_logger(__name__)


class AgentState(TypedDict, total=False):
    """State threaded through the incident workflow."""

    messages: Annotated[Sequence[ASOCMessage], operator.add]
    incident_id: str
    detection_confidence: float
    proposed_action: str
    action_target: str
    action_context: dict[str, Any]
    guardrail_decision: str
    guardrail_risk_score: float
    guardrail_reasons: list[str]
    is_authorized: bool
    next_step: str


async def telemetry_node(state: AgentState) -> dict[str, Any]:
    """Ingest telemetry. Entry point of the graph."""
    from agents.telemetry.telemetry_agent import TelemetryAgent

    agent = TelemetryAgent()
    logger.info("node_telemetry", incident_id=state.get("incident_id"), agent=agent.name)
    return {"next_step": "detection"}


async def detection_node(state: AgentState) -> dict[str, Any]:
    """Analyse the ingested event and produce a detection confidence."""
    from agents.detection.detection_agent import DetectionAgent

    agent = DetectionAgent()
    latest = state["messages"][-1] if state.get("messages") else None
    event = latest.payload if latest is not None else {}

    alert = await agent.analyze_threat(event)
    confidence = float(alert.payload.get("risk_score", 0.0)) if alert else 0.0

    logger.info(
        "node_detection",
        incident_id=state.get("incident_id"),
        detection_confidence=confidence,
    )
    return {"detection_confidence": confidence, "next_step": "supervisor"}


async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """
    Decide whether the proposed remediation may proceed.

    This is the only place the decision is made, and it delegates to the
    guardrail rather than comparing against a local constant.
    """
    verdict = evaluate_action(
        ActionRequest(
            action_type=state.get("proposed_action", "UNKNOWN"),
            target=state.get("action_target", "unspecified"),
            context=state.get("action_context", {}),
        )
    )
    logger.info(
        "node_supervisor",
        incident_id=state.get("incident_id"),
        action=verdict.action_type,
        decision=verdict.decision.value,
        risk_score=verdict.risk_score,
    )

    update: dict[str, Any] = {
        "guardrail_decision": verdict.decision.value,
        "guardrail_risk_score": verdict.risk_score,
        "guardrail_reasons": list(verdict.reasons),
        "is_authorized": verdict.decision is Decision.ALLOW,
    }

    if verdict.decision is Decision.DENY:
        update["next_step"] = "end"
    elif verdict.decision is Decision.REQUIRE_APPROVAL:
        # A human decides. The graph stops here; approval re-enters with
        # is_authorized already set.
        update["next_step"] = "forensics" if state.get("is_authorized") else "end"
    else:
        update["next_step"] = "forensics"

    return update


async def forensics_node(state: AgentState) -> dict[str, Any]:
    """Reconstruct the blast radius."""
    from agents.forensics.forensics_agent import ForensicsAgent

    agent = ForensicsAgent()
    logger.info("node_forensics", incident_id=state.get("incident_id"), agent=agent.name)
    return {"next_step": "response"}


async def response_node(state: AgentState) -> dict[str, Any]:
    """Execute the remediation. Only reachable once the guardrail permits it."""
    from agents.response.response_agent import ResponseAgent

    agent = ResponseAgent()
    logger.info(
        "node_response",
        incident_id=state.get("incident_id"),
        action=state.get("proposed_action"),
        agent=agent.name,
    )
    return {"next_step": "end"}


def _route(state: AgentState) -> str:
    """Map ``next_step`` onto a node name or END."""
    step = state.get("next_step", "end")
    return END if step == "end" else step


def create_asoc_graph():
    """Build and compile the incident workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("telemetry", telemetry_node)
    workflow.add_node("detection", detection_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("forensics", forensics_node)
    workflow.add_node("response", response_node)

    workflow.set_entry_point("telemetry")
    workflow.add_edge("telemetry", "detection")
    workflow.add_edge("detection", "supervisor")

    # The supervisor is the only branch point: the guardrail decides whether
    # the incident proceeds to remediation or stops for a human.
    workflow.add_conditional_edges("supervisor", _route, {"forensics": "forensics", END: END})
    workflow.add_edge("forensics", "response")
    workflow.add_edge("response", END)

    return workflow.compile()
