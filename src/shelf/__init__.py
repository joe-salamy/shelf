"""Shelf: convert PDF/EPUB textbooks into nested, grep-friendly markdown directories."""

__version__ = "0.1.0"


def shelf(input_path, output_dir=None, depth=3, summarize=False):
    """High-level API: convert a textbook file to a markdown directory tree."""
    from pathlib import Path
    from shelf.convert import convert
    from shelf.split import split_markdown
    from shelf.output import write_shelf

    input_path = Path(input_path)
    if output_dir is None:
        output_dir = Path.cwd() / input_path.stem
    else:
        output_dir = Path(output_dir)

    markdown = convert(input_path)
    tree = split_markdown(markdown, depth=depth, source_path=input_path)

    smart_index = None
    if summarize:
        from shelf.summarize import generate_smart_index
        smart_index = generate_smart_index(tree)

    write_shelf(tree, output_dir, smart_index=smart_index)
    return output_dir
