# Getting Started

From a fresh clone to a working assistant, using only `make`. Run `make help` to list every target.

**Prerequisite:** Docker (Docker Desktop / OrbStack). The keys are pre-filled in `.env.example`, so there is nothing else to configure.

---

## 1. Start everything

```bash
make up
make logs # tail logs
```

One command: creates `.env`, builds the image, starts `postgres`, `mcp-server`, `api` and
`inngest`, and seeds the mock data. It runs detached, so the stack keeps running after it returns.

- Watch logs: `make logs` · Stop: `make down` · Wipe the DB: `make down && docker compose down -v`

> **First query returns a 502?** Give it ~10s after `make up` — the Inngest dev server needs a
> moment to sync the workflow functions. Retry and it clears.

---

## 2. Test with curl

**A plain query:**

```bash
curl -s localhost:8000/query \
  -H 'content-type: application/json' \
  -d '{"question":"Which datasets relate to diabetes?"}'
```

```json
{
  "answer": "…Primary Care Diabetes Cohort…",
  "sources": ["DS001"],
  "trace_id": "1de50134"
}
```

**As a researcher** — add `?researcher=<username>` to scope the request to that person's access:

```bash
# Scoped to alice — resolves her own projects
curl -s "localhost:8000/query?researcher=alice" \
  -H 'content-type: application/json' \
  -d '{"question":"Which projects can I access?"}'
```

RBAC in action — analysing a **restricted** dataset outside a researcher's projects is withheld:

```bash
# alice is not on the Sepsis project → the result is withheld
curl -s "localhost:8000/query?researcher=alice" \
  -H 'content-type: application/json' \
  -d '{"question":"Run an analysis on the Sepsis Registry"}'
```

> A researcher who **is** on that project (e.g. `laura`) passes the RBAC check.

Every response carries a `trace_id` — keep it for step 5.

---

## 3. Test from the docs page

1. Open **http://localhost:8000/docs** (the Scalar API reference).
2. Expand **`POST /query`** and click **Test Request**.
3. Edit the `question` in the request body. To test as a researcher, set the `researcher` query
   parameter (e.g. `alice`).
4. Click **Send** — the `{answer, sources, trace_id}` renders in the page.

---

## 4. Monitor a run in Inngest

1. Open **http://localhost:8288** → **Runs**.
2. Open the most recent run to see the durable workflow as a waterfall:
   **`run_agent` → `govern` → `persist_audit`**.
3. Click any step for its input, output, timing, and any retries.

---

## 5. Get the audit for a run

Every request writes one audit row, looked up by its `trace_id`.

**Via curl:**

```bash
curl -s localhost:8000/audit/<trace_id>   # one run: tools invoked, governance decisions, timing, errors, researcher
curl -s localhost:8000/audit              # recent runs, newest first
```

When you supplied `?researcher=`, the single-run record also includes a minimal researcher profile.

**Via the docs page:** open **http://localhost:8000/docs** → **`GET /audit/{trace_id}`** →
**Test Request** → paste the `trace_id` → **Send**.

---

## Local development (host, hot reload)

Prefer running on your machine (auto-reload, per-component logs)? Postgres still runs in Docker;
everything else runs via `uv`.

```bash
make env         # once: create .env
make stack       # postgres + seed + MCP + Inngest + API in one terminal (prefixed logs; Ctrl-C stops all)
```

Finer control: `make db`, `make seed`, `make mcp`, `make api`, `make inngest`, `make inspector`.

---

## Evaluate end-to-end (optional)

```bash
make eval        # POSTs the 25 eval questions (+ RBAC cases), scores sources + governance
```

Prints per-question `PASS`/`FAIL` and latency percentiles against the running API.

---

## Troubleshooting

| Symptom                     | Fix                                                      |
| --------------------------- | -------------------------------------------------------- |
| First `/query` is a 502     | Inngest hasn't synced yet (~10s after `make up`). Retry. |
| Answers say data is missing | The seed didn't run — `make db-seed`.                    |
| `make up` fails on a port   | 5432 / 8000 / 8001 / 8288 already in use — free it.      |
| Want a clean database       | `make down` then `docker compose down -v`.               |
