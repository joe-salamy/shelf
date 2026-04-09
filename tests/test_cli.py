"""Integration tests for the shelf CLI using Click's CliRunner."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from shelf.cli import main
from shelf.models import BookTree, Section


FAKE_MARKDOWN = """\
# Constitutional Law

Introduction.

## Chapter 1: Due Process

Due process content.

## Chapter 2: Equal Protection

Equal protection content.
"""


def _make_fake_tree():
    sec1 = Section(
        title="Chapter 1: Due Process", level=2, content="Due process content."
    )
    sec2 = Section(
        title="Chapter 2: Equal Protection",
        level=2,
        content="Equal protection content.",
    )
    ch = Section(
        title="Constitutional Law",
        level=1,
        content="Introduction.",
        children=[sec1, sec2],
    )
    return BookTree(
        title="Constitutional Law", sections=[ch], source_path=Path("test.pdf")
    )


def test_shelf_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "INPUT_PATH" in result.output
    assert "--output" in result.output
    assert "--summarize" in result.output
    assert "--depth" in result.output


def test_shelf_runs_end_to_end(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    out_dir = tmp_path / "output"

    fake_tree = _make_fake_tree()

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf") as mock_write,
    ):
        result = runner.invoke(main, [str(pdf), "--output", str(out_dir)])

    assert result.exit_code == 0
    mock_write.assert_called_once()


def test_shelf_prints_success_message(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf"),
    ):
        result = runner.invoke(main, [str(pdf), "--output", str(tmp_path / "out")])

    assert "Done!" in result.output
    assert "sections" in result.output
    assert "chapters" in result.output
    assert "CLAUDE.md" in result.output


def test_shelf_unsupported_format(tmp_path):
    docx = tmp_path / "test.docx"
    docx.write_text("content")

    runner = CliRunner()
    with patch(
        "shelf.cli.convert", side_effect=ValueError("Unsupported file type '.docx'")
    ):
        result = runner.invoke(main, [str(docx)])

    assert result.exit_code != 0
    assert "Unsupported" in result.output


def test_shelf_default_output_dir(tmp_path):
    pdf = tmp_path / "my-textbook.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()
    captured_args = {}

    def capture_write(tree, output_dir, smart_index=None):
        captured_args["output_dir"] = output_dir

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf", side_effect=capture_write),
    ):
        result = runner.invoke(main, [str(pdf)])

    assert "output_dir" in captured_args
    assert captured_args["output_dir"].name == "my-textbook"


def test_shelf_summarize_flag(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()
    from shelf.summarize import SmartIndex

    fake_smart_index = SmartIndex(descriptions={}, overview="Test overview.")

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf"),
        patch("shelf.summarize.generate_smart_index", return_value=fake_smart_index),
    ):
        result = runner.invoke(
            main, [str(pdf), "--output", str(tmp_path / "out"), "--summarize"]
        )

    assert result.exit_code == 0
