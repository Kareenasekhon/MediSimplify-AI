"""Report-history user interface for MediSimplify AI."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Mapping, Sequence

import streamlit as st

from components.doctor_questions import render_doctor_questions
from components.health_charts import render_health_analytics
from components.parameter_cards import render_status_sections
from components.recommendation_cards import render_recommendation_cards
from components.report_summary import render_report_summary
from services import history_service
from utils.pdf_generator import generate_medical_report_pdf


def _safe(value: Any, fallback: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    return escape(text or fallback)


def _pretty(value: Any) -> str:
    return str(value or "Unknown").replace("_", " ").title()


def _date_label(value: Any) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y · %I:%M %p")
    except (TypeError, ValueError):
        return "Date unavailable"


def _filter_reports(
    reports: Sequence[Mapping[str, Any]], search: str, report_type: str
) -> list[Mapping[str, Any]]:
    query = search.strip().lower()
    filtered = []
    for entry in reports:
        if report_type != "all" and entry.get("report_type") != report_type:
            continue
        searchable = " ".join(
            str(entry.get(key) or "")
            for key in ("filename", "report_type", "provider", "language", "summary")
        ).lower()
        if query and query not in searchable:
            continue
        filtered.append(entry)
    return filtered


def _render_stats(reports: Sequence[Mapping[str, Any]]) -> None:
    counts = {
        "blood": sum(item.get("report_type") == "blood_report" for item in reports),
        "prescription": sum(item.get("report_type") == "prescription" for item in reports),
        "radiology": sum(item.get("report_type") == "radiology_report" for item in reports),
    }
    columns = st.columns(4)
    columns[0].metric("Saved reports", len(reports))
    columns[1].metric("Blood", counts["blood"])
    columns[2].metric("Prescription", counts["prescription"])
    columns[3].metric("Radiology", counts["radiology"])


def render_history_preview(entry: Mapping[str, Any]) -> None:
    """Render a previously saved analysis without recreating report bytes or RAG state."""
    analysis = entry.get("analysis") or {}
    items = analysis.get("items") or []
    st.markdown('<div class="ms-history-preview-anchor"></div>', unsafe_allow_html=True)
    st.info(
        "You are viewing a locally saved structured analysis. The original uploaded file "
        "and its report-scoped chat knowledge base are not stored in history."
    )
    render_report_summary(analysis, report_type=entry.get("report_type", "medical_report"))
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

    try:
        pdf_bytes = generate_medical_report_pdf(
            analysis=analysis,
            report_type=entry.get("report_type", "medical_report"),
            language=entry.get("language", "English"),
            generated_at=datetime.now(),
        )
        st.download_button(
            "Download saved analysis PDF",
            data=pdf_bytes,
            file_name=f"medisimplify_history_{entry.get('report_id', 'report')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"history_preview_pdf_{entry.get('report_id')}",
        )
    except Exception as exc:
        st.warning(f"The saved PDF could not be prepared: {exc}")


def render_history_panel() -> None:
    """Render search, filters, cards, preview, deletion and PDF redownload."""
    reports = history_service.list_reports()
    st.markdown("## 📚 Report History")
    st.caption(
        "Search, reopen, download, or delete your previously analyzed reports."
    )

    with st.expander(
        f"Saved Reports ({len(reports)})",
        expanded=True,
    ):
        st.caption(
            "History is stored locally in this frontend as structured analysis only. "
            "Uploaded report files are not retained."
        )
        if not reports:
            st.markdown(
                """
                <div class="ms-history-empty">
                    <div class="ms-history-empty-icon">🗂️</div>
                    <strong>No saved analyses yet</strong>
                    <span>Complete a report explanation and it will appear here automatically.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        _render_stats(reports)
        filter_col, type_col, clear_col = st.columns([2, 1, 1])
        search = filter_col.text_input(
            "Search history",
            placeholder="Filename, provider, type or summary",
            key="history_search",
        )
        types = sorted({str(item.get("report_type") or "unknown") for item in reports})
        selected_type = type_col.selectbox(
            "Report type",
            ["all", *types],
            format_func=lambda value: "All report types" if value == "all" else _pretty(value),
            key="history_type_filter",
        )
        if clear_col.button("Clear history", use_container_width=True, key="history_clear_all"):
            removed = history_service.clear_history()
            st.session_state.history_preview_entry = None
            st.toast(f"Removed {removed} saved report(s).")
            st.rerun()

        filtered = _filter_reports(reports, search, selected_type)
        st.caption(f"Showing {len(filtered)} of {len(reports)} saved report(s)")
        if not filtered:
            st.info("No saved reports match the current search and filter.")
            return

        for entry in filtered:
            report_id = str(entry.get("report_id") or "unknown")
            st.markdown(
                f"""
                <article class="ms-history-card">
                    <div class="ms-history-file-icon">📄</div>
                    <div class="ms-history-card-copy">
                        <div class="ms-history-card-title">{_safe(entry.get('filename'), 'Medical report')}</div>
                        <div class="ms-history-card-meta">
                            {_safe(_pretty(entry.get('report_type')))} · {_safe(entry.get('provider'), 'Unknown provider')} ·
                            {_safe(entry.get('language'), 'Unknown language')} · {_safe(_date_label(entry.get('updated_at')))}
                        </div>
                        <div class="ms-history-card-summary">{_safe(entry.get('summary'), 'No saved summary.')}</div>
                    </div>
                </article>
                """,
                unsafe_allow_html=True,
            )
            action_col, pdf_col, delete_col = st.columns([1, 1, 1])
            if action_col.button("Open analysis", key=f"history_open_{report_id}", use_container_width=True):
                st.session_state.history_preview_entry = dict(entry)
                st.rerun()

            try:
                pdf_bytes = generate_medical_report_pdf(
                    analysis=entry.get("analysis") or {},
                    report_type=entry.get("report_type", "medical_report"),
                    language=entry.get("language", "English"),
                    generated_at=datetime.now(),
                )
                pdf_col.download_button(
                    "Download PDF",
                    data=pdf_bytes,
                    file_name=f"medisimplify_{report_id}.pdf",
                    mime="application/pdf",
                    key=f"history_pdf_{report_id}",
                    use_container_width=True,
                )
            except Exception:
                pdf_col.button(
                    "PDF unavailable",
                    key=f"history_pdf_disabled_{report_id}",
                    disabled=True,
                    use_container_width=True,
                )

            if delete_col.button("Delete", key=f"history_delete_{report_id}", use_container_width=True):
                history_service.delete_report(report_id)
                preview = st.session_state.get("history_preview_entry") or {}
                if str(preview.get("report_id")) == report_id:
                    st.session_state.history_preview_entry = None
                st.toast("Saved report removed.")
                st.rerun()

    preview = st.session_state.get("history_preview_entry")
    if preview:
        header_col, close_col = st.columns([5, 1])
        header_col.markdown("### Saved Analysis Preview")
        if close_col.button("Close preview", use_container_width=True, key="history_close_preview"):
            st.session_state.history_preview_entry = None
            st.rerun()
        render_history_preview(preview)
