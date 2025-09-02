from orchestrator.prompt_loader import load_prompt


def test_tool_system_prompt_contains_tool_call_requirement():
    prompt = load_prompt("tool_system_prompt")
    assert "USE A TOOL" in prompt
    assert "Do NOT output placeholders" in prompt
