import json

from langchain_core.messages import ToolMessage

from research_assistant.agent.engine import _governance_from_tools, _tool_payload

_SUPPRESSED = {
    "suppressed": True,
    "governance": [{"policy": "min_records", "action": "suppress"}],
}


def test_payload_read_from_artifact():
    msg = ToolMessage(
        content="[]",
        artifact={"structured_content": _SUPPRESSED},
        tool_call_id="t1",
    )
    assert _tool_payload(msg) == _SUPPRESSED


def test_payload_read_from_text_block_content():
    msg = ToolMessage(
        content=[{"type": "text", "text": json.dumps(_SUPPRESSED)}],
        tool_call_id="t1",
    )
    assert _tool_payload(msg) == _SUPPRESSED


def test_governance_extracted_from_suppressed_tool():
    msg = ToolMessage(
        content="[]",
        artifact={"structured_content": _SUPPRESSED},
        tool_call_id="t1",
    )
    assert _governance_from_tools([msg]) == _SUPPRESSED["governance"]


def test_no_governance_when_not_suppressed():
    msg = ToolMessage(
        content="[]",
        artifact={"structured_content": {"suppressed": False, "rows": []}},
        tool_call_id="t1",
    )
    assert _governance_from_tools([msg]) == []
