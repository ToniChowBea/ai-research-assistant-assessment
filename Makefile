.DEFAULT_GOAL := help
.PHONY: help env db seed mcp api inspector stack up down db-seed logs eval test

help:            ## show available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

env:             ## create .env from .env.example (keys already filled in)
	@test -f .env && echo ".env exists — leaving it untouched" || (cp .env.example .env && echo "created .env — ready to go")

db:              ## start postgres (docker compose, detached)
	docker compose up -d postgres

seed: db         ## seed mock-data into postgres (idempotent)
	uv run python -m research_assistant.db.seed

mcp:             ## run the MCP server on :8001 (needs a seeded db)
	uv run --env-file .env python -m research_assistant.mcp_server.server

api:             ## run the FastAPI app on :8000 (loads .env for the LLM key)
	uv run --env-file .env uvicorn research_assistant.main:app --reload --port 8000

inspector:       ## open the MCP Inspector UI
	npx @modelcontextprotocol/inspector

stack: seed      ## run everything in one terminal: db + seed + MCP + API (Ctrl-C stops all)
	@trap 'kill 0' EXIT INT TERM; \
	uv run --env-file .env python -m research_assistant.mcp_server.server 2>&1 | sed 's/^/[mcp] /' & \
	sleep 1; \
	uv run --env-file .env uvicorn research_assistant.main:app --port 8000 2>&1 | sed 's/^/[api] /'; \
	wait

up: env          ## one command to hit the ground running: create .env, build, seed, start (detached). Then curl :8000 or `make logs`.
	docker compose up --build -d
	$(MAKE) db-seed
	@echo "Stack up. Try: curl -s localhost:8000/query -H 'content-type: application/json' -d '{\"question\":\"Which datasets relate to diabetes?\"}'"

db-seed:         ## seed the Docker db (run once after `make up`)
	docker compose run --rm api python -m research_assistant.db.seed

logs:            ## follow the Docker stack logs (Ctrl-C stops watching)
	docker compose logs -f

down:            ## stop and remove the Docker stack (add -v to also wipe the db)
	docker compose down

eval:            ## run eval suite (25 questions + RBAC) against a running API
	uv run python -m evals.run

test:            ## run the unit test suite (pytest, no DB needed)
	uv run --group dev pytest -q
