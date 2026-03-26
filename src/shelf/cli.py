"""Click CLI for shelf."""

import click
from pathlib import Path
from shelf.convert import convert
from shelf.split import split_markdown
from shelf.output import write_shelf


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    default=None,
    type=click.Path(path_type=Path),
    help="Output directory (default: <input stem>/ in current directory)",
)
@click.option(
    "--depth", "-d",
    default=3,
    show_default=True,
    help="Maximum heading depth to split into separate files (H1=chapters, H2=sections)",
)
@click.option(
    "--summarize", "-s",
    is_flag=True,
    default=False,
    help="Add LLM-generated summaries to each section (requires Ollama or API key)",
)
def main(input_path: Path, output: Path | None, depth: int, summarize: bool):
    """Convert a PDF or EPUB textbook into a nested markdown directory.

    INPUT_PATH is the path to the PDF or EPUB file to convert.
    """

    output_dir = output if output is not None else Path.cwd() / input_path.stem

    click.echo(f"Converting {input_path.name}...")
    try:
        markdown = convert(input_path)
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo("Splitting into sections...")
    tree = split_markdown(markdown, depth=depth, source_path=input_path)

    if summarize:
        click.echo("Generating summaries...")
        try:
            from shelf.summarize import summarize_tree
            summarize_tree(tree)
        except Exception as e:
            raise click.ClickException(f"Summarization failed: {e}")

    write_shelf(tree, output_dir)

    chapter_count = tree.chapter_count()
    section_count = tree.section_count()
    rel_out = output_dir.name

    click.echo(
        f"\u2713 Wrote {section_count} sections across {chapter_count} chapters \u2192 {rel_out}/"
    )
    click.echo(f"\u2713 Generated {rel_out}/CLAUDE.md")
    click.echo(
        f"\nAdd this to your root CLAUDE.md to make this book discoverable:\n"
        f"  Reference textbooks are in ./{rel_out}/"
    )
