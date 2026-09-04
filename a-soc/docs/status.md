# Implementation status

What in this repository actually runs, and what is a stub. The README describes
the system's shape; this file says how much of it is wired.

Written because the distinction was not discoverable from the code: the agents
carry comments like `# In a real implementation, we would call the LLM here`
alongside hardcoded return values, and a reviewer had no way to tell which
claims were load-bearing.

## Implemented and tested

| Component | Status | Covered by |
|---|---|---|
| Action guardrail (`guardrails/decision.py`) | Real. Scores an action, applies deny/approve/allow precedence, explains itself. | `tests/unit/test_guardrail_policy.py` |
| Risk scorer (`guardrails/risk_scoring/scorer.py`) | Real, deterministic table plus context modifiers. | same |
| Rego policy | Real, and pinned to the Python authority by parity tests. | `TestRegoParity` |
| WebSocket fan-out (`core/realtime/`) | Real. Fault-tolerant, prunes dead clients, times out hung ones. | `tests/unit/test_connection_manager.py` |
| LangGraph workflow (`core/orchestration/workflow.py`) | Graph is real and compiles; the supervisor consults the guardrail. | `tests/unit/test_workflow.py` |
| HTTP probes, policy endpoint, WS auth | Real. | `tests/integration/test_api.py` |
| Configuration | Real, typed, environment-driven. | — |

## Simulated

| Component | What it actually does |
|---|---|
| `agents/detection` | Returns a fixed `risk_score` of 0.85 and a canned reasoning string. No LLM call. |
| `agents/telemetry` | Emits a mock CloudTrail event. The boto3 client is constructed but `lookup_events` is commented out. |
| `agents/forensics`, `agents/response`, `agents/compliance` | Return canned payloads; no cloud API is called. |
| `BaseAgent.send_message` | `pass`. There is no message bus. |
| `api.py` incident stream | Replays one of three scripted scenarios from `core/simulation/scenarios.py`. |

The simulation is the product here: it drives the dashboard and exercises the
guardrail end to end. It is not an autonomous SOC, and nothing in this
repository connects to a real AWS account.

## Declared but not wired

Present in `requirements.txt` and `core/config/settings.py`, imported by nothing
that runs:

- PostgreSQL / SQLAlchemy / asyncpg — `DATABASE_URL` is read, no schema exists
- Redis — `REDIS_URL` is read, nothing caches
- Pinecone — no vector store is created
- Vault — `VAULT_ADDR` is read, no secret is fetched
- Kubernetes client — no cluster call is made
- `k8s/backend.yaml` — a manifest, never applied by anything in this repo

`core/memory/event_store.py` does append events to a local JSONL file, so the
audit trail is real to that extent. It is not immutable, signed, or replicated,
so it does not meet the compliance bar the class docstring implies.

## Known gaps

- No LLM integration despite `LLM_PROVIDER` and three provider keys in settings.
- No authentication on the HTTP API. Only the WebSocket has an optional token.
- No persistence of incidents; state lives in the process.
- The dashboard has no tests.
- `main.py` is a one-shot CLI demo, separate from the API. The container image
  previously ran it by mistake, so nothing listened on port 8000.

## If you want to make it real

In order of value:

1. Wire `DetectionAgent.analyze_threat` to an actual model behind a provider
   interface, with the current canned response as the offline fallback.
2. Persist incidents and verdicts to Postgres; the settings already describe it.
3. Evaluate the rego policy through a real OPA sidecar and compare its verdict
   against `guardrails.decision` at runtime, not only in tests.
4. Add authentication to the HTTP API.
