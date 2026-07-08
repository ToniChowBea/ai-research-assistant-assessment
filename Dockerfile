FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY research_assistant ./research_assistant
COPY mock-data ./mock-data

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# API :8000, MCP server :8001
EXPOSE 8000 8001

CMD ["uvicorn", "research_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"]
