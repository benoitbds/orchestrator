from agents.planner import TOOL_SYSTEM_PROMPT


def test_tool_system_prompt_contains_tool_call_requirement():
    assert "MUST call a TOOL" in TOOL_SYSTEM_PROMPT
    assert "Do NOT return placeholders" in TOOL_SYSTEM_PROMPT
