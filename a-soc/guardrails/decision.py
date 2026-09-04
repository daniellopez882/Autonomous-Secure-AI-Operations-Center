"""
guardrails/decision.py
The single place that decides whether a proposed action may execute.

Before this module existed the pieces were present but disconnected:

* ``guardrails/risk_scoring/scorer.py`` defined ``RiskScorer`` and was imported
  by nothing.
* ``guardrails/policies/action_policy.rego`` encoded the real policy and was
  evaluated by nothing.
* The actual gate in ``api.py`` was ``if risk_score > 0.6:  # Threshold for
  demo`` -- a magic number that agreed with neither.

The three also disagreed with each other. ``RiskScorer.requires_approval``
triggers at ``>= 0.5``; the rego ``require_approval`` rule only fires for
``0.5 <= score < 0.8``, so a 0.9-risk destructive action matched no approval
rule at all. And the action names used by the scenarios (``ISOLATE_INSTANCE``,
``BLOCK_IP``) were absent from the scorer's table, so they silently fell
through to its 0.5 default.

This module is the one authority. The rego file remains the deployable policy
for an external OPA sidecar; ``POLICY_PARITY_CASES`` pins the two to the same
answers so they cannot drift apart unnoticed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from guardrails.risk_scoring.scorer import RiskLevel, RiskScorer


class Decision(str, Enum):
    """What the guardrail permits for a proposed action."""

    ALLOW = "allow"  # execute immediately
    REQUIRE_APPROVAL = "require_approval"  # execute only after a human approves
    DENY = "deny"  # never execute, approval cannot override


# Canonical action identifiers. The scenarios previously used names that did
# not appear in the scorer's table; aliases keep the older names working while
# resolving them to something the policy actually knows about.
ACTION_ALIASES: dict[str, str] = {
    "ISOLATE_INSTANCE": "K8S_ISOLATE",
    "BLOCK_IP": "NETWORK_BLOCK",
    "TERMINATE_INSTANCE": "K8S_TERMINATE",
    "REVOKE_CREDENTIALS": "IAM_REVOKE",
}

# Actions that cannot be undone by re-running the opposite action.
DESTRUCTIVE_ACTIONS: frozenset[str] = frozenset({"K8S_TERMINATE", "K8S_ISOLATE", "IAM_REVOKE"})

# Above this, a destructive action is refused outright unless an emergency
# override is presented. Mirrors the rego `deny` rule.
DENY_THRESHOLD = 0.95

# At or above this, a human must approve. Mirrors `RiskScorer.requires_approval`.
APPROVAL_THRESHOLD = 0.5


@dataclass(frozen=True)
class ActionRequest:
    """A proposed action, as submitted to the guardrail."""

    action_type: str
    target: str
    context: dict[str, Any] = field(default_factory=dict)
    emergency_override: bool = False

    @property
    def canonical_type(self) -> str:
        return ACTION_ALIASES.get(self.action_type, self.action_type)

    @property
    def is_destructive(self) -> bool:
        return self.canonical_type in DESTRUCTIVE_ACTIONS


@dataclass(frozen=True)
class GuardrailVerdict:
    """The guardrail's answer, with the reasoning that produced it."""

    decision: Decision
    risk_score: float
    risk_level: RiskLevel
    action_type: str
    reasons: tuple[str, ...]
    audit_required: bool

    @property
    def may_execute_now(self) -> bool:
        return self.decision is Decision.ALLOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "risk_score": round(self.risk_score, 3),
            "risk_level": self.risk_level.value,
            "action_type": self.action_type,
            "reasons": list(self.reasons),
            "audit_required": self.audit_required,
        }


def evaluate_action(request: ActionRequest) -> GuardrailVerdict:
    """
    Score a proposed action and decide whether it may run.

    Ordering matters: deny is checked before approval, so a catastrophic
    destructive action cannot be waved through by an operator clicking approve.
    """
    canonical = request.canonical_type
    score = RiskScorer.score_action(canonical, request.context)
    level = RiskScorer.get_risk_level(score)
    reasons: list[str] = [f"base risk for {canonical} scored {score:.2f} ({level.value})"]

    if request.is_destructive:
        reasons.append("action is destructive and cannot be automatically undone")

    # 1. Hard denial.
    if score >= DENY_THRESHOLD and request.is_destructive:
        if request.emergency_override:
            reasons.append(
                f"score {score:.2f} >= {DENY_THRESHOLD} would deny, "
                "but an emergency override was presented"
            )
        else:
            reasons.append(f"score {score:.2f} >= {DENY_THRESHOLD} on a destructive action: denied")
            return GuardrailVerdict(
                decision=Decision.DENY,
                risk_score=score,
                risk_level=level,
                action_type=canonical,
                reasons=tuple(reasons),
                audit_required=True,
            )

    # 2. Human approval.
    if score >= APPROVAL_THRESHOLD or request.is_destructive:
        reasons.append(
            f"score {score:.2f} >= {APPROVAL_THRESHOLD}"
            if score >= APPROVAL_THRESHOLD
            else "destructive actions always require approval"
        )
        return GuardrailVerdict(
            decision=Decision.REQUIRE_APPROVAL,
            risk_score=score,
            risk_level=level,
            action_type=canonical,
            reasons=tuple(reasons),
            audit_required=True,
        )

    # 3. Allowed outright.
    reasons.append(f"score {score:.2f} < {APPROVAL_THRESHOLD} and action is not destructive")
    return GuardrailVerdict(
        decision=Decision.ALLOW,
        risk_score=score,
        risk_level=level,
        action_type=canonical,
        reasons=tuple(reasons),
        audit_required=False,
    )


# Cases the Python guardrail and the rego policy must both agree on. The test
# suite asserts these; if the rego file is edited without updating this table,
# the divergence is caught rather than discovered in an incident.
POLICY_PARITY_CASES: tuple[tuple[str, dict[str, Any], Decision], ...] = (
    ("LOG_QUERY", {}, Decision.ALLOW),
    ("ALERT_CREATE", {}, Decision.ALLOW),
    ("NETWORK_BLOCK", {}, Decision.REQUIRE_APPROVAL),
    ("IAM_REVOKE", {}, Decision.REQUIRE_APPROVAL),
    ("K8S_ISOLATE", {}, Decision.REQUIRE_APPROVAL),
    ("K8S_TERMINATE", {}, Decision.REQUIRE_APPROVAL),
    (
        "K8S_TERMINATE",
        {"production_environment": True, "irreversible": True},
        Decision.DENY,
    ),
)
