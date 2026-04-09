"""Data models for the summarization pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entity:
    """A named entity extracted from textbook content."""

    name: str
    kind: str  # "term", "case", "person", "statute", "concept"
    definition: str


@dataclass
class Relationship:
    """A directed relationship between two entities."""

    source: str
    relation: str  # "PART-OF", "CITED-IN", "DEFINES", "APPLIES-IN", etc.
    target: str


@dataclass
class SectionSummary:
    """LLM-generated summary and entities for a single H2 section."""

    section_title: str
    chapter_title: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    leads_to: list[str] = field(default_factory=list)


@dataclass
class ChapterSummary:
    """Rolled-up summary for a chapter, built from its section summaries."""

    chapter_title: str
    summary: str
    section_summaries: list[SectionSummary] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)


@dataclass
class BookSummary:
    """Top-level result of the entire summarization pipeline."""

    overview: str
    chapter_summaries: list[ChapterSummary] = field(default_factory=list)
    all_entities: list[Entity] = field(default_factory=list)
    all_relationships: list[Relationship] = field(default_factory=list)
