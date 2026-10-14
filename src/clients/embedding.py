import numpy as np
import requests

from src.config import settings


def get_embedding(text: str) -> np.ndarray:
    response = requests.post(
        f"{settings.ollama_base_url}/api/embeddings", json={"prompt": text, "model": settings.embedding_model}
    )
    response.raise_for_status()
    return np.array(response.json()["embedding"])


def get_embeddings_batch(texts: list[str]) -> list[np.ndarray]:
    response = requests.post(
        f"{settings.ollama_base_url}/api/embeddings", json={"prompt": texts, "model": settings.embedding_model}
    )
    response.raise_for_status()
    return [np.array(embedding) for embedding in response.json()["embeddings"]]


def to_vector(a: np.ndarray) -> list[float]:
    """Convert an embedding to the list[float] form the pgvector columns declare.

    The ORM models (`ReferenceLibrary.embedding`, `ClassificationLog.embedding`) declare
    `Mapped[list[float]]`, but pgvector's `VECTOR.bind_processor` accepts `Any` on write, so
    an `np.ndarray` passed straight to the constructor is silently accepted at runtime and
    invisible to mypy (SQLAlchemy declarative `__init__` is `**kw: Any`). This helper makes
    the conversion explicit at the write boundary so callers hand the ORM a real,
    type-checked `list[float]` rather than relying on pgvector's untyped leniency.

    Uses an element-wise comprehension rather than `ndarray.tolist()`: numpy's stubs type
    `tolist()` as returning `Any`, which would defeat the point of having a checkable
    boundary here.
    """
    return [float(x) for x in a]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def cosine_similarity_batch(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.dot(a, b.T) / (np.linalg.norm(a, axis=1, keepdims=True) * np.linalg.norm(b, axis=1, keepdims=True))
