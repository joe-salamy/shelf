"""Tests for shelf.slugify."""

import pytest
from shelf.slugify import slugify


def test_simple_ascii():
    assert slugify("Hello World") == "hello-world"


def test_removes_special_chars():
    assert slugify("Due Process: A History") == "due-process-a-history"


def test_unicode_normalization():
    assert slugify("Café au Lait") == "cafe-au-lait"


def test_multiple_spaces():
    assert slugify("too  many   spaces") == "too-many-spaces"


def test_leading_trailing_hyphens():
    assert slugify("  -leading trailing-  ") == "leading-trailing"


def test_numbers_preserved():
    assert slugify("Chapter 1: Introduction") == "chapter-1-introduction"


def test_already_slugified():
    assert slugify("already-slugified") == "already-slugified"


def test_empty_string():
    assert slugify("") == ""


def test_only_special_chars():
    assert slugify("!!!") == ""


def test_underscores_become_hyphens():
    assert slugify("snake_case_title") == "snake-case-title"
