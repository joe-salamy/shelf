"""Bottom-up summarization pipeline: section → chapter → book."""

from __future__ import annotations

import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from shelf.config import SHELF_PARALLEL_WORKERS
from shelf.models import BookTree, Section
from shelf.summarize.base import LLMBackend
from shelf.summarize.exceptions import ContextWindowExceededError

logger = logging.getLogger(__name__)
from shelf.summarize.models import (
    BookSummary,
    ChapterSummary,
    Entity,
    Relationship,
    SectionSummary,
)
from shelf.summarize.prompts import (
    BOOK_ROLLUP_PROMPT,
    CHAPTER_ROLLUP_PROMPT,
    SECTION_PROMPT,
)
from shelf.summarize.splitter import split_section_content


def generate_book_summary(
    tree: BookTree,
    backend: LLMBackend,
    max_chars: int = 24_000,
    on_progress: Callable[[str], None] | None = None,
    section_limit: int | None = None,
) -> BookSummary:
    """Run the full bottom-up summarization pipeline."""

    def _log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    chapters = [s for s in tree.sections if s.title != "Front Matter"]

    # Collect all H2 sections across chapters for progress counting
    total_sections = sum(len(ch.children) for ch in chapters)
    progress_counter = 0
    progress_lock = threading.Lock()

    # --- Phase 1: section summaries (parallel) ---
    # Build a flat list of (chapter_title, section_index, section) to submit
    tasks: list[tuple[str, int, Section]] = []
    for chapter in chapters:
        for sec_idx, section in enumerate(chapter.children):
            tasks.append((chapter.title, sec_idx, section))

    if section_limit is not None:
        tasks = tasks[:section_limit]
        total_sections = len(tasks)

    # Pre-allocate ordered lists per chapter
    chapter_section_summaries: dict[str, list[SectionSummary | None]] = {
        ch.title: [None] * len(ch.children) for ch in chapters
    }

    with ThreadPoolExecutor(max_workers=SHELF_PARALLEL_WORKERS) as pool:
        future_to_task = {
            pool.submit(_summarize_section, section, ch_title, backend, max_chars): (
                ch_title,
                sec_idx,
                section.title,
            )
            for ch_title, sec_idx, section in tasks
        }
        for fut in as_completed(future_to_task):
            ch_title, sec_idx, sec_title = future_to_task[fut]
            ss = fut.result()
            chapter_section_summaries[ch_title][sec_idx] = ss
            with progress_lock:
                progress_counter += 1
                _log(f"Section {progress_counter}/{total_sections}: {sec_title}")

    # Cast away the None placeholders (all filled by now in unlimited mode;
    # in limited mode, filter out sections that weren't summarized)
    if section_limit is not None:
        filled_summaries: dict[str, list[SectionSummary]] = {
            k: [s for s in v if s is not None]
            for k, v in chapter_section_summaries.items()
            if any(s is not None for s in v)
        }
    else:
        filled_summaries = {
            k: list(v) for k, v in chapter_section_summaries.items()  # type: ignore[arg-type]
        }

    # --- Phase 2: chapter rollups (parallel) ---
    # When section_limit is active, only roll up chapters that had sections summarized
    if section_limit is not None:
        summarized_titles = {ch_title for ch_title, _, _ in tasks}
        rollup_chapters = [ch for ch in chapters if ch.title in summarized_titles]
    else:
        rollup_chapters = chapters

    chapter_summaries: list[ChapterSummary | None] = [None] * len(rollup_chapters)

    with ThreadPoolExecutor(max_workers=SHELF_PARALLEL_WORKERS) as pool:
        future_to_idx = {
            pool.submit(
                _rollup_chapter,
                ch.title,
                filled_summaries[ch.title],
                backend,
            ): idx
            for idx, ch in enumerate(rollup_chapters)
        }
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            _log(
                f"Chapter {idx + 1}/{len(rollup_chapters)}: {rollup_chapters[idx].title}"
            )
            chapter_summaries[idx] = fut.result()

    # All slots filled — narrow the type
    completed_chapters: list[ChapterSummary] = list(chapter_summaries)  # type: ignore[arg-type]

    # --- Phase 3: book rollup ---
    _log("Generating book overview...")
    overview = _rollup_book(completed_chapters, backend)

    all_entities = _dedup_entities(
        [e for cs in completed_chapters for e in cs.entities]
    )
    all_relationships = _dedup_relationships(
        [r for cs in completed_chapters for r in cs.relationships]
    )

    return BookSummary(
        overview=overview,
        chapter_summaries=completed_chapters,
        all_entities=all_entities,
        all_relationships=all_relationships,
    )


# ---------------------------------------------------------------------------
# Phase 1 helpers
# ---------------------------------------------------------------------------


def _render_section_text(section: Section) -> str:
    """Render a section and its children as plain markdown text."""
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


def _summarize_section(
    section: Section,
    chapter_title: str,
    backend: LLMBackend,
    max_chars: int,
) -> SectionSummary:
    """Summarize a single H2 section, splitting if needed."""
    content = _render_section_text(section)
    chunks = split_section_content(content, max_chars)

    if len(chunks) == 1:
        return _call_section_llm(section.title, chapter_title, chunks[0], backend)

    # Multiple chunks: summarize each, then merge
    partials: list[SectionSummary] = []
    for chunk in chunks:
        partials.append(_call_section_llm(section.title, chapter_title, chunk, backend))
    return _merge_section_summaries(section.title, chapter_title, partials)


def _call_section_llm(
    section_title: str,
    chapter_title: str,
    content: str,
    backend: LLMBackend,
) -> SectionSummary:
    """Make one LLM call for a section (or chunk) and parse the result."""
    try:
        raw = backend.summarize(content, SECTION_PROMPT).text
    except ContextWindowExceededError:
        raise
    except Exception as exc:
        logger.warning("LLM call failed for section '%s': %s", section_title, exc)
        return _degraded_section(section_title, chapter_title)

    return _parse_section_response(raw, section_title, chapter_title)


_EXPECTED_SECTION_KEYS = {"summary", "key_points", "entities", "relationships",
                          "prerequisites", "leads_to"}
_VALID_KINDS = {"term", "case", "person", "statute", "concept"}
_VALID_RELATIONS = {"PART-OF", "DEFINES", "CITED-IN", "APPLIES-IN",
                    "OVERRULES", "ESTABLISHES", "PREREQUISITE-FOR", "RELATED-TO"}


def _parse_section_response(
    raw: str, section_title: str, chapter_title: str
) -> SectionSummary:
    """Parse LLM JSON response into a SectionSummary."""
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        logger.warning("No JSON found in LLM response for section '%s'",
                        section_title)
        return SectionSummary(
            section_title=section_title,
            chapter_title=chapter_title,
            summary=raw.strip() or "[Summarization failed]",
        )

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in LLM response for section '%s'",
                        section_title)
        return SectionSummary(
            section_title=section_title,
            chapter_title=chapter_title,
            summary=raw.strip() or "[Summarization failed]",
        )

    missing_keys = _EXPECTED_SECTION_KEYS - data.keys()
    if missing_keys:
        logger.warning("Section '%s': missing keys in LLM response: %s",
                        section_title, ", ".join(sorted(missing_keys)))

    raw_entities = data.get("entities", [])
    entities = []
    for e in raw_entities:
        if not isinstance(e, dict) or not e.get("name"):
            logger.warning("Section '%s': dropped malformed entity: %s",
                            section_title, e)
            continue
        kind = e.get("kind", "concept")
        if kind not in _VALID_KINDS:
            logger.warning("Section '%s': unexpected entity kind '%s' for '%s'",
                            section_title, kind, e.get("name"))
        entities.append(Entity(
            name=e.get("name", ""),
            kind=kind,
            definition=e.get("definition", ""),
        ))

    raw_rels = data.get("relationships", [])
    relationships = []
    for r in raw_rels:
        if not isinstance(r, dict) or not r.get("source") or not r.get("target"):
            logger.warning("Section '%s': dropped malformed relationship: %s",
                            section_title, r)
            continue
        relation = r.get("relation", "")
        if relation not in _VALID_RELATIONS:
            logger.warning("Section '%s': unexpected relation '%s' (%s -> %s)",
                            section_title, relation, r.get("source"), r.get("target"))
        relationships.append(Relationship(
            source=r.get("source", ""),
            relation=relation,
            target=r.get("target", ""),
        ))

    return SectionSummary(
        section_title=section_title,
        chapter_title=chapter_title,
        summary=data.get("summary", raw.strip()),
        key_points=data.get("key_points", []),
        entities=entities,
        relationships=relationships,
        prerequisites=data.get("prerequisites", []),
        leads_to=data.get("leads_to", []),
    )


def _degraded_section(section_title: str, chapter_title: str) -> SectionSummary:
    return SectionSummary(
        section_title=section_title,
        chapter_title=chapter_title,
        summary="[Summarization failed]",
    )


def _merge_section_summaries(
    section_title: str,
    chapter_title: str,
    partials: list[SectionSummary],
) -> SectionSummary:
    """Merge multiple partial SectionSummary objects from chunk splitting."""
    summaries = [p.summary for p in partials if p.summary != "[Summarization failed]"]
    key_points: list[str] = []
    entities: list[Entity] = []
    relationships: list[Relationship] = []
    prerequisites: list[str] = []
    leads_to: list[str] = []

    for p in partials:
        key_points.extend(p.key_points)
        entities.extend(p.entities)
        relationships.extend(p.relationships)
        prerequisites.extend(p.prerequisites)
        leads_to.extend(p.leads_to)

    return SectionSummary(
        section_title=section_title,
        chapter_title=chapter_title,
        summary=" ".join(summaries) if summaries else "[Summarization failed]",
        key_points=key_points,
        entities=_dedup_entities(entities),
        relationships=_dedup_relationships(relationships),
        prerequisites=list(dict.fromkeys(prerequisites)),
        leads_to=list(dict.fromkeys(leads_to)),
    )


# ---------------------------------------------------------------------------
# Phase 2 helpers
# ---------------------------------------------------------------------------


def _rollup_chapter(
    chapter_title: str,
    section_summaries: list[SectionSummary],
    backend: LLMBackend,
) -> ChapterSummary:
    """Roll up section summaries into a chapter summary."""
    # Build input text for the LLM
    lines = [f"Chapter: {chapter_title}\n"]
    for ss in section_summaries:
        lines.append(f"## {ss.section_title}")
        lines.append(ss.summary)
        if ss.key_points:
            lines.append("Key points:")
            for kp in ss.key_points:
                lines.append(f"- {kp}")
        lines.append("")
    input_text = "\n".join(lines)

    summary = chapter_title  # fallback
    try:
        raw = backend.summarize(input_text, CHAPTER_ROLLUP_PROMPT).text
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if "summary" not in data:
                logger.warning("Chapter '%s': missing 'summary' key in rollup response",
                                chapter_title)
            summary = data.get("summary", raw.strip())
        else:
            logger.warning("No JSON found in chapter rollup for '%s'", chapter_title)
            summary = raw.strip()
    except ContextWindowExceededError:
        raise
    except Exception as exc:
        logger.warning("Chapter rollup failed for '%s': %s", chapter_title, exc)
        summary = "[Chapter summarization failed]"

    # Merge entities and relationships from all sections
    all_ents = [e for ss in section_summaries for e in ss.entities]
    all_rels = [r for ss in section_summaries for r in ss.relationships]

    return ChapterSummary(
        chapter_title=chapter_title,
        summary=summary,
        section_summaries=section_summaries,
        entities=_dedup_entities(all_ents),
        relationships=_dedup_relationships(all_rels),
    )


# ---------------------------------------------------------------------------
# Phase 3 helpers
# ---------------------------------------------------------------------------


def _rollup_book(
    chapter_summaries: list[ChapterSummary],
    backend: LLMBackend,
) -> str:
    """Roll up chapter summaries into a book overview."""
    lines = []
    for cs in chapter_summaries:
        lines.append(f"## {cs.chapter_title}")
        lines.append(cs.summary)
        lines.append("")
    input_text = "\n".join(lines)

    try:
        raw = backend.summarize(input_text, BOOK_ROLLUP_PROMPT).text
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if "overview" not in data:
                logger.warning("Book rollup: missing 'overview' key in response")
            return data.get("overview", raw.strip())
        logger.warning("No JSON found in book rollup response")
        return raw.strip()
    except ContextWindowExceededError:
        raise
    except Exception as exc:
        logger.warning("Book rollup failed: %s", exc)
        return "[Book overview generation failed]"


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------


def _dedup_entities(entities: list[Entity]) -> list[Entity]:
    """Deduplicate entities by (name, kind), keeping the longer definition."""
    seen: dict[tuple[str, str], Entity] = {}
    for e in entities:
        key = (e.name.lower().strip(), e.kind)
        if key not in seen or len(e.definition) > len(seen[key].definition):
            seen[key] = e
    return list(seen.values())


def _dedup_relationships(relationships: list[Relationship]) -> list[Relationship]:
    """Deduplicate relationships by (source, relation, target)."""
    seen: set[tuple[str, str, str]] = set()
    result: list[Relationship] = []
    for r in relationships:
        key = (
            r.source.lower().strip(),
            r.relation.lower().strip(),
            r.target.lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result
