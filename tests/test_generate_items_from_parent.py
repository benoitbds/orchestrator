import asyncio
from types import SimpleNamespace
import pytest

from agents.handlers import (
    _validate_payload,
    _dedup_titles,
    generate_items_from_parent_handler,
)


def test_validate_payload_us_filters_invalid():
    payload = {
        "items": [
            {
                "title": "A",
                "as_a": "user",
                "i_want": "x",
                "so_that": "y",
                "acceptance_criteria": ["one"],
            },
            {
                "title": "B",
                "as_a": "user",
                "i_want": "x",
                "so_that": "y",
                "acceptance_criteria": ["one", "two"],
            },
        ]
    }
    out = _validate_payload("US", payload)
    assert len(out) == 1
    assert out[0]["title"] == "B"


@pytest.mark.asyncio
async def test_dedup_titles_removes_duplicates():
    candidates = [{"title": "Gestion du backlog"}, {"title": "Analyse"}]
    existing = [{"title": "Gestion du backlog"}]
    out = await _dedup_titles(candidates, existing)
    assert out == [{"title": "Analyse"}]


@pytest.mark.asyncio
async def test_generate_items_from_parent_handler_creates_items(monkeypatch):
    created = []

    monkeypatch.setattr(
        "agents.handlers.crud.get_item",
        lambda item_id: SimpleNamespace(
            id=item_id, type="Feature", title="Feat", description="", project_id=1
        ),
    )
    monkeypatch.setattr(
        "agents.handlers.crud.get_items",
        lambda project_id, type=None, limit=200, offset=0: [
            SimpleNamespace(id=2, type="US", title="Story existante", parent_id=1)
        ],
    )
    monkeypatch.setattr(
        "agents.handlers.crud.create_item",
        lambda item: created.append(item) or SimpleNamespace(id=len(created), title=item.title),
    )
    monkeypatch.setattr(
        "agents.handlers._build_llm_json_object",
        lambda: SimpleNamespace(
            invoke=lambda msgs: SimpleNamespace(
                content="{\n  \"parent_id\": 1, \n  \"type\": \"US\", \n  \"items\": [\n    {\"title\": \"Story existante\", \"as_a\": \"user\", \"i_want\": \"x\", \"so_that\": \"y\", \"acceptance_criteria\": [\"a\", \"b\"]},\n    {\"title\": \"Nouvelle story\", \"as_a\": \"user\", \"i_want\": \"x2\", \"so_that\": \"y2\", \"acceptance_criteria\": [\"a2\", \"b2\"], \"priority\": \"Could\", \"estimate\": 5}\n  ]\n}"
            )
        ),
    )
    monkeypatch.setattr(
        "agents.handlers.search_documents_handler",
        lambda args: {"ok": True, "matches": []},
    )
    monkeypatch.setattr(
        "agents.handlers.summarize_project_tool",
        lambda args: {"ok": True, "result": {"text": "ctx"}},
    )

    res = await generate_items_from_parent_handler(
        {"project_id": 1, "parent_id": 1, "target_type": "US", "n": 3}
    )
    assert res["ok"] is True
    assert len(res["items"]) == 1
    assert res["items"][0]["title"] == "Nouvelle story"


@pytest.mark.asyncio
async def test_generate_items_from_parent_handler_bad_type():
    res = await generate_items_from_parent_handler(
        {"project_id": 1, "parent_id": 1, "target_type": "Task"}
    )
    assert res["ok"] is False
    assert "Unsupported" in res["error"]
