"""Tests for shelf.summarize.orchestrator."""

import json
import pytest
from pathlib import Path
from shelf.models import BookTree, Section
from shelf.summarize.models import BookSummary, ChapterSummary, SectionSummary
from shelf.summarize.orchestrator import (
    generate_book_summary,
    _dedup_entities,
    _dedup_relationships,
)
from shelf.summarize.models import Entity, Relationship


# ---------------------------------------------------------------------------
# Mock backend
# ---------------------------------------------------------------------------


class MockBackend:
    """Returns well-formed JSON for any summarize call."""

    def __init__(self):
        self.call_count = 0

    def summarize(self, text: str, prompt: str) -> str:
        self.call_count += 1
        # Detect which prompt type by unique keywords in the prompt
        if "prerequisites" in prompt:
            # Section prompt
            return json.dumps(
                {
                    "summary": "This section covers important concepts.",
                    "key_points": ["Point A", "Point B"],
                    "entities": [
                        {
                            "name": "Due Process",
                            "kind": "term",
                            "definition": "Constitutional guarantee of fair procedures.",
                        }
                    ],
                    "relationships": [
                        {
                            "source": "Due Process",
                            "relation": "PART-OF",
                            "target": "Fourteenth Amendment",
                        }
                    ],
                    "prerequisites": ["Constitutional basics"],
                    "leads_to": ["Equal Protection"],
                }
            )
        elif "entire textbook" in prompt.lower():
            # Book rollup prompt
            return json.dumps(
                {"overview": "This textbook covers constitutional law fundamentals."}
            )
        else:
            # Chapter rollup prompt
            return json.dumps(
                {"summary": "This chapter provides a comprehensive overview."}
            )


class FailingBackend:
    """Raises on every call."""

    def summarize(self, text: str, prompt: str) -> str:
        raise ConnectionError("LLM unreachable")


class BadJsonBackend:
    """Returns invalid JSON."""

    def summarize(self, text: str, prompt: str) -> str:
        return "This is not JSON at all, sorry!"


# ---------------------------------------------------------------------------
# Test tree builders
# ---------------------------------------------------------------------------


def _make_tree() -> BookTree:
    sec1 = Section(title="Section 1.1", level=2, content="Content for section 1.1.")
    sec2 = Section(title="Section 1.2", level=2, content="Content for section 1.2.")
    ch1 = Section(
        title="Chapter 1", level=1, content="Chapter one intro.", children=[sec1, sec2]
    )
    sec3 = Section(title="Section 2.1", level=2, content="Content for section 2.1.")
    ch2 = Section(
        title="Chapter 2", level=1, content="Chapter two intro.", children=[sec3]
    )
    return BookTree(
        title="Test Book", sections=[ch1, ch2], source_path=Path("test.pdf")
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_book_summary_returns_book_summary():
    tree = _make_tree()
    backend = MockBackend()
    result = generate_book_summary(tree, backend)
    assert isinstance(result, BookSummary)


def test_generates_correct_chapter_count():
    tree = _make_tree()
    backend = MockBackend()
    result = generate_book_summary(tree, backend)
    assert len(result.chapter_summaries) == 2


def test_generates_correct_section_count():
    tree = _make_tree()
    backend = MockBackend()
    result = generate_book_summary(tree, backend)
    ch1 = result.chapter_summaries[0]
    assert len(ch1.section_summaries) == 2
    ch2 = result.chapter_summaries[1]
    assert len(ch2.section_summaries) == 1


def test_book_overview_populated():
    tree = _make_tree()
    backend = MockBackend()
    result = generate_book_summary(tree, backend)
    assert "constitutional law" in result.overview.lower()


def test_entities_extracted():
    tree = _make_tree()
    backend = MockBackend()
    result = generate_book_summary(tree, backend)
    entity_names = [e.name for e in result.all_entities]
    assert "Due Process" in entity_names


def test_relationships_extracted():
    tree = _make_tree()
    backend = MockBackend()
    result = generate_book_summary(tree, backend)
    assert len(result.all_relationships) > 0
    rel = result.all_relationships[0]
    assert rel.source == "Due Process"


def test_llm_call_count():
    """S sections + C chapters + 1 book = 3 + 2 + 1 = 6 calls."""
    tree = _make_tree()
    backend = MockBackend()
    generate_book_summary(tree, backend)
    assert backend.call_count == 6


def test_on_progress_called():
    tree = _make_tree()
    backend = MockBackend()
    messages = []
    generate_book_summary(tree, backend, on_progress=messages.append)
    assert len(messages) > 0
    assert any("Section" in m for m in messages)
    assert any("Chapter" in m for m in messages)


def test_graceful_degradation_on_failure():
    tree = _make_tree()
    backend = FailingBackend()
    result = generate_book_summary(tree, backend)
    assert isinstance(result, BookSummary)
    # Sections should have degraded summaries
    for cs in result.chapter_summaries:
        for ss in cs.section_summaries:
            assert ss.summary == "[Summarization failed]"


def test_graceful_degradation_on_bad_json():
    tree = _make_tree()
    backend = BadJsonBackend()
    result = generate_book_summary(tree, backend)
    assert isinstance(result, BookSummary)
    # Should still produce a result, just with raw text as summaries
    for cs in result.chapter_summaries:
        for ss in cs.section_summaries:
            assert ss.summary  # non-empty


def test_dedup_entities_by_name_and_kind():
    entities = [
        Entity(name="Due Process", kind="term", definition="Short def."),
        Entity(name="due process", kind="term", definition="A longer definition here."),
        Entity(name="Due Process", kind="case", definition="Different kind."),
    ]
    result = _dedup_entities(entities)
    assert len(result) == 2  # one term, one case
    term = [e for e in result if e.kind == "term"][0]
    assert "longer" in term.definition  # kept the longer one


def test_dedup_relationships():
    rels = [
        Relationship(source="A", relation="DEFINES", target="B"),
        Relationship(source="a", relation="defines", target="b"),
        Relationship(source="A", relation="CITES", target="B"),
    ]
    result = _dedup_relationships(rels)
    assert len(result) == 2
