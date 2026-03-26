"""Protocol definition for LLM summarization backends."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMBackend(Protocol):
    def summarize(self, text: str, prompt: str) -> str:
        """Summarize the given text using the given system prompt."""
        ...
