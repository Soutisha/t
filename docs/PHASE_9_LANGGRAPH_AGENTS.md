# Phase 9 — LangGraph Agentic Workflows

## Goal
Introduce a supervised multi-agent orchestration layer that delegates requests to narrowly scoped specialist agents. The initial release is intentionally read-only. Agents query existing platform records and approved knowledge sources; they do not directly change rewards, inventory, fitment status, profiles or dealer records.

## Supervisor and specialist agents
- **Supervisor/router:** deterministic intent classification and routing.
- **Knowledge agent:** retrieves only approved Phase 8 knowledge chunks and returns source-cited extractive answers; abstains when no evidence meets the retrieval threshold.
- **Fitment agent:** searches only existing `verified` fitment records. It never infers compatibility from product text or semantic similarity.
- **Rewards agent:** calculates the signed-in mechanic's balance from their own reward ledger; no cross-user access.
- **Tool Bank agent:** reads active tools and recorded inventory; it does not reserve or dispatch.
- **Mechanic support agent:** reads the signed-in user's mechanic profile and verification status.
- **Action planner:** detects mutation requests such as reserve, redeem, approve, dispatch, update or award. It blocks execution and marks the request as requiring a separate human-approved workflow.
- **General assistant:** explains supported capabilities and asks for a narrower request.

## Orchestration
`run_agent_workflow()` uses a LangGraph `StateGraph` when LangGraph is installed. It has a supervisor node, conditional routing to a specialist node, and a terminal edge. If the optional dependency is absent, a deterministic fallback executes the same nodes and routing so local development and tests remain usable.

Install the optional dependency with:
```bash
pip install -r backend/requirements-agentic.txt
```

The base backend remains installable without LangGraph. The current verification environment did not have LangGraph installed, so automated tests exercised the deterministic fallback. The LangGraph branch is implemented but must be integration-tested after installing the optional dependency.

## API
- `POST /api/v1/agents/run` — authenticated agent workflow request.
- `GET /api/v1/agents/runs/{run_id}` — retrieve only the signed-in user's run.
- `POST /api/v1/agents/runs/{run_id}/feedback` — record feedback in the run trace.

Every run stores the request, selected intent, response, status, agent trace, user ID and approval-required flag. The response reports the engine used and explicitly reports that no side effects were performed.

## Safety and boundaries
- All specialist tools are read-only database queries.
- Knowledge retrieval is restricted to approved documents.
- Fitment is a lookup of historical verified records, not an installation approval.
- Rewards are scoped to the authenticated mechanic.
- Tool availability is a snapshot of recorded inventory, not a reservation guarantee.
- Mutating requests are routed to an action planner, blocked, and flagged as requiring human approval. No pending command or approval object is created in this phase.
- No external messaging, payments, inventory reservation, dealer ordering, reward issuance or fitment approval is performed.
- Agent traces are visible to the caller and are stored for audit.

## Current limitations
- Intent classification is deterministic and keyword-based, not an LLM planner.
- LangGraph is optional in this bundle and was not installed in the test environment. Install the optional requirements and run integration tests before deployment.
- No external LLM or tool server is configured.
- Fitment lookup is limited to verified records already present in the database; the platform has no authoritative vehicle compatibility catalogue supplied yet.
- Dealer discovery, geospatial routing, stock availability and external ERP actions are not implemented in this phase.
- The UI is not yet wired to the agent API.
- Human approval is a safety boundary only; the approval inbox and execution workflow are later integration work.

## Verification
- 50 backend Python files pass syntax compilation.
- Full backend test suite passes 23 tests.
- API import, route registration and database metadata registration are checked separately.
- The tests cover intent routing, read-only general assistance, blocked mutation requests, run persistence and per-user run privacy.
