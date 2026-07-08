import asyncpg

from research_assistant.data_api import guardrails
from research_assistant.data_api.introspection import describe_schema
from research_assistant.db.session import get_ro_pool
from research_assistant.governance import apply_policies
from research_assistant.governance.engine import SUPPRESSION_NOTICE, AnalyticalResult

_AGGREGATES = {"count", "avg", "sum", "min", "max"}
_OPS = {"=": "=", "!=": "<>", ">": ">", ">=": ">=", "<": "<", "<=": "<="}


def _governed(
    dataset_id: str | None, sql: str, rows: list[dict], record_count: int
) -> dict:
    governed = apply_policies(
        AnalyticalResult(rows=rows, record_count=record_count),
        {"dataset_id": dataset_id},
    )
    triggered = [
        {"policy": d.policy, "action": d.action, "reason": d.reason}
        for d in governed.decisions
        if d.action != "allow"
    ]
    payload = {
        "dataset_id": dataset_id,
        "sql": sql,
        "record_count": None if governed.suppressed else record_count,
        "suppressed": governed.suppressed,
        "rows": governed.rows,
        "governance": triggered,
    }

    # ----- Suppressed Result -----------
    # Doing this as the agent thinks suppression == failure and
    # keeps retrying until guardrails terminate it.
    if governed.suppressed:
        payload["notice"] = SUPPRESSION_NOTICE

    return payload


# ------------------------------------
# --- Run analysis
# ------------------------------------
async def run_analysis(
    dataset_id: str,
    metric: str,
    column: str | None = None,
    group_by: str | None = None,
    filters: list[dict] | None = None,
) -> dict:
    schema = await describe_schema(dataset_id)
    # ----- No data in dataset -----------
    if not schema.get("has_data"):
        return schema

    # ----- Validation -----------
    valid_cols = {c["name"] for c in schema["columns"]}
    metric = metric.lower()
    if metric not in _AGGREGATES:
        return {
            "error": f"Unknown metric '{metric}', choose one of: {sorted(_AGGREGATES)}"
        }
    if metric != "count":
        if not column:
            return {
                "error": f"Metric {metric} requires a column. Columns: {sorted(valid_cols)}"
            }
        if column not in valid_cols:
            return {
                "error": f"Column {column} does not exist. Columns: {sorted(valid_cols)}"
            }
    if group_by and group_by not in valid_cols:
        return {
            "error": f"group_by column '{group_by}' does not exist. Columns: {sorted(valid_cols)}"
        }

    # ----- Filter Construction -----------
    where_parts: list[str] = []
    params: list = []
    for f in filters or []:
        col, op, value = f.get("column"), f.get("op", "="), f.get("value")
        if col not in valid_cols:
            return {
                "error": f"filter column '{col}' does not exist. Columns: {sorted(valid_cols)} "
            }
        if op not in _OPS:
            return {"error": f"Filter op '{op}' not allowed. Allowed: {sorted(_OPS)}."}

        params.append(value)
        where_parts.append(f"{col} {_OPS[op]} ${len(params)}")

    # ----- SQL construction -----------
    agg = "COUNT(*)" if metric == "count" else f"{metric.upper()}({column})"
    alias = "count" if metric == "count" else f"{metric}_{column}"
    table = schema["table"]
    where = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

    if group_by:
        sql = (
            f"SELECT {group_by}, {agg} AS {alias}, COUNT(*) AS record_count "
            f"FROM {table}{where} GROUP BY {group_by} ORDER BY {group_by}"
        )

    else:
        sql = f"SELECT {agg} AS {alias}, COUNT(*) AS record_count FROM {table}{where}"

    # ----- Execute -----------
    pool = await get_ro_pool()
    try:
        records = await pool.fetch(sql, *params)
    except asyncpg.PostgresError as e:
        return {"error": f"Query failed: {e}", "sql": sql}

    rows = guardrails.shape_rows(records)
    record_count = sum(r["record_count"] for r in rows) if rows else 0
    return _governed(schema["dataset_id"], sql, rows, record_count)
