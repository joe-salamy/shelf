"""Convert PDF/EPUB files to markdown. Dispatches by file extension."""

from importlib.metadata import entry_points
from pathlib import Path

from shelf.convert.base import ConvertBackend, ProgressCallback


def _load_backends() -> dict[str, type[ConvertBackend]]:
    """Load all registered converter backends from entry points."""
    backends: dict[str, type[ConvertBackend]] = {}
    for ep in entry_points(group="shelf.converters"):
        backends[ep.name.lower()] = ep.load()
    return backends


def convert(path: Path | str, on_progress: ProgressCallback | None = None) -> str:
    """Convert a PDF or EPUB file to markdown text.

    Args:
        path: Path to the input file.
        on_progress: Optional callback for long-running conversion updates.

    Returns:
        Markdown string.

    Raises:
        ValueError: If the file extension is not supported.
    """
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")

    backends = _load_backends()
    if ext not in backends:
        supported = ", ".join(f".{k}" for k in sorted(backends))
        supported = supported or "none registered"
        raise ValueError(f"Unsupported file type '.{ext}'. Supported: {supported}")

    backend = backends[ext]()
    markdown = backend.convert(path, on_progress=on_progress)
    if not markdown.strip():
        raise ValueError(
            "Conversion produced no extractable text. This PDF may be scanned, "
            "image-only, encrypted, or otherwise unsupported by the current "
            "text extractor."
        )
    return markdown
