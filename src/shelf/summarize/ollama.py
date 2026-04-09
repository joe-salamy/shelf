"""Ollama local LLM backend."""

import os


class OllamaBackend:
    def __init__(self):
        self.base_url = os.environ.get("SHELF_OLLAMA_URL", "http://localhost:11434")
        self.model = os.environ.get("SHELF_OLLAMA_MODEL", "llama3")

    def is_available(self) -> bool:
        """Check if Ollama is running locally."""
        import httpx

        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def summarize(self, text: str, prompt: str) -> str:
        import httpx

        payload = {
            "model": self.model,
            "prompt": f"{prompt}\n\n{text}",
            "stream": False,
        }
        resp = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
