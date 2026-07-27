import numpy as np

from app.models.llm_models import LLMGenerationResult, ProviderName
from app.services import rag_service, session_service
from app.services.chat_memory_service import chat_memory_service
from app.services.vector_store_service import vector_store_service


class FakeEmbeddings:
    model_name = "fake"

    def embed_documents(self, texts):
        values = []
        for index, _ in enumerate(texts):
            vector = np.zeros(4, dtype="float32")
            vector[index % 4] = 1.0
            values.append(vector)
        return np.vstack(values)

    def embed_query(self, text):
        return np.array([1.0, 0.0, 0.0, 0.0], dtype="float32")


def test_chat_lifecycle_api(client, monkeypatch):
    report_id = "api-rag-report"
    session_service.create_session(
        report_id,
        {
            "report_id": report_id,
            "confirmed": True,
            "raw_text": "Vitamin D: 18 ng/mL. Laboratory reference range: 30-100 ng/mL.",
        },
    )
    vector_store_service.delete(report_id)
    chat_memory_service.clear(report_id)
    fake_embeddings = FakeEmbeddings()
    monkeypatch.setattr(rag_service, "get_embedding_service", lambda: fake_embeddings)

    from app.services import retriever_service

    monkeypatch.setattr(retriever_service, "get_embedding_service", lambda: fake_embeddings)

    async def fake_generate(request):
        return LLMGenerationResult(
            provider=ProviderName.GEMINI,
            model="fake-model",
            content="The report lists Vitamin D as 18 ng/mL.",
        )

    monkeypatch.setattr(rag_service.llm_service, "generate", fake_generate)

    status_response = client.get(f"/api/v1/chat/{report_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["ready"] is False

    build_response = client.post(f"/api/v1/chat/{report_id}/knowledge-base")
    assert build_response.status_code == 200
    assert build_response.json()["ready"] is True

    chat_response = client.post(
        "/api/v1/chat",
        json={
            "report_id": report_id,
            "question": "What is my Vitamin D value?",
            "language": "english",
            "preferred_provider": "gemini",
        },
    )
    assert chat_response.status_code == 200
    assert "18 ng/mL" in chat_response.json()["answer"]
    assert chat_response.json()["sources"]

    clear_response = client.delete(f"/api/v1/chat/{report_id}/conversation")
    assert clear_response.status_code == 200
    assert clear_response.json()["cleared"] is True
