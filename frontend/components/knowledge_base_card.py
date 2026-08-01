"""Knowledge-base status card and actions."""
from __future__ import annotations

from html import escape
from typing import Any, Mapping

import streamlit as st


def render_knowledge_base_card(status: Mapping[str, Any] | None) -> None:
    status = status or {}
    ready = bool(status.get("ready"))
    state_text = "Ready" if ready else "Not built"
    state_class = "ready" if ready else "pending"
    chunks = status.get("chunk_count", 0)
    store = status.get("vector_store", "FAISS")
    model = status.get("embedding_model", "Not available yet")
    st.markdown(
        f"""
        <section class="ms-kb-card {state_class}">
          <div class="ms-kb-icon">🧠</div>
          <div class="ms-kb-copy">
            <div class="ms-kb-topline"><strong>Report Knowledge Base</strong><span>{escape(state_text)}</span></div>
            <p>The assistant retrieves relevant sections from this report before answering.</p>
            <div class="ms-kb-meta">
              <span>Chunks <b>{escape(str(chunks))}</b></span>
              <span>Retriever <b>{escape(str(store))}</b></span>
              <span>Embedding <b>{escape(str(model))}</b></span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
