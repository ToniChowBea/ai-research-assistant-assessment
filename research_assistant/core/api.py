import uuid

from fastapi import APIRouter, HTTPException, Query

from research_assistant.core.types import (
    AuditRecord,
    QueryRequest,
    QueryResponse,
    Researcher,
)
from research_assistant.agent.engine import run_agent
from research_assistant.governance import apply_response_policies
from research_assistant.audit import get_audit, list_audit, persist_audit
from research_assistant.data_api import lookups

router = APIRouter()


# ----- Query -----------
@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    researcher: str | None = Query(
        default=None, description="Optional researcher username"
    ),
) -> QueryResponse:
    trace_id = uuid.uuid4().hex[:8]
    run = await run_agent(body.question, trace_id, researcher)
    governed = await apply_response_policies(run, {"researcher": researcher})
    await persist_audit(trace_id, body.question, governed, researcher)
    audit = await get_audit(trace_id)
    return QueryResponse(
        answer=governed["answer"],
        sources=governed["sources"],
        trace_id=trace_id,
        audit=audit,
    )


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
