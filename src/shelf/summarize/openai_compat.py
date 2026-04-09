"""OpenAI-compatible API backend using centralized config."""

from shelf.config import SHELF_LLM_API_KEY, SHELF_LLM_BASE_URL, SHELF_LLM_MODEL
from shelf.summarize.exceptions import ContextWindowExceededError


class OpenAICompatBackend:
    def __init__(self):
        self.api_key = SHELF_LLM_API_KEY
        self.base_url = SHELF_LLM_BASE_URL
        self.model = SHELF_LLM_MODEL

    def summarize(self, text: str, prompt: str) -> str:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
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
        return resp.json()["choices"][0]["message"]["content"].strip()
