"""Summarize layer: smart index generation via a single LLM call."""

from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass

from shelf.models import BookTree, Section
from shelf.summarize.base import LLMBackend

_SYSTEM_PROMPT = (
    "You are generating a navigation index for a textbook. "
    "Given an outline with section titles and opening sentences, return a JSON object with:\n"
    '1. "descriptions": an object mapping each section title to a concise one-line description (under 15 words)\n'
    '2. "overview": a 2-3 sentence summary of the book\'s scope and structure'
)


@dataclass
class SmartIndex:
    descriptions: dict[str, str]
    overview: str


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


def _first_sentences(text: str, n: int = 2) -> str:
    """Extract the first n sentences from a block of text."""
    text = text.strip()
    if not text:
        return ""
    # Split on sentence-ending punctuation followed by whitespace or end-of-string
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


def _build_outline(tree: BookTree) -> str:
    """Build a compact outline: title + first 2 sentences per section."""
    lines: list[str] = [f"Book: {tree.title}", ""]
    chapters = [s for s in tree.sections if s.title != "Front Matter"]
    for chapter in chapters:
        lines.append(f"Chapter: {chapter.title}")
        snippet = _first_sentences(chapter.content)
        if snippet:
            lines.append(f"  {snippet}")
        for section in chapter.children:
            lines.append(f"  Section: {section.title}")
            snippet = _first_sentences(section.content)
            if snippet:
                lines.append(f"    {snippet}")
        lines.append("")
    return "\n".join(lines)


def generate_smart_index(tree: BookTree) -> SmartIndex:
    """Send a single LLM call to generate one-line descriptions and a book overview."""
    backend = get_backend()
    outline = _build_outline(tree)
    raw = backend.summarize(outline, _SYSTEM_PROMPT)

    # Extract JSON from the response (may be wrapped in a code fence)
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return SmartIndex(descriptions={}, overview=raw.strip())

    try:
        data = json.loads(json_match.group())
        descriptions = data.get("descriptions", {})
        overview = data.get("overview", "")
        return SmartIndex(descriptions=descriptions, overview=overview)
    except json.JSONDecodeError:
        return SmartIndex(descriptions={}, overview=raw.strip())
