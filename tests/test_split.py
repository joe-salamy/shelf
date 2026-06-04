"""Tests for shelf.split — the most critical layer."""

import pytest

from shelf.split import split_markdown

# --- Basic structure ---


def test_basic_two_chapters(simple_markdown):
    tree = split_markdown(simple_markdown)
    chapters = [s for s in tree.sections if s.title != "Front Matter"]
    assert len(chapters) == 2
    assert chapters[0].title == "Chapter One"
    assert chapters[1].title == "Chapter Two"


def test_tree_title_from_h1(simple_markdown):
    tree = split_markdown(simple_markdown)
    assert tree.title == "Chapter One"


def test_sections_nested_under_chapters(simple_markdown):
    tree = split_markdown(simple_markdown)
    ch1 = next(s for s in tree.sections if s.title == "Chapter One")
    assert len(ch1.children) == 2
    assert ch1.children[0].title == "Section 1.1"
    assert ch1.children[1].title == "Section 1.2"


def test_subsections_nested_under_sections(simple_markdown):
    tree = split_markdown(simple_markdown)
    ch1 = next(s for s in tree.sections if s.title == "Chapter One")
    sec1 = ch1.children[0]
    assert len(sec1.children) == 1
    assert sec1.children[0].title == "Subsection 1.1.1"


def test_content_assigned_correctly(simple_markdown):
    tree = split_markdown(simple_markdown)
    ch1 = next(s for s in tree.sections if s.title == "Chapter One")
    assert "Introduction to chapter one" in ch1.content
    sec1 = ch1.children[0]
    assert "Content for section 1.1" in sec1.content


def test_book_title_h1_wrapping_numbered_h2_chapters_is_promoted():
    md = (
        "Preface before title.\n\n"
        "# Modern Recording Techniques\n\n"
        "Title-page content.\n\n"
        "## Copyright\n\n"
        "Copyright page.\n\n"
        "## Chapter 1. Introduction\n\n"
        "Chapter one intro.\n\n"
        "### The recording studio\n\n"
        "Studio content.\n\n"
        "## Chapter 2. Sound and Hearing\n\n"
        "Chapter two intro.\n"
    )

    tree = split_markdown(md)

    assert tree.title == "Modern Recording Techniques"
    assert [section.title for section in tree.sections] == [
        "Front Matter",
        "Chapter 1. Introduction",
        "Chapter 2. Sound and Hearing",
    ]
    assert "Preface before title." in tree.sections[0].content
    assert "Title-page content." in tree.sections[0].content
    assert "## Copyright" in tree.sections[0].content
    assert "Copyright page." in tree.sections[0].content
    assert tree.sections[1].level == 1
    assert tree.sections[1].children[0].title == "The recording studio"
    assert tree.sections[1].children[0].level == 2


def test_single_h1_with_non_chapter_h2_sections_is_not_promoted():
    md = (
        "# Book Title\n\n"
        "Intro.\n\n"
        "## Part 1\n\n"
        "Part content.\n\n"
        "## Chapter 1. Lone Chapter\n\n"
        "Chapter content.\n"
    )

    tree = split_markdown(md)

    assert [section.title for section in tree.sections] == ["Book Title"]
    assert [section.title for section in tree.sections[0].children] == [
        "Part 1",
        "Chapter 1. Lone Chapter",
    ]


# --- Front matter ---


def test_front_matter_captured():
    md = "Some preamble text.\n\nMore preamble.\n\n# Chapter One\n\nContent.\n"
    tree = split_markdown(md)
    fm = next((s for s in tree.sections if s.title == "Front Matter"), None)
    assert fm is not None
    assert "preamble" in fm.content


def test_no_front_matter_when_starts_with_header():
    md = "# Chapter One\n\nContent.\n"
    tree = split_markdown(md)
    fm = next((s for s in tree.sections if s.title == "Front Matter"), None)
    assert fm is None


# --- Depth limiting ---


def test_depth_1_no_sections():
    md = "# Chapter One\n\nContent.\n\n## Section 1.1\n\nSection content.\n"
    tree = split_markdown(md, depth=1)
    ch = tree.sections[0]
    assert ch.title == "Chapter One"
    assert len(ch.children) == 0
    # H2 content should be in body (not split out)


def test_depth_2_no_subsections():
    md = "# Ch\n\n## Sec\n\n### Sub\n\nSub content.\n"
    tree = split_markdown(md, depth=2)
    ch = tree.sections[0]
    sec = ch.children[0]
    assert sec.title == "Sec"
    assert len(sec.children) == 0


def test_depth_3_captures_h3(simple_markdown):
    tree = split_markdown(simple_markdown, depth=3)
    ch1 = next(s for s in tree.sections if s.title == "Chapter One")
    sec1 = ch1.children[0]
    assert len(sec1.children) == 1
    assert sec1.children[0].level == 3


# --- Edge cases ---


def test_no_headers():
    md = "Just some plain text.\nNo headers at all.\n"
    tree = split_markdown(md)
    assert len(tree.sections) == 1
    assert tree.sections[0].title == "Untitled"
    assert "synthetic parts" in tree.sections[0].content
    assert len(tree.sections[0].children) == 1
    assert tree.sections[0].children[0].title == "Part 001"
    assert "plain text" in tree.sections[0].children[0].content


def test_empty_string():
    tree = split_markdown("")
    assert len(tree.sections) == 0


def test_no_headers_split_into_synthetic_parts():
    md = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    tree = split_markdown(md, fallback_max_chars=35)
    chapter = tree.sections[0]

    assert chapter.title == "Untitled"
    assert [section.title for section in chapter.children] == ["Part 001", "Part 002"]
    assert chapter.children[0].content == "First paragraph.\n\nSecond paragraph."
    assert chapter.children[1].content == "Third paragraph."


def test_no_headers_hard_splits_oversized_paragraph():
    tree = split_markdown("abcdefghij", fallback_max_chars=4)
    sections = tree.sections[0].children

    assert [section.content for section in sections] == ["abcd", "efgh", "ij"]


def test_no_headers_fallback_none_raises():
    with pytest.raises(ValueError, match="No markdown headers"):
        split_markdown("Just text.", fallback="none")


def test_skipped_levels():
    """H1 directly to H3 — H3 should nest under H1."""
    md = "# Chapter\n\n### Deep Section\n\nDeep content.\n"
    tree = split_markdown(md, depth=3)
    ch = tree.sections[0]
    assert len(ch.children) == 1
    assert ch.children[0].title == "Deep Section"
    assert ch.children[0].level == 3


def test_duplicate_titles():
    md = "# Chapter\n\n## Introduction\n\nFirst.\n\n## Introduction\n\nSecond.\n"
    tree = split_markdown(md)
    ch = tree.sections[0]
    assert len(ch.children) == 2
    assert all(s.title == "Introduction" for s in ch.children)


def test_source_path_stored(tmp_path):
    path = tmp_path / "test.pdf"
    tree = split_markdown("# Title\n\nContent.\n", source_path=path)
    assert tree.source_path == path


def test_title_falls_back_to_source_path(tmp_path):
    path = tmp_path / "my-textbook.pdf"
    tree = split_markdown("No headers here.", source_path=path)
    assert tree.title == "my-textbook"


def test_title_falls_back_to_untitled():
    tree = split_markdown("No headers here.")
    assert tree.title == "Untitled"


def test_content_between_chapters():
    md = (
        "# Chapter One\n\nChapter one intro.\n\n"
        "## Sec 1\n\nSec content.\n\n"
        "# Chapter Two\n\nChapter two intro.\n"
    )
    tree = split_markdown(md)
    chapters = [s for s in tree.sections if s.title != "Front Matter"]
    assert "Chapter one intro" in chapters[0].content
    assert "Chapter two intro" in chapters[1].content


def test_deeply_nested():
    md = "# A\n\n## B\n\n### C\n\n#### D\n\nDeep content.\n"
    tree = split_markdown(md, depth=4)
    a = tree.sections[0]
    b = a.children[0]
    c = b.children[0]
    assert c.title == "C"
    d = c.children[0]
    assert d.title == "D"
    assert "Deep content" in d.content
