import hashlib

import numpy as np

from cm_shared.settings.app import get_settings

VECTOR_SIZE = 1536


def fit_vector(values: list[float]) -> list[float]:
    """Pad or truncate embeddings so they fit the pgvector column size."""
    if len(values) >= VECTOR_SIZE:
        return values[:VECTOR_SIZE]
    return [*values, *([0.0] * (VECTOR_SIZE - len(values)))]


def deterministic_embedding(text: str) -> list[float]:
    """Create a stable local embedding fallback for development and tests."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    numbers = [((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(VECTOR_SIZE)]
    vector = np.array(numbers, dtype=np.float32)
    norm = float(np.linalg.norm(vector)) or 1.0
    return (vector / norm).tolist()


def embed_text(text: str) -> list[float]:
    """Generate an embedding with the configured provider or fallback locally."""
    settings = get_settings()
    openai_api_key = settings.effective_openai_api_key
    if settings.llm_provider == "openai" and openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        model = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=openai_api_key,
            base_url=settings.openai_base_url,
        )
        return fit_vector(model.embed_query(text))
    if settings.llm_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        model = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )
        return fit_vector(model.embed_query(text))
    return deterministic_embedding(text)
