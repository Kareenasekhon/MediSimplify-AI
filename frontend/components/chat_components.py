"""Conversation renderer for the intelligent medical assistant."""
from __future__ import annotations

from typing import Any, Iterable, Mapping

import streamlit as st


def render_chat_messages(messages: Iterable[Mapping[str, Any]]) -> None:
    messages = list(messages)
    if not messages:
        st.markdown(
            """
            <div class="ms-chat-empty">
              <div class="ms-chat-empty-icon">💬</div>
              <strong>Your conversation will appear here</strong>
              <p>Choose a suggested question or type your own question below.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for message in messages:
        role = message.get("role", "assistant")
        avatar = "🧑" if role == "user" else "🩺"
        with st.chat_message(role, avatar=avatar):
            st.write(message.get("content", ""))
            mode = message.get("mode_used")
            if mode:
                style = message.get("explanation_style", "standard")
                st.caption(
                    f"Mode: {str(mode).replace('_', ' ').title()} · "
                    f"Style: {str(style).title()}"
                )
            if message.get("audio"):
                st.audio(message["audio"], format="audio/mp3")
            sources = message.get("sources") or []
            if sources:
                with st.expander("Report sections used"):
                    for source in sources:
                        st.caption(source.get("chunk_id", "Report section"))
                        st.write(source.get("excerpt", ""))
