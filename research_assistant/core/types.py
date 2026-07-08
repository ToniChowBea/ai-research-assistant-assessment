from datetime import datetime

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=1, description="Natural language research question"
    )


class AuditRecord(BaseModel):
    """One per-request audit row (requirement #5)."""

    trace_id: str
    question: str
    tools_invoked: list[dict]
    sources: list[str]
    governance: list[dict]
    duration_ms: int | None
    error: str | None
    researcher: str | None = None
    researcher_profile: dict | None = None
    created_at: datetime


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    trace_id: str
    audit: AuditRecord | None = None


class Researcher(BaseModel):
    """A researcher and the projects their account can access."""

    username: str
    display_name: str
    role: str
    projects: list[str] = Field(
        description="Accessible project ids; '*' means administrator (all)."
    )
