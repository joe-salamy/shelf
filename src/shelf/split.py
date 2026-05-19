"""Parse markdown text into a BookTree by detecting ATX headers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from shelf.models import BookTree, Section

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$")
FallbackMode = Literal["auto", "none"]


def split_markdown(
    text: str,
    depth: int | None = None,
    source_path: Path | None = None,
    fallback: FallbackMode = "auto",
    fallback_max_chars: int = 24000,
) -> BookTree:
    """Parse markdown into a BookTree.

    Args:
        text: Raw markdown text.
        depth: Maximum heading level to split (1=H1 only, 2=H1+H2, 3=H1-H3, etc.).
               Headers deeper than `depth` remain as body content.
               If None, all heading levels present in the document are used.
        source_path: Optional path to the source file (stored on the tree).
        fallback: What to do with non-empty text when no usable headers are found.
                  "auto" creates synthetic Part sections; "none" raises ValueError.
        fallback_max_chars: Target maximum characters per synthetic section.

    Returns:
        BookTree with nested Section objects.
    """
    if fallback not in ("auto", "none"):
        raise ValueError("fallback must be 'auto' or 'none'")
    if fallback_max_chars < 1:
        raise ValueError("fallback_max_chars must be at least 1")

    lines = text.splitlines(keepends=True)

    # Build flat list of (level, title, line_index) for all headers first
    all_headers: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        m = _HEADER_RE.match(line.rstrip())
        if m:
            level = len(m.group(1))
            all_headers.append((level, m.group(2).strip(), i))

    # Determine effective depth
    effective_depth = (
        depth
        if depth is not None
        else (max((lvl for lvl, _, _ in all_headers), default=6))
    )

    # Filter to headers within depth
    headers = [
        (lvl, title, idx) for lvl, title, idx in all_headers if lvl <= effective_depth
    ]

    tree_title = _tree_title(headers, source_path)
    if not headers and text.strip():
        if fallback == "none":
            raise ValueError(
                "No markdown headers were detected in the converted document. "
                "Use --fallback auto to create synthetic sections."
            )
        return _split_headerless_text(
            text,
            title=tree_title,
            source_path=source_path,
            max_chars=fallback_max_chars,
        )

    # Determine the line ranges for each header's content
    # Content for header[i] runs from line after its header to line before header[i+1]
    def _get_content(start_line: int, end_line: int) -> str:
        return "".join(lines[start_line:end_line]).strip()

    # Build sections list from flat header list using a stack
    top_sections: list[Section] = []
    # front_matter: text before first header
    first_header_line = headers[0][2] if headers else len(lines)
    front_matter_text = _get_content(0, first_header_line)

    if front_matter_text:
        top_sections.append(
            Section(title="Front Matter", level=1, content=front_matter_text)
        )

    # stack entries: (section, level)
    stack: list[tuple[Section, int]] = []

    for idx, (level, title, line_idx) in enumerate(headers):
        # Determine content end
        if idx + 1 < len(headers):
            end_line = headers[idx + 1][2]
        else:
            end_line = len(lines)

        # Content is lines after header line up to next header
        content = _get_content(line_idx + 1, end_line)
        section = Section(title=title, level=level, content=content)

        # Pop stack until we find a parent with lower level number
        while stack and stack[-1][1] >= level:
            stack.pop()

        if not stack:
            top_sections.append(section)
        else:
            stack[-1][0].children.append(section)

        stack.append((section, level))

    return BookTree(title=tree_title, sections=top_sections, source_path=source_path)


def _tree_title(
    headers: list[tuple[int, str, int]], source_path: Path | None
) -> str:
    """Determine tree title: first H1 title, source filename, or Untitled."""
    first_h1 = next(
        (title for level, title, _ in headers if level == 1),
        None,
    )
    if first_h1:
        return first_h1
    if source_path:
        return source_path.stem
    return "Untitled"


def _split_headerless_text(
    text: str, title: str, source_path: Path | None, max_chars: int
) -> BookTree:
    """Build a synthetic one-chapter tree for documents with no detected headers."""
    chapter = Section(
        title=title,
        level=1,
        content=(
            "Shelf did not detect source headings, so this chapter contains "
            "synthetic parts split from the document text."
        ),
    )
    chapter.children = [
        Section(title=f"Part {idx:03d}", level=2, content=chunk)
        for idx, chunk in enumerate(_chunk_text(text, max_chars), start=1)
    ]
    return BookTree(title=title, sections=[chapter], source_path=source_path)


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into paragraph-aware chunks with hard splits for long paragraphs."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_hard_split(paragraph, max_chars))
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)
    return chunks


def _hard_split(text: str, max_chars: int) -> list[str]:
    return [
        text[start : start + max_chars].strip()
        for start in range(0, len(text), max_chars)
        if text[start : start + max_chars].strip()
    ]
