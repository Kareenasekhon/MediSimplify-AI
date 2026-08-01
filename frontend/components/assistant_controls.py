"""Interactive controls used by the intelligent medical assistant."""
from __future__ import annotations

import streamlit as st

_MODE_LABELS = {
    "auto": "Smart Auto Routing",
    "report": "Report Only",
    "educational": "General Education",
    "hybrid": "Report + Education",
}


def render_assistant_controls() -> dict:
    st.markdown(
        "<div class='ms-assistant-section-label'>Assistant preferences</div>",
        unsafe_allow_html=True,
    )
    mode_col, style_col = st.columns([1.35, 1])
    assistant_mode = mode_col.selectbox(
        "Answer mode",
        list(_MODE_LABELS),
        format_func=_MODE_LABELS.__getitem__,
        key="assistant_answer_mode",
        help="Choose whether answers should use only the report, general education, or both.",
    )
    grandma_mode = style_col.toggle(
        "Grandma Mode",
        key="assistant_grandma_mode",
        help="Uses very simple, gentle, everyday language.",
    )

    voice_col1, voice_col2 = st.columns(2)
    voice_input = voice_col1.toggle(
        "Voice Input",
        value=True,
        key="assistant_voice_input",
        help="Record your question and transcribe it locally with Whisper.",
    )
    voice_reply = voice_col2.toggle(
        "Voice Reply",
        value=False,
        key="assistant_voice_reply",
        help="Read the assistant answer aloud in the selected language.",
    )
    return {
        "mode": assistant_mode,
        "grandma_mode": grandma_mode,
        "voice_input": voice_input,
        "voice_reply": voice_reply,
    }
