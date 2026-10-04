import logging
import os
import time
from collections import OrderedDict
from functools import lru_cache
from threading import RLock

import numpy as np

from app.core.config import settings
from app.core.exceptions import ProviderError


logger = logging.getLogger(__name__)


def _memory_usage_mb() -> float | None:
    """
    Return the process maximum resident set size in MB.

    On Linux, ru_maxrss is reported in KB.
    On macOS, it is reported in bytes.
    On Windows, it is reported in bytes.
    """
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        value = float(usage.ru_maxrss)

        if os.name == "posix":
            # Linux reports ru_maxrss in KB.
            return value / 1024.0

        # Windows reports bytes.
        return value / (1024.0 * 1024.0)

    except (ImportError, AttributeError, OSError, ValueError):
        return None


def _memory_label() -> str:
    memory_mb = _memory_usage_mb()

    if memory_mb is None:
        return "memory_mb=unavailable"

    return f"memory_mb={memory_mb:.1f}"


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
            logger.info(
                "EMBEDDING MODEL CACHE HIT | model=%s | %s",
                self.model_name,
                _memory_label(),
            )
            return self._model

        with self._model_lock:
            if self._model is not None:
                logger.info(
                    "EMBEDDING MODEL CACHE HIT AFTER LOCK | model=%s | %s",
                    self.model_name,
                    _memory_label(),
                )
                return self._model

            logger.info(
                "EMBEDDING MODEL LOAD START | model=%s | %s",
                self.model_name,
                _memory_label(),
            )

            load_start = time.perf_counter()

            try:
                logger.info(
                    "EMBEDDING IMPORT START | model=%s | %s",
                    self.model_name,
                    _memory_label(),
                )

                from sentence_transformers import SentenceTransformer

                logger.info(
                    "EMBEDDING IMPORT COMPLETE | model=%s | %s",
                    self.model_name,
                    _memory_label(),
                )

            except ImportError as exc:
                logger.exception(
                    "EMBEDDING IMPORT FAILED | model=%s | %s",
                    self.model_name,
                    _memory_label(),
                )

                raise ProviderError(
                    "Sentence Transformers is not installed. "
                    "Run pip install -r requirements.txt."
                ) from exc

            try:
                logger.info(
                    "EMBEDDING SENTENCE_TRANSFORMER INIT START | "
                    "model=%s | %s",
                    self.model_name,
                    _memory_label(),
                )

                self._model = SentenceTransformer(self.model_name)

                load_duration = time.perf_counter() - load_start

                logger.info(
                    "EMBEDDING MODEL LOAD COMPLETE | "
                    "model=%s | duration=%.2fs | %s",
                    self.model_name,
                    load_duration,
                    _memory_label(),
                )

            except Exception as exc:
                load_duration = time.perf_counter() - load_start

                logger.exception(
                    "EMBEDDING MODEL LOAD FAILED | "
                    "model=%s | duration=%.2fs | %s",
                    self.model_name,
                    load_duration,
                    _memory_label(),
                )

                raise ProviderError(
                    f"Could not load embedding model '{self.model_name}'."
                ) from exc

        return self._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype="float32")

        logger.info(
            "EMBED DOCUMENTS START | model=%s | texts=%d | batch_size=%d | %s",
            self.model_name,
            len(texts),
            settings.embedding_batch_size,
            _memory_label(),
        )

        model = self._load_model()

        logger.info(
            "EMBED DOCUMENTS MODEL READY | model=%s | texts=%d | %s",
            self.model_name,
            len(texts),
            _memory_label(),
        )

        encode_start = time.perf_counter()

        try:
            values = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=settings.embedding_batch_size,
            )

            encode_duration = time.perf_counter() - encode_start

            result = np.asarray(values, dtype="float32")

            logger.info(
                "EMBED DOCUMENTS COMPLETE | "
                "model=%s | texts=%d | shape=%s | dtype=%s | "
                "duration=%.2fs | %s",
                self.model_name,
                len(texts),
                result.shape,
                result.dtype,
                encode_duration,
                _memory_label(),
            )

            return result

        except Exception as exc:
            encode_duration = time.perf_counter() - encode_start

            logger.exception(
                "EMBED DOCUMENTS FAILED | "
                "model=%s | texts=%d | duration=%.2fs | %s",
                self.model_name,
                len(texts),
                encode_duration,
                _memory_label(),
            )

            raise ProviderError(
                f"Could not generate embeddings using '{self.model_name}'."
            ) from exc

    def embed_query(self, text: str) -> np.ndarray:
        normalized = text.strip()
        cache_size = settings.embedding_query_cache_size

        if cache_size > 0:
            with self._query_cache_lock:
                cached = self._query_cache.get(normalized)

                if cached is not None:
                    self._query_cache.move_to_end(normalized)

                    logger.info(
                        "EMBED QUERY CACHE HIT | %s",
                        _memory_label(),
                    )

                    return cached.copy()

        logger.info(
            "EMBED QUERY START | text_length=%d | %s",
            len(normalized),
            _memory_label(),
        )

        result = self.embed_documents([normalized])[0]

        if cache_size > 0:
            with self._query_cache_lock:
                self._query_cache[normalized] = result.copy()
                self._query_cache.move_to_end(normalized)

                while len(self._query_cache) > cache_size:
                    self._query_cache.popitem(last=False)

        logger.info(
            "EMBED QUERY COMPLETE | text_length=%d | %s",
            len(normalized),
            _memory_label(),
        )

        return result

    def clear_query_cache(self) -> None:
        with self._query_cache_lock:
            self._query_cache.clear()

        logger.info(
            "EMBED QUERY CACHE CLEARED | %s",
            _memory_label(),
        )


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    logger.info(
        "EMBEDDING SERVICE CREATED | model=%s | %s",
        settings.embedding_model,
        _memory_label(),
    )

    return EmbeddingService()