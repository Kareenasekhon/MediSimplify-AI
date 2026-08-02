from collections import OrderedDict
from functools import lru_cache
from threading import RLock

import numpy as np

from app.core.config import settings
from app.core.exceptions import ProviderError


class EmbeddingService:
    """Lazy sentence-transformer adapter with bounded query embedding caching."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None
        self._model_lock = RLock()
        self._query_cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._query_cache_lock = RLock()

    def _load_model(self):
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is not None:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ProviderError(
                    "Sentence Transformers is not installed. Run pip install -r requirements.txt."
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                raise ProviderError(f"Could not load embedding model '{self.model_name}'.") from exc
        return self._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype="float32")
        model = self._load_model()
        values = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=settings.embedding_batch_size,
        )
        return np.asarray(values, dtype="float32")

    def embed_query(self, text: str) -> np.ndarray:
        normalized = text.strip()
        cache_size = settings.embedding_query_cache_size
        if cache_size > 0:
            with self._query_cache_lock:
                cached = self._query_cache.get(normalized)
                if cached is not None:
                    self._query_cache.move_to_end(normalized)
                    return cached.copy()

        result = self.embed_documents([normalized])[0]
        if cache_size > 0:
            with self._query_cache_lock:
                self._query_cache[normalized] = result.copy()
                self._query_cache.move_to_end(normalized)
                while len(self._query_cache) > cache_size:
                    self._query_cache.popitem(last=False)
        return result

    def clear_query_cache(self) -> None:
        with self._query_cache_lock:
            self._query_cache.clear()


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
