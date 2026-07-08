import json
import time

import inngest
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from research_assistant.agent.prompts import SYSTEM_PROMPT
from research_assistant.config import get_settings
from research_assistant.governance import apply_response_policies
from research_assistant.audit import persist_audit
from research_assistant.workflow.client import inngest_client

RECURSION_LIMIT = 25

_agent = None


class AgentResponse(BaseModel):
    """Structured final response: answer prose plus cited project/dataset ids."""

    answer: str = Field(description="Concise factual answer for the researcher")
    sources: list[str] = Field(
        default_factory=list,
        description="Project/dataset ids actually used, e.g. ['DS001']",
    )


# ----- Agent instance -----------
async def _get_agent():
    """Load MCP tools once and build the ReAct agent with structured output."""
    global _agent
    if _agent is None:
        settings = get_settings()
        client = MultiServerMCPClient(
            {
                "research": {
                    "url": settings.mcp_server_url,
                    "transport": "streamable_http",
                }
            }
        )
        tools = await client.get_tools()
        _agent = create_agent(
            model=settings.llm_model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            response_format=AgentResponse,
        )
    return _agent


# ----- Extract tools invoked -----------
def _tools_invoked(messages: list) -> list[dict]:
    """Tool names and truncated args for the audit log."""
    tools: list[dict] = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            tools.append(
                {"tool": call["name"], "args": str(call.get("args", {}))[:200]}
            )
    return tools


# ----- Tool payload recovery -----------
def _tool_payload(message: ToolMessage) -> dict | None:
    """Recover a tool's dict result. LangChain puts MCP structured output in
    `artifact['structured_content']`; content is a list of text blocks."""
    artifact = getattr(message, "artifact", None)
    if isinstance(artifact, dict):
        return artifact.get("structured_content", artifact)
    content = message.content
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                try:
                    return json.loads(block.get("text", ""))
                except json.JSONDecodeError:
                    continue
    return None


# ----- Governance from tools -----------
def _governance_from_tools(messages: list) -> list[dict]:
    """Query-time suppression decisions returned by analysis tools."""
    governance: list[dict] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        payload = _tool_payload(message)
        if isinstance(payload, dict) and payload.get("suppressed"):
            governance.extend(payload.get("governance") or [])
    return governance


# ----- Build messages -----------
def _messages(question: str, researcher: str | None) -> list[dict]:
    """User turn plus optional researcher identity for access-scoped questions."""
    messages: list[dict] = [{"role": "user", "content": question}]
    if researcher:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    f"You are assisting researcher '{researcher}'. Use this username "
                    "with the tools when resolving what they can access."
                ),
            },
        )
    return messages


async def run_agent(
    question: str, trace_id: str, researcher: str | None = None
) -> dict:
    """Run the agent and return structured answer, sources, and audit fields."""
    started = time.perf_counter()
    answer, sources, error = "", [], None
    tools: list[dict] = []
    governance: list[dict] = []

    try:
        agent = await _get_agent()
        result = await agent.ainvoke(
            {"messages": _messages(question, researcher)},
            config={
                "recursion_limit": RECURSION_LIMIT,
                "run_name": "research_query",
                "tags": ["research-agent"],
                "metadata": {"trace_id": trace_id},
            },
        )
        messages = result.get("messages", [])
        tools = _tools_invoked(messages)
        governance = _governance_from_tools(messages)
        structured = result.get("structured_response")
        if structured is not None:
            answer = structured.answer
            sources = [str(source) for source in structured.sources]
    except GraphRecursionError:
        error = f"recursion_limit_exceeded ({RECURSION_LIMIT})"
        answer = (
            "The assistant could not complete this question within its step "
            "budget. Please try rephrasing or narrowing it."
        )

    return {
        "answer": answer,
        "sources": sources,
        "tools": tools,
        "governance": governance,
        "error": error,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }


# ------------------------------------
# --- Inngest Workflow
# ------------------------------------
@inngest_client.create_function(
    fn_id="research_query",
    trigger=inngest.TriggerEvent(event="research/query.requested"),
)
async def research_query(ctx: inngest.Context) -> dict:
    question = ctx.event.data["question"]
    trace_id = ctx.event.data["trace_id"]
    researcher = ctx.event.data.get("researcher")

    run = await ctx.step.run(
        "run_agent", lambda: run_agent(question, trace_id, researcher)
    )
    governed = await ctx.step.run(
        "govern", lambda: apply_response_policies(run, {"researcher": researcher})
    )
    await ctx.step.run(
        "persist_audit",
        lambda: persist_audit(trace_id, question, governed, researcher),
    )
    return {"answer": governed["answer"], "sources": governed["sources"]}
