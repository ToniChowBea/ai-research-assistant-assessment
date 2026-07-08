import json

from research_assistant.db.session import get_admin_pool, get_ro_pool


async def write_audit(
    trace_id: str,
    question: str,
    tools: list[dict],
    governance: list[dict],
    sources: list[str],
    duration_ms: int,
    error: str | None,
    researcher: str | None = None,
) -> None:
    """One audit row per request.
    Takes plain JSON-safe lists so it can run as a durable workflow step."""
    pool = await get_admin_pool()
    await pool.execute(
        """INSERT INTO audit_log
        (trace_id, question, tools_invoked, sources, governance, duration_ms, error, researcher)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        trace_id,
        question,
        json.dumps(tools),
        json.dumps(sources),
        json.dumps(governance),
        duration_ms,
        error,
        researcher,
    )


def _audit_row(row) -> dict:
    """Shape one audit_log row for the API (JSONB columns come back as text)."""
    return {
        "trace_id": row["trace_id"],
        "question": row["question"],
        "tools_invoked": json.loads(row["tools_invoked"]),
        "sources": json.loads(row["sources"]),
        "governance": json.loads(row["governance"]),
        "duration_ms": row["duration_ms"],
        "error": row["error"],
        "researcher": row.get("researcher"),
        "created_at": row["created_at"],
    }


async def list_audit(limit: int = 50) -> list[dict]:
    """Recent audit records, newest first (read-only role)."""
    pool = await get_ro_pool()
    rows = await pool.fetch(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT $1", limit
    )
    return [_audit_row(r) for r in rows]


async def get_audit(trace_id: str) -> dict | None:
    """One audit record by trace id (plus a minimal researcher profile), or None."""
    pool = await get_ro_pool()
    row = await pool.fetchrow("SELECT * FROM audit_log WHERE trace_id = $1", trace_id)
    if row is None:
        return None
    record = _audit_row(row)
    if record["researcher"]:
        profile = await pool.fetchrow(
            "SELECT username, display_name, role FROM researchers WHERE username = $1",
            record["researcher"],
        )
        record["researcher_profile"] = dict(profile) if profile else None
    return record


async def persist_audit(
    trace_id: str, question: str, governed: dict, researcher: str | None = None
) -> None:
    """Write the audit row for a governed run (the workflow's final step)."""
    await write_audit(
        trace_id,
        question,
        governed["tools"],
        governed["governance"],
        governed["sources"],
        governed["duration_ms"],
        governed["error"],
        researcher,
    )
