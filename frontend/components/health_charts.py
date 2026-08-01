"""Interactive, non-diagnostic health analytics for report explanations."""

from __future__ import annotations

from collections import Counter
from html import escape
import re
from typing import Any, Mapping, Sequence

import streamlit as st

from components.parameter_cards import normalize_status

_STATUS_LABELS = {
    "normal": "Within range",
    "low": "Low",
    "high": "High",
    "critical": "Critical",
    "attention": "Needs attention",
    "unknown": "Not stated",
}

_STATUS_ORDER = ("normal", "low", "high", "attention", "critical", "unknown")


def _safe(value: Any, fallback: str = "") -> str:
    text = str(value if value is not None else fallback).strip()
    return escape(text or fallback)


def _numeric_value(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _reference_bounds(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if len(numbers) < 2:
        return None
    try:
        low, high = float(numbers[0]), float(numbers[1])
    except ValueError:
        return None
    if high <= low:
        return None
    return low, high


def _status_counts(items: Sequence[Mapping[str, Any]]) -> Counter[str]:
    return Counter(normalize_status(item.get("status")) for item in items)


def _visual_score(items: Sequence[Mapping[str, Any]]) -> int | None:
    classified = [item for item in items if normalize_status(item.get("status")) != "unknown"]
    if not classified:
        return None
    normal_count = sum(
        1 for item in classified if normalize_status(item.get("status")) == "normal"
    )
    return round((normal_count / len(classified)) * 100)


def _render_metric_cards(items: Sequence[Mapping[str, Any]]) -> None:
    counts = _status_counts(items)
    abnormal = sum(
        counts[key] for key in ("low", "high", "critical", "attention")
    )
    score = _visual_score(items)
    score_text = f"{score}%" if score is not None else "N/A"

    st.markdown(
        f"""
        <div class="ms-analytics-metric-grid">
            <article class="ms-analytics-metric">
                <span>Total findings</span><strong>{len(items)}</strong>
                <small>Structured items identified</small>
            </article>
            <article class="ms-analytics-metric metric-normal">
                <span>Within range</span><strong>{counts['normal']}</strong>
                <small>Marked normal in the explanation</small>
            </article>
            <article class="ms-analytics-metric metric-attention">
                <span>Needs attention</span><strong>{abnormal}</strong>
                <small>Low, high, critical or borderline</small>
            </article>
            <article class="ms-analytics-metric metric-score">
                <span>Visual summary</span><strong>{score_text}</strong>
                <small>Share of classified values within range</small>
            </article>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_gauge(score: int | None) -> None:
    if score is None:
        st.info("A visual score is unavailable because the report did not provide status labels.")
        return

    try:
        import plotly.graph_objects as go
    except ImportError:
        st.progress(score / 100)
        st.caption(f"{score}% of classified values were marked within range.")
        return

    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 34}},
            title={"text": "Values marked within range", "font": {"size": 15}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#14b8a6"},
                "bgcolor": "rgba(148,163,184,0.14)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "rgba(239,68,68,0.10)"},
                    {"range": [50, 75], "color": "rgba(245,158,11,0.10)"},
                    {"range": [75, 100], "color": "rgba(22,163,74,0.10)"},
                ],
            },
        )
    )
    figure.update_layout(
        height=280,
        margin=dict(l=22, r=22, t=55, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _render_distribution(items: Sequence[Mapping[str, Any]]) -> None:
    counts = _status_counts(items)
    labels = [_STATUS_LABELS[key] for key in _STATUS_ORDER if counts[key]]
    values = [counts[key] for key in _STATUS_ORDER if counts[key]]

    if not values:
        st.info("No status distribution is available for this report.")
        return

    try:
        import plotly.graph_objects as go
    except ImportError:
        for label, value in zip(labels, values):
            st.write(f"**{label}:** {value}")
        return

    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.64,
                textinfo="label+value",
                hovertemplate="%{label}: %{value}<extra></extra>",
                marker={
                    "colors": [
                        "#16a34a",
                        "#f59e0b",
                        "#ef4444",
                        "#f97316",
                        "#dc2626",
                        "#64748b",
                    ][: len(values)]
                },
            )
        ]
    )
    figure.update_layout(
        height=280,
        margin=dict(l=12, r=12, t=35, b=15),
        title={"text": "Finding status distribution", "x": 0.5, "font": {"size": 15}},
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _normalized_rows(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        observed = _numeric_value(
            item.get("observed_value") or item.get("value") or item.get("result")
        )
        bounds = _reference_bounds(item.get("reference_range"))
        if observed is None or bounds is None:
            continue
        low, high = bounds
        position = ((observed - low) / (high - low)) * 100
        rows.append(
            {
                "name": str(item.get("name") or "Report item"),
                "position": max(-50.0, min(150.0, position)),
                "observed": observed,
                "low": low,
                "high": high,
                "unit": str(item.get("unit") or ""),
                "status": normalize_status(item.get("status")),
            }
        )
    return rows[:12]


def _render_normalized_parameters(items: Sequence[Mapping[str, Any]]) -> None:
    rows = _normalized_rows(items)
    if not rows:
        st.caption(
            "A normalized comparison could not be created because numeric values and two-sided reference ranges were not available."
        )
        return

    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    color_map = {
        "normal": "#16a34a",
        "low": "#f59e0b",
        "high": "#ef4444",
        "critical": "#dc2626",
        "attention": "#f97316",
        "unknown": "#64748b",
    }
    names = [row["name"] for row in rows]
    positions = [row["position"] for row in rows]
    colors = [color_map[row["status"]] for row in rows]
    hover = [
        f"{row['observed']:g} {row['unit']}<br>Reference: {row['low']:g}–{row['high']:g} {row['unit']}"
        for row in rows
    ]

    figure = go.Figure(
        go.Bar(
            x=positions,
            y=names,
            orientation="h",
            marker_color=colors,
            customdata=hover,
            hovertemplate="%{y}<br>%{customdata}<br>Normalized position: %{x:.0f}%<extra></extra>",
        )
    )
    figure.add_vrect(x0=0, x1=100, fillcolor="rgba(22,163,74,0.08)", line_width=0)
    figure.add_vline(x=0, line_dash="dot", line_color="#94a3b8")
    figure.add_vline(x=100, line_dash="dot", line_color="#94a3b8")
    figure.update_layout(
        height=max(300, 48 * len(rows)),
        margin=dict(l=12, r=20, t=55, b=35),
        title={"text": "Position within the stated reference range", "x": 0.5, "font": {"size": 15}},
        xaxis={
            "title": "0% = lower limit · 100% = upper limit",
            "range": [-50, 150],
            "ticksuffix": "%",
            "gridcolor": "rgba(148,163,184,0.16)",
        },
        yaxis={"autorange": "reversed"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif"},
    )
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    st.caption(
        "This chart normalizes different units only for visual placement against each item’s own reference range. It does not compare medical importance."
    )


def _render_attention_panel(items: Sequence[Mapping[str, Any]]) -> None:
    attention = [
        item
        for item in items
        if normalize_status(item.get("status"))
        in {"low", "high", "critical", "attention"}
    ]
    if not attention:
        st.markdown(
            '<div class="ms-analytics-empty">✓ No structured findings were marked as low, high, critical or needing attention.</div>',
            unsafe_allow_html=True,
        )
        return

    cards = []
    for item in attention[:8]:
        status = normalize_status(item.get("status"))
        value = item.get("observed_value") or item.get("value") or item.get("result") or "—"
        unit = item.get("unit") or ""
        cards.append(
            f"""
            <article class="ms-attention-card status-{status}">
                <span>{_safe(item.get('name'), 'Report item')}</span>
                <strong>{_safe(value, '—')} {_safe(unit)}</strong>
                <small>{_safe(_STATUS_LABELS[status])}</small>
            </article>
            """
        )
    st.markdown(
        '<div class="ms-attention-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_health_analytics(
    items: Sequence[Mapping[str, Any]] | None,
    *,
    show_normalized_chart: bool = True,
) -> None:
    """Render the complete Phase 9.5 Batch 2 analytics dashboard."""
    safe_items = list(items or [])
    st.markdown(
        """
        <section class="ms-analytics-heading">
            <div>
                <span>PHASE 9.5 · VISUAL ANALYTICS</span>
                <h3>Health Analytics Dashboard</h3>
                <p>Visual summaries of the structured labels returned from your report explanation.</p>
            </div>
            <div class="ms-analytics-badge">Non-diagnostic</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not safe_items:
        st.info("No structured report findings are available for analytics.")
        return

    _render_metric_cards(safe_items)

    gauge_col, distribution_col = st.columns(2)
    with gauge_col:
        with st.container(border=True):
            _render_gauge(_visual_score(safe_items))
    with distribution_col:
        with st.container(border=True):
            _render_distribution(safe_items)

    st.markdown("#### Findings that need attention")
    _render_attention_panel(safe_items)

    if show_normalized_chart:
        with st.expander("View normalized parameter chart", expanded=False):
            _render_normalized_parameters(safe_items)

    st.markdown(
        """
        <div class="ms-analytics-disclaimer">
            These visuals summarize AI-assigned labels from the confirmed report text. They are not a diagnosis, urgency score, prognosis, or substitute for the original report and a qualified clinician.
        </div>
        """,
        unsafe_allow_html=True,
    )
