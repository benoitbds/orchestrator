import pytest
from agents.handlers import delete_item_tool, crud


@pytest.mark.asyncio
async def test_delete_item_rejects_generic_reason(monkeypatch):
    monkeypatch.setattr(crud, "get_item", lambda _: object())
    monkeypatch.setattr(crud, "delete_item", lambda _: 1)
    res = await delete_item_tool({
        "id": 1,
        "project_id": 1,
        "type": "US",
        "reason": "cleanup",
        "explicit_confirm": True,
    })
    assert not res["ok"]
    assert res["error"] == "invalid_reason"


@pytest.mark.asyncio
async def test_delete_item_requires_confirmation(monkeypatch):
    monkeypatch.setattr(crud, "get_item", lambda _: object())
    monkeypatch.setattr(crud, "delete_item", lambda _: 1)
    res = await delete_item_tool({
        "id": 1,
        "project_id": 1,
        "type": "US",
        "reason": "because",
        "explicit_confirm": False,
    })
    assert not res["ok"]
    assert res["error"] == "explicit_confirm_required"


@pytest.mark.asyncio
async def test_delete_item_logs_and_deletes(monkeypatch, caplog):
    monkeypatch.setattr(crud, "get_item", lambda _: object())
    monkeypatch.setattr(crud, "delete_item", lambda _: 1)
    with caplog.at_level("INFO"):
        res = await delete_item_tool({
            "id": 1,
            "project_id": 1,
            "type": "US",
            "reason": "remove",  # non-generic reason
            "explicit_confirm": True,
        })
    assert res["ok"]
    assert res["item_id"] == 1
    assert any("'tool': 'delete_item'" in r.getMessage() for r in caplog.records)
