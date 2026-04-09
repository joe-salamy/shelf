"""Tests for shelf.output."""

import pytest
from pathlib import Path
from shelf.models import BookTree, Section
from shelf.output import write_shelf


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
    assert (out / "01-chapter-one" / "README.md").exists()
    assert (out / "02-chapter-two" / "README.md").exists()


def test_readme_contains_chapter_title(tmp_path):
    tree = _make_tree()
    out = tmp_path / "out"
    write_shelf(tree, out)
    content = (out / "01-chapter-one" / "README.md").read_text()
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
    assert "01-chapter-one/README.md" in content
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
    md_files = [f for f in ch_dir.iterdir() if f.name != "README.md"]
    assert md_files == []
