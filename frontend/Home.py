from pathlib import Path

import streamlit as st
from components.extraction_review_component import render_extraction_review
from components.report_summary import render_report_summary
from components.parameter_cards import render_status_sections
from components.recommendation_cards import render_recommendation_cards
from components.doctor_questions import render_doctor_questions
from components.report_actions import render_report_actions
from components.report_export import render_report_export
from components.health_charts import render_health_analytics
from components.history_panel import render_history_panel
from components.ux_feedback import render_error_state, render_process_steps, toast_once
from services import history_service
from components.assistant_header import render_assistant_header
from components.assistant_controls import render_assistant_controls
from components.knowledge_base_card import render_knowledge_base_card
from components.suggested_questions import render_suggested_questions
from components.chat_components import render_chat_messages
from services.api_client import APIClient
from utils import ui_helpers

FRONTEND_DIR = Path(__file__).resolve().parent
FAVICON = FRONTEND_DIR / "assets" / "logo" / "favicon.png"

st.set_page_config(
    page_title="MediSimplify AI - Simple Medical Report Explanations",
    page_icon=str(FAVICON) if FAVICON.exists() else "🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui_helpers.apply_custom_theme()

pending_toast = st.session_state.pop("ux_pending_toast", None)
if pending_toast:
    st.toast(pending_toast, icon="✅")

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
    "knowledge_base_status": None,
    "chat_history": [],
    "suggested_questions": [],
    "pending_chat_question": None,
    "last_voice_signature": None,
    "current_report_file": None,
    "history_preview_entry": None,
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
        "knowledge_base_status",
        "chat_history",
        "uploaded_report",
        "camera_report",
        "current_report_file",
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


api_client = APIClient()
health_status = api_client.check_health()
try:
    provider_status = api_client.get_provider_status() if health_status.get("status") == "healthy" else {}
except RuntimeError:
    provider_status = {}

with st.sidebar:
    ui_helpers.render_sidebar_brand()

    st.markdown('<div class="ms-sidebar-label">Experience</div>', unsafe_allow_html=True)
    language = st.selectbox(
        "Language",
        ["English", "हिंदी (Hindi)", "ਪੰਜਾਬੀ (Punjabi)"],
        help="Choose the language used for report explanations and voice replies.",
    )

    provider = st.selectbox(
        "AI Provider",
        ["Gemini", "Groq", "Ollama (Local)"],
        index=0,
        help="Choose the provider used for routing, analysis and chat.",
    )

    status_by_name = {
        item.get("provider"): item
        for item in provider_status.get("providers", [])
    }
    selected_key = provider.lower().replace(" (local)", "")
    selected_status = status_by_name.get(selected_key)

    if selected_status:
        if selected_status.get("available"):
            st.success(f"{provider} is ready · {selected_status.get('model', 'model available')}")
        else:
            st.warning(selected_status.get("detail", f"{provider} is unavailable"))

    if st.button(
        "Test AI Provider",
        use_container_width=True,
        help="Makes one small live request and may consume API credits.",
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

    st.markdown('<div class="ms-sidebar-label">Session</div>', unsafe_allow_html=True)
    st.caption("Your uploaded report, OCR review, analysis, RAG chat and voice controls remain available below.")
    if st.button("Clear Session", use_container_width=True):
        st.session_state.clear()
        st.rerun()

ui_helpers.render_dashboard_hero()
provider_count = sum(1 for item in provider_status.get("providers", []) if item.get("configured")) or 3
ui_helpers.render_dashboard_stats(
    api_online=health_status.get("status") == "healthy",
    provider_count=provider_count,
)

render_history_panel()
ui_helpers.render_section_heading(
    "Medical Report Workspace",
    "Connect the backend, accept the safety guidance and add a report to begin.",
)

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
        render_error_state(
            "Backend is offline",
            health_status.get("error", "The FastAPI service could not be reached."),
            "Start it with: uvicorn app.main:app --reload --port 8000",
        )
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

    st.markdown("<div class='glass-card ms-upload-workspace'>", unsafe_allow_html=True)
    ui_helpers.render_upload_header()

    st.radio(
        "Choose report source",
        ["Upload File", "Take Photo"],
        horizontal=True,
        key="report_source",
        disabled=not ready or st.session_state.extraction_result is not None,
        label_visibility="collapsed",
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
        ui_helpers.render_selected_file(
            filename=selected_report["name"],
            size_bytes=selected_report["size"],
            content_type=selected_report["content_type"],
        )
        if st.button("Extract & Review Report", type="primary", use_container_width=True):
            st.session_state.current_report_file = selected_report
            with st.status("Preparing your report...", expanded=True) as status:
                render_process_steps(
                    ["Validate upload", "Read document", "Extract medical text", "Prepare review"],
                    active_index=1,
                )
                try:
                    st.write("🔒 Validating file type and size")
                    st.write("📄 Reading the medical document")
                    st.write("🔎 Running OCR and extracting medical text")
                    st.session_state.extraction_result = api_client.extract_report(
                        filename=selected_report["name"],
                        content=selected_report["content"],
                        content_type=selected_report["content_type"],
                    )
                    st.write("✅ Preparing the side-by-side review")
                    st.session_state.extraction_confirmed = False
                    st.session_state.confirmation_result = None
                    st.session_state.last_extraction_message = (
                        "Extraction completed successfully. Review and correct the result below."
                    )
                    status.update(label="Report is ready for review", state="complete")
                    st.session_state["ux_pending_toast"] = "Report extraction completed."
                    st.rerun()
                except RuntimeError as exc:
                    status.update(label="Extraction could not be completed", state="error")
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
            original_file=st.session_state.get("current_report_file"),
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
                                    st.session_state["ux_pending_toast"] = "Your report explanation is ready."
                                    st.rerun()
                                except RuntimeError as exc:
                                    st.error(str(exc))
                    else:
                        analysis = st.session_state.analysis_result
                        items = analysis.get("items", [])

                        # Phase 9.5 Batch 3: persist structured analysis locally.
                        current_file = st.session_state.get("current_report_file") or {}
                        history_service.save_report(
                            report_id=report_id,
                            filename=current_file.get("name", f"{route.get('report_type', 'medical_report')}.pdf"),
                            report_type=route.get("report_type", "medical_report"),
                            language=language,
                            provider=analysis.get("provider_used") or provider,
                            analysis=analysis,
                            routing=route,
                        )
                        toast_once(f"history_{report_id}", "Analysis saved to Report History.", "📚")

                        render_report_summary(
                            analysis,
                            report_type=route.get("report_type", "medical_report"),
                        )

                        render_status_sections(items)

                        render_health_analytics(items)

                        render_recommendation_cards(
                            title="Important notes",
                            items=analysis.get("important_notes", []),
                            card_type="info",
                        )
                        render_recommendation_cards(
                            title="Unclear information",
                            items=analysis.get("unclear_information", []),
                            card_type="warning",
                        )
                        render_doctor_questions(analysis.get("questions_for_doctor", []))

                        disclaimer = analysis.get(
                            "disclaimer",
                            "This explanation is educational and does not replace professional medical advice.",
                        )
                        if disclaimer:
                            st.markdown(
                                f'<div class="ms-disclaimer-card">⚕️ {disclaimer}</div>',
                                unsafe_allow_html=True,
                            )

                        render_report_actions(
                            analysis=analysis,
                            report_type=route.get("report_type", "medical_report"),
                            on_upload_another=reset_report_state,
                        )

                        render_report_export(
                            analysis=analysis,
                            report_type=route.get("report_type", "medical_report"),
                            language=language,
                        )

                        st.success("✅ Phase 5 complete for this report.")
                        st.markdown('<div id="report-assistant"></div>', unsafe_allow_html=True)
                        st.markdown("---")
                        # Phase 9.4 — Intelligent Medical Assistant
                        if st.session_state.knowledge_base_status is None:
                            try:
                                st.session_state.knowledge_base_status = (
                                    api_client.get_knowledge_base_status(report_id)
                                )
                            except RuntimeError as exc:
                                st.warning(str(exc))

                        kb_status = st.session_state.knowledge_base_status or {}
                        render_assistant_header(
                            provider=provider,
                            language=language,
                            report_type=route.get("report_type", "medical_report"),
                            ready=bool(kb_status.get("ready")),
                        )
                        render_knowledge_base_card(kb_status)

                        if not kb_status.get("ready"):
                            st.info(
                                "Build the report knowledge base to enable grounded questions and answers."
                            )
                            if st.button(
                                "Build Knowledge Base",
                                type="primary",
                                use_container_width=True,
                                key="assistant_build_kb",
                            ):
                                with st.spinner("Creating report embeddings and FAISS index..."):
                                    try:
                                        st.session_state.knowledge_base_status = (
                                            api_client.build_knowledge_base(report_id)
                                        )
                                        st.rerun()
                                    except RuntimeError as exc:
                                        st.error(str(exc))
                        else:
                            kb_action_col1, kb_action_col2 = st.columns(2)
                            if kb_action_col1.button(
                                "Clear Conversation",
                                use_container_width=True,
                                key="assistant_clear_chat",
                            ):
                                try:
                                    api_client.clear_conversation(report_id)
                                    st.session_state.chat_history = []
                                    st.rerun()
                                except RuntimeError as exc:
                                    st.error(str(exc))
                            if kb_action_col2.button(
                                "Rebuild Knowledge Base",
                                use_container_width=True,
                                key="assistant_rebuild_kb",
                            ):
                                with st.spinner("Rebuilding report knowledge base..."):
                                    try:
                                        st.session_state.knowledge_base_status = (
                                            api_client.build_knowledge_base(report_id, force=True)
                                        )
                                        api_client.clear_conversation(report_id)
                                        st.session_state.chat_history = []
                                        st.rerun()
                                    except RuntimeError as exc:
                                        st.error(str(exc))

                            controls = render_assistant_controls()

                            if not st.session_state.suggested_questions:
                                try:
                                    suggestions = api_client.get_suggested_questions(report_id)
                                    st.session_state.suggested_questions = suggestions.get("questions", [])
                                except RuntimeError:
                                    st.session_state.suggested_questions = []

                            selected_suggestion = render_suggested_questions(
                                st.session_state.suggested_questions
                            )
                            if selected_suggestion:
                                st.session_state.pending_chat_question = selected_suggestion
                                st.rerun()

                            st.markdown(
                                "<div class='ms-assistant-section-label'>Conversation</div>",
                                unsafe_allow_html=True,
                            )
                            render_chat_messages(st.session_state.chat_history)

                            voice_question = None
                            if controls["voice_input"]:
                                recorded_audio = st.audio_input(
                                    "Record your question",
                                    key="assistant_audio_input",
                                )
                                if recorded_audio is not None:
                                    signature = (recorded_audio.name, len(recorded_audio.getvalue()))
                                    if signature != st.session_state.last_voice_signature:
                                        with st.spinner("Transcribing your voice locally..."):
                                            try:
                                                language_key = {
                                                    "English": "english",
                                                    "हिंदी (Hindi)": "hindi",
                                                    "ਪੰਜਾਬੀ (Punjabi)": "punjabi",
                                                }[language]
                                                transcript = api_client.transcribe_audio(
                                                    filename=recorded_audio.name or "voice.wav",
                                                    content=recorded_audio.getvalue(),
                                                    content_type=recorded_audio.type or "audio/wav",
                                                    language=language_key,
                                                )
                                                voice_question = transcript.get("text")
                                                st.session_state.last_voice_signature = signature
                                                st.success(f"I heard: {voice_question}")
                                            except RuntimeError as exc:
                                                st.error(str(exc))

                            typed_question = st.chat_input(
                                "Ask about your report or a general medical term",
                                key="assistant_chat_input",
                            )
                            question = (
                                st.session_state.pending_chat_question
                                or voice_question
                                or typed_question
                            )
                            if question:
                                st.session_state.pending_chat_question = None
                                st.session_state.chat_history.append(
                                    {"role": "user", "content": question}
                                )
                                language_key = {
                                    "English": "english",
                                    "हिंदी (Hindi)": "hindi",
                                    "ਪੰਜਾਬੀ (Punjabi)": "punjabi",
                                }[language]
                                with st.spinner(
                                    "Choosing the safest answer mode and preparing your answer..."
                                ):
                                    try:
                                        chat_result = api_client.ask_report_question(
                                            report_id=report_id,
                                            question=question,
                                            language=language_key,
                                            provider=provider,
                                            mode=controls["mode"],
                                            explanation_style=(
                                                "grandma"
                                                if controls["grandma_mode"]
                                                else "standard"
                                            ),
                                        )
                                        answer_text = chat_result.get("answer", "")
                                        answer_audio = None
                                        if controls["voice_reply"] and answer_text:
                                            try:
                                                answer_audio = api_client.synthesize_speech(
                                                    text=answer_text,
                                                    language=language_key,
                                                    slow=controls["grandma_mode"],
                                                )
                                            except RuntimeError as voice_exc:
                                                st.warning(
                                                    "Text answer is ready, but voice output failed: "
                                                    f"{voice_exc}"
                                                )
                                        st.session_state.chat_history.append(
                                            {
                                                "role": "assistant",
                                                "content": answer_text,
                                                "audio": answer_audio,
                                                "sources": chat_result.get("sources", []),
                                                "mode_used": chat_result.get("mode_used"),
                                                "explanation_style": chat_result.get(
                                                    "explanation_style", "standard"
                                                ),
                                            }
                                        )
                                        st.rerun()
                                    except RuntimeError as exc:
                                        st.session_state.chat_history.pop()
                                        st.error(str(exc))

            st.button(
                "Upload Another Report",
                type="secondary",
                use_container_width=True,
                on_click=reset_report_state,
            )
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='footer'>MediSimplify AI — Phase 9 Frontend Enhancement</div>",
    unsafe_allow_html=True,
)


ui_helpers.render_footer()
