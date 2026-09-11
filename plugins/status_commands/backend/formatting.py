"""Shared text formatting for diagnostic replies."""

def content_to_text(content: object) -> str:
    """Extract readable text from plain or multimodal conversation content."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")).strip())
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip()


def preview_text(text: str, limit: int = 80) -> str:
    """Collapse whitespace and bound a one-line diagnostic preview."""
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


