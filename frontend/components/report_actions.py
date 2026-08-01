"""Report actions for the Phase 9.3 analysis dashboard."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping

import streamlit as st


def _download_payload(analysis: Mapping[str, Any], report_type: str) -> bytes:
    payload = {
        "report_type": report_type,
        "summary": analysis.get("summary"),
        "items": analysis.get("items", []),
        "important_notes": analysis.get("important_notes", []),
        "unclear_information": analysis.get("unclear_information", []),
        "questions_for_doctor": analysis.get("questions_for_doctor", []),
        "disclaimer": analysis.get("disclaimer"),
        "agent_used": analysis.get("agent_used"),
        "provider_used": analysis.get("provider_used"),
        "model": analysis.get("model"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def render_report_actions(
    *,
    analysis: Mapping[str, Any],
    report_type: str,
    on_upload_another: Callable[[], None],
) -> None:
    """Render analysis download, assistant continuation and reset actions."""
    st.markdown(
        """
        <section class="ms-report-actions-header">
            <div>
                <div class="ms-report-actions-kicker">Next steps</div>
                <h3>Continue with your report</h3>
                <p>Download this educational explanation, continue to report chat, or start with another report.</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    download_col, assistant_col, reset_col = st.columns(3)
    with download_col:
        st.download_button(
            "Download explanation",
            data=_download_payload(analysis, report_type),
            file_name=f"medisimplify_{report_type}_explanation.json",
            mime="application/json",
            use_container_width=True,
        )
    with assistant_col:
        st.markdown(
            '<a class="ms-action-link" href="#report-assistant">Ask about this report</a>',
            unsafe_allow_html=True,
        )
    with reset_col:
        st.button(
            "Upload another report",
            use_container_width=True,
            on_click=on_upload_another,
            key="phase_9_3_upload_another",
        )
