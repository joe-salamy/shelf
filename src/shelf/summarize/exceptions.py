"""Custom exceptions for the summarization pipeline."""


class ContextWindowExceededError(Exception):
    """Raised when an LLM call exceeds the model's context window."""

    def __init__(self, model: str, detail: str = ""):
        self.model = model
        self.detail = detail
        super().__init__(
            f"Context window exceeded for model '{model}'. {detail}"
        )
