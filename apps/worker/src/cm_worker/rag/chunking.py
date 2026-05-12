def chunk_text(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    """Split documentation text into overlapping chunks for embedding."""
    clean = " ".join((text or "").split())
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks

