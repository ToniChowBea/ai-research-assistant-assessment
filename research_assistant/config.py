from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = ""
    database_url_ro: str = ""
    llm_model: str = "openai:gpt-4o-mini"
    mcp_server_url: str = "http://localhost:8001/mcp"
    governance_min_records: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
