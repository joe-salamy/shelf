"""Protocol definition for converter backends."""

from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

ProgressCallback = Callable[[str], None]


@runtime_checkable
class ConvertBackend(Protocol):
    def convert(self, path: Path, on_progress: ProgressCallback | None = None) -> str:
        """Convert the file at path to a markdown string."""
        ...
