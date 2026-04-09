"""OpenAI-compatible API backend using environment variables."""

import os


class OpenAICompatBackend:
    def __init__(self):
        self.api_key = os.environ["SHELF_LLM_API_KEY"]
        self.base_url = os.environ.get(
            "SHELF_LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.model = os.environ.get("SHELF_LLM_MODEL", "gpt-4o-mini")

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
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
