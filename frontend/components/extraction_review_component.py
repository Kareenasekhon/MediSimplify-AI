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


def render_extraction_review(
    extraction: Dict[str, Any],
    api_client: APIClient,
    selected_language: str,
    selected_provider: str,
    is_confirmed: bool = False,
) -> Optional[Dict[str, Any]]:
    """Render mandatory extraction review and return confirmation result."""
    st.subheader("Review Extracted Report")
    st.caption(
        "Check medical values, decimal points, units, reference ranges, and "
        "medicine names before confirming."
    )

    for warning in extraction.get("quality_warnings", []):
        st.warning(warning)

    unreadable = extraction.get("unreadable_text", [])
    if unreadable:
        st.error("Unreadable or uncertain content was detected:")
        for item in unreadable:
            st.write(f"• {item}")

    structured_data = extraction.get("structured_data", {})
    document_type = structured_data.get("document_type_hint", "unknown")
    st.info(
        f"Input type: **{extraction.get('input_type', 'unknown')}**  |  "
        f"Document hint: **{document_type}**"
    )

    text_key = f"confirmed_text_{extraction['report_id']}"
    if text_key not in st.session_state:
        st.session_state[text_key] = extraction.get("extracted_text", "")

    confirmed_text = st.text_area(
        "Extracted text",
        key=text_key,
        height=320,
        help="Correct extraction errors here before confirming.",
        disabled=is_confirmed,
    )

    with st.expander("View structured extraction", expanded=False):
        st.json(structured_data)

    if is_confirmed:
        st.info("This extraction has already been confirmed.")
        return None

    confirm_disabled = not bool(confirmed_text.strip())
    if st.button(
        "Confirm Extracted Report",
        type="primary",
        use_container_width=True,
        disabled=confirm_disabled,
    ):
        with st.spinner("Confirming your reviewed extraction..."):
            try:
                result = api_client.confirm_extraction(
                    report_id=extraction["report_id"],
                    confirmed_text=confirmed_text,
                    corrected_structured_data=structured_data,
                    language=LANGUAGE_CODES.get(selected_language, "en"),
                    provider=PROVIDER_CODES.get(selected_provider, "gemini"),
                )
                return result
            except RuntimeError as exc:
                st.error(str(exc))

    if confirm_disabled:
        st.caption("Add or restore extracted text to enable confirmation.")

    return None
