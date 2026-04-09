"""Logging wrapper for LLM backends — writes JSONL logs to disk."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from shelf.summarize.base import LLMBackend


class LoggingBackend:
    """Decorator that logs all LLM calls to a JSONL file."""

    def __init__(self, inner: LLMBackend, log_file: Path):
        self._inner = inner
        self._log_file = log_file
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._call_index = 0

    def summarize(self, text: str, prompt: str) -> str:
        self._call_index += 1
        start = time.monotonic()
        error_info = None
        response = None
        try:
            response = self._inner.summarize(text, prompt)
            return response
        except Exception as exc:
            error_info = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            elapsed = time.monotonic() - start
            entry = {
                "call_index": self._call_index,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(elapsed, 2),
                "prompt_system": prompt[:500],
                "input_text_length": len(text),
                "input_text_preview": text[:500],
                "response": response,
                "error": error_info,
            }
            with self._log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
