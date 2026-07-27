import numpy as np
import pytest

from app.models.chat_models import ChatRequest
from app.models.llm_models import LLMGenerationResult, ProviderName
from app.services import rag_service, session_service
from app.services.chat_memory_service import chat_memory_service
from app.services.chunking_service import chunk_report_text
from app.services.vector_store_service import VectorStoreService, vector_store_service


class FakeEmbeddings:
    model_name = "fake-medical-embeddings"

    @staticmethod
    def _vector(text: str) -> np.ndarray:
        lowered = text.lower()
        values = np.array(
            [
                lowered.count("hemoglobin") + lowered.count("hb"),
                lowered.count("platelet"),
                lowered.count("glucose"),
                max(len(lowered), 1) / 1000,
            ],
            dtype="float32",
        )
        norm = np.linalg.norm(values)
        return values / norm if norm else values

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._vector(text) for text in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._vector(text)


def test_chunk_report_text_preserves_order_and_ids():
    text = "Hemoglobin: 10.2 g/dL.\n\nPlatelets: 250000 /uL.\n\nGlucose: 92 mg/dL."
    chunks = chunk_report_text("report-1", text, chunk_size=45, overlap=8)

    assert len(chunks) >= 2
    assert chunks[0].chunk_id == "report-1_chunk_1"
    assert [item.order for item in chunks] == list(range(len(chunks)))
    assert "Hemoglobin" in chunks[0].text


def test_vector_store_returns_most_similar_chunk():
    service = VectorStoreService()
    embeddings = FakeEmbeddings()
    chunks = chunk_report_text(
        "report-2",
        "Hemoglobin: 10.2 g/dL.\n\nPlatelets: 250000 /uL.",
        chunk_size=30,
        overlap=5,
    )
    service.build("report-2", chunks, embeddings.embed_documents([item.text for item in chunks]))

    results = service.search("report-2", embeddings.embed_query("What is my hemoglobin?"), 1)

    assert len(results) == 1
    assert "Hemoglobin" in results[0].text


@pytest.mark.asyncio
async def test_rag_answer_uses_report_context_and_memory(monkeypatch):
    report_id = "rag-chat-report"
    session_service.create_session(
        report_id,
        {
            "report_id": report_id,
            "confirmed": True,
            "raw_text": "Hemoglobin: 10.2 g/dL. Reference range: 12-15 g/dL.",
        },
    )
    vector_store_service.delete(report_id)
    chat_memory_service.clear(report_id)
    fake_embeddings = FakeEmbeddings()
    monkeypatch.setattr(rag_service, "get_embedding_service", lambda: fake_embeddings)

    from app.services import retriever_service

    monkeypatch.setattr(retriever_service, "get_embedding_service", lambda: fake_embeddings)

    async def fake_generate(request):
        prompt = request.messages[-1].content
        assert "Hemoglobin: 10.2 g/dL" in prompt
        return LLMGenerationResult(
            provider=ProviderName.GEMINI,
            model="fake-gemini",
            content="Your report lists hemoglobin as 10.2 g/dL. Please discuss it with your doctor.",
        )

    monkeypatch.setattr(rag_service.llm_service, "generate", fake_generate)

    response = await rag_service.answer_question(
        ChatRequest(report_id=report_id, question="What is my hemoglobin?")
    )

    assert "10.2 g/dL" in response.answer
    assert response.sources
    assert len(chat_memory_service.get(report_id)) == 2
