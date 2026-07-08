from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference, Theme
from research_assistant.core.api import router as api_router


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

    return app


app = create_app()
