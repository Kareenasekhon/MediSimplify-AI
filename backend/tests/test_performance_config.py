import numpy as np

from app.core.config import Settings
from app.models.rag_models import ReportChunk
from app.providers.provider_factory import ProviderFactory
from app.services.chat_memory_service import ChatMemoryService
from app.services.vector_store_service import VectorStoreService


def test_performance_defaults_are_bounded():
    configured = Settings(_env_file=None)
    assert configured.embedding_batch_size >= 1
    assert configured.embedding_query_cache_size >= 0
    assert configured.max_in_memory_vector_stores >= 1
    assert configured.chat_history_max_messages >= 2
    assert configured.http_max_keepalive_connections <= configured.http_max_connections


def test_provider_factory_reuses_instances(monkeypatch):
    monkeypatch.setattr("app.providers.provider_factory.settings.provider_instance_cache_enabled", True)
    ProviderFactory.clear_cache()
    first = ProviderFactory.create("gemini")
    second = ProviderFactory.create("gemini")
    assert first is second


def test_chat_memory_keeps_bounded_recent_messages():
    memory = ChatMemoryService(max_messages=4)
    for index in range(4):
        memory.add_turn("report", f"q{index}", f"a{index}")
    history = memory.get("report")
    assert len(history) == 4
    assert history[0].content == "q2"
    assert history[-1].content == "a3"


def test_vector_store_evicts_least_recently_used_store():
    service = VectorStoreService(max_stores=2)
    vectors = np.asarray([[1.0, 0.0]], dtype="float32")
    for report_id in ("one", "two"):
        service.build(report_id, [ReportChunk(report_id=report_id, chunk_id="c", order=0, text="x")], vectors)
    assert service.get("one") is not None  # one becomes most recently used
    service.build("three", [ReportChunk(report_id="three", chunk_id="c", order=0, text="x")], vectors)
    assert service.get("one") is not None
    assert service.get("two") is None
    assert service.get("three") is not None
