# NHS AI Research Assistant

An AI research assistant for a regional NHS Research & Analytics Platform. Researchers ask
questions in plain English (e.g. _"Which datasets relate to diabetes?"_); an agent decides which
tools to call, every data access is governed and least-privilege, and every request returns a
traceable `{answer, sources, trace_id}`.

The system is built in four layers, each with a single job, so the boundary between _reasoning_
and _data_ is physical rather than conventional: **the agent never touches the database.**

## Tech stack

| Layer         | Technology                         | Why                                                                                                                                                  |
| ------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| API           | **FastAPI**                        | Async, typed request/response; auto docs via Scalar at `/docs`.                                                                                      |
| Orchestration | **Plain async** (in `core/api.py`) | A direct `run_agent → govern → audit` pipeline; a durable engine (Inngest/Temporal) drops into the same seam when needed.                            |
| Agent         | **LangGraph**                      | Prebuilt ReAct loop with schema-enforced structured output and native MCP tools; provider-agnostic, so we ship value without re-inventing the wheel. |
| Protocol      | **FastMCP** (streamable HTTP)      | The MCP server runs as its own service — the physical "agent never touches data" boundary.                                                           |
| Data          | **PostgreSQL + asyncpg**           | Real SQL for real analysis; identifiers validated, values parameterised, all reads under a read-only role.                                           |
| Packaging     | **Docker Compose + uv**            | Three services from one image; one command (`make up`); lockfile-reproducible.                                                                       |

## Architecture

A request flows down the layers; the answer comes back up.

```
   POST /query  { question }
         │
         ▼
 ┌─ API (FastAPI)          mints trace_id, delegates all reasoning
 │
 ├─ Orchestration          run_agent → govern → persist_audit  (direct async)
 │
 ├─ Agent (LangGraph)      decides which tools to call
 │
 ├─ MCP server (FastMCP)   11 tools · zero SQL
 │
 ├─ data_api               the only SQL · governance applied here
 │
 └─ Postgres               read-only role
         │
         ▼
   { answer, sources, trace_id }
```

**API** — `core/api.py`

- Endpoints: `POST /query` (`?researcher=` optional), `GET /audit`, `GET /audit/{trace_id}`, `GET /researchers`, `GET /health`
- Delegates all reasoning: mints `trace_id`, runs the pipeline, returns the result

**Orchestration** — inlined in `core/api.py`

- The `/query` handler awaits a direct pipeline: `run_agent → govern → persist_audit`
- Synchronous; a durable engine (Inngest, Temporal) would wrap these three as retryable steps for long-running jobs, without touching agent or tool logic

**Agent** — `agent/engine.py` (LangGraph ReAct)

- Tools loaded from the MCP server; forced through a schema to return `{answer, sources}` (never parsed from prose)
- Recursion limit bounds runaways; prompt strategy is _discover → inspect → analyse_

**MCP server** — `mcp_server/` (FastMCP, streamable HTTP) — thin adapters, **zero SQL**

- Discovery: `list_projects`, `get_project`, `search_projects`, `search_datasets`, `list_datasets`, `get_dataset_metadata`, `list_researchers`
- Introspection: `describe_schema`, `sample_rows`, `list_distinct_values` — read the _real_ schema, no hallucinating
- Analysis: `run_analysis`

**Data layer** — `data_api/` (the only code that runs SQL)

- `run_analysis`: structured builder (`metric` + optional `group_by`, `filters`); identifiers validated against the live schema, values parameterised → **the agent never composes SQL**
- Warehouse model: metadata as linked tables + one typed table per dataset (`ds001`…`ds010`, columns inferred at seed time)
- Governance applied before any result leaves

## Governance

Governance is enforced in the platform, not the prompt — an agent (or any client) cannot talk its
way around it. Policies are a **pluggable registry** (adding one = a new file in
`governance/policies/` plus one line) applied in two tiers:

- **Read-only role** _(database)_ — `data_api` connects as `ra_readonly`, which can only `SELECT`;
  even a hallucinated write is impossible. This is the _irreducible_ guarantee — enforced at the
  layer of ultimate authority, not by a check that could have a bug.
- **`min_records`** _(result tier)_ — suppresses any result built on fewer than the threshold of
  **underlying records** (not output rows), mirroring NHS small-number disclosure control.
- **`grounding`** _(response tier)_ — withholds an answer that cites sources but made no tool call.
- **`researcher_access`** _(response tier)_ — when scoped to a researcher, restricts analysis of
  restricted datasets to that researcher's own projects.

## Observability

Failures can come from any layer, so observability spans two axes, correlated by one `trace_id`:

- **Agent — LangSmith.** The agent's internal reasoning and tool calls (optional, env-driven).
- **Audit — Postgres.** A persistent `audit_log` row per request: id, tools invoked, governance
  decisions, duration, errors, and the requesting researcher (with a minimal profile on the
  single-record read).

## Setup

Requires Docker. Full setup in `GETTING_STARTED.md`.

```bash
make up
```

One command: creates `.env` (LLM key pre-filled), builds the image, starts `postgres`,
`mcp-server` and `api`, and seeds the mock data.

```bash
curl -s localhost:8000/query -H 'content-type: application/json' \
  -d '{"question": "Which datasets relate to diabetes?"}'
# → { "answer": "...", "sources": ["DS001"], "trace_id": "...",
#     "audit": { tools_invoked, governance, duration_ms, researcher, ... } }
```

## Evals

The brief ships 25 evaluation questions, as a real platform would. `evals/` drives them (plus RBAC
cases) through the API and scores **deterministic facts** — `sources` as sets, governance decisions
read from the audit table — guarding against regressions rather than grading prose.

## Project structure

```
research_assistant/
├── main.py         # FastAPI app factory (Scalar docs)
├── config.py       # env-driven settings (pydantic-settings)
├── audit.py        # audit_log read/write
├── core/           # api.py (routes + orchestration) · types.py (request/response schemas)
├── agent/          # engine.py (LangGraph agent) · prompts.py
├── mcp_server/     # server.py (FastMCP, 11 tools) · tools.py (adapters, zero SQL)
├── data_api/       # lookups · introspection · analysis (run_analysis) · guardrails
├── governance/     # engine.py (registry) · policies/ (min_records, grounding, researcher_access)
└── db/             # schema.sql · seed.py · session.py (admin + read-only pools)
evals/              # black-box eval harness (questions + expected facts)
mock-data/          # provided synthetic data (never modified)
```

## Assumptions

- The system serves both general queries and researcher-scoped ones; `?researcher=` identifies, it
  does not authenticate.
- The analyses run on the datasets are known to the engineers (structured `run_analysis` over
  free-form SQL).
- The provided mock data is the whole universe; only DS001–DS010 have analysable rows.

## Limitations

- No response streaming yet; `POST /query` blocks until the run completes.
- DS011–DS020 are metadata-only (no analysable rows).
- `researcher_access` is enforced after the query runs (the read happens; the answer is withheld).
- `min_records` suppresses on total underlying records, not per-group cells.

## Future improvements

- Push RBAC down to a platform-level guardrail so restricted queries never run, rather than being
  withheld after the fact.
- Deterministic source extraction (from run state / tool calls) instead of trusting the agent's
  structured output.
- A durable workflow engine (Inngest, Temporal) for retry-heavy or
  long-running research jobs — without touching agent or tool logic.
- Stream responses to the client so researchers don't have to wait until the full analysis is done.
- Interruption: researchers should be able to interrupt runs.
- Client-side observability so researchers can watch the agent's steps as they happen.
- Test-driven development: a unit/integration suite (governance policies, guardrails, tool-payload
  extraction) alongside the black-box evals, so regressions are caught before a run reaches them.
