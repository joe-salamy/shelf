"""Tests for shelf.convert."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from shelf.convert import convert


def test_unsupported_extension(tmp_path):
    f = tmp_path / "document.docx"
    f.write_text("content")
    with pytest.raises(ValueError, match="Unsupported file type"):
        convert(f)


def test_pdf_dispatches_to_pdf_backend(tmp_path):
    f = tmp_path / "test.pdf"
    f.write_bytes(b"%PDF-1.4 fake")

    mock_backend_instance = MagicMock()
    mock_backend_instance.convert.return_value = "# Header\n\nContent."
    mock_backend_class = MagicMock(return_value=mock_backend_instance)

    with patch("shelf.convert._load_backends", return_value={"pdf": mock_backend_class}):
        result = convert(f)

    assert result == "# Header\n\nContent."
    mock_backend_instance.convert.assert_called_once_with(f)


def test_epub_dispatches_to_epub_backend(tmp_path):
    f = tmp_path / "test.epub"
    f.write_bytes(b"PK fake epub")

    mock_backend_instance = MagicMock()
    mock_backend_instance.convert.return_value = "# EPUB Header\n\nEPUB Content."
    mock_backend_class = MagicMock(return_value=mock_backend_instance)

    with patch("shelf.convert._load_backends", return_value={"epub": mock_backend_class}):
        result = convert(f)

    assert result == "# EPUB Header\n\nEPUB Content."


def test_string_path_accepted(tmp_path):
    f = tmp_path / "test.pdf"
    f.write_bytes(b"%PDF-1.4 fake")

    mock_backend_instance = MagicMock()
    mock_backend_instance.convert.return_value = "markdown"
    mock_backend_class = MagicMock(return_value=mock_backend_instance)

    with patch("shelf.convert._load_backends", return_value={"pdf": mock_backend_class}):
        result = convert(str(f))

    assert result == "markdown"


def test_extension_case_insensitive(tmp_path):
    f = tmp_path / "test.PDF"
    f.write_bytes(b"%PDF fake")

    mock_backend_instance = MagicMock()
    mock_backend_instance.convert.return_value = "markdown"
    mock_backend_class = MagicMock(return_value=mock_backend_instance)

    with patch("shelf.convert._load_backends", return_value={"pdf": mock_backend_class}):
        result = convert(f)

    assert result == "markdown"
