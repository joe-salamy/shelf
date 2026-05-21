"""Click CLI for shelf."""

from __future__ import annotations

import contextlib
import logging
import sys
from datetime import datetime
from typing import TextIO

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.WARNING)

import click
from pathlib import Path
from shelf.convert import convert
from shelf.split import split_markdown
from shelf.output import write_shelf


class _TeeStream:
    """Write text to the original stream and an additional log file."""

    def __init__(self, primary: TextIO, secondary: TextIO):
        self._primary = primary
        self._secondary = secondary

    def write(self, text: str) -> int:
        self._primary.write(text)
        self._secondary.write(text)
        return len(text)

    def flush(self) -> None:
        self._primary.flush()
        self._secondary.flush()

    def isatty(self) -> bool:
        return self._primary.isatty()

    @property
    def encoding(self) -> str | None:
        return self._primary.encoding

    @property
    def errors(self) -> str | None:
        return self._primary.errors

    def __getattr__(self, name: str):
        return getattr(self._primary, name)


@contextlib.contextmanager
def _tee_console_output(log_file: Path | None):
    """Mirror stdout and stderr to log_file while preserving normal console output."""
    if log_file is None:
        yield
        return

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        f = log_file.open("a", encoding="utf-8")
    except OSError as e:
        raise click.ClickException(f"Unable to open console log file: {e}") from e

    with f:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        tee_stdout = _TeeStream(original_stdout, f)
        tee_stderr = _TeeStream(original_stderr, f)
        retargeted_handlers = []

        sys.stdout = tee_stdout  # type: ignore[assignment]
        sys.stderr = tee_stderr  # type: ignore[assignment]
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler):
                if handler.stream is original_stdout:
                    retargeted_handlers.append((handler, handler.stream))
                    handler.setStream(tee_stdout)
                elif handler.stream is original_stderr:
                    retargeted_handlers.append((handler, handler.stream))
                    handler.setStream(tee_stderr)
        try:
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            for handler, stream in retargeted_handlers:
                handler.setStream(stream)
            sys.stdout = original_stdout
            sys.stderr = original_stderr


def _format_root_textbook_section(
    tree, rel_out: Path, index_filename: str, chapter_count: int, section_count: int
) -> str:
    """Return a compact, textbook-specific AGENTS.md section."""
    rel_out_text = rel_out.as_posix()
    source = tree.source_path.name if tree.source_path else "unknown"
    return "\n".join(
        [
            f"## Shelf Textbook: {tree.title}",
            "",
            f"- Textbook path: `./{rel_out_text}/`",
            f"- Navigation guide: `./{rel_out_text}/{index_filename}`",
            f"- Source file: `{source}`",
            f"- Scope: {chapter_count} chapters, {section_count} sections",
        ]
    )


def _append_root_agents_textbook_section(
    output_dir: Path,
    rel_out: Path,
    tree,
    index_filename: str,
    chapter_count: int,
    section_count: int,
) -> str:
    """Append a generated-book section to the root AGENTS.md when possible."""
    root_agents = Path.cwd() / "AGENTS.md"

    try:
        output_dir.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return "skipped"

    rel_out_text = rel_out.as_posix()
    path_line = f"- Textbook path: `./{rel_out_text}/`"
    section = _format_root_textbook_section(
        tree, rel_out, index_filename, chapter_count, section_count
    )

    try:
        existing = (
            root_agents.read_text(encoding="utf-8") if root_agents.exists() else ""
        )
        if path_line in existing:
            return "present"

        prefix = ""
        separator = "\n" if existing else ""
        if existing and not existing.endswith("\n"):
            prefix = "\n"

        with root_agents.open("a", encoding="utf-8") as f:
            f.write(f"{prefix}{separator}{section}\n")
    except OSError:
        return "failed"

    return "appended"


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(path_type=Path),
    help="Output directory (default: shelf/<input stem>/ in current directory)",
)
@click.option(
    "--depth",
    "-d",
    default=None,
    type=int,
    help="Maximum heading depth to split into separate files (default: all heading levels found in the document)",
)
@click.option(
    "--summarize",
    "-s",
    is_flag=True,
    default=False,
    help="Generate cascading agent summaries and entity indexes via LLM",
)
@click.option(
    "--index-filename",
    default="AGENTS.md",
    show_default=True,
    help="Filename for navigation index files",
)
@click.option(
    "--max-section-chars",
    default=24000,
    type=int,
    show_default=True,
    help="Max characters per LLM call before splitting sections",
)
@click.option(
    "--fallback",
    type=click.Choice(["auto", "none"]),
    default="auto",
    show_default=True,
    help="Behavior when no markdown headers are detected",
)
@click.option(
    "--fallback-max-chars",
    default=24000,
    type=int,
    show_default=True,
    help="Target max characters per synthetic section when fallback is auto",
)
@click.option(
    "--log",
    "enable_log",
    is_flag=True,
    default=False,
    help="Log all LLM request/response pairs to logs/<textbook>/",
)
@click.option(
    "--test",
    "-t",
    is_flag=True,
    default=False,
    help="Test mode: only summarize the first 5 sections (implies --summarize)",
)
@click.option(
    "--offset",
    default=0,
    type=int,
    show_default=True,
    help="Skip the first N sections before summarizing (useful with --test to skip intro material)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip cost-estimate confirmation prompt",
)
def main(
    input_path: Path,
    output: Path | None,
    depth: int,
    summarize: bool,
    index_filename: str,
    max_section_chars: int,
    fallback: str,
    fallback_max_chars: int,
    enable_log: bool,
    test: bool,
    offset: int,
    yes: bool,
) -> None:
    """Convert a PDF or EPUB textbook into a nested markdown directory.

    INPUT_PATH is the path to the PDF or EPUB file to convert.
    """

    output_dir = (
        output if output is not None else Path.cwd() / "shelf" / input_path.stem
    )

    if test:
        summarize = True
    elif enable_log and not summarize:
        raise click.UsageError("--log requires --summarize or --test")

    llm_log_file = None
    console_log_file = None
    if enable_log:
        from shelf.slugify import slugify

        book_slug = slugify(input_path.stem)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        log_dir = Path.cwd() / "logs" / book_slug
        llm_log_file = log_dir / f"{timestamp}.jsonl"
        console_log_file = log_dir / f"{timestamp}.txt"

    with _tee_console_output(console_log_file):
        if test:
            msg = "Test mode: limiting to 5 section summaries"
            if offset:
                msg += f" (skipping first {offset} sections)"
            click.echo(msg)

        click.echo(f"Converting {input_path.name}...")
        try:
            markdown = convert(
                input_path, on_progress=lambda msg: click.echo(f"  {msg}")
            )
        except ValueError as e:
            raise click.ClickException(str(e))

        click.echo("Splitting into sections...")
        try:
            tree = split_markdown(
                markdown,
                depth=depth,
                source_path=input_path,
                fallback=fallback,  # type: ignore[arg-type]
                fallback_max_chars=fallback_max_chars,
            )
        except ValueError as e:
            raise click.ClickException(str(e))

        book_summary = None
        if summarize:
            click.echo("Generating summaries and entity indexes...")
            try:
                from shelf.summarize import (
                    ContextWindowExceededError,
                    generate_book_summary,
                    get_backend,
                )
                from shelf.summarize.logging_backend import LoggingBackend

                backend = get_backend()

                # Cost estimate & approval
                from shelf.summarize.estimate import estimate_cost

                section_lim = 5 if test else None
                est = estimate_cost(
                    tree,
                    max_chars=max_section_chars,
                    section_limit=section_lim,
                    section_offset=offset,
                )

                click.echo("\nEstimated LLM usage:")
                click.echo(
                    f"  Sections:  ~{est.phase1_input_tokens:,} input / "
                    f"~{est.phase1_output_tokens:,} output tokens "
                    f"({est.phase1_llm_calls} calls)"
                )
                click.echo(
                    f"  Chapters:  ~{est.phase2_input_tokens:,} input / "
                    f"~{est.phase2_output_tokens:,} output tokens "
                    f"({est.phase2_llm_calls} calls)"
                )
                click.echo(
                    f"  Book:      ~{est.phase3_input_tokens:,} input / "
                    f"~{est.phase3_output_tokens:,} output tokens "
                    f"({est.phase3_llm_calls} calls)"
                )
                click.echo(
                    f"  Total:     ~{est.total_input_tokens:,} input / "
                    f"~{est.total_output_tokens:,} output tokens"
                )
                click.echo(f"  Est. cost: ${est.total_cost_usd:.4f}\n")

                if not yes:
                    click.confirm("Proceed?", default=True, abort=True)

                # Wrap backend with JSONL logger if --log is enabled
                if llm_log_file is not None:
                    backend = LoggingBackend(backend, llm_log_file)
                    click.echo(
                        f"  Logging LLM calls to {llm_log_file.relative_to(Path.cwd())}"
                    )
                    click.echo(
                        "  Logging console output to "
                        f"{console_log_file.relative_to(Path.cwd())}"
                    )

                book_summary = generate_book_summary(
                    tree,
                    backend,
                    max_chars=max_section_chars,
                    on_progress=lambda msg: click.echo(f"  {msg}"),
                    section_limit=5 if test else None,
                    section_offset=offset,
                )
            except ContextWindowExceededError as e:
                raise click.ClickException(
                    f"Context window exceeded: {e}\n"
                    "Try reducing --max-section-chars or using a model with a larger context window."
                )
            except click.Abort:
                raise
            except click.ClickException:
                raise
            except Exception as e:
                raise click.ClickException(f"Summarization failed: {e}")

        write_shelf(
            tree, output_dir, book_summary=book_summary, index_filename=index_filename
        )

        chapter_count = tree.chapter_count()
        section_count = tree.section_count()
        try:
            rel_out = output_dir.relative_to(Path.cwd())
        except ValueError:
            rel_out = output_dir

        if test:
            summarized = min(5, section_count)
            click.echo(
                f"Done! Summarized {summarized} of {section_count} sections (test mode) across {chapter_count} chapters -> {rel_out}/"
            )
        else:
            click.echo(
                f"Done! Wrote {section_count} sections across {chapter_count} chapters -> {rel_out}/"
            )
        click.echo(f"Generated {rel_out}/{index_filename}")

        if book_summary:
            click.echo(f"Generated {rel_out}/ENTITIES.md and {rel_out}/GRAPH.md")

        if output_dir.exists():
            pointer_status = _append_root_agents_textbook_section(
                output_dir,
                rel_out,
                tree,
                index_filename,
                chapter_count,
                section_count,
            )
        else:
            pointer_status = "skipped"

        if pointer_status == "appended":
            click.echo(f"Added textbook pointer to {Path.cwd() / 'AGENTS.md'}")
        elif pointer_status == "present":
            click.echo(f"Textbook pointer already exists in {Path.cwd() / 'AGENTS.md'}")
        else:
            click.echo(
                f"\nAdd this to your root AGENTS.md to make this book discoverable:\n"
                f"{_format_root_textbook_section(tree, rel_out, index_filename, chapter_count, section_count)}"
            )
