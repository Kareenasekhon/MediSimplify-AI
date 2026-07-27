from dataclasses import dataclass
from threading import RLock
from typing import Protocol

import numpy as np

from app.core.exceptions import ProviderError
from app.models.rag_models import ReportChunk, RetrievedChunk


class VectorIndex(Protocol):
    def search(self, query: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]: ...


@dataclass
class StoredKnowledgeBase:
    chunks: list[ReportChunk]
    index: VectorIndex
    dimension: int
    backend: str


class _NumpyIndex:
    def __init__(self, vectors: np.ndarray) -> None:
        self.vectors = vectors

    def search(self, query: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        scores = self.vectors @ query.reshape(-1)
        order = np.argsort(scores)[::-1][:top_k]
        return scores[order].reshape(1, -1), order.reshape(1, -1)


class VectorStoreService:
    """Report-scoped in-memory vector store using FAISS with a safe NumPy fallback."""

    def __init__(self) -> None:
        self._stores: dict[str, StoredKnowledgeBase] = {}
        self._lock = RLock()

    @staticmethod
    def _build_index(vectors: np.ndarray) -> tuple[VectorIndex, str]:
        if vectors.ndim != 2 or not len(vectors):
            raise ProviderError("Cannot build a vector index without embeddings.")
        try:
            import faiss

            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(np.ascontiguousarray(vectors, dtype="float32"))
            return index, "FAISS IndexFlatIP"
        except ImportError:
            return _NumpyIndex(vectors), "NumPy cosine fallback"

    def build(self, report_id: str, chunks: list[ReportChunk], vectors: np.ndarray) -> StoredKnowledgeBase:
        if len(chunks) != len(vectors):
            raise ProviderError("Chunk and embedding counts do not match.")
        index, backend = self._build_index(vectors)
        store = StoredKnowledgeBase(
            chunks=chunks,
            index=index,
            dimension=int(vectors.shape[1]),
            backend=backend,
        )
        with self._lock:
            self._stores[report_id] = store
        return store

    def search(self, report_id: str, query_vector: np.ndarray, top_k: int) -> list[RetrievedChunk]:
        with self._lock:
            store = self._stores.get(report_id)
        if store is None:
            return []
        scores, indexes = store.index.search(
            np.ascontiguousarray(query_vector.reshape(1, -1), dtype="float32"),
            min(top_k, len(store.chunks)),
        )
        results: list[RetrievedChunk] = []
        for score, index in zip(scores[0], indexes[0]):
            if int(index) < 0:
                continue
            chunk = store.chunks[int(index)]
            results.append(RetrievedChunk(**chunk.model_dump(), score=float(score)))
        return results

    def get(self, report_id: str) -> StoredKnowledgeBase | None:
        with self._lock:
            return self._stores.get(report_id)

    def delete(self, report_id: str) -> bool:
        with self._lock:
            return self._stores.pop(report_id, None) is not None


vector_store_service = VectorStoreService()
