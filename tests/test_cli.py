"""Integration tests for the shelf CLI using Click's CliRunner."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from shelf.cli import main
from shelf.models import BookTree, Section
from shelf.summarize.base import LLMResult
from shelf.summarize.models import BookSummary

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


def test_shelf_processes_multiple_inputs_in_series(tmp_path):
    pdf1 = tmp_path / "first.pdf"
    pdf2 = tmp_path / "second.pdf"
    pdf1.write_bytes(b"%PDF-1.4 fake")
    pdf2.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()
    converted = []
    output_dirs = []

    def capture_convert(path, **kwargs):
        converted.append(path.name)
        return FAKE_MARKDOWN

    def capture_write(tree, output_dir, book_summary=None, index_filename="AGENTS.md"):
        output_dirs.append(output_dir)

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", side_effect=capture_convert),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf", side_effect=capture_write),
    ):
        result = runner.invoke(main, [str(pdf1), str(pdf2)])

    assert result.exit_code == 0, result.output
    assert converted == ["first.pdf", "second.pdf"]
    assert [path.name for path in output_dirs] == ["first", "second"]
    assert "Textbook 1/2: first.pdf" in result.output
    assert "Textbook 2/2: second.pdf" in result.output


def test_shelf_rejects_output_with_multiple_inputs(tmp_path):
    pdf1 = tmp_path / "first.pdf"
    pdf2 = tmp_path / "second.pdf"
    pdf1.write_bytes(b"%PDF-1.4 fake")
    pdf2.write_bytes(b"%PDF-1.4 fake")

    runner = CliRunner()
    with patch("shelf.cli.convert") as mock_convert:
        result = runner.invoke(
            main, [str(pdf1), str(pdf2), "--output", str(tmp_path / "out")]
        )

    assert result.exit_code != 0
    assert "--output can only be used with one input" in result.output
    mock_convert.assert_not_called()


def test_shelf_stops_batch_on_first_failure(tmp_path):
    pdf1 = tmp_path / "first.pdf"
    pdf2 = tmp_path / "second.pdf"
    pdf1.write_bytes(b"%PDF-1.4 fake")
    pdf2.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()
    writes = []

    def capture_convert(path, **kwargs):
        if path.name == "second.pdf":
            raise ValueError("Unsupported file type")
        return FAKE_MARKDOWN

    def capture_write(tree, output_dir, book_summary=None, index_filename="AGENTS.md"):
        writes.append(output_dir.name)

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", side_effect=capture_convert),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf", side_effect=capture_write),
    ):
        result = runner.invoke(main, [str(pdf1), str(pdf2)])

    assert result.exit_code != 0
    assert writes == ["first"]
    assert "Unsupported file type" in result.output


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


def test_shelf_auto_appends_root_agents_textbook_section(tmp_path):
    fake_tree = _make_fake_tree()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        pdf = Path("test.pdf")
        pdf.write_bytes(b"%PDF-1.4 fake")
        Path("AGENTS.md").write_text("# Project\n", encoding="utf-8")

        def capture_write(
            tree, output_dir, book_summary=None, index_filename="AGENTS.md"
        ):
            output_dir.mkdir(parents=True)

        with (
            patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
            patch("shelf.cli.split_markdown", return_value=fake_tree),
            patch("shelf.cli.write_shelf", side_effect=capture_write),
        ):
            result = runner.invoke(main, [str(pdf), "--output", "shelf/con-law"])

        assert result.exit_code == 0
        assert "Added textbook pointer" in result.output
        content = Path("AGENTS.md").read_text(encoding="utf-8")
        assert "## Shelf Textbook: Constitutional Law" in content
        assert f"- Textbook path: `./{Path('shelf/con-law').as_posix()}/`" in content
        assert "- Navigation guide: `./shelf/con-law/AGENTS.md`" in content
        assert "- Source file: `test.pdf`" in content
        assert "- Scope: 1 chapters, 2 sections" in content
        assert "## File guide" not in content
        assert "`INDEX.md`" not in content


def test_shelf_creates_root_agents_when_missing(tmp_path):
    fake_tree = _make_fake_tree()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        pdf = Path("test.pdf")
        pdf.write_bytes(b"%PDF-1.4 fake")

        def capture_write(
            tree, output_dir, book_summary=None, index_filename="AGENTS.md"
        ):
            output_dir.mkdir(parents=True)

        with (
            patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
            patch("shelf.cli.split_markdown", return_value=fake_tree),
            patch("shelf.cli.write_shelf", side_effect=capture_write),
        ):
            result = runner.invoke(main, [str(pdf), "--output", "shelf/con-law"])

        assert result.exit_code == 0
        assert Path("AGENTS.md").exists()
        content = Path("AGENTS.md").read_text(encoding="utf-8")
        assert content.startswith("## Shelf Textbook: Constitutional Law\n")
        assert f"- Textbook path: `./{Path('shelf/con-law').as_posix()}/`" in content


def test_shelf_does_not_duplicate_existing_textbook_section(tmp_path):
    fake_tree = _make_fake_tree()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        pdf = Path("test.pdf")
        pdf.write_bytes(b"%PDF-1.4 fake")

        existing_section = "\n".join(
            [
                "## Shelf Textbook: Constitutional Law",
                "",
                "- Textbook path: `./shelf/con-law/`",
                "- Navigation guide: `./shelf/con-law/AGENTS.md`",
                "- Source file: `test.pdf`",
                "- Scope: 1 chapters, 2 sections",
                "",
            ]
        )
        Path("AGENTS.md").write_text(existing_section, encoding="utf-8")

        def capture_write(
            tree, output_dir, book_summary=None, index_filename="AGENTS.md"
        ):
            output_dir.mkdir(parents=True)

        with (
            patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
            patch("shelf.cli.split_markdown", return_value=fake_tree),
            patch("shelf.cli.write_shelf", side_effect=capture_write),
        ):
            result = runner.invoke(main, [str(pdf), "--output", "shelf/con-law"])

        assert result.exit_code == 0
        assert "already exists" in result.output
        assert Path("AGENTS.md").read_text(encoding="utf-8") == existing_section


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


def test_shelf_resume_summaries_passes_checkpoint_dir(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake_tree = _make_fake_tree()
    fake_summary = BookSummary(overview="Test overview.", chapter_summaries=[])
    captured_kwargs = {}

    def capture_summary(tree, backend, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_summary

    runner = CliRunner()
    with (
        patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
        patch("shelf.cli.split_markdown", return_value=fake_tree),
        patch("shelf.cli.write_shelf"),
        patch("shelf.summarize.get_backend", return_value=MagicMock()),
        patch(
            "shelf.summarize.generate_book_summary",
            side_effect=capture_summary,
        ),
    ):
        result = runner.invoke(
            main,
            [
                str(pdf),
                "--output",
                str(tmp_path / "out"),
                "--summarize",
                "--resume-summaries",
                "--yes",
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured_kwargs["checkpoint_dir"] == (
        tmp_path / "out" / ".shelf-summary-cache"
    )


def test_shelf_resume_summaries_requires_summarization(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    runner = CliRunner()
    result = runner.invoke(main, [str(pdf), "--resume-summaries"])

    assert result.exit_code != 0
    assert "--resume-summaries requires --summarize or --test" in result.output


def test_shelf_log_requires_summarization(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    runner = CliRunner()
    result = runner.invoke(main, [str(pdf), "--log"])

    assert result.exit_code != 0
    assert "--log requires --summarize or --test" in result.output


def test_shelf_log_writes_jsonl_and_console_txt_files(tmp_path):
    fake_tree = _make_fake_tree()
    fake_summary = BookSummary(overview="Test overview.", chapter_summaries=[])
    inner_backend = MagicMock()
    inner_backend.summarize.return_value = LLMResult(
        text='{"overview": "Logged."}',
        metadata={"provider": "test"},
    )

    def capture_summary(tree, backend, **kwargs):
        backend.summarize("input", "prompt")
        return fake_summary

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        pdf = Path("Test Book.pdf")
        pdf.write_bytes(b"%PDF-1.4 fake")

        with (
            patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
            patch("shelf.cli.split_markdown", return_value=fake_tree),
            patch("shelf.cli.write_shelf"),
            patch("shelf.summarize.get_backend", return_value=inner_backend),
            patch(
                "shelf.summarize.generate_book_summary",
                side_effect=capture_summary,
            ),
        ):
            result = runner.invoke(
                main,
                [str(pdf), "--output", "out", "--summarize", "--log", "--yes"],
            )

        assert result.exit_code == 0, result.output
        log_files = list(Path("logs/test-book").glob("*.jsonl"))
        assert len(log_files) == 1
        assert log_files[0].read_text(encoding="utf-8").strip()
        console_log_files = list(Path("logs/test-book").glob("*.txt"))
        assert len(console_log_files) == 1
        console_log = console_log_files[0].read_text(encoding="utf-8")
        assert "Converting Test Book.pdf..." in console_log
        assert "Splitting into sections..." in console_log
        assert "Estimated LLM usage:" in console_log
        assert "Logging LLM calls to logs" in console_log
        assert "Logging console output to logs" in console_log
        assert "Done!" in console_log
        assert "Generated out/AGENTS.md" in console_log
        assert "Logging LLM calls to logs" in result.output
        assert "Logging console output to logs" in result.output


def test_shelf_log_console_txt_captures_stdout_and_stderr(tmp_path):
    fake_tree = _make_fake_tree()
    fake_summary = BookSummary(overview="Test overview.", chapter_summaries=[])
    inner_backend = MagicMock()
    inner_backend.summarize.return_value = LLMResult(
        text='{"overview": "Logged."}',
        metadata={"provider": "test"},
    )

    def capture_summary(tree, backend, **kwargs):
        print("third-party stdout")
        print("third-party stderr", file=sys.stderr)
        backend.summarize("input", "prompt")
        return fake_summary

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        pdf = Path("Test Book.pdf")
        pdf.write_bytes(b"%PDF-1.4 fake")

        with (
            patch("shelf.cli.convert", return_value=FAKE_MARKDOWN),
            patch("shelf.cli.split_markdown", return_value=fake_tree),
            patch("shelf.cli.write_shelf"),
            patch("shelf.summarize.get_backend", return_value=inner_backend),
            patch(
                "shelf.summarize.generate_book_summary",
                side_effect=capture_summary,
            ),
        ):
            result = runner.invoke(
                main,
                [str(pdf), "--output", "out", "--summarize", "--log", "--yes"],
            )

        assert result.exit_code == 0, result.output
        console_log_files = list(Path("logs/test-book").glob("*.txt"))
        assert len(console_log_files) == 1
        console_log = console_log_files[0].read_text(encoding="utf-8")
        assert "third-party stdout" in console_log
        assert "third-party stderr" in console_log


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
