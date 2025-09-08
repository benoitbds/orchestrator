import types
from orchestrator.core_loop import _filter_tools_by_objective


def _tool(name: str):
    return types.SimpleNamespace(
        name=name,
        description="",
        args_schema=types.SimpleNamespace(__name__="S"),
    )


def test_create_intent_excludes_delete_item():
    tools = [
        _tool("create_item"),
        _tool("delete_item"),
        _tool("update_item"),
        _tool("get_item"),
        _tool("list_items"),
        _tool("move_item"),
    ]
    filtered = _filter_tools_by_objective("Please create a new item", tools)
    names = {t.name for t in filtered}
    assert "delete_item" not in names
    assert names == {"create_item", "update_item", "get_item", "list_items"}


def test_delete_intent_includes_delete_item():
    tools = [_tool("delete_item"), _tool("update_item")]
    filtered = _filter_tools_by_objective("remove the old item", tools)
    names = {t.name for t in filtered}
    assert "delete_item" in names
