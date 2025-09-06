# orchestrator/llm/provider.py
"""LLM provider abstractions."""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable

log = logging.getLogger(__name__)


class OpenAIProvider:
    """Factory for creating OpenAI chat models.

    Parameters
    ----------
    base_model: str
        Model used during normal conversation.
    tool_model: str
        Model used when the agent is in a tool-exchange phase.
    **common_kwargs: Any
        Parameters forwarded to ``ChatOpenAI``.
    """

    name = "openai"

    def __init__(self, base_model: str, tool_model: str, **common_kwargs: Any) -> None:
        self.base_model = base_model
        self.tool_model = tool_model
        self.common_kwargs = common_kwargs

    def make_llm(self, *, tool_phase: bool, tools: Optional[List[Any]] = None) -> Runnable:
        """Instantiate an ``ChatOpenAI`` and optionally bind tools.

        Parameters
        ----------
        tool_phase:
            ``True`` if the model should be optimised for tool calls.
        tools:
            Optional list of LangChain ``StructuredTool`` objects.
        """

        model = self.tool_model if tool_phase else self.base_model
        log.info({"event": "llm_model_selected", "model": model, "tool_phase": tool_phase})
        llm = ChatOpenAI(model=model, **self.common_kwargs)
        return llm.bind_tools(tools) if tools else llm


class BoundLLMProvider:
    """Simple provider wrapping a pre-instantiated LLM."""

    def __init__(self, llm: Any, name: str | None = None) -> None:
        self._llm = llm
        self.name = name or getattr(llm, "name", None) or getattr(llm, "model_name", None)

    def make_llm(self, *, tool_phase: bool, tools: Optional[List[Any]] = None) -> Runnable:
        if tools and hasattr(self._llm, "bind_tools"):
            try:
                return self._llm.bind_tools(tools)
            except Exception:
                pass
        return self._llm
