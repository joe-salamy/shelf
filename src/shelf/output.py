"""Write a BookTree to a nested directory of markdown files."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from shelf.models import BookTree, Section
from shelf.slugify import slugify

if TYPE_CHECKING:
    from shelf.summarize.models import (
        BookSummary,
        ChapterSummary,
        Entity,
        Relationship,
    )

# Windows MAX_PATH is 260; reserve room for the prefix digits, separators, and .md
_MAX_PATH = 260 if sys.platform == "win32" else 1024


def write_shelf(
    tree: BookTree,
    output_dir: Path,
    book_summary: "BookSummary | None" = None,
    index_filename: str = "CLAUDE.md",
) -> None:
    """Materialize the BookTree as a nested markdown directory.

    Layout:
      output_dir/
        INDEX.md              — linked TOC
        CLAUDE.md             — navigation guide (or custom *index_filename*)
        ENTITIES.md           — entity index (if summarized)
        GRAPH.md              — entity relationships (if summarized)
        01-chapter-slug/
          CLAUDE.md           — chapter navigation (if summarized)
          CONCEPTS.md         — chapter entities (if summarized)
          00-introduction.md           — H1 body content
          01-section-slug.md
          ...
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Separate front matter from H1 chapters
    chapters = [s for s in tree.sections if s.title != "Front Matter"]
    front_matter = next((s for s in tree.sections if s.title == "Front Matter"), None)

    chapter_dirs: list[tuple[str, Path, Section]] = []  # (slug, dir_path, section)

    # Budget for slug lengths: total path must fit within _MAX_PATH.
    slug_budget = _MAX_PATH - len(str(output_dir)) - 11
    max_slug = max(slug_budget // 2, 20)

    # Build a lookup from chapter title → ChapterSummary
    ch_summary_map: dict[str, "ChapterSummary"] = {}
    if book_summary:
        for cs in book_summary.chapter_summaries:
            ch_summary_map[cs.chapter_title] = cs

    for ch_idx, chapter in enumerate(chapters, start=1):
        ch_slug = slugify(chapter.title, max_length=max_slug) or f"chapter-{ch_idx}"
        ch_dir = output_dir / f"{ch_idx:02d}-{ch_slug}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        chapter_dirs.append((ch_slug, ch_dir, chapter))

        # 00-introduction.md — chapter's own body content
        intro_content = f"# {chapter.title}\n\n{chapter.content}\n"
        (ch_dir / "00-introduction.md").write_text(intro_content, encoding="utf-8")

        # H2 sections → individual .md files
        for sec_idx, section in enumerate(chapter.children, start=1):
            sec_slug = (
                slugify(section.title, max_length=max_slug) or f"section-{sec_idx}"
            )
            sec_file = ch_dir / f"{sec_idx:02d}-{sec_slug}.md"
            sec_content = _render_section(section)
            sec_file.write_text(sec_content, encoding="utf-8")

        # Chapter-level CLAUDE.md and CONCEPTS.md (if summarized)
        cs = ch_summary_map.get(chapter.title)
        if cs:
            _write_chapter_index(ch_dir, cs, index_filename)
            _write_chapter_concepts(ch_dir, cs)

    # Write front matter to output root if present
    if front_matter:
        (output_dir / "front-matter.md").write_text(
            front_matter.content + "\n", encoding="utf-8"
        )

    # INDEX.md — build descriptions from first sentence of section summaries
    descriptions: dict[str, str] = {}
    if book_summary:
        for cs in book_summary.chapter_summaries:
            descriptions[cs.chapter_title] = _first_sentence(cs.summary)
            for ss in cs.section_summaries:
                descriptions[ss.section_title] = _first_sentence(ss.summary)

    index_lines = [f"# {tree.title}\n", ""]
    for ch_idx, (ch_slug, ch_dir, chapter) in enumerate(chapter_dirs, start=1):
        ch_prefix = f"{ch_idx:02d}-{ch_slug}"
        ch_desc = descriptions.get(chapter.title, "")
        ch_link = f"- [{chapter.title}]({ch_prefix}/00-introduction.md)"
        index_lines.append(f"{ch_link} — {ch_desc}" if ch_desc else ch_link)
        for sec_idx, section in enumerate(chapter.children, start=1):
            sec_slug = (
                slugify(section.title, max_length=max_slug) or f"section-{sec_idx}"
            )
            sec_prefix = f"{sec_idx:02d}-{sec_slug}"
            sec_desc = descriptions.get(section.title, "")
            sec_link = f"  - [{section.title}]({ch_prefix}/{sec_prefix}.md)"
            index_lines.append(f"{sec_link} — {sec_desc}" if sec_desc else sec_link)
            # H3+ as anchor links
            for subsec in section.children:
                anchor = _to_anchor(subsec.title)
                index_lines.append(
                    f"    - [{subsec.title}]({ch_prefix}/{sec_prefix}.md#{anchor})"
                )
    index_lines.append("")
    (output_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

    # Root navigation file (CLAUDE.md or custom name)
    _write_root_index(output_dir, tree, chapters, book_summary, index_filename)

    # Entity indexes (if summarized)
    if book_summary:
        _write_root_entities(
            output_dir, tree.title, book_summary, chapter_dirs, max_slug
        )
        _write_root_graph(output_dir, tree.title, book_summary)


# ---------------------------------------------------------------------------
# Root-level file writers
# ---------------------------------------------------------------------------


def _write_root_index(
    output_dir: Path,
    tree: BookTree,
    chapters: list[Section],
    book_summary: "BookSummary | None",
    index_filename: str,
) -> None:
    """Write the root navigation index file (CLAUDE.md or custom name)."""
    chapter_count = len(chapters)
    section_count = sum(len(ch.children) for ch in chapters)
    subsection_count = sum(len(sec.children) for ch in chapters for sec in ch.children)

    lines = [
        f"# {tree.title} — Navigation Guide",
        "",
        "This directory was generated by **shelf** and is designed for navigation by coding agents.",
        "",
    ]

    if book_summary and book_summary.overview:
        lines += ["## Overview", "", book_summary.overview, ""]

    lines += [
        "## Structure",
        "",
        f"- **{chapter_count}** chapters (H1 → numbered directories)",
        f"- **{section_count}** sections (H2 → `.md` files inside each chapter directory)",
        f"- **{subsection_count}** subsections (H3 → headings within section files)",
        "",
    ]

    # Chapter summaries
    if book_summary:
        lines += ["## Chapters", ""]
        for cs in book_summary.chapter_summaries:
            lines.append(f"### {cs.chapter_title}")
            lines.append(cs.summary)
            lines.append("")

    lines += [
        "## How to navigate",
        "",
        "- `INDEX.md` — full linked table of contents",
        "- Each chapter is a directory: `01-chapter-name/`",
        "- Each section is a file: `01-chapter-name/01-section-name.md`",
        "- Chapter overview: `01-chapter-name/00-introduction.md`",
    ]
    if book_summary:
        lines += [
            "- `ENTITIES.md` — all terms, cases, people with file locations",
            "- `GRAPH.md` — entity relationships",
            f"- Each chapter has `{index_filename}` and `CONCEPTS.md`",
        ]
    lines += [
        "",
        "## Grep hints",
        "",
        "```bash",
        "# Find all section headings",
        f'grep -r "^## " {output_dir.name}/',
        "",
        "# Search for a topic",
        f'grep -rl "due process" {output_dir.name}/',
        "",
        "# List all chapters",
        f"ls {output_dir.name}/",
        "```",
        "",
        "## Statistics",
        "",
        f"- Chapters: {chapter_count}",
        f"- Sections: {section_count}",
        f"- Subsections: {subsection_count}",
        f"- Source: {tree.source_path.name if tree.source_path else 'unknown'}",
        "",
    ]
    (output_dir / index_filename).write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Chapter-level file writers
# ---------------------------------------------------------------------------


def _write_chapter_index(
    ch_dir: Path,
    chapter_summary: "ChapterSummary",
    index_filename: str,
) -> None:
    """Write a chapter-level CLAUDE.md (or custom name) with section summaries."""
    lines = [
        f"# {chapter_summary.chapter_title} — Navigation Guide",
        "",
        "## Summary",
        "",
        chapter_summary.summary,
        "",
        "## Sections",
        "",
    ]
    for ss in chapter_summary.section_summaries:
        lines.append(f"### {ss.section_title}")
        lines.append(ss.summary)
        if ss.key_points:
            lines.append("")
            lines.append("**Key points:**")
            for kp in ss.key_points:
                lines.append(f"- {kp}")
        lines.append("")
        lines.append("---")
        lines.append("")

    (ch_dir / index_filename).write_text("\n".join(lines), encoding="utf-8")


def _write_chapter_concepts(
    ch_dir: Path,
    chapter_summary: "ChapterSummary",
) -> None:
    """Write a chapter-level CONCEPTS.md with structured entity lists."""
    lines = [f"# {chapter_summary.chapter_title} — Key Concepts", ""]

    # Group entities by kind
    by_kind: dict[str, list["Entity"]] = {}
    for e in chapter_summary.entities:
        by_kind.setdefault(e.kind, []).append(e)

    kind_labels = {
        "term": "Terms",
        "case": "Cases",
        "person": "People",
        "statute": "Statutes",
        "concept": "Concepts",
    }

    for kind, label in kind_labels.items():
        entities = by_kind.get(kind, [])
        if entities:
            lines.append(f"## {label}")
            lines.append("")
            for e in entities:
                lines.append(f"- **{e.name}**: {e.definition}")
            lines.append("")

    # Prerequisites and leads-to (union across sections)
    all_prereqs: list[str] = []
    all_leads: list[str] = []
    for ss in chapter_summary.section_summaries:
        all_prereqs.extend(ss.prerequisites)
        all_leads.extend(ss.leads_to)
    prereqs = list(dict.fromkeys(all_prereqs))
    leads = list(dict.fromkeys(all_leads))

    if prereqs:
        lines += ["## Prerequisites", ""]
        for p in prereqs:
            lines.append(f"- {p}")
        lines.append("")

    if leads:
        lines += ["## Leads To", ""]
        for l in leads:
            lines.append(f"- {l}")
        lines.append("")

    (ch_dir / "CONCEPTS.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entity index writers
# ---------------------------------------------------------------------------


def _write_root_entities(
    output_dir: Path,
    book_title: str,
    book_summary: "BookSummary",
    chapter_dirs: list[tuple[str, Path, Section]],
    max_slug: int,
) -> None:
    """Write ENTITIES.md — a flat lookup table of all entities with file locations."""
    # Build a map: (entity_name, kind) → list of file paths
    entity_locations: dict[tuple[str, str], list[str]] = {}

    for ch_idx, (ch_slug, ch_dir, chapter) in enumerate(chapter_dirs, start=1):
        ch_prefix = f"{ch_idx:02d}-{ch_slug}"
        cs = None
        for c in book_summary.chapter_summaries:
            if c.chapter_title == chapter.title:
                cs = c
                break
        if not cs:
            continue

        for ss in cs.section_summaries:
            # Find the matching section file
            sec_idx = None
            for i, section in enumerate(chapter.children, start=1):
                if section.title == ss.section_title:
                    sec_idx = i
                    break
            if sec_idx is None:
                continue

            sec_slug = (
                slugify(ss.section_title, max_length=max_slug) or f"section-{sec_idx}"
            )
            sec_path = f"{ch_prefix}/{sec_idx:02d}-{sec_slug}.md"

            for e in ss.entities:
                key = (e.name.lower().strip(), e.kind)
                entity_locations.setdefault(key, [])
                if sec_path not in entity_locations[key]:
                    entity_locations[key].append(sec_path)

    lines = [f"# {book_title} — Entity Index", ""]

    # Group by kind
    kind_labels = {
        "term": "Terms",
        "case": "Cases",
        "person": "People",
        "statute": "Statutes",
        "concept": "Concepts",
    }

    for kind, label in kind_labels.items():
        kind_entities = [e for e in book_summary.all_entities if e.kind == kind]
        if not kind_entities:
            continue

        lines += [f"## {label}", ""]
        lines += ["| Name | Definition | Found In |", "|------|-----------|----------|"]
        for e in sorted(kind_entities, key=lambda x: x.name.lower()):
            key = (e.name.lower().strip(), e.kind)
            locations = entity_locations.get(key, [])
            loc_links = ", ".join(f"[{loc}]({loc})" for loc in locations[:3])
            # Escape pipe characters in entity fields
            name = e.name.replace("|", "\\|")
            defn = e.definition.replace("|", "\\|")
            lines.append(f"| {name} | {defn} | {loc_links} |")
        lines.append("")

    (output_dir / "ENTITIES.md").write_text("\n".join(lines), encoding="utf-8")


def _write_root_graph(
    output_dir: Path,
    book_title: str,
    book_summary: "BookSummary",
) -> None:
    """Write GRAPH.md — one relationship per line, grep-friendly."""
    lines = [f"# {book_title} — Entity Relationships", ""]
    for r in book_summary.all_relationships:
        lines.append(f"{r.source} --{r.relation}--> {r.target}")
    lines.append("")

    (output_dir / "GRAPH.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Rendering helpers (unchanged)
# ---------------------------------------------------------------------------


def _render_section(section: Section) -> str:
    """Render an H2 section and its H3+ children as a single markdown file."""
    parts = [f"## {section.title}\n\n{section.content}"]
    for subsec in section.children:
        parts.append(_render_subsection(subsec, base_level=3))
    return "\n\n".join(parts) + "\n"


def _render_subsection(section: Section, base_level: int) -> str:
    hashes = "#" * base_level
    parts = [f"{hashes} {section.title}\n\n{section.content}"]
    for child in section.children:
        parts.append(_render_subsection(child, base_level + 1))
    return "\n\n".join(parts)


def _to_anchor(title: str) -> str:
    """Convert a heading title to a GitHub-style markdown anchor."""
    anchor = title.lower()
    anchor = re.sub(r"[^\w\s-]", "", anchor)
    anchor = re.sub(r"\s+", "-", anchor)
    return anchor.strip("-")


def _first_sentence(text: str) -> str:
    """Extract the first sentence from text for use as a description."""
    text = text.strip()
    if not text:
        return ""
    match = re.match(r"[^.!?]*[.!?]", text)
    return match.group().strip() if match else text[:100]
