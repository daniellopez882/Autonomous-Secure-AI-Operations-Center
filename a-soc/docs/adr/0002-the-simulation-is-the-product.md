# ADR 0002 — The simulation is the product; `docs/status.md` is the contract

**Status:** accepted · **Date:** 2026-09-06 (records the decision made in PR #1)

## Context

The original README described an autonomous security operations centre with
detection, forensics, response and compliance agents acting on a cloud
account. The code did not: the agents return hardcoded findings next to
comments such as `# In a real implementation, we would call the LLM here`,
`BaseAgent.send_message` is `pass`, the telemetry agent's `lookup_events` call
is commented out, and PostgreSQL, Redis, Pinecone, Vault and the Kubernetes
client are declared in `requirements.txt` and `settings.py` and used by
nothing. A reviewer could not tell which claims were load-bearing.

Two ways forward were considered: wire the declared integrations (weeks of
work against real cloud accounts, with nothing to test them on), or state
precisely what runs and make that honest core solid.

## Decision

State it. [`docs/status.md`](../status.md) separates **implemented and
tested** (the guardrail, the risk scorer, the rego parity, the WebSocket
fan-out, the LangGraph graph, the HTTP probes, configuration), **simulated**
(every agent; the incident stream replays three scripted scenarios), and
**declared but not wired** (the five integrations and the k8s manifest). The
README leads with that distinction and links the file.

The simulation drives the dashboard and exercises the guardrail end to end,
so it is treated as the product and tested as such: scenario actions are in
the scorer's table, the feed survives dead clients, `/ready` self-tests the
guardrail. Nothing in the repository connects to a real AWS account, and
nothing pretends to.

The event store (`core/memory/event_store.py`) is described as what it is —
an append-only local JSONL file — not the immutable compliance record its
docstring implied.

## Consequences

- Adding a real integration means moving a row in `status.md` from
  "declared" to "implemented" together with the tests that prove it; the
  file is reviewed with the code.
- The unused dependencies remain declared until either wired or removed; the
  README says they are inert. Removing them is a smaller follow-up.
- Anyone evaluating the repository can see in one screen that it is a
  guardrail with a simulated SOC around it, which is what it is.
