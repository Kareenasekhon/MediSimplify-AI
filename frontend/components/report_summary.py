"""Summary components for the Phase 9.3 report-analysis dashboard."""

from __future__ import annotations

from html import escape
from typing import Any, Mapping, Sequence

import streamlit as st


_NORMAL_STATUSES = {
    "normal",
    "within range",
    "within normal range",
    "healthy",
    "ok",
    "stable",
}


def _text(value: Any, fallback: str = "") -> str:
    """Return a safely escaped display string."""
    if value is None:
        return escape(fallback)
    rendered = str(value).strip()
    return escape(rendered if rendered else fallback)


def _normal_item_count(items: Sequence[Mapping[str, Any]]) -> int:
    count = 0
    for item in items:
        status = str(item.get("status") or "").strip().lower()
        if status in _NORMAL_STATUSES:
            count += 1
    return count


def calculate_report_score(items: Sequence[Mapping[str, Any]]) -> int | None:
    """
    Calculate a non-diagnostic visual score from item statuses.

    The score only represents the percentage of parsed items labelled normal.
    It must never be presented as a diagnosis or medical risk score.
    """
    if not items:
        return None
    return round((_normal_item_count(items) / len(items)) * 100)


def render_analysis_header(
    *,
    report_type: str,
    agent_used: str | None = None,
    provider_used: str | None = None,
    model: str | None = None,
) -> None:
    """Render the analysis title, metadata and completion badge."""
    pretty_report_type = report_type.replace("_", " ").title() if report_type else "Medical Report"

    metadata = []
    if agent_used:
        metadata.append(f"Agent: {_text(agent_used).replace('_', ' ').title()}")
    if provider_used:
        metadata.append(f"Provider: {_text(provider_used).title()}")
    if model:
        metadata.append(f"Model: {_text(model)}")

    meta_html = " · ".join(metadata) if metadata else "Specialised medical-report explanation"

    st.markdown(
        f"""
        <section class="ms-analysis-header">
            <div class="ms-analysis-title-wrap">
                <div class="ms-analysis-icon">🩺</div>
                <div>
                    <div class="ms-analysis-eyebrow">Report Analysis</div>
                    <h2 class="ms-analysis-title">{_text(pretty_report_type)}</h2>
                    <div class="ms-analysis-meta">{meta_html}</div>
                </div>
            </div>
            <div class="ms-analysis-complete">● Analysis complete</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_summary_card(
    *,
    summary: str | None,
    items: Sequence[Mapping[str, Any]] | None = None,
    show_visual_score: bool = True,
) -> None:
    """Render the plain-language summary and optional non-diagnostic score."""
    safe_items = list(items or [])
    score = calculate_report_score(safe_items)
    summary_html = _text(summary, "No summary was returned for this report.")
    empty_class = " ms-summary-empty" if not summary else ""

    if show_visual_score and score is not None:
        score_card = f"""
        <aside class="ms-score-card">
            <div class="ms-score-label">Values marked within range</div>
            <div class="ms-score-value">{score}%</div>
            <div class="ms-score-track" aria-label="{score} percent of parsed values marked normal">
                <div class="ms-score-fill" style="width:{max(0, min(score, 100))}%"></div>
            </div>
            <div class="ms-score-note">
                Visual summary only — not a diagnosis, health score, or urgency assessment.
            </div>
        </aside>
        """
    else:
        score_card = ""

    grid_class = "ms-summary-grid" if score_card else "ms-summary-grid ms-summary-grid-single"
    st.markdown(
        f"""
        <div class="{grid_class}">
            <article class="ms-summary-card">
                <div class="ms-card-kicker">✨ In simple words</div>
                <p class="ms-summary-copy{empty_class}">{summary_html}</p>
            </article>
            {score_card}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_summary(
    analysis: Mapping[str, Any],
    *,
    report_type: str = "medical_report",
    show_visual_score: bool = True,
) -> None:
    """Convenience renderer for the complete analysis heading and summary."""
    render_analysis_header(
        report_type=report_type,
        agent_used=analysis.get("agent_used"),
        provider_used=analysis.get("provider_used"),
        model=analysis.get("model"),
    )
    render_summary_card(
        summary=analysis.get("summary"),
        items=analysis.get("items") or [],
        show_visual_score=show_visual_score,
    )
