"""Tests for shelf.summarize.splitter."""

from shelf.summarize.splitter import split_section_content


def test_content_under_limit_returns_single_chunk():
    content = "Short content."
    result = split_section_content(content, max_chars=1000)
    assert result == [content]


def test_splits_at_h3_heading():
    content = "Intro paragraph.\n\n### Section A\n\nContent A.\n\n### Section B\n\nContent B."
    result = split_section_content(content, max_chars=30)
    assert len(result) >= 2
    # All original content should be present across chunks
    joined = " ".join(result)
    assert "Section A" in joined
    assert "Section B" in joined


def test_splits_at_paragraph_when_no_headings():
    content = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    result = split_section_content(content, max_chars=25)
    assert len(result) >= 2
    joined = " ".join(result)
    assert "Paragraph one" in joined
    assert "Paragraph three" in joined


def test_recursive_splitting_for_large_content():
    # Each paragraph is ~20 chars, limit is 30, so should split multiple times
    paragraphs = [f"Paragraph number {i}." for i in range(10)]
    content = "\n\n".join(paragraphs)
    result = split_section_content(content, max_chars=50)
    assert len(result) >= 3
    joined = " ".join(result)
    assert "Paragraph number 0" in joined
    assert "Paragraph number 9" in joined


def test_hard_split_when_no_breaks():
    content = "x" * 100
    result = split_section_content(content, max_chars=30)
    assert len(result) >= 2
    assert "".join(result) == content


def test_empty_content():
    result = split_section_content("", max_chars=100)
    assert result == [""]
