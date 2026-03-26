"""Convert PDF/EPUB files to markdown. Dispatches by file extension."""

from pathlib import Path
from importlib.metadata import entry_points

from shelf.convert.base import ConvertBackend


def _load_backends() -> dict[str, type[ConvertBackend]]:
    """Load all registered converter backends from entry points."""
    backends: dict[str, type[ConvertBackend]] = {}
    for ep in entry_points(group="shelf.converters"):
        backends[ep.name.lower()] = ep.load()
    return backends


def convert(path: Path | str) -> str:
    """Convert a PDF or EPUB file to markdown text.

    Args:
        path: Path to the input file.

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
        raise ValueError(
            f"Unsupported file type '.{ext}'. Supported: {supported or 'none registered'}"
        )

    backend = backends[ext]()
    return backend.convert(path)
