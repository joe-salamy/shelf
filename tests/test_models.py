"""Tests for shelf.models."""

import pytest
from shelf.models import Section, BookTree


def _make_tree():
    """Build a small test tree."""
    sub = Section(title="Subsection 1.1.1", level=3, content="sub content")
    sec1 = Section(title="Section 1.1", level=2, content="sec 1.1 content", children=[sub])
    sec2 = Section(title="Section 1.2", level=2, content="sec 1.2 content")
    ch1 = Section(title="Chapter One", level=1, content="ch1 content", children=[sec1, sec2])
    ch2 = Section(title="Chapter Two", level=1, content="ch2 content")
    return BookTree(title="My Book", sections=[ch1, ch2])


def test_chapter_count():
    tree = _make_tree()
    assert tree.chapter_count() == 2


def test_section_count():
    tree = _make_tree()
    # ch1 + sec1 + sub + sec2 + ch2 = 5
    assert tree.section_count() == 5


def test_walk_order():
    tree = _make_tree()
    titles = [s.title for s in tree.walk()]
    assert titles == [
        "Chapter One", "Section 1.1", "Subsection 1.1.1", "Section 1.2", "Chapter Two"
    ]


def test_section_walk():
    sub = Section(title="Sub", level=3, content="")
    sec = Section(title="Sec", level=2, content="", children=[sub])
    titles = [s.title for s in sec.walk()]
    assert titles == ["Sec", "Sub"]


def test_empty_tree():
    tree = BookTree(title="Empty")
    assert tree.chapter_count() == 0
    assert tree.section_count() == 0
    assert list(tree.walk()) == []
