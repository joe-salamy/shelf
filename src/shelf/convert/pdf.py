"""PDF converter backend using pymupdf4llm."""

from pathlib import Path
from typing import cast


class PDFBackend:
    def convert(self, path: Path) -> str:
        """Convert a PDF file to markdown using pymupdf4llm."""
        import pymupdf4llm  # type: ignore[import-untyped]

        return cast(str, pymupdf4llm.to_markdown(str(path)))
