import asyncio
import json
import uuid

import httpx
import inngest
from fastapi import APIRouter, HTTPException, Query

from research_assistant.config import get_settings
from research_assistant.core.types import (
    AuditRecord,
    QueryRequest,
    QueryResponse,
    Researcher,
)
from research_assistant.data_api import lookups
from research_assistant.audit import get_audit, list_audit
from research_assistant.workflow.client import inngest_client

router = APIRouter()

_QUERY_EVENT = "research/query.requested"


# ----- Query -----------
@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    researcher: str | None = Query(
        default=None, description="Optional researcher username"
    ),
) -> QueryResponse:
    """Ask a research question. An optional researcher username applies RBAC scoping."""
    trace_id = uuid.uuid4().hex[:8]
    ids = await inngest_client.send(
        inngest.Event(
            name=_QUERY_EVENT,
            data={
                "question": body.question,
                "trace_id": trace_id,
                "researcher": researcher,
            },
        )
    )
    event_id = ids[0]

    async with httpx.AsyncClient(
        base_url=get_settings().inngest_api_base, timeout=5
    ) as http:
        for _ in range(120):  # ~60s ceiling
            resp = await http.get(f"/v1/events/{event_id}/runs")
            runs = resp.json().get("data", [])
            if runs and runs[0].get("status") in ("Completed", "Failed", "Cancelled"):
                run = runs[0]
                if run["status"] == "Completed":
                    out = run.get("output")
                    if out is None:
                        # "Completed" can be visible before the output is
                        # attached — two writes, not one. Keep polling.
                        await asyncio.sleep(0.2)
                        continue
                    if isinstance(out, str):
                        out = json.loads(out)
                    return QueryResponse(
                        answer=out["answer"],
                        sources=out["sources"],
                        trace_id=trace_id,
                    )
                raise HTTPException(
                    502, f"workflow {run['status'].lower()}: {trace_id}"
                )
            await asyncio.sleep(0.5)
    raise HTTPException(504, f"workflow timed out: {trace_id}")


# ----- Audit -----------
@router.get("/audit", response_model=list[AuditRecord])
async def audit_list(limit: int = Query(50, ge=1, le=500)):
    """Recent audit records, newest first."""
    return await list_audit(limit)


@router.get("/audit/{trace_id}", response_model=AuditRecord)
async def audit_get(trace_id: str):
    """One audit record by trace id (the id returned from POST /query)."""
    record = await get_audit(trace_id)
    if record is None:
        raise HTTPException(404, f"no audit record for trace_id '{trace_id}'")
    return record


# ----- Researchers -----------
@router.get("/researchers", response_model=list[Researcher])
async def list_researchers():
    """All researchers with their role and accessible projects ('*' = admin)."""
    return await lookups.list_researchers()
