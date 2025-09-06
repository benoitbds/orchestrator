# tests/llm/test_openai_provider.py
import pytest

from orchestrator.llm.provider import OpenAIProvider


class DummyChat:
    def __init__(self, *, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs
        self.bound = None

    def bind_tools(self, tools):
        self.bound = tools
        return self


def test_make_llm_base_model(monkeypatch):
    monkeypatch.setattr("orchestrator.llm.provider.ChatOpenAI", DummyChat)
    prov = OpenAIProvider(base_model="base", tool_model="tool", temperature=0)
    llm = prov.make_llm(tool_phase=False, tools=None)
    assert isinstance(llm, DummyChat)
    assert llm.model == "base"


def test_make_llm_tool_model(monkeypatch):
    monkeypatch.setattr("orchestrator.llm.provider.ChatOpenAI", DummyChat)
    prov = OpenAIProvider(base_model="base", tool_model="tool", temperature=0)
    llm = prov.make_llm(tool_phase=True, tools=None)
    assert llm.model == "tool"


def test_make_llm_bind_tools(monkeypatch):
    monkeypatch.setattr("orchestrator.llm.provider.ChatOpenAI", DummyChat)
    tools = [object()]
    prov = OpenAIProvider(base_model="base", tool_model="tool", temperature=0)
    llm = prov.make_llm(tool_phase=False, tools=tools)
    assert llm.bound is tools
