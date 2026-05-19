"""Integration tests for the shelf CLI using Click's CliRunner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

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
    assert "--index-filename" in result.output
    assert "--max-section-chars" in result.output
    assert "--fallback" in result.output
    assert "--fallback-max-chars" in result.output


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
    assert "AGENTS.md" in result.output


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

    def capture_write(tree, output_dir, book_summary=None, index_filename="AGENTS.md"):
        captured_args["output_dir"] = output_dir

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf", side_effect=capture_write),
    ):
        runner.invoke(main, [str(pdf)])

    assert "output_dir" in captured_args
    assert captured_args["output_dir"].name == "my-textbook"
    assert captured_args["output_dir"].parent.name == "shelf"


def test_shelf_summarize_flag(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()

    from shelf.summarize.models import BookSummary

    fake_summary = BookSummary(overview="Test overview.", chapter_summaries=[])

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf"),
        patch("shelf.summarize.get_backend", return_value=MagicMock()),
        patch(
            "shelf.summarize.generate_book_summary",
            return_value=fake_summary,
        ),
    ):
        result = runner.invoke(
            main,
            [str(pdf), "--output", str(tmp_path / "out"), "--summarize", "--yes"],
        )

    assert result.exit_code == 0, result.output


def test_shelf_index_filename_flag(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()
    captured_args = {}

    def capture_write(tree, output_dir, book_summary=None, index_filename="AGENTS.md"):
        captured_args["index_filename"] = index_filename

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf", side_effect=capture_write),
    ):
        result = runner.invoke(main, [str(pdf), "--index-filename", "NAV.md"])

    assert result.exit_code == 0
    assert captured_args["index_filename"] == "NAV.md"


def test_shelf_headerless_input_uses_synthetic_sections(tmp_path):
    pdf = tmp_path / "headerless.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    captured_args = {}

    def capture_write(tree, output_dir, book_summary=None, index_filename="AGENTS.md"):
        captured_args["tree"] = tree

    runner = CliRunner()
    with (
        patch(
            "shelf.cli.convert",
            return_value="First paragraph.\n\nSecond paragraph.",
        ),
        patch("shelf.cli.write_shelf", side_effect=capture_write),
    ):
        result = runner.invoke(main, [str(pdf), "--output", str(tmp_path / "out")])

    assert result.exit_code == 0, result.output
    tree = captured_args["tree"]
    assert tree.chapter_count() == 1
    assert tree.section_count() == 1
    assert tree.sections[0].children[0].title == "Part 001"


def test_shelf_fallback_none_fails_for_headerless_input(tmp_path):
    pdf = tmp_path / "headerless.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    runner = CliRunner()
    with patch("shelf.cli.convert", return_value="No headings here."):
        result = runner.invoke(main, [str(pdf), "--fallback", "none"])

    assert result.exit_code != 0
    assert "No markdown headers" in result.output


def test_shelf_passes_fallback_max_chars(tmp_path):
    pdf = tmp_path / "headerless.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value="No headings here."),
        patch("shelf.cli.split_markdown", return_value=_make_fake_tree()) as mock_split,
        patch("shelf.cli.write_shelf"),
    ):
        result = runner.invoke(
            main,
            [
                str(pdf),
                "--fallback-max-chars",
                "12000",
                "--output",
                str(tmp_path / "out"),
            ],
        )

    assert result.exit_code == 0, result.output
    assert mock_split.call_args.kwargs["fallback_max_chars"] == 12000
