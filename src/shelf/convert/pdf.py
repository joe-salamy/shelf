"""PDF converter backend using pymupdf4llm."""

from pathlib import Path
from typing import cast

from shelf.convert.base import ProgressCallback

_PDF_BATCH_SIZE = 25


class PDFBackend:
    def convert(self, path: Path, on_progress: ProgressCallback | None = None) -> str:
        """Convert a PDF file to markdown using pymupdf4llm."""
        import fitz  # type: ignore[import-untyped]
        import pymupdf4llm  # type: ignore[import-untyped]

        with fitz.open(path) as doc:
            page_count = doc.page_count

        if page_count == 0:
            return ""

        chunks: list[str] = []
        for start in range(0, page_count, _PDF_BATCH_SIZE):
            end = min(start + _PDF_BATCH_SIZE, page_count)
            if on_progress:
                on_progress(f"Extracting PDF pages {start + 1}-{end} of {page_count}")
            chunk = cast(
                str,
                pymupdf4llm.to_markdown(
                    str(path),
                    pages=list(range(start, end)),
                    ignore_images=True,
                    ignore_graphics=True,
                ),
            )
            if chunk.strip():
                chunks.append(chunk)

        return "\n\n".join(chunks)
