"""Summarize layer: LLM-generated summaries for BookTree sections."""

from __future__ import annotations
import os

from shelf.models import BookTree, Section
from shelf.summarize.base import LLMBackend

_SUMMARY_PROMPT = (
    "Summarize the following textbook section in one concise paragraph "
    "suitable for a law student. Focus on key concepts and rules."
)

_SUMMARY_TEMPLATE = "> **Summary:** {summary}\n\n---\n\n{original}"


def get_backend() -> LLMBackend:
    """Return the appropriate LLM backend based on environment variables."""
    api_key = os.environ.get("SHELF_LLM_API_KEY")
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


def summarize_tree(tree: BookTree) -> None:
    """Walk the tree and prepend LLM summaries to each section's content (in-place)."""
    backend = get_backend()
    for section in tree.walk():
        if section.content.strip():
            summary = backend.summarize(section.content, _SUMMARY_PROMPT)
            section.content = _SUMMARY_TEMPLATE.format(
                summary=summary, original=section.content
            )
