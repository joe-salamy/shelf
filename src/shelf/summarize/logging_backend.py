"""Logging wrapper for LLM backends — writes JSONL logs to disk."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from shelf.summarize.base import LLMBackend, LLMResult


class LoggingBackend:
    """Decorator that logs all LLM calls to a JSONL file."""

    def __init__(self, inner: LLMBackend, log_file: Path):
        self._inner = inner
        self._log_file = log_file
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._call_index = 0

    def summarize(self, text: str, prompt: str) -> LLMResult:
        self._call_index += 1
        start = time.monotonic()
        error_info = None
        result: LLMResult | None = None
        try:
            result = self._inner.summarize(text, prompt)
            return result
        except Exception as exc:
            error_info = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            elapsed = time.monotonic() - start
            entry = {
                "call_index": self._call_index,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(elapsed, 2),
                "prompt_system": prompt,
                "input_text": text,
                "input_text_length": len(text),
                "response_text": result.text if result else None,
                "response_metadata": result.metadata if result else None,
                "error": error_info,
            }
            with self._log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
