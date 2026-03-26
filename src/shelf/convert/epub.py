"""EPUB converter backend using markitdown."""

from pathlib import Path


class EPUBBackend:
    def convert(self, path: Path) -> str:
        """Convert an EPUB file to markdown using markitdown."""
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(path))
        return result.text_content
