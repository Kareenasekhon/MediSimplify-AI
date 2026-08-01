from __future__ import annotations

import base64
from html import escape
from typing import Any, Dict, Optional

import streamlit as st

from services.api_client import APIClient


LANGUAGE_CODES = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
}

PROVIDER_CODES = {
    "Gemini": "gemini",
    "Groq": "groq",
    "Ollama (Local)": "ollama",
}


def _render_original_preview(original_file: Optional[Dict[str, Any]]) -> None:
    if not original_file:
        st.info(
            "The original preview is unavailable. The extracted text can still "
            "be reviewed and edited."
        )
        return

    content = original_file.get("content", b"")
    content_type = original_file.get("content_type", "")
    filename = original_file.get("name", "Medical report")

    if content_type.startswith("image/"):
        st.image(content, caption=filename, use_container_width=True)
        return

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        encoded = base64.b64encode(content).decode("ascii")
        st.markdown(
            f'<iframe class="ms-pdf-preview" '
            f'src="data:application/pdf;base64,{encoded}" '
            f'title="Original report"></iframe>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Some browsers may block inline PDF previews. The extracted text "
            "remains editable on the right."
        )
        return

    safe_name = escape(filename)
    st.markdown(
        f"""
        <div class="ms-document-placeholder">
            <div class="ms-document-icon">📄</div>
            <strong>{safe_name}</strong>
            <span>Preview is not available for this document type.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_extraction_review(
    extraction: Dict[str, Any],
    api_client: APIClient,
    selected_language: str,
    selected_provider: str,
    is_confirmed: bool = False,
    original_file: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Render a polished mandatory OCR review and return confirmation result."""
    st.markdown(
        """
        <div class="ms-review-heading">
            <div>
                <span class="ms-step-pill">STEP 2 · OCR REVIEW</span>
                <h2>Review extracted report</h2>
                <p>
                    Compare the original document with the extracted text.
                    Correct values, units, ranges and medicine names before approval.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    warnings = extraction.get("quality_warnings", [])
    unreadable = extraction.get("unreadable_text", [])
    if warnings or unreadable:
        with st.expander("Extraction quality checks", expanded=True):
            for warning in warnings:
                st.warning(warning)
            if unreadable:
                st.error("Unreadable or uncertain content was detected:")
                for item in unreadable:
                    st.write(f"• {item}")

    structured_data = extraction.get("structured_data", {})
    document_type = structured_data.get("document_type_hint", "unknown")
    meta1, meta2, meta3 = st.columns(3)
    meta1.metric(
        "Input",
        str(extraction.get("input_type", "unknown")).replace("_", " ").title(),
    )
    meta2.metric(
        "Document hint",
        str(document_type).replace("_", " ").title(),
    )
    meta3.metric("Review status", "Approved" if is_confirmed else "Needs review")

    text_key = f"confirmed_text_{extraction['report_id']}"
    if text_key not in st.session_state:
        st.session_state[text_key] = extraction.get("extracted_text", "")

    preview_col, text_col = st.columns([1, 1.15], gap="large")
    with preview_col:
        st.markdown(
            '<div class="ms-review-column-title">Original report</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            _render_original_preview(original_file)

    with text_col:
        st.markdown(
            '<div class="ms-review-column-title">Extracted text</div>',
            unsafe_allow_html=True,
        )
        confirmed_text = st.text_area(
            "Extracted text",
            key=text_key,
            height=430,
            help="Correct OCR mistakes here before approving the report.",
            disabled=is_confirmed,
            label_visibility="collapsed",
        )
        word_count = len(confirmed_text.split())
        st.caption(
            f"{word_count:,} words · Review decimal points, units, dates and "
            "medicine spellings carefully."
        )

    with st.expander("Structured extraction data", expanded=False):
        st.json(structured_data)

    if is_confirmed:
        st.success(
            "This extraction has been reviewed and approved. You can continue "
            "to report routing and analysis."
        )
        return None

    action_left, action_mid, action_right = st.columns([1, 1, 1.35])
    if action_left.button("↻ Start Over", use_container_width=True):
        for key in (
            "extraction_result",
            "extraction_confirmed",
            "confirmation_result",
            "routing_result",
            "analysis_result",
            "knowledge_base_status",
            "current_report_file",
            "uploaded_report",
            "camera_report",
        ):
            st.session_state.pop(key, None)
        st.session_state.extraction_result = None
        st.session_state.extraction_confirmed = False
        st.rerun()

    action_mid.download_button(
        "Download OCR Text",
        data=confirmed_text,
        file_name=f"{extraction.get('report_id', 'report')}_ocr.txt",
        mime="text/plain",
        use_container_width=True,
    )

    confirm_disabled = not bool(confirmed_text.strip())
    if action_right.button(
        "Approve & Continue →",
        type="primary",
        use_container_width=True,
        disabled=confirm_disabled,
    ):
        with st.status("Saving your reviewed report...", expanded=True) as status:
            try:
                st.write("✓ Validating the corrected text")
                st.write("✓ Saving the confirmed extraction")
                result = api_client.confirm_extraction(
                    report_id=extraction["report_id"],
                    confirmed_text=confirmed_text,
                    corrected_structured_data=structured_data,
                    language=LANGUAGE_CODES.get(selected_language, "en"),
                    provider=PROVIDER_CODES.get(selected_provider, "gemini"),
                )
                status.update(label="OCR review approved", state="complete")
                return result
            except RuntimeError as exc:
                status.update(label="Approval could not be saved", state="error")
                st.error(str(exc))

    if confirm_disabled:
        st.caption("Add or restore extracted text to enable approval.")

    return None
