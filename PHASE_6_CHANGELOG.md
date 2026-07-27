# Phase 6 — Conversational RAG

## Added

- Report chunking with configurable overlap
- Lazy Hugging Face sentence-transformer embedding service
- FAISS inner-product vector index with NumPy fallback
- Report-scoped knowledge-base lifecycle
- Top-k retriever with duplicate removal and source chunk IDs
- Report-scoped short-term conversation memory
- Multilingual grounded report Q&A through the existing provider layer
- Chat, status, build/rebuild, clear-history, and delete-index APIs
- Streamlit chat UI with source excerpts and knowledge-base controls
- Phase 5 and Phase 6 README documentation
- RAG service, vector store, and API tests

## Verified

```text
36 passed
```

## Git branch suggestion

```bash
git checkout -b phase-6-rag-chat
git add .
git commit -m "Complete Phase 6: Conversational RAG and report Q&A"
git push -u origin phase-6-rag-chat
```
