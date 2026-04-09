"""Centralized configuration — reads from environment with sensible defaults."""

import os

# LLM (OpenAI-compatible)
SHELF_LLM_API_KEY: str = os.environ.get("SHELF_LLM_API_KEY", "")
SHELF_LLM_BASE_URL: str = os.environ.get(
    "SHELF_LLM_BASE_URL", "https://openrouter.ai/api/v1"
)
SHELF_LLM_MODEL: str = os.environ.get("SHELF_LLM_MODEL", "google/gemma-4-31b-it:free")

# Ollama
SHELF_OLLAMA_URL: str = os.environ.get("SHELF_OLLAMA_URL", "http://localhost:11434")
SHELF_OLLAMA_MODEL: str = os.environ.get("SHELF_OLLAMA_MODEL", "llama3")

# Parallelism
SHELF_PARALLEL_WORKERS: int = int(os.environ.get("SHELF_PARALLEL_WORKERS", "1"))
