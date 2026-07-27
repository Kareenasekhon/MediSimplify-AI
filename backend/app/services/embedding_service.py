from functools import lru_cache

import numpy as np

from app.core.config import settings
from app.core.exceptions import ProviderError


class EmbeddingService:
    """Lazy Hugging Face sentence-transformer embedding adapter."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None

    def _load_model(self):
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
        values = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(values, dtype="float32")

    def embed_query(self, text: str) -> np.ndarray:
        result = self.embed_documents([text])
        return result[0]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
