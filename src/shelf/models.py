"""Data models for the book tree structure."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Section:
    title: str
    level: int
    content: str = ""
    children: list[Section] = field(default_factory=list)

    def walk(self) -> Iterator[Section]:
        """Yield self and all descendants depth-first."""
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class BookTree:
    title: str
    sections: list[Section] = field(default_factory=list)
    source_path: Path | None = None

    def walk(self) -> Iterator[Section]:
        """Yield all sections depth-first."""
        for section in self.sections:
            yield from section.walk()

    def chapter_count(self) -> int:
        """Count top-level sections (H1 chapters)."""
        return len(self.sections)

    def section_count(self) -> int:
        """Count all sections at all levels."""
        return sum(1 for _ in self.walk())
