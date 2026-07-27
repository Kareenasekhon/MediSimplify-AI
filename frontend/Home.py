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
    "routing_result": None,
    "analysis_result": None,
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
        "routing_result",
        "analysis_result",
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
try:
    provider_status = api_client.get_provider_status() if health_status.get("status") == "healthy" else {}
except RuntimeError:
    provider_status = {}

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
        help=(
            "Phase 2 image extraction uses Gemini. Phase 3 prepares Gemini, "
            "Groq, and local Ollama for later medical agents."
        ),
    )

    status_by_name = {
        item.get("provider"): item
        for item in provider_status.get("providers", [])
    }
    selected_key = provider.lower().replace(" (local)", "")
    selected_status = status_by_name.get(selected_key)
    if selected_status:
        if selected_status.get("available"):
            st.success(
                f"{provider} configured: {selected_status.get('model', 'unknown model')}"
            )
        else:
            st.warning(f"{provider}: {selected_status.get('detail', 'Not available')}")

    if st.button(
        "Test Selected Provider",
        use_container_width=True,
        help="Makes one small live model request and may consume API credits.",
        disabled=not selected_status or not selected_status.get("configured", False),
    ):
        with st.spinner(f"Testing {provider}..."):
            try:
                test_result = api_client.test_provider(provider)
                st.success(
                    f"Connected through {test_result.get('provider')} "
                    f"using {test_result.get('model')}."
                )
            except RuntimeError as exc:
                st.error(str(exc))

    st.markdown("---")
    st.write("Current phase: **Phase 5 — Specialized Report Agents**")
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
            st.success("✅ Phase 2 complete for this report: Ready for routing.")
            report_id = st.session_state.extraction_result.get("report_id")

            if st.session_state.routing_result is None:
                if st.button("Detect Report Type", type="primary", use_container_width=True):
                    with st.spinner("Supervisor Agent is identifying the report type..."):
                        try:
                            st.session_state.routing_result = api_client.route_report(
                                report_id=report_id,
                                provider=provider,
                            )
                            st.rerun()
                        except RuntimeError as exc:
                            st.error(str(exc))
            else:
                route = st.session_state.routing_result
                st.subheader("Supervisor Routing")
                st.metric(
                    "Detected report type",
                    route["report_type"].replace("_", " ").title(),
                )
                st.progress(float(route.get("confidence", 0.0)))
                st.caption(
                    f"Confidence: {float(route.get('confidence', 0.0)):.0%} · "
                    f"Method: {route.get('method', 'unknown')} · "
                    f"Selected agent: {route.get('selected_agent', 'fallback_agent')}"
                )
                st.write(route.get("reason", ""))
                for warning in route.get("warnings", []):
                    st.warning(warning)

                if route.get("requires_manual_selection"):
                    manual_type = st.selectbox(
                        "Confirm the report type manually",
                        ["blood_report", "prescription", "radiology_report", "mixed_report", "unknown"],
                        format_func=lambda value: value.replace("_", " ").title(),
                    )
                    if st.button("Save Manual Route", use_container_width=True):
                        try:
                            st.session_state.routing_result = api_client.set_manual_route(
                                report_id, manual_type
                            )
                            st.rerun()
                        except RuntimeError as exc:
                            st.error(str(exc))
                else:
                    st.success("✅ Phase 4 complete: Report routed and ready for its specialised agent.")

                    if st.session_state.analysis_result is None:
                        if st.button("Explain Report", type="primary", use_container_width=True):
                            language_key = {
                                "English": "english",
                                "हिंदी (Hindi)": "hindi",
                                "ਪੰਜਾਬੀ (Punjabi)": "punjabi",
                            }[language]
                            with st.spinner("The specialised agent is preparing a safe explanation..."):
                                try:
                                    st.session_state.analysis_result = api_client.explain_report(
                                        report_id=report_id,
                                        language=language_key,
                                        provider=provider,
                                    )
                                    st.rerun()
                                except RuntimeError as exc:
                                    st.error(str(exc))
                    else:
                        analysis = st.session_state.analysis_result
                        st.subheader("Educational Report Explanation")
                        st.caption(
                            f"Agent: {analysis.get('agent_used', 'unknown')} · "
                            f"Provider: {analysis.get('provider_used', 'unknown')} · "
                            f"Model: {analysis.get('model', 'unknown')}"
                        )
                        st.write(analysis.get("summary", ""))

                        items = analysis.get("items", [])
                        if items:
                            st.markdown("#### Report details")
                            for index, item in enumerate(items, start=1):
                                title = item.get("name") or f"Item {index}"
                                with st.expander(title, expanded=index <= 3):
                                    details = []
                                    for label, key in (
                                        ("Value", "observed_value"),
                                        ("Unit", "unit"),
                                        ("Reference range", "reference_range"),
                                        ("Status", "status"),
                                        ("Dosage", "dosage"),
                                        ("Frequency", "frequency"),
                                        ("Duration", "duration"),
                                        ("Section", "section"),
                                    ):
                                        if item.get(key):
                                            details.append(f"**{label}:** {item[key]}")
                                    if details:
                                        st.markdown("  \n".join(details))
                                    st.write(item.get("simple_explanation", ""))

                        for heading, key, message_type in (
                            ("Important notes", "important_notes", "info"),
                            ("Unclear information", "unclear_information", "warning"),
                            ("Questions for your doctor", "questions_for_doctor", "info"),
                        ):
                            values = analysis.get(key, [])
                            if values:
                                st.markdown(f"#### {heading}")
                                for value in values:
                                    getattr(st, message_type)(value)

                        st.warning(analysis.get("disclaimer", ""))
                        st.success("✅ Phase 5 complete for this report.")

            st.button(
                "Upload Another Report",
                type="secondary",
                use_container_width=True,
                on_click=reset_report_state,
            )
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='footer'>MediSimplify AI — Phase 5 Specialized Report Agents</div>",
    unsafe_allow_html=True,
)
