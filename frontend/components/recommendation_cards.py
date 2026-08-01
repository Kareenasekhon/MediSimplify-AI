"""Recommendation and notice cards for Phase 9.3 report analysis."""

from __future__ import annotations

from html import escape
from typing import Any, Sequence

import streamlit as st


_CARD_CONFIG = {
    "info": {"icon": "💡", "label": "Information"},
    "warning": {"icon": "⚠️", "label": "Needs review"},
    "success": {"icon": "✓", "label": "Helpful note"},
    "danger": {"icon": "!", "label": "Important"},
}


def _safe(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return escape(text if text else fallback)


def render_recommendation_cards(
    *,
    title: str,
    items: Sequence[Any] | None,
    card_type: str = "info",
    empty_message: str | None = None,
) -> None:
    """Render a titled collection of medical-analysis notes."""
    safe_items = [str(item).strip() for item in (items or []) if str(item).strip()]
    config = _CARD_CONFIG.get(card_type, _CARD_CONFIG["info"])

    if not safe_items:
        if empty_message:
            st.caption(empty_message)
        return

    st.markdown(
        f"""
        <div class="ms-recommendation-heading">
            <div>
                <span class="ms-recommendation-kicker">{_safe(config['label'])}</span>
                <h3>{_safe(title)}</h3>
            </div>
            <span class="ms-recommendation-count">{len(safe_items)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for index, item in enumerate(safe_items, start=1):
        st.markdown(
            f"""
            <article class="ms-recommendation-card type-{_safe(card_type)}">
                <div class="ms-recommendation-icon">{config['icon']}</div>
                <div class="ms-recommendation-copy">
                    <span class="ms-recommendation-number">{index:02d}</span>
                    <p>{_safe(item)}</p>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )
