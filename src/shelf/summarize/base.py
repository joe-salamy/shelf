"""Protocol definition for LLM summarization backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class LLMResult:
    """Full result from an LLM call: generated text plus raw API metadata."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMBackend(Protocol):
    def summarize(self, text: str, prompt: str) -> LLMResult:
        """Summarize the given text using the given system prompt."""
        ...
