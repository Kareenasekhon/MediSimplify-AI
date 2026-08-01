"""Parameter-card components for Phase 9.3 report analysis."""

from __future__ import annotations

from html import escape
import re
from typing import Any, Mapping, Sequence

import streamlit as st


_STATUS_ALIASES = {
    "normal": "normal",
    "within range": "normal",
    "within normal range": "normal",
    "healthy": "normal",
    "ok": "normal",
    "stable": "normal",
    "low": "low",
    "below range": "low",
    "below normal": "low",
    "high": "high",
    "above range": "high",
    "above normal": "high",
    "critical": "critical",
    "dangerously low": "critical",
    "dangerously high": "critical",
    "abnormal": "attention",
    "needs attention": "attention",
    "attention": "attention",
    "borderline": "attention",
}

_STATUS_LABELS = {
    "normal": "Normal",
    "low": "Low",
    "high": "High",
    "critical": "Critical",
    "attention": "Attention",
    "unknown": "Not stated",
}


def _safe(value: Any, fallback: str = "") -> str:
    if value is None:
        return escape(fallback)
    text = str(value).strip()
    return escape(text if text else fallback)


def normalize_status(status: Any) -> str:
    """Convert model-provided status wording into a stable CSS category."""
    raw = str(status or "").strip().lower()
    if not raw:
        return "unknown"
    if raw in _STATUS_ALIASES:
        return _STATUS_ALIASES[raw]

    for phrase, normalized in _STATUS_ALIASES.items():
        if phrase in raw:
            return normalized
    return "unknown"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def _display_value(item: Mapping[str, Any]) -> str:
    for key in ("observed_value", "value", "result", "dosage"):
        if item.get(key) not in (None, ""):
            return str(item[key]).strip()
    return "—"


def _secondary_detail(item: Mapping[str, Any]) -> str:
    details = []
    if item.get("frequency"):
        details.append(str(item["frequency"]).strip())
    if item.get("duration"):
        details.append(str(item["duration"]).strip())
    if item.get("section"):
        details.append(str(item["section"]).strip())
    return " · ".join(part for part in details if part)


def render_parameter_card(item: Mapping[str, Any], *, index: int = 0) -> None:
    """Render one lab value, medicine or radiology finding as a visual card."""
    name = str(item.get("name") or f"Report item {index + 1}").strip()
    status_key = normalize_status(item.get("status"))
    status_label = _STATUS_LABELS[status_key]
    value = _display_value(item)
    unit = str(item.get("unit") or "").strip()
    reference = str(item.get("reference_range") or "").strip()
    explanation = str(item.get("simple_explanation") or "").strip()
    secondary = _secondary_detail(item)

    if reference:
        reference_html = f"Reference: {_safe(reference)}"
    elif secondary:
        reference_html = _safe(secondary)
    else:
        reference_html = "Reference information not available"

    explanation_html = (
        f'<div class="ms-parameter-explanation">{_safe(explanation)}</div>'
        if explanation
        else ""
    )

    st.markdown(
        f"""
        <article class="ms-parameter-card status-{status_key}" id="parameter-{_slug(name)}-{index}">
            <div class="ms-parameter-top">
                <div class="ms-parameter-name">{_safe(name)}</div>
                <span class="ms-parameter-status status-{status_key}">{status_label}</span>
            </div>
            <div class="ms-parameter-value-row">
                <span class="ms-parameter-value">{_safe(value, '—')}</span>
                <span class="ms-parameter-unit">{_safe(unit)}</span>
            </div>
            <div class="ms-parameter-reference">{reference_html}</div>
            {explanation_html}
        </article>
        """,
        unsafe_allow_html=True,
    )


def group_items_by_status(
    items: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Return normal, attention and unknown groups while preserving order."""
    normal: list[Mapping[str, Any]] = []
    attention: list[Mapping[str, Any]] = []
    unknown: list[Mapping[str, Any]] = []

    for item in items:
        status = normalize_status(item.get("status"))
        if status == "normal":
            normal.append(item)
        elif status == "unknown":
            unknown.append(item)
        else:
            attention.append(item)
    return normal, attention, unknown


def render_parameter_grid(
    items: Sequence[Mapping[str, Any]] | None,
    *,
    title: str = "Key Findings",
    empty_message: str = "No structured report items were returned.",
) -> None:
    """Render all structured analysis items in a responsive card grid."""
    safe_items = list(items or [])
    st.markdown(
        f"""
        <div class="ms-findings-heading">
            <h3>📊 {_safe(title)}</h3>
            <span class="ms-findings-count">{len(safe_items)} item{'s' if len(safe_items) != 1 else ''}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not safe_items:
        st.info(empty_message)
        return

    # Streamlit columns are used so each HTML card remains responsive and
    # accessible without relying on one large injected HTML grid.
    columns_per_row = 3
    for row_start in range(0, len(safe_items), columns_per_row):
        row = safe_items[row_start : row_start + columns_per_row]
        columns = st.columns(columns_per_row)
        for offset, item in enumerate(row):
            with columns[offset]:
                render_parameter_card(item, index=row_start + offset)


def render_status_sections(items: Sequence[Mapping[str, Any]] | None) -> None:
    """Render separate attention, normal and unclassified sections."""
    safe_items = list(items or [])
    normal, attention, unknown = group_items_by_status(safe_items)

    if attention:
        render_parameter_grid(attention, title="Needs Attention")
    if normal:
        render_parameter_grid(normal, title="Within Range")
    if unknown:
        render_parameter_grid(unknown, title="Other Report Details")

    st.markdown(
        """
        <div class="ms-analysis-note">
            Status labels are reproduced from the AI-generated structured explanation.
            Always verify important or abnormal findings with the original report and a qualified doctor.
        </div>
        """,
        unsafe_allow_html=True,
    )
