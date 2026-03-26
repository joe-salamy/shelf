"""Parse markdown text into a BookTree by detecting ATX headers."""

from __future__ import annotations
import re
from pathlib import Path
from shelf.models import BookTree, Section


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def split_markdown(text: str, depth: int = 3, source_path: Path | None = None) -> BookTree:
    """Parse markdown into a BookTree.

    Args:
        text: Raw markdown text.
        depth: Maximum heading level to split (1=H1 only, 2=H1+H2, 3=H1-H3, etc.).
               Headers deeper than `depth` remain as body content.
        source_path: Optional path to the source file (stored on the tree).

    Returns:
        BookTree with nested Section objects.
    """
    lines = text.splitlines(keepends=True)

    # Build flat list of (level, title, line_index) for headers within depth
    headers: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        m = _HEADER_RE.match(line.rstrip())
        if m:
            level = len(m.group(1))
            if level <= depth:
                headers.append((level, m.group(2).strip(), i))

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
        top_sections.append(Section(title="Front Matter", level=1, content=front_matter_text))

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

    # Determine tree title: first H1 title, or source filename, or "Untitled"
    first_h1 = next(
        (title for level, title, _ in headers if level == 1),
        None,
    )
    if first_h1:
        tree_title = first_h1
    elif source_path:
        tree_title = source_path.stem
    else:
        tree_title = "Untitled"

    return BookTree(title=tree_title, sections=top_sections, source_path=source_path)
