"""Shared pytest fixtures."""

import pytest
from pathlib import Path


SIMPLE_MARKDOWN = """\
# Chapter One

Introduction to chapter one.

## Section 1.1

Content for section 1.1.

### Subsection 1.1.1

Content for subsection 1.1.1.

## Section 1.2

Content for section 1.2.

# Chapter Two

Introduction to chapter two.

## Section 2.1

Content for section 2.1.
"""


@pytest.fixture
def simple_markdown():
    return SIMPLE_MARKDOWN


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"
