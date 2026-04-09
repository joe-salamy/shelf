"""Tests for shelf.summarize — get_backend selection logic."""

import pytest
from unittest.mock import MagicMock, patch
from shelf.summarize import get_backend


def test_get_backend_uses_api_key_when_set(monkeypatch):
    monkeypatch.setattr("shelf.summarize.SHELF_LLM_API_KEY", "test-key")
    with patch("shelf.summarize.openai_compat.OpenAICompatBackend") as mock_cls:
        mock_cls.return_value = MagicMock()
        backend = get_backend()
    mock_cls.assert_called_once()


def test_get_backend_uses_ollama_when_available(monkeypatch):
    monkeypatch.setattr("shelf.summarize.SHELF_LLM_API_KEY", "")
    with patch("shelf.summarize.ollama.OllamaBackend") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_cls.return_value = mock_instance
        backend = get_backend()
    assert backend is mock_instance


def test_get_backend_raises_when_nothing_available(monkeypatch):
    monkeypatch.setattr("shelf.summarize.SHELF_LLM_API_KEY", "")
    with patch("shelf.summarize.ollama.OllamaBackend") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = False
        mock_cls.return_value = mock_instance
        with pytest.raises(RuntimeError, match="No LLM backend"):
            get_backend()
