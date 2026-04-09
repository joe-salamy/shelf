"""Tests for shelf.output."""

import pytest
from pathlib import Path
from shelf.models import BookTree, Section
from shelf.output import write_shelf
from shelf.summarize.models import (
    BookSummary,
    ChapterSummary,
    Entity,
    Relationship,
    SectionSummary,
)


def _make_tree() -> BookTree:
    sub = Section(title="Subsection 1.1.1", level=3, content="Subsection content.")
    sec1 = Section(
        title="Section One Point One",
        level=2,
        content="Section 1.1 content.",
        children=[sub],
    )
    sec2 = Section(
        title="Section One Point Two", level=2, content="Section 1.2 content."
    )
    ch1 = Section(
        title="Chapter One",
        level=1,
        content="Chapter one intro.",
        children=[sec1, sec2],
    )
    ch2 = Section(title="Chapter Two", level=1, content="Chapter two intro.")
    return BookTree(
        title="Test Book", sections=[ch1, ch2], source_path=Path("test.pdf")
    )


def _make_book_summary() -> BookSummary:
    ss1 = SectionSummary(
        section_title="Section One Point One",
        chapter_title="Chapter One",
        summary="This section covers important concepts. It is detailed.",
        key_points=["Point A", "Point B"],
        entities=[
            Entity(
                name="Due Process", kind="term", definition="Fair legal procedures."
            ),
            Entity(
                name="Lochner v. NY", kind="case", definition="1905 labor law case."
            ),
        ],
        relationships=[
            Relationship(
                source="Due Process", relation="DEFINES", target="Fourteenth Amendment"
            ),
        ],
        prerequisites=["Constitutional basics"],
        leads_to=["Equal Protection"],
    )
    ss2 = SectionSummary(
        section_title="Section One Point Two",
        chapter_title="Chapter One",
        summary="This section extends the analysis.",
        key_points=["Point C"],
    )
    cs1 = ChapterSummary(
        chapter_title="Chapter One",
        summary="Chapter one provides a comprehensive overview.",
        section_summaries=[ss1, ss2],
        entities=[
            Entity(
                name="Due Process", kind="term", definition="Fair legal procedures."
            ),
            Entity(
                name="Lochner v. NY", kind="case", definition="1905 labor law case."
            ),
        ],
        relationships=[
            Relationship(
                source="Due Process", relation="DEFINES", target="Fourteenth Amendment"
            ),
        ],
    )
    cs2 = ChapterSummary(
        chapter_title="Chapter Two",
        summary="Chapter two covers advanced topics.",
        section_summaries=[],
    )
    return BookSummary(
        overview="This textbook covers constitutional law fundamentals.",
        chapter_summaries=[cs1, cs2],
        all_entities=[
            Entity(
                name="Due Process", kind="term", definition="Fair legal procedures."
            ),
            Entity(
                name="Lochner v. NY", kind="case", definition="1905 labor law case."
            ),
        ],
        all_relationships=[
            Relationship(
                source="Due Process", relation="DEFINES", target="Fourteenth Amendment"
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Existing tests (structural output, no summarization)
# ---------------------------------------------------------------------------


def test_output_directories_created(tmp_path):
    tree = _make_tree()
    write_shelf(tree, tmp_path / "out")
    out = tmp_path / "out"
    assert (out / "01-chapter-one").is_dir()
    assert (out / "02-chapter-two").is_dir()


def test_readme_files_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    assert (out / "01-chapter-one" / "00-introduction.md").exists()
    assert (out / "02-chapter-two" / "00-introduction.md").exists()


def test_readme_contains_chapter_title(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    content = (out / "01-chapter-one" / "00-introduction.md").read_text()
    assert "Chapter One" in content
    assert "Chapter one intro" in content


def test_section_files_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    ch1_dir = out / "01-chapter-one"
    assert (ch1_dir / "01-section-one-point-one.md").exists()
    assert (ch1_dir / "02-section-one-point-two.md").exists()


def test_section_file_contains_h3(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    content = (out / "01-chapter-one" / "01-section-one-point-one.md").read_text()
    assert "Subsection 1.1.1" in content
    assert "Subsection content" in content


def test_index_md_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    assert (out / "INDEX.md").exists()


def test_index_md_contains_links(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    content = (out / "INDEX.md").read_text()
    assert "Chapter One" in content
    assert "01-chapter-one/00-introduction.md" in content
    assert "Section One Point One" in content


def test_index_md_contains_h3_anchors(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    content = (out / "INDEX.md").read_text()
    assert "Subsection 1.1.1" in content
    assert "#" in content  # anchor link


def test_claude_md_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    assert (out / "CLAUDE.md").exists()


def test_claude_md_contains_stats(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    content = (out / "CLAUDE.md").read_text()
    assert "2" in content  # chapter count
    assert "grep" in content.lower()


def test_front_matter_written(tmp_path):
    sec = Section(title="Front Matter", level=1, content="Preface text.")
    ch = Section(title="Chapter One", level=1, content="Intro.")
    tree = BookTree(title="Book", sections=[sec, ch])
    out = tmp_path / "out"
    write_shelf(tree, out)
    assert (out / "front-matter.md").exists()
    content = (out / "front-matter.md").read_text()
    assert "Preface text" in content


def test_output_dir_created_if_missing(tmp_path):
    tree = _make_tree()
    out = tmp_path / "new" / "nested" / "dir"
    write_shelf(tree, out)
    assert out.is_dir()


def test_empty_chapter_no_section_files(tmp_path):
    ch = Section(title="Chapter One", level=1, content="Just content, no sections.")
    tree = BookTree(title="Book", sections=[ch])
    out = tmp_path / "out"
    write_shelf(tree, out)
    ch_dir = out / "01-chapter-one"
    md_files = [f for f in ch_dir.iterdir() if f.name != "00-introduction.md"]
    assert md_files == []


# ---------------------------------------------------------------------------
# Tests for new summarization output
# ---------------------------------------------------------------------------


def test_chapter_claude_md_created_with_summary(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    assert (out / "01-chapter-one" / "CLAUDE.md").exists()


def test_chapter_claude_md_contains_section_summaries(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "01-chapter-one" / "CLAUDE.md").read_text()
    assert "Section One Point One" in content
    assert "important concepts" in content
    assert "Point A" in content


def test_chapter_concepts_md_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    assert (out / "01-chapter-one" / "CONCEPTS.md").exists()


def test_chapter_concepts_md_contains_entities(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "01-chapter-one" / "CONCEPTS.md").read_text()
    assert "Due Process" in content
    assert "Lochner v. NY" in content


def test_chapter_concepts_md_contains_prerequisites(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "01-chapter-one" / "CONCEPTS.md").read_text()
    assert "Constitutional basics" in content
    assert "Equal Protection" in content


def test_root_entities_md_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    assert (out / "ENTITIES.md").exists()


def test_root_entities_md_contains_entities(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "ENTITIES.md").read_text()
    assert "Due Process" in content
    assert "Lochner v. NY" in content


def test_root_graph_md_created(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    assert (out / "GRAPH.md").exists()


def test_root_graph_md_contains_relationships(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "GRAPH.md").read_text()
    assert "Due Process" in content
    assert "DEFINES" in content
    assert "Fourteenth Amendment" in content


def test_root_claude_md_contains_overview(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "CLAUDE.md").read_text()
    assert "constitutional law" in content.lower()


def test_root_claude_md_contains_chapter_summaries(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "CLAUDE.md").read_text()
    assert "Chapter One" in content
    assert "comprehensive overview" in content


def test_index_md_contains_descriptions_with_summary(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out, book_summary=_make_book_summary())
    content = (out / "INDEX.md").read_text()
    # Should have first-sentence descriptions from summaries
    assert (
        "comprehensive overview" in content.lower()
        or "important concepts" in content.lower()
    )


def test_custom_index_filename(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(
        tree, out, book_summary=_make_book_summary(), index_filename="AGENTS.md"
    )
    assert (out / "AGENTS.md").exists()
    assert not (out / "CLAUDE.md").exists()
    # Chapter level too
    assert (out / "01-chapter-one" / "AGENTS.md").exists()


def test_no_summary_files_without_book_summary(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    # Should NOT have entity/graph/concepts files
    assert not (out / "ENTITIES.md").exists()
    assert not (out / "GRAPH.md").exists()
    assert not (out / "01-chapter-one" / "CONCEPTS.md").exists()
    # But should still have root CLAUDE.md
    assert (out / "CLAUDE.md").exists()
