"""Split oversized section content to fit within LLM context windows."""

from __future__ import annotations

import re

DEFAULT_MAX_CHARS = 24_000  # ~6k tokens, safe for 8k-context models


def split_section_content(
    content: str, max_chars: int = DEFAULT_MAX_CHARS
) -> list[str]:
    """Split content into chunks that fit within an LLM context window.

    Strategy:
    1. If content fits, return as a single chunk.
    2. Split at the H3 heading closest to the midpoint.
    3. If no H3 headings, split at the paragraph break closest to the midpoint.
    4. Recurse if either half still exceeds *max_chars*.
    """
    if len(content) <= max_chars:
        return [content]

    mid = len(content) // 2

    # Try splitting at an H3+ heading boundary
    heading_positions = [m.start() for m in re.finditer(r"^#{3,6}\s+", content, re.M)]
    if heading_positions:
        split_pos = _closest(heading_positions, mid)
        if split_pos > 0:
            left, right = content[:split_pos].rstrip(), content[split_pos:].lstrip()
            return _recurse(left, right, max_chars)

    # Fall back to paragraph break
    para_positions = [m.start() for m in re.finditer(r"\n\n+", content)]
    if para_positions:
        split_pos = _closest(para_positions, mid)
        if split_pos > 0:
            left, right = content[:split_pos].rstrip(), content[split_pos:].lstrip()
            return _recurse(left, right, max_chars)

    # Last resort: hard split at midpoint
    return _recurse(content[:mid], content[mid:], max_chars)


def _closest(positions: list[int], target: int) -> int:
    """Return the position closest to *target*."""
    return min(positions, key=lambda p: abs(p - target))


def _recurse(left: str, right: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    if left:
        chunks.extend(split_section_content(left, max_chars))
    if right:
        chunks.extend(split_section_content(right, max_chars))
    return chunks
