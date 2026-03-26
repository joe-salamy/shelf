"""Protocol definition for converter backends."""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ConvertBackend(Protocol):
    def convert(self, path: Path) -> str:
        """Convert the file at path to a markdown string."""
        ...
