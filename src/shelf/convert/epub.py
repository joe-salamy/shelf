"""EPUB converter backend using markitdown."""

from pathlib import Path

from shelf.convert.base import ProgressCallback


class EPUBBackend:
    def convert(self, path: Path, on_progress: ProgressCallback | None = None) -> str:
        """Convert an EPUB file to markdown using markitdown."""
        if on_progress:
            on_progress("Extracting EPUB text...")

        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert(str(path))
        return result.text_content
