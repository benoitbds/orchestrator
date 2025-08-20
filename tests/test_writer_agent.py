import json
import types

import pytest

from agents.writer import make_feature_proposals
from agents.schemas import FeatureProposals
from langchain_openai import ChatOpenAI


@pytest.mark.usefixtures("patch_graph")
def test_make_feature_proposals(monkeypatch):
    expected = {
        "project_id": 1,
        "parent_id": 2,
        "parent_title": "Epic demo",
        "proposals": [
            {"title": "Feat1", "description": "Desc1"},
            {"title": "Feat2", "description": "Desc2"},
        ],
    }

    def fake_invoke(self, messages):
        return types.SimpleNamespace(content=json.dumps(expected))

    monkeypatch.setattr(ChatOpenAI, "invoke", fake_invoke)

    result = make_feature_proposals(1, 2, "Epic demo")
    assert isinstance(result, FeatureProposals)
    assert result.project_id == expected["project_id"]
    assert result.parent_id == expected["parent_id"]
    assert result.parent_title == expected["parent_title"]
    assert len(result.proposals) == len(expected["proposals"])
    for prop, exp in zip(result.proposals, expected["proposals"]):
        assert prop.title == exp["title"]
        assert prop.description == exp["description"]
