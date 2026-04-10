"""OpenAI-compatible API backend using centralized config."""

from __future__ import annotations

import logging
import time

from shelf.config import SHELF_LLM_API_KEY, SHELF_LLM_BASE_URL, SHELF_LLM_MODEL
from shelf.summarize.base import LLMResult
from shelf.summarize.exceptions import ContextWindowExceededError

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0  # seconds


class OpenAICompatBackend:
    def __init__(self):
        self.api_key = SHELF_LLM_API_KEY
        self.base_url = SHELF_LLM_BASE_URL
        self.model = SHELF_LLM_MODEL

    def summarize(self, text: str, prompt: str) -> LLMResult:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        }

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if resp.status_code == 429:
                    last_exc = exc
                    wait = INITIAL_BACKOFF * (2 ** attempt)
                    logger.info("Rate limited (429), retrying in %.1fs...", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 400:
                    try:
                        body = resp.json()
                        err = body.get("error", {})
                        code = str(err.get("code", ""))
                        message = str(err.get("message", ""))
                        if "context_length" in code or "context length" in message:
                            raise ContextWindowExceededError(
                                self.model, detail=message
                            ) from exc
                    except (ValueError, KeyError):
                        pass
                raise

            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            choice = data["choices"][0]
            metadata = {
                "provider": "openai_compat",
                "request": {"model": self.model, "temperature": 0},
                "response_id": data.get("id"),
                "response_model": data.get("model"),
                "created": data.get("created"),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage"),
            }
            return LLMResult(text=content, metadata=metadata)

        raise last_exc  # type: ignore[misc]
