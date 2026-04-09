"""Pure-Python slugification using only unicodedata and re."""

import re
import unicodedata


def slugify(text: str, max_length: int = 80) -> str:
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
    slug = text.strip("-")
    # Truncate to max_length, breaking at a hyphen boundary when possible
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]
    return slug
