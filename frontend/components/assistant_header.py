"""Header for the report-scoped intelligent medical assistant."""
from __future__ import annotations

from html import escape

import streamlit as st

from components.assistant_badges import render_assistant_badges


def render_assistant_header(
    *,
    provider: str,
    language: str,
    report_type: str,
    ready: bool,
) -> None:
    status = "Knowledge base ready" if ready else "Setup required"
    status_class = "is-ready" if ready else "is-pending"
    st.markdown(
        f"""
        <section class="ms-assistant-header">
          <div class="ms-assistant-avatar">✦</div>
          <div class="ms-assistant-heading-copy">
            <div class="ms-assistant-kicker">REPORT-SCOPED AI SUPPORT</div>
            <h2>Intelligent Medical Assistant</h2>
            <p>Ask questions about the confirmed report in clear, patient-friendly language.</p>
          </div>
          <div class="ms-assistant-status {status_class}">● {escape(status)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    render_assistant_badges(
        [
            ("⚡", provider),
            ("🌐", language),
            ("📄", report_type.replace("_", " ").title()),
            ("🔒", "Report grounded"),
        ]
    )
