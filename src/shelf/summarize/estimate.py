"""Pre-flight cost estimation for the summarization pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from shelf.config import (
    SHELF_LLM_INPUT_COST,
    SHELF_LLM_OUTPUT_COST,
    SHELF_OUTPUT_TOKEN_RATIO,
    SHELF_TOKENS_PER_WORD,
)
from shelf.models import BookTree, Section
from shelf.summarize.prompts import (
    BOOK_ROLLUP_PROMPT,
    CHAPTER_ROLLUP_PROMPT,
    SECTION_PROMPT,
)
from shelf.summarize.splitter import split_section_content


@dataclass
class CostEstimate:
    phase1_input_tokens: int
    phase1_output_tokens: int
    phase1_llm_calls: int
    phase2_input_tokens: int
    phase2_output_tokens: int
    phase2_llm_calls: int
    phase3_input_tokens: int
    phase3_output_tokens: int
    phase3_llm_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float


def _word_count(text: str) -> int:
    return len(text.split())


def _words_to_tokens(words: int) -> int:
    return int(words * SHELF_TOKENS_PER_WORD)


def _render_section_text(section: Section) -> str:
    """Render a section and its children as plain markdown text (mirrors orchestrator)."""
    parts = [f"## {section.title}\n\n{section.content}"]
    for child in section.children:
        parts.append(_render_child(child, level=3))
    return "\n\n".join(parts)


def _render_child(section: Section, level: int) -> str:
    hashes = "#" * level
    parts = [f"{hashes} {section.title}\n\n{section.content}"]
    for child in section.children:
        parts.append(_render_child(child, level + 1))
    return "\n\n".join(parts)


def estimate_cost(
    tree: BookTree,
    max_chars: int = 24_000,
    section_limit: int | None = None,
    section_offset: int = 0,
) -> CostEstimate:
    """Estimate token usage and cost for all 3 pipeline phases."""

    chapters = [s for s in tree.sections if s.title != "Front Matter"]
    prompt_words = {
        "section": _word_count(SECTION_PROMPT),
        "chapter": _word_count(CHAPTER_ROLLUP_PROMPT),
        "book": _word_count(BOOK_ROLLUP_PROMPT),
    }

    # Build task list (same logic as orchestrator)
    tasks: list[tuple[str, Section]] = []
    for chapter in chapters:
        for section in chapter.children:
            tasks.append((chapter.title, section))

    if section_offset:
        tasks = tasks[section_offset:]
    if section_limit is not None:
        tasks = tasks[:section_limit]

    # --- Phase 1: section summarization ---
    p1_input_tokens = 0
    p1_calls = 0
    chapter_task_counts: dict[str, int] = {}

    for ch_title, section in tasks:
        content = _render_section_text(section)
        chunks = split_section_content(content, max_chars)
        for chunk in chunks:
            content_words = _word_count(chunk)
            p1_input_tokens += _words_to_tokens(content_words + prompt_words["section"])
            p1_calls += 1
        chapter_task_counts[ch_title] = chapter_task_counts.get(ch_title, 0) + len(chunks)

    p1_output_tokens = int(p1_input_tokens * SHELF_OUTPUT_TOKEN_RATIO)

    # --- Phase 2: chapter rollups ---
    # Each chapter's input ≈ its share of phase 1 output + prompt overhead
    rollup_chapters = list(chapter_task_counts.keys())
    p2_input_tokens = 0
    p2_calls = len(rollup_chapters)

    for ch_title in rollup_chapters:
        # Rough estimate: phase 1 output for this chapter becomes phase 2 input
        ch_fraction = chapter_task_counts[ch_title] / max(p1_calls, 1)
        ch_output_tokens = int(p1_output_tokens * ch_fraction)
        p2_input_tokens += ch_output_tokens + _words_to_tokens(prompt_words["chapter"])

    p2_output_tokens = int(p2_input_tokens * SHELF_OUTPUT_TOKEN_RATIO)

    # --- Phase 3: book rollup ---
    p3_input_tokens = p2_output_tokens + _words_to_tokens(prompt_words["book"])
    p3_output_tokens = int(p3_input_tokens * SHELF_OUTPUT_TOKEN_RATIO)
    p3_calls = 1

    # --- Totals ---
    total_in = p1_input_tokens + p2_input_tokens + p3_input_tokens
    total_out = p1_output_tokens + p2_output_tokens + p3_output_tokens
    cost = (total_in / 1_000_000) * SHELF_LLM_INPUT_COST + (
        total_out / 1_000_000
    ) * SHELF_LLM_OUTPUT_COST

    return CostEstimate(
        phase1_input_tokens=p1_input_tokens,
        phase1_output_tokens=p1_output_tokens,
        phase1_llm_calls=p1_calls,
        phase2_input_tokens=p2_input_tokens,
        phase2_output_tokens=p2_output_tokens,
        phase2_llm_calls=p2_calls,
        phase3_input_tokens=p3_input_tokens,
        phase3_output_tokens=p3_output_tokens,
        phase3_llm_calls=p3_calls,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_cost_usd=cost,
    )
