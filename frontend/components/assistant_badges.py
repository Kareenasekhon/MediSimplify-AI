"""Reusable status badges for the medical assistant interface."""
from __future__ import annotations

from html import escape
from typing import Iterable, Tuple

import streamlit as st


def render_assistant_badges(badges: Iterable[Tuple[str, str]]) -> None:
    chips = "".join(
        f'<span class="ms-assistant-badge"><span>{escape(icon)}</span>{escape(str(label))}</span>'
        for icon, label in badges
        if label
    )
    st.markdown(f'<div class="ms-assistant-badges">{chips}</div>', unsafe_allow_html=True)
