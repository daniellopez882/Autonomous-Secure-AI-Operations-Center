"""
Tests for the action guardrail.

This is the security control the project exists to demonstrate, and before this
revision it was not exercised at all: ``RiskScorer`` was imported by nothing,
the rego policy was evaluated by nothing, and the live gate in api.py was
``if risk_score > 0.6:  # Threshold for demo``.

The three also disagreed. These tests pin the decision table, the alias
resolution, and parity between the Python authority and the rego file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.simulation.scenarios import SCENARIOS
from guardrails.decision import (
    ACTION_ALIASES,
    APPROVAL_THRESHOLD,
    DENY_THRESHOLD,
    DESTRUCTIVE_ACTIONS,
    POLICY_PARITY_CASES,
    ActionRequest,
    Decision,
    evaluate_action,
)
from guardrails.risk_scoring.scorer import RiskLevel, RiskScorer

REGO = Path(__file__).resolve().parents[2] / "guardrails" / "policies" / "action_policy.rego"

# The action types RiskScorer assigns an explicit base score to. Anything else
# falls through to its 0.5 default, which is what silently happened to the
# scenario actions before aliases existed.
SCORED_ACTIONS = frozenset(
    {
        "IAM_REVOKE",
        "IAM_CREATE",
        "K8S_ISOLATE",
        "K8S_TERMINATE",
        "NETWORK_BLOCK",
        "LOG_QUERY",
        "ALERT_CREATE",
    }
)


class TestDecisionTable:
    @pytest.mark.parametrize("action_type,context,expected", POLICY_PARITY_CASES)
    def test_expected_decision(self, action_type, context, expected):
        verdict = evaluate_action(ActionRequest(action_type, "target", context))
        assert verdict.decision is expected, verdict.reasons

    def test_read_only_actions_need_no_approval(self):
        assert evaluate_action(ActionRequest("LOG_QUERY", "logs")).decision is Decision.ALLOW

    def test_destructive_actions_always_require_approval(self):
        """Even if a future score lands below the numeric threshold."""
        for action in DESTRUCTIVE_ACTIONS:
            verdict = evaluate_action(ActionRequest(action, "t"))
            assert verdict.decision is not Decision.ALLOW, action

    def test_deny_outranks_approval(self):
        """A catastrophic action must not be approvable by clicking a button."""
        verdict = evaluate_action(
            ActionRequest(
                "K8S_TERMINATE",
                "prod-db",
                {"production_environment": True, "irreversible": True},
            )
        )
        assert verdict.decision is Decision.DENY

    def test_emergency_override_downgrades_deny_to_approval(self):
        verdict = evaluate_action(
            ActionRequest(
                "K8S_TERMINATE",
                "prod-db",
                {"production_environment": True, "irreversible": True},
                emergency_override=True,
            )
        )
        assert verdict.decision is Decision.REQUIRE_APPROVAL

    def test_unknown_action_is_not_silently_allowed(self):
        """An unrecognised action takes the 0.5 default, which needs approval."""
        verdict = evaluate_action(ActionRequest("SOMETHING_NEW", "t"))
        assert verdict.decision is Decision.REQUIRE_APPROVAL

    def test_context_escalates_risk(self):
        plain = evaluate_action(ActionRequest("NETWORK_BLOCK", "t")).risk_score
        loaded = evaluate_action(
            ActionRequest(
                "NETWORK_BLOCK", "t", {"production_environment": True, "irreversible": True}
            )
        ).risk_score
        assert loaded > plain


class TestVerdictContents:
    def test_verdict_explains_itself(self):
        verdict = evaluate_action(ActionRequest("IAM_REVOKE", "admin"))
        assert verdict.reasons
        assert any("IAM_REVOKE" in r for r in verdict.reasons)

    def test_non_trivial_actions_are_audited(self):
        assert evaluate_action(ActionRequest("IAM_REVOKE", "admin")).audit_required is True

    def test_trivial_actions_are_not_audited(self):
        assert evaluate_action(ActionRequest("LOG_QUERY", "logs")).audit_required is False

    def test_serialisable_for_the_websocket(self):
        d = evaluate_action(ActionRequest("IAM_REVOKE", "admin")).to_dict()
        assert set(d) == {
            "decision",
            "risk_score",
            "risk_level",
            "action_type",
            "reasons",
            "audit_required",
        }
        assert isinstance(d["reasons"], list)

    def test_may_execute_now_only_for_allow(self):
        assert evaluate_action(ActionRequest("LOG_QUERY", "l")).may_execute_now is True
        assert evaluate_action(ActionRequest("IAM_REVOKE", "a")).may_execute_now is False


class TestActionAliases:
    """Scenario action names were absent from the scorer's table entirely."""

    @pytest.mark.parametrize("alias,canonical", sorted(ACTION_ALIASES.items()))
    def test_alias_resolves(self, alias, canonical):
        assert evaluate_action(ActionRequest(alias, "t")).action_type == canonical

    def test_alias_scores_as_its_canonical_action(self):
        assert (
            evaluate_action(ActionRequest("ISOLATE_INSTANCE", "t")).risk_score
            == evaluate_action(ActionRequest("K8S_ISOLATE", "t")).risk_score
        )

    def test_every_scenario_action_is_known_to_the_scorer(self):
        """Regression: ISOLATE_INSTANCE and BLOCK_IP silently took the default."""
        for scenario in SCENARIOS:
            canonical = ACTION_ALIASES.get(scenario.action, scenario.action)
            assert canonical in SCORED_ACTIONS, (
                f"{scenario.name}: {scenario.action} -> {canonical} "
                "is not in the risk scoring table, so it would take the 0.5 default"
            )

    @pytest.mark.parametrize(
        "action,expected_base",
        [
            ("IAM_REVOKE", 0.8),
            ("IAM_CREATE", 0.6),
            ("K8S_ISOLATE", 0.7),
            ("K8S_TERMINATE", 0.9),
            ("NETWORK_BLOCK", 0.5),
            ("LOG_QUERY", 0.1),
            ("ALERT_CREATE", 0.2),
        ],
    )
    def test_scored_actions_have_their_documented_base_score(self, action, expected_base):
        """
        Pins SCORED_ACTIONS to the scorer's real table. If a base score is
        changed or an entry removed, this fails rather than the constant above
        quietly going stale.
        """
        assert RiskScorer.score_action(action, {}) == pytest.approx(expected_base)

    def test_scored_actions_constant_covers_the_whole_table(self):
        assert SCORED_ACTIONS == {
            "IAM_REVOKE",
            "IAM_CREATE",
            "K8S_ISOLATE",
            "K8S_TERMINATE",
            "NETWORK_BLOCK",
            "LOG_QUERY",
            "ALERT_CREATE",
        }

    def test_unknown_action_takes_the_default(self):
        assert RiskScorer.score_action("__not_a_real_action__", {}) == pytest.approx(0.5)


class TestScorer:
    def test_score_is_bounded(self):
        score = RiskScorer.score_action(
            "K8S_TERMINATE",
            {
                "production_environment": True,
                "affects_multiple_resources": True,
                "irreversible": True,
            },
        )
        assert score == 1.0

    @pytest.mark.parametrize(
        "score,level",
        [
            (0.1, RiskLevel.LOW),
            (0.45, RiskLevel.MEDIUM),
            (0.7, RiskLevel.HIGH),
            (0.9, RiskLevel.CRITICAL),
        ],
    )
    def test_risk_levels(self, score, level):
        assert RiskScorer.get_risk_level(score) is level

    def test_scorer_and_guardrail_agree_on_approval(self):
        """The gate must not drift from the scorer's own threshold."""
        for action in ("LOG_QUERY", "ALERT_CREATE", "NETWORK_BLOCK", "IAM_CREATE"):
            score = RiskScorer.score_action(action, {})
            verdict = evaluate_action(ActionRequest(action, "t"))
            if RiskScorer.requires_approval(score):
                assert verdict.decision is not Decision.ALLOW, action
            else:
                assert verdict.decision is Decision.ALLOW, action


class TestRegoParity:
    """
    The rego file is deployed to an external OPA. It must encode the same
    thresholds as the Python authority, or the two will diverge in production.
    """

    def test_rego_file_exists(self):
        assert REGO.is_file()

    def test_thresholds_match(self):
        text = REGO.read_text(encoding="utf-8")
        approval = re.search(r"approval_threshold\s*:=\s*([0-9.]+)", text)
        deny = re.search(r"deny_threshold\s*:=\s*([0-9.]+)", text)
        assert approval and deny, "thresholds not declared in the rego policy"
        assert float(approval.group(1)) == APPROVAL_THRESHOLD
        assert float(deny.group(1)) == DENY_THRESHOLD

    def test_destructive_set_matches(self):
        text = REGO.read_text(encoding="utf-8")
        block = re.search(r"destructive_actions\s*:=\s*\{([^}]*)\}", text)
        assert block, "destructive_actions not declared in the rego policy"
        in_rego = {a.strip().strip('"') for a in block.group(1).split(",") if a.strip()}
        assert in_rego == set(DESTRUCTIVE_ACTIONS)

    def test_aliases_match(self):
        text = REGO.read_text(encoding="utf-8")
        block = re.search(r"action_aliases\s*:=\s*\{(.*?)\n\}", text, re.S)
        assert block, "action_aliases not declared in the rego policy"
        pairs = dict(re.findall(r'"([A-Z0-9_]+)":\s*"([A-Z0-9_]+)"', block.group(1)))
        assert pairs == dict(ACTION_ALIASES)
