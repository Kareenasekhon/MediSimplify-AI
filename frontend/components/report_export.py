"""Streamlit UI for exporting a professional MediSimplify AI PDF report."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import streamlit as st

from utils.pdf_generator import generate_medical_report_pdf


def _safe_filename_part(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    return "_".join(part for part in cleaned.split("_") if part) or "medical_report"


def render_report_export(
    *,
    analysis: Mapping[str, Any],
    report_type: str = "medical_report",
    language: str = "English",
) -> None:
    """Render the PDF export card and an immediate Streamlit download button."""
    generated_at = datetime.now()
    pretty_type = report_type.replace("_", " ").title() if report_type else "Medical Report"

    st.markdown(
        f"""
        <section class="ms-export-card">
            <div class="ms-export-icon">PDF</div>
            <div class="ms-export-copy">
                <div class="ms-export-kicker">Professional report export</div>
                <h3>Download your AI medical explanation</h3>
                <p>Create a polished PDF with the summary, key findings, notes, doctor questions and safety disclaimer.</p>
                <div class="ms-export-meta">
                    <span><b>Report:</b> {pretty_type}</span>
                    <span><b>Language:</b> {language}</span>
                    <span><b>Generated:</b> {generated_at.strftime('%d %b %Y')}</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    try:
        pdf_bytes = generate_medical_report_pdf(
            analysis=analysis,
            report_type=report_type,
            language=language,
            generated_at=generated_at,
        )
    except Exception as exc:  # Keep the analysis page usable if PDF creation fails.
        st.error(f"The PDF could not be generated: {exc}")
        return

    file_name = (
        f"medisimplify_{_safe_filename_part(report_type)}_"
        f"{generated_at.strftime('%Y%m%d_%H%M')}.pdf"
    )
    st.download_button(
        "Download PDF Report",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        use_container_width=True,
        type="primary",
        key="phase_9_5_download_pdf",
    )
    st.caption("Educational AI explanation only. Keep the original medical report for clinical reference.")
