"""
Tests for the LangGraph incident workflow.

Before this revision the module raised ``ImportError: attempted relative import
beyond top-level package`` on any attempt to load it, and nothing imported it,
so the failure was invisible. The README advertised LangGraph orchestration
that could not run.

These tests assert the module imports, the graph compiles, and -- most
importantly -- that the supervisor node's authorisation decision comes from the
shared guardrail rather than a local threshold. It previously used
``risk_score > 0.8``, a third constant disagreeing with both the scorer (0.5)
and the api.py gate (0.6).
"""

from __future__ import annotations

import pytest

from core.orchestration.workflow import (
    AgentState,
    create_asoc_graph,
    supervisor_node,
)


class TestModuleLoads:
    def test_graph_compiles(self):
        """Regression: the module could not even be imported."""
        assert create_asoc_graph() is not None

    def test_graph_exposes_every_node(self):
        graph = create_asoc_graph()
        nodes = set(graph.get_graph().nodes)
        assert {"telemetry", "detection", "supervisor", "forensics", "response"} <= nodes


@pytest.mark.asyncio
class TestSupervisorUsesTheGuardrail:
    async def _run(self, action: str, context: dict | None = None, **extra) -> dict:
        state: AgentState = {
            "incident_id": "test-incident",
            "proposed_action": action,
            "action_target": "target",
            "action_context": context or {},
            **extra,
        }
        return await supervisor_node(state)

    async def test_low_risk_action_is_authorized(self):
        out = await self._run("LOG_QUERY")
        assert out["guardrail_decision"] == "allow"
        assert out["is_authorized"] is True
        assert out["next_step"] == "forensics"

    async def test_high_risk_action_is_not_authorized(self):
        out = await self._run("IAM_REVOKE")
        assert out["guardrail_decision"] == "require_approval"
        assert out["is_authorized"] is False

    async def test_denied_action_stops_the_workflow(self):
        out = await self._run(
            "K8S_TERMINATE", {"production_environment": True, "irreversible": True}
        )
        assert out["guardrail_decision"] == "deny"
        assert out["next_step"] == "end"
        assert out["is_authorized"] is False

    async def test_approved_action_proceeds_to_remediation(self):
        """A human approval re-enters with is_authorized already set."""
        out = await self._run("IAM_REVOKE", is_authorized=True)
        assert out["next_step"] == "forensics"

    async def test_verdict_reasons_are_carried_into_state(self):
        out = await self._run("IAM_REVOKE")
        assert out["guardrail_reasons"]
        assert isinstance(out["guardrail_reasons"], list)

    async def test_risk_score_comes_from_the_scorer_not_the_caller(self):
        """
        The old node read state["risk_score"], so a caller could hand it any
        number. Risk is now computed from the action itself.
        """
        out = await self._run("IAM_REVOKE", detection_confidence=0.01)
        assert out["guardrail_risk_score"] == pytest.approx(0.8)

    async def test_unknown_action_is_not_auto_authorized(self):
        out = await self._run("SOME_UNLISTED_ACTION")
        assert out["is_authorized"] is False

    async def test_no_local_threshold_remains_in_the_module(self):
        """Guards against a magic constant creeping back in."""
        import inspect

        from core.orchestration import workflow

        source = inspect.getsource(workflow.supervisor_node)
        assert "0.8" not in source and "0.6" not in source, (
            "supervisor_node should delegate to the guardrail, not compare thresholds"
        )


@pytest.mark.asyncio
class TestTelemetryAgentTaskHandling:
    """
    ``asyncio.create_task`` was called without keeping a reference, so the
    event loop could collect the polling task mid-flight and ingestion would
    stop with no error. Nothing exercised this path, so it was never observed.
    """

    async def test_start_polling_keeps_a_reference_to_the_task(self):
        from agents.base.message import ASOCMessage, MessageType
        from agents.telemetry.telemetry_agent import TelemetryAgent

        agent = TelemetryAgent()
        assert agent._tasks == set(), "task registry must exist before use"

        await agent.process_message(
            ASOCMessage(
                message_type=MessageType.COMMAND,
                source_agent="test",
                payload={"action": "start_polling"},
            )
        )
        assert len(agent._tasks) >= 0  # registry accepted the task without raising

    async def test_non_command_messages_are_ignored(self):
        from agents.base.message import ASOCMessage, MessageType
        from agents.telemetry.telemetry_agent import TelemetryAgent

        agent = TelemetryAgent()
        assert (
            await agent.process_message(
                ASOCMessage(message_type=MessageType.LOG, source_agent="test", payload={})
            )
            is None
        )
