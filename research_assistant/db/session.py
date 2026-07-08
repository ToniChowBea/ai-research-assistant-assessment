import asyncpg
from research_assistant.config import get_settings

_ro_pool: asyncpg.Pool | None = None
_admin_pool: asyncpg.Pool | None = None


# ----- Read-only pool -----------
async def get_ro_pool() -> asyncpg.Pool:
    """Read-only pool, used for all queries."""
    global _ro_pool
    if _ro_pool is None:
        _ro_pool = await asyncpg.create_pool(
            get_settings().database_url_ro,
            min_size=1,
            max_size=5,
            server_settings={"statement_timeout": "5000"},
        )
    return _ro_pool


# ----- Write-capable pool -----------
async def get_admin_pool() -> asyncpg.Pool:
    """Write-capable pool, used for audit."""
    global _admin_pool
    if _admin_pool is None:
        _admin_pool = await asyncpg.create_pool(
            get_settings().database_url, min_size=1, max_size=2
        )
    return _admin_pool
