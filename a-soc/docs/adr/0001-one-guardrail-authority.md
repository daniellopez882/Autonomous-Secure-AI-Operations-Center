# ADR 0001 — One guardrail authority, deny before approval, rego pinned to it

**Status:** accepted · **Date:** 2026-09-06 (records the decision made in PR #1)

## Context

The project exists to gate autonomous response actions. When the work started
the gate was three disagreeing artefacts and one magic number:

- `guardrails/risk_scoring/scorer.py` defined `RiskScorer` (`requires_approval`
  at `>= 0.5`) and was imported by nothing.
- `guardrails/policies/action_policy.rego` encoded the policy for an OPA
  sidecar; its `require_approval` rule fired only for `0.5 <= score < 0.8`, so a
  0.9-risk destructive action matched no approval rule at all. Nothing
  evaluated it.
- `api.py` gated on `if risk_score > 0.6:  # Threshold for demo`; the LangGraph
  supervisor used `0.8`.
- The scenario actions `ISOLATE_INSTANCE` and `BLOCK_IP` were absent from the
  scoring table and silently took the 0.5 default.

There was no single answer to "would this action be permitted?".

## Decision

`guardrails/decision.py` is the one place that decides. It resolves action
aliases, scores through `RiskScorer`, and applies a strict precedence: **deny
before approval** — a denied action cannot be turned into an executed one by a
human clicking approve. Verdicts carry their reasoning so the dashboard and the
audit trail can show *why*.

The rego file stays as the deployable policy for an external OPA sidecar, but
it is not a second authority: `POLICY_PARITY_CASES` in
`tests/unit/test_guardrail_policy.py` (`TestRegoParity`) evaluates both against
the same inputs, and CI runs the rego under OPA, so the two cannot drift apart
unnoticed. `/api/v1/policy/evaluate` exposes a decision without executing it.

## Consequences

- Every caller — HTTP, WebSocket feed, LangGraph supervisor — gets the same
  verdict for the same action; the thresholds live in one table.
- Changing policy means changing `decision.py` **and** the rego, and the parity
  test says so when one is changed without the other.
- The scorer's table is now closed: an unknown action is a test failure, not a
  0.5 default.
- The dashboard's approval button can no longer override a deny; that is the
  point, and it is documented in the threat model (T1).
