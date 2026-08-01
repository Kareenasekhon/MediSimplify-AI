"""Clickable report-specific question suggestions."""
from __future__ import annotations

from typing import Iterable, Optional

import streamlit as st


def render_suggested_questions(questions: Iterable[str]) -> Optional[str]:
    clean = [str(q).strip() for q in questions if str(q).strip()]
    if not clean:
        return None
    st.markdown(
        "<div class='ms-assistant-section-label'>Suggested questions</div>",
        unsafe_allow_html=True,
    )
    selected = None
    columns = st.columns(2)
    for index, question in enumerate(clean):
        if columns[index % 2].button(
            f"✦  {question}",
            key=f"assistant_suggestion_{index}",
            use_container_width=True,
        ):
            selected = question
    return selected
