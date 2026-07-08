import json
from research_assistant.db.session import get_ro_pool


# ----- List all projects -----------
async def list_projects(status: str | None = None) -> list[dict]:
    """List research projects on the platform"""
    pool = await get_ro_pool()
    if status:
        rows = await pool.fetch(
            "SELECT * FROM projects WHERE lower(status) = lower($1) ORDER BY id",
            status,
        )
    else:
        rows = await pool.fetch("SELECT * FROM projects ORDER by id")
    return [dict(r) for r in rows]


# ----- Get a single project -----------
async def get_project(project_id: str) -> dict:
    """One project + its linked datasets."""
    pool = await get_ro_pool()
    row = await pool.fetchrow(
        "SELECT * FROM projects WHERE upper(id) = upper($1)", project_id
    )
    if row is None:
        return {
            "found": False,
            "error": f"Project '{project_id}' not found.",
        }
    linked = await pool.fetch(
        "SELECT * FROM project_x_datasets WHERE project_id = $1 ORDER BY dataset_id",
        row["id"],
    )
    datasets = [dict(r) for r in linked]
    return {
        "found": True,
        "project": dict(row),
        "datasets": datasets,
    }


# ----- Search projects (keyword) -----------
async def search_projects(query: str) -> list[dict]:
    """Keyword search over project title and organisation (discipline/theme)."""
    pool = await get_ro_pool()
    rows = await pool.fetch(
        """
        SELECT * FROM projects
        WHERE title ILIKE '%' || $1 || '%'
        OR organisation ILIKE '%' || $1 || '%'
        ORDER BY id
        """,
        query,
    )
    return [dict(r) for r in rows]


# ----- Search datasets (Keyword) -----------
async def search_datasets(query: str) -> list[dict]:
    """Keyword search over dataset name, description and field names."""
    pool = await get_ro_pool()
    rows = await pool.fetch(
        """
        SELECT id, name, description, records, restricted, fields
        FROM datasets
        WHERE name ILIKE '%' || $1 || '%'
        OR description ILIKE '%' || $1 || '%'
        OR fields::text ILIKE '%' || $1 || '%'
        ORDER BY id
        """,
        query,
    )
    return [{**dict(r), "fields": json.loads(r["fields"])} for r in rows]


# ----- List all datasets (discovery) -----------
async def list_datasets() -> list[dict]:
    """Every dataset's id, name, record count and restricted flag."""
    pool = await get_ro_pool()
    rows = await pool.fetch(
        "SELECT id, name, records, restricted FROM datasets ORDER BY id"
    )
    return [dict(r) for r in rows]


# ----- Get dataset metadata -----------
async def get_dataset_metadata(dataset_id: str) -> dict:
    """One dataset's catalogue entry"""
    pool = await get_ro_pool()
    row = await pool.fetchrow(
        "SELECT * FROM datasets WHERE upper(id) = upper($1)", dataset_id
    )
    if row is None:
        return {"found": False, "error": f"Dataset '{dataset_id}' not found."}
    return {"found": True, **dict(row), "fields": json.loads(row["fields"])}


# ----- List researchers -----------
async def list_researchers(username: str | None = None) -> list[dict]:
    """Researchers with role and project access ('*' = all projects)."""
    pool = await get_ro_pool()
    base = """
        SELECT r.username, r.display_name, r.role,
               array_remove(array_agg(rp.project_id ORDER BY rp.project_id), NULL) AS projects
        FROM researchers r
        LEFT JOIN researcher_x_projects rp ON rp.username = r.username
    """
    tail = " GROUP BY r.username, r.display_name, r.role ORDER BY r.username"
    if username:
        rows = await pool.fetch(
            base + " WHERE lower(r.username) = lower($1)" + tail, username
        )
    else:
        rows = await pool.fetch(base + tail)
    return [dict(r) for r in rows]


# ----- Researcher access footprint (RBAC) -----------
async def get_researcher_access(username: str) -> dict:
    """A researcher's access: found?, admin? ('*'), and their projects' dataset ids."""
    pool = await get_ro_pool()
    exists = await pool.fetchrow(
        "SELECT 1 FROM researchers WHERE username = $1", username
    )
    if exists is None:
        return {"found": False, "is_admin": False, "dataset_ids": []}
    projects = [
        r["project_id"]
        for r in await pool.fetch(
            "SELECT project_id FROM researcher_x_projects WHERE username = $1", username
        )
    ]
    if "*" in projects:
        return {"found": True, "is_admin": True, "dataset_ids": []}
    rows = await pool.fetch(
        "SELECT dataset_id FROM project_x_datasets WHERE project_id = ANY($1::text[])",
        projects,
    )
    return {
        "found": True,
        "is_admin": False,
        "dataset_ids": [r["dataset_id"] for r in rows],
    }
