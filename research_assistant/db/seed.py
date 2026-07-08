import asyncio
import json
import asyncpg
from pathlib import Path
from research_assistant.config import get_settings

MOCK_DATA = Path(__file__).resolve().parents[2] / "mock-data"
SCHEMA = Path(__file__).with_name("schema.sql")


def _pg_type(value: object) -> str:
    """Map a json sample value to a pg column type."""
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INT"
    if isinstance(value, float):
        return "REAL"
    return "TEXT"


def _load(name: str) -> object:
    return json.loads((MOCK_DATA / name).read_text())


async def seed() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(SCHEMA.read_text())
        # ----- Metadata tables -----------
        for d in _load("datasets.json"):
            await conn.execute(
                """INSERT INTO datasets VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (id) DO NOTHING""",
                d["id"],
                d["name"],
                d["description"],
                d["records"],
                d["restricted"],
                json.dumps(d["fields"]),
            )

        # ----- Project tables -----------
        for p in _load("projects.json"):
            await conn.execute(
                """INSERT INTO projects VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (id) DO NOTHING""",
                p["id"],
                p["title"],
                p["status"],
                p["principal_investigator"],
                p["organisation"],
            )
            for ds in p["datasets"]:
                await conn.execute(
                    """INSERT INTO project_x_datasets VALUES ($1, $2)
                       ON CONFLICT DO NOTHING""",
                    p["id"],
                    ds,
                )
        # ----- Researcher tables -----------
        for r in _load("researchers.json"):
            await conn.execute(
                """INSERT INTO researchers VALUES ($1, $2, $3)
                   ON CONFLICT (username) DO NOTHING""",
                r["username"],
                r["display_name"],
                r["role"],
            )
            for prj in r["projects"]:
                await conn.execute(
                    """INSERT INTO researcher_x_projects VALUES ($1, $2)
                       ON CONFLICT DO NOTHING""",
                    r["username"],
                    prj,
                )

        # ----- Per-dataset row tables -----------
        for ds_id, payload in _load("sample_query_results.json").items():
            rows = payload["rows"]
            if not rows:
                continue
            table = ds_id.lower()
            cols = {name: _pg_type(value) for name, value in rows[0].items()}
            col_ddl = ", ".join(f"{name} {typ}" for name, typ in cols.items())
            await conn.execute(f"DROP TABLE IF EXISTS {table}")
            await conn.execute(f"CREATE TABLE {table} ({col_ddl})")
            names = list(cols)
            placeholders = ", ".join(f"${i + 1}" for i in range(len(names)))
            await conn.executemany(
                f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders})",
                [tuple(row[n] for n in names) for row in rows],
            )
        # ----- Grant permissions -----------
        await conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO ra_readonly")
        print("Seed complete.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
