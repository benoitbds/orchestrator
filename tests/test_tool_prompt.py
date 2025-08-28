from agents.planner import TOOL_SYSTEM_PROMPT


def test_tool_system_prompt_contains_tool_call_requirement():
    assert "USE A TOOL" in TOOL_SYSTEM_PROMPT
    assert "Do NOT output placeholders" in TOOL_SYSTEM_PROMPT
