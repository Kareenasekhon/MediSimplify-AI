"""Doctor-question cards for Phase 9.3 report analysis."""

from __future__ import annotations

from html import escape
from typing import Any, Sequence

import streamlit as st


def _safe(value: Any) -> str:
    return escape(str(value or "").strip())


def render_doctor_questions(
    questions: Sequence[Any] | None,
    *,
    title: str = "Questions for your doctor",
) -> None:
    """Render suggested follow-up questions in numbered, copy-friendly cards."""
    safe_questions = [str(question).strip() for question in (questions or []) if str(question).strip()]
    if not safe_questions:
        return

    st.markdown(
        f"""
        <section class="ms-doctor-header">
            <div class="ms-doctor-icon">👩‍⚕️</div>
            <div>
                <div class="ms-doctor-kicker">Prepare for your appointment</div>
                <h3>{_safe(title)}</h3>
                <p>Save these questions and discuss them with a qualified healthcare professional.</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    for index, question in enumerate(safe_questions, start=1):
        st.markdown(
            f"""
            <article class="ms-doctor-question">
                <span class="ms-doctor-number">{index}</span>
                <p>{_safe(question)}</p>
            </article>
            """,
            unsafe_allow_html=True,
        )
