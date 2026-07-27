import streamlit as st

from components.extraction_review_component import render_extraction_review
from services.api_client import APIClient
from utils import ui_helpers

st.set_page_config(
    page_title="MediSimplify AI - Simple Medical Report Explanations",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui_helpers.apply_custom_theme()

SESSION_DEFAULTS = {
    "extraction_result": None,
    "extraction_confirmed": False,
    "confirmation_result": None,
    "consent_accepted": False,
    "report_source": "Upload File",
    "captured_camera_report": None,
    "last_extraction_message": None,
}

for key, default in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


def reset_report_state() -> None:
    """Clear the current report while preserving consent and app preferences."""
    report_id = None
    if isinstance(st.session_state.get("extraction_result"), dict):
        report_id = st.session_state.extraction_result.get("report_id")

    for key in (
        "extraction_result",
        "extraction_confirmed",
        "confirmation_result",
        "captured_camera_report",
        "last_extraction_message",
        "uploaded_report",
        "camera_report",
    ):
        st.session_state.pop(key, None)

    if report_id:
        st.session_state.pop(f"confirmed_text_{report_id}", None)

    st.session_state.extraction_result = None
    st.session_state.extraction_confirmed = False
    st.session_state.confirmation_result = None
    st.session_state.captured_camera_report = None
    st.session_state.last_extraction_message = None
    st.session_state.report_source = "Upload File"


def reset_camera_capture() -> None:
    """Discard a captured photo and reopen the camera input."""
    st.session_state.captured_camera_report = None
    st.session_state.pop("camera_report", None)


st.markdown("<div class='main-header'>MediSimplify AI</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='tagline'>Understand your medical report in your language.</div>",
    unsafe_allow_html=True,
)

api_client = APIClient()
health_status = api_client.check_health()

with st.sidebar:
    st.markdown("## MediSimplify AI")
    st.markdown("### Settings")
    language = st.selectbox(
        "Language",
        ["English", "हिंदी (Hindi)", "ਪੰਜਾਬੀ (Punjabi)"],
    )
    provider = st.selectbox(
        "LLM Provider",
        ["Gemini", "Groq", "Ollama (Local)"],
        index=0,
        help="Phase 2 multimodal extraction currently requires Gemini.",
    )
    st.markdown("---")
    st.write("Current phase: **Phase 2 — Report Upload & OCR**")
    if st.button("Clear Session", use_container_width=True):
        st.session_state.clear()
        st.rerun()

status_col, content_col = st.columns([1, 2])

with status_col:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("System Status")
    if health_status.get("status") == "healthy":
        st.markdown(
            "API Server: <span class='status-badge status-online'>ONLINE</span>",
            unsafe_allow_html=True,
        )
        st.write(f"**Version:** {health_status.get('version', 'unknown')}")
    else:
        st.markdown(
            "API Server: <span class='status-badge status-offline'>OFFLINE</span>",
            unsafe_allow_html=True,
        )
        st.error(health_status.get("error", "Backend unavailable"))
        st.code("uvicorn app.main:app --reload --port 8000")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Supported Files")
    st.write("PDF, DOCX, TXT, JPG, JPEG, PNG, WEBP")
    st.caption("Maximum upload size: 5 MB")
    st.markdown("</div>", unsafe_allow_html=True)

with content_col:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Consent & Safety")
    st.warning(
        "This tool explains written medical reports for educational purposes. "
        "It does not diagnose illness, prescribe treatment, or replace a doctor."
    )
    st.info(
        "Files are processed temporarily. Image and scanned-PDF extraction may "
        "send report content to the configured Gemini provider."
    )
    st.session_state.consent_accepted = st.checkbox(
        "I understand and accept the safety and privacy guidelines.",
        value=st.session_state.consent_accepted,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    ready = (
        st.session_state.consent_accepted
        and health_status.get("status") == "healthy"
    )

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Add Medical Report")

    st.radio(
        "Choose report source",
        ["Upload File", "Take Photo"],
        horizontal=True,
        key="report_source",
        disabled=not ready or st.session_state.extraction_result is not None,
    )

    selected_report = None

    if st.session_state.report_source == "Upload File":
        uploaded_file = st.file_uploader(
            "Upload Medical Report",
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"],
            disabled=not ready or st.session_state.extraction_result is not None,
            key="uploaded_report",
        )
        if uploaded_file is not None:
            selected_report = {
                "name": uploaded_file.name,
                "content": uploaded_file.getvalue(),
                "content_type": uploaded_file.type or "application/octet-stream",
                "size": uploaded_file.size,
            }

    else:
        captured_report = st.session_state.captured_camera_report

        if captured_report is None and st.session_state.extraction_result is None:
            camera_file = st.camera_input(
                "Take a clear photo of the report",
                disabled=not ready,
                key="camera_report",
            )
            if camera_file is not None:
                st.session_state.captured_camera_report = {
                    "name": camera_file.name or "camera_report.jpg",
                    "content": camera_file.getvalue(),
                    "content_type": camera_file.type or "image/jpeg",
                    "size": camera_file.size,
                }
                st.rerun()
        elif captured_report is not None:
            st.success("Photo captured. The camera has been turned off.")
            st.image(
                captured_report["content"],
                caption="Captured medical report",
                use_container_width=True,
            )
            selected_report = captured_report
            st.button(
                "Retake Photo",
                use_container_width=True,
                on_click=reset_camera_capture,
            )

    if not ready:
        st.caption("Accept consent and start the backend to enable report input.")
    elif selected_report is not None and st.session_state.extraction_result is None:
        st.write(
            f"Selected: **{selected_report['name']}** "
            f"({selected_report['size'] / 1024:.1f} KB)"
        )
        if st.button("Extract Report", type="primary", use_container_width=True):
            with st.spinner("Validating and extracting the report..."):
                try:
                    st.session_state.extraction_result = api_client.extract_report(
                        filename=selected_report["name"],
                        content=selected_report["content"],
                        content_type=selected_report["content_type"],
                    )
                    st.session_state.extraction_confirmed = False
                    st.session_state.confirmation_result = None
                    st.session_state.last_extraction_message = (
                        "Extraction completed successfully. Review the result below."
                    )
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    if st.session_state.last_extraction_message:
        st.success(st.session_state.last_extraction_message)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.extraction_result:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        confirmation = render_extraction_review(
            extraction=st.session_state.extraction_result,
            api_client=api_client,
            selected_language=language,
            selected_provider=provider,
            is_confirmed=st.session_state.extraction_confirmed,
        )
        if confirmation:
            st.session_state.extraction_confirmed = True
            st.session_state.confirmation_result = confirmation
            st.rerun()

        if st.session_state.extraction_confirmed:
            st.success("✅ Phase 2 complete for this report: Ready for analysis.")
            st.button(
                "Upload Another Report",
                type="secondary",
                use_container_width=True,
                on_click=reset_report_state,
            )
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='footer'>MediSimplify AI — Phase 2 Report Upload & OCR</div>",
    unsafe_allow_html=True,
)
