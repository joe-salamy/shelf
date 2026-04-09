"""Click CLI for shelf."""

import logging
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.WARNING)

import click
from pathlib import Path
from shelf.convert import convert
from shelf.split import split_markdown
from shelf.output import write_shelf


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
    help="Generate cascading CLAUDE.md summaries and entity indexes via LLM",
)
@click.option(
    "--index-filename",
    default="CLAUDE.md",
    show_default=True,
    help="Filename for navigation index files (e.g. AGENTS.md for non-Claude harnesses)",
)
@click.option(
    "--max-section-chars",
    default=24000,
    type=int,
    show_default=True,
    help="Max characters per LLM call before splitting sections",
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
    enable_log: bool,
    test: bool,
    yes: bool,
):
    """Convert a PDF or EPUB textbook into a nested markdown directory.

    INPUT_PATH is the path to the PDF or EPUB file to convert.
    """

    output_dir = (
        output if output is not None else Path.cwd() / "shelf" / input_path.stem
    )

    click.echo(f"Converting {input_path.name}...")
    try:
        markdown = convert(input_path)
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("Splitting into sections...")
    tree = split_markdown(markdown, depth=depth, source_path=input_path)

    if test:
        summarize = True
        click.echo("Test mode: limiting to first 5 section summaries")

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
            from shelf.slugify import slugify

            backend = get_backend()

            # Cost estimate & approval
            from shelf.summarize.estimate import estimate_cost

            section_lim = 5 if test else None
            est = estimate_cost(tree, max_chars=max_section_chars, section_limit=section_lim)

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
            if enable_log:
                book_slug = slugify(input_path.stem)
                log_file = (
                    Path.cwd()
                    / "logs"
                    / book_slug
                    / f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.jsonl"
                )
                backend = LoggingBackend(backend, log_file)
                click.echo(f"  Logging LLM calls to {log_file.relative_to(Path.cwd())}")

            book_summary = generate_book_summary(
                tree,
                backend,
                max_chars=max_section_chars,
                on_progress=lambda msg: click.echo(f"  {msg}"),
                section_limit=5 if test else None,
            )
        except ContextWindowExceededError as e:
            raise click.ClickException(
                f"Context window exceeded: {e}\n"
                "Try reducing --max-section-chars or using a model with a larger context window."
            )
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

    click.echo(
        f"Done! Wrote {section_count} sections across {chapter_count} chapters -> {rel_out}/"
    )
    click.echo(f"Generated {rel_out}/{index_filename}")

    if book_summary:
        click.echo(f"Generated {rel_out}/ENTITIES.md and {rel_out}/GRAPH.md")

    # Suggest how to make the book discoverable
    click.echo(
        f"\nAdd this to your root CLAUDE.md to make this book discoverable:\n"
        f"  Reference textbooks are in ./{rel_out}/"
    )

    # Auto-append pointer to root CLAUDE.md if output dir was actually created
    root_claude = Path.cwd() / "CLAUDE.md"
    if root_claude.exists() and output_dir.exists():
        try:
            output_dir.resolve().relative_to(Path.cwd().resolve())
        except ValueError:
            pass  # output dir is outside cwd — skip
        else:
            existing = root_claude.read_text(encoding="utf-8")
            pointer_line = f"\nReference textbooks are in ./{rel_out}/\n"
            if str(rel_out) not in existing:
                try:
                    with root_claude.open("a", encoding="utf-8") as f:
                        f.write(pointer_line)
                    click.echo(f"  (Auto-appended to {root_claude.name})")
                except OSError:
                    pass
