from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference, Theme
from research_assistant.core.api import router as api_router
from research_assistant.workflow.routes import mount_inngest


def create_app():
    # ----- App Instance -----------
    app = FastAPI(
        title="Research AI Assistant.",
        description="A research assistant that helps you with your research.",
        docs_url="/docs/swagger",
    )

    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "ok"}

    # ----- Scalar API Ref -----------
    @app.get("/docs", include_in_schema=False)
    async def get_docs():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url, title=app.title, theme=Theme.SATURN
        )

    # ----- Attach routes -----------
    app.include_router(api_router)

    # ----- Inngest (durable workflow) -----------
    mount_inngest(app)
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/inngest"):
            route.include_in_schema = False

    return app


app = create_app()
