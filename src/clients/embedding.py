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


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def cosine_similarity_batch(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.dot(a, b.T) / (np.linalg.norm(a, axis=1, keepdims=True) * np.linalg.norm(b, axis=1, keepdims=True))
