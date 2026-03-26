"""Tests for shelf.summarize smart index generation."""

import json
import pytest
from unittest.mock import MagicMock, patch
from shelf.models import BookTree, Section
from shelf.summarize import generate_smart_index, get_backend, SmartIndex


class MockBackend:
    def summarize(self, text: str, prompt: str) -> str:
        return json.dumps({
            "descriptions": {
                "Chapter 1": "First chapter covering basics.",
                "Section 1.1": "Detailed look at subsection one.",
            },
            "overview": "This book covers constitutional law fundamentals.",
        })


def _make_tree() -> BookTree:
    sec = Section(title="Section 1.1", level=2, content="Section content here. More details follow.")
    ch = Section(title="Chapter 1", level=1, content="Chapter intro here.", children=[sec])
    return BookTree(title="Con Law", sections=[ch])


def test_generate_smart_index_returns_smart_index():
    tree = _make_tree()
    with patch("shelf.summarize.get_backend", return_value=MockBackend()):
        result = generate_smart_index(tree)
    assert isinstance(result, SmartIndex)


def test_generate_smart_index_descriptions():
    tree = _make_tree()
    with patch("shelf.summarize.get_backend", return_value=MockBackend()):
        result = generate_smart_index(tree)
    assert "Chapter 1" in result.descriptions
    assert "Section 1.1" in result.descriptions


def test_generate_smart_index_overview():
    tree = _make_tree()
    with patch("shelf.summarize.get_backend", return_value=MockBackend()):
        result = generate_smart_index(tree)
    assert "constitutional law" in result.overview.lower()


def test_generate_smart_index_handles_malformed_json():
    class BadBackend:
        def summarize(self, text: str, prompt: str) -> str:
            return "not json at all"

    tree = _make_tree()
    with patch("shelf.summarize.get_backend", return_value=BadBackend()):
        result = generate_smart_index(tree)
    assert isinstance(result, SmartIndex)
    assert result.descriptions == {}


def test_generate_smart_index_handles_json_in_code_fence():
    class FenceBackend:
        def summarize(self, text: str, prompt: str) -> str:
            return '```json\n{"descriptions": {"Ch": "desc"}, "overview": "ov"}\n```'

    tree = _make_tree()
    with patch("shelf.summarize.get_backend", return_value=FenceBackend()):
        result = generate_smart_index(tree)
    assert result.descriptions.get("Ch") == "desc"
    assert result.overview == "ov"


def test_get_backend_uses_api_key_when_set(monkeypatch):
    monkeypatch.setenv("SHELF_LLM_API_KEY", "test-key")
    with patch("shelf.summarize.openai_compat.OpenAICompatBackend") as mock_cls:
        mock_cls.return_value = MagicMock()
        backend = get_backend()
    mock_cls.assert_called_once()


def test_get_backend_uses_ollama_when_available(monkeypatch):
    monkeypatch.delenv("SHELF_LLM_API_KEY", raising=False)
    with patch("shelf.summarize.ollama.OllamaBackend") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_cls.return_value = mock_instance
        backend = get_backend()
    assert backend is mock_instance


def test_get_backend_raises_when_nothing_available(monkeypatch):
    monkeypatch.delenv("SHELF_LLM_API_KEY", raising=False)
    with patch("shelf.summarize.ollama.OllamaBackend") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = False
        mock_cls.return_value = mock_instance
        with pytest.raises(RuntimeError, match="No LLM backend"):
            get_backend()
