"""Pure-Python slugification using only unicodedata and re."""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to a lowercase, hyphen-separated filename-safe slug."""
    # Normalize unicode to ASCII equivalents where possible
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    text = text.lower()
    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")
