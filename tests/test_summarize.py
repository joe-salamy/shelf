"""Tests for shelf.summarize with mocked LLM backend."""

import pytest
from unittest.mock import MagicMock, patch
from shelf.models import BookTree, Section
from shelf.summarize import summarize_tree, get_backend


class MockBackend:
    def summarize(self, text: str, prompt: str) -> str:
        return f"Summary of: {text[:20]}"


def test_summarize_tree_prepends_summary():
    sec = Section(title="Section 1", level=2, content="Original content here.")
    ch = Section(title="Chapter 1", level=1, content="Chapter content.", children=[sec])
    tree = BookTree(title="Book", sections=[ch])

    with patch("shelf.summarize.get_backend", return_value=MockBackend()):
        summarize_tree(tree)

    assert "> **Summary:**" in ch.content
    assert "---" in ch.content
    assert "Chapter content" in ch.content


def test_summarize_tree_all_sections():
    sec1 = Section(title="Sec 1", level=2, content="Content 1.")
    sec2 = Section(title="Sec 2", level=2, content="Content 2.")
    ch = Section(title="Ch 1", level=1, content="Ch content.", children=[sec1, sec2])
    tree = BookTree(title="Book", sections=[ch])

    with patch("shelf.summarize.get_backend", return_value=MockBackend()):
        summarize_tree(tree)

    for section in tree.walk():
        if section.content:
            assert "> **Summary:**" in section.content


def test_summarize_skips_empty_content():
    sec = Section(title="Empty Section", level=2, content="")
    ch = Section(title="Ch", level=1, content="Content.", children=[sec])
    tree = BookTree(title="Book", sections=[ch])

    with patch("shelf.summarize.get_backend", return_value=MockBackend()):
        summarize_tree(tree)

    # Empty section should not get a summary header
    assert sec.content == ""


def test_get_backend_uses_api_key_when_set(monkeypatch):
    monkeypatch.setenv("SHELF_LLM_API_KEY", "test-key")
    with patch("shelf.summarize.openai_compat.OpenAICompatBackend") as mock_cls:
        mock_cls.return_value = MagicMock()
        from shelf.summarize import get_backend
        backend = get_backend()
    mock_cls.assert_called_once()


def test_get_backend_uses_ollama_when_available(monkeypatch):
    monkeypatch.delenv("SHELF_LLM_API_KEY", raising=False)
    with patch("shelf.summarize.ollama.OllamaBackend") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_cls.return_value = mock_instance
        from shelf.summarize import get_backend
        backend = get_backend()
    assert backend is mock_instance


def test_get_backend_raises_when_nothing_available(monkeypatch):
    monkeypatch.delenv("SHELF_LLM_API_KEY", raising=False)
    with patch("shelf.summarize.ollama.OllamaBackend") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = False
        mock_cls.return_value = mock_instance
        from shelf.summarize import get_backend
        with pytest.raises(RuntimeError, match="No LLM backend"):
            get_backend()
