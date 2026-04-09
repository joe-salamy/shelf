"""Summarize layer: deep section-by-section summarization with entity extraction."""

from __future__ import annotations

from shelf.config import SHELF_LLM_API_KEY
from shelf.summarize.base import LLMBackend
from shelf.summarize.exceptions import ContextWindowExceededError
from shelf.summarize.models import BookSummary
from shelf.summarize.orchestrator import generate_book_summary

__all__ = [
    "get_backend",
    "generate_book_summary",
    "BookSummary",
    "ContextWindowExceededError",
]


def get_backend() -> LLMBackend:
    """Return the appropriate LLM backend based on environment variables."""
    api_key = SHELF_LLM_API_KEY
    if api_key:
        from shelf.summarize.openai_compat import OpenAICompatBackend

        return OpenAICompatBackend()

    # Try Ollama
    from shelf.summarize.ollama import OllamaBackend

    backend = OllamaBackend()
    if backend.is_available():
        return backend

    raise RuntimeError(
        "No LLM backend available. Set SHELF_LLM_API_KEY for an OpenAI-compatible API, "
        "or start Ollama locally."
    )
