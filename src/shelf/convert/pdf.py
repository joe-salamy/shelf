"""PDF converter backend using pymupdf4llm."""

from pathlib import Path


class PDFBackend:
    def convert(self, path: Path) -> str:
        """Convert a PDF file to markdown using pymupdf4llm."""
        import pymupdf4llm
        return pymupdf4llm.to_markdown(str(path))
