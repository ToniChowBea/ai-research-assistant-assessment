import inngest.fast_api
from fastapi import FastAPI

from research_assistant.agent.engine import research_query
from research_assistant.workflow.client import inngest_client


def mount_inngest(app: FastAPI) -> None:
    """Expose /api/inngest so the dev server can discover and execute steps."""
    inngest.fast_api.serve(app, inngest_client, [research_query])
