from typing import Any

from pydantic import BaseModel, Field


class ReportChunk(BaseModel):
    chunk_id: str
    report_id: str
    text: str = Field(min_length=1, max_length=12_000)
    order: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(ReportChunk):
    score: float = Field(ge=-1.0, le=1.0)


class KnowledgeBaseStatus(BaseModel):
    report_id: str
    ready: bool
    chunk_count: int = Field(ge=0)
    embedding_model: str
    vector_store: str
    message: str
