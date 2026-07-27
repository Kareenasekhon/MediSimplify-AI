from app.models.rag_models import RetrievedChunk
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.vector_store_service import VectorStoreService, vector_store_service


class RetrieverService:
    def __init__(
        self,
        embeddings: EmbeddingService | None = None,
        vector_store: VectorStoreService | None = None,
    ) -> None:
        self.embeddings = embeddings or get_embedding_service()
        self.vector_store = vector_store or vector_store_service

    def retrieve(self, report_id: str, question: str, top_k: int = 4) -> list[RetrievedChunk]:
        query_vector = self.embeddings.embed_query(question)
        candidates = self.vector_store.search(report_id, query_vector, top_k)
        unique: list[RetrievedChunk] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = " ".join(item.text.lower().split())
            if normalized not in seen:
                seen.add(normalized)
                unique.append(item)
        return sorted(unique, key=lambda item: item.order)
