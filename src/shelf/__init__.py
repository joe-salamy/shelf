"""Shelf: convert PDF/EPUB textbooks into nested, grep-friendly markdown directories."""

from pathlib import Path

__version__ = "0.1.0"


def shelf(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    depth: int | None = 3,
    summarize: bool = False,
    fallback: str = "auto",
    fallback_max_chars: int = 24000,
) -> Path:
    """High-level API: convert a textbook file to a markdown directory tree."""

    from shelf.convert import convert
    from shelf.output import write_shelf
    from shelf.split import split_markdown
    from shelf.summarize.models import BookSummary

    input_path = Path(input_path)
    if output_dir is None:
        output_dir = Path.cwd() / input_path.stem
    else:
        output_dir = Path(output_dir)

    markdown = convert(input_path)
    tree = split_markdown(
        markdown,
        depth=depth,
        source_path=input_path,
        fallback=fallback,  # type: ignore[arg-type]
        fallback_max_chars=fallback_max_chars,
    )

    book_summary: BookSummary | None = None
    if summarize:
        from shelf.summarize import generate_book_summary, get_backend

        book_summary = generate_book_summary(tree, get_backend())

    write_shelf(tree, output_dir, book_summary=book_summary)
    return output_dir
