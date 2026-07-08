from research_assistant.config import get_settings
from research_assistant.db.session import get_ro_pool
from research_assistant.governance.engine import SUPPRESSION_NOTICE


# ----- Describe schema -----------
async def describe_schema(dataset_id: str) -> dict:
    """Table name + typed columns for a dataset's data table."""
    pool = await get_ro_pool()
    dataset = await pool.fetchrow(
        "SELECT id FROM datasets WHERE upper(id) = upper($1)", dataset_id
    )
    if dataset is None:
        return {"found": False, "error": f"Dataset '{dataset_id}' not found."}
    table = dataset["id"].lower()
    cols = await pool.fetch(
        """SELECT column_name, data_type
           FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = $1
           ORDER BY ordinal_position""",
        table,
    )
    if not cols:
        return {
            "found": True,
            "dataset_id": dataset["id"],
            "has_data": False,
            "message": "No analytical data is available for this dataset (metadata only).",
        }
    return {
        "found": True,
        "dataset_id": dataset["id"],
        "has_data": True,
        "table": table,
        "columns": [{"name": c["column_name"], "type": c["data_type"]} for c in cols],
    }


# ----- Get sample rows -----------
async def sample_rows(dataset_id: str, num_rows: int = 3) -> dict:
    """A few real rows so value formats are visible. num_rows clamped to 1-5.
    Refuses below the disclosure threshold — a sample from a tiny dataset
    IS the dataset (side channel around min_records otherwise)."""
    schema = await describe_schema(dataset_id)
    if not schema.get("has_data"):
        return schema
    pool = await get_ro_pool()
    total = await pool.fetchval(f"SELECT COUNT(*) FROM {schema['table']}")
    if total < get_settings().governance_min_records:
        return {
            "dataset_id": schema["dataset_id"],
            "suppressed": True,
            "governance": [
                {
                    "policy": "min_records",
                    "action": "suppress",
                    "reason": (
                        "Sample rows are unavailable: this dataset holds fewer "
                        "records than the platform's disclosure threshold."
                    ),
                }
            ],
            "notice": SUPPRESSION_NOTICE,
        }
    num_rows = max(1, min(num_rows, 5))
    rows = await pool.fetch(f"SELECT * FROM {schema['table']} LIMIT {num_rows}")
    return {"dataset_id": schema["dataset_id"], "rows": [dict(r) for r in rows]}


# ----- List distinct values -----------
async def list_distinct_values(dataset_id: str, column: str) -> dict:
    """Exact distinct values of one column, for precise filters."""
    schema = await describe_schema(dataset_id)
    if not schema.get("has_data"):
        return schema
    valid = {c["name"] for c in schema["columns"]}
    if column not in valid:
        return {
            "found": False,
            "error": (
                f"Column '{column}' does not exist on {schema['dataset_id']}. "
                f"Valid columns: {sorted(valid)}"
            ),
        }
    pool = await get_ro_pool()
    rows = await pool.fetch(
        f"SELECT DISTINCT {column} AS value FROM {schema['table']} "
        f"ORDER BY value LIMIT 50"
    )
    return {
        "dataset_id": schema["dataset_id"],
        "column": column,
        "values": [r["value"] for r in rows],
    }
