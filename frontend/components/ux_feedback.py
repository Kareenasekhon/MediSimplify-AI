"""Reusable Phase 9.5 Batch 4 UX feedback components."""
from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st


def render_empty_state(title: str, message: str, icon: str = "✨") -> None:
    st.markdown(
        f"""
        <div class="ms-empty-state">
          <div class="ms-empty-icon">{escape(icon)}</div>
          <strong>{escape(title)}</strong>
          <span>{escape(message)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_process_steps(steps: Iterable[str], active_index: int = 0) -> None:
    safe_steps = list(steps)
    cards = []
    for index, step in enumerate(safe_steps):
        state = "done" if index < active_index else "active" if index == active_index else "pending"
        symbol = "✓" if state == "done" else str(index + 1)
        cards.append(
            f'<div class="ms-process-step {state}"><b>{symbol}</b><span>{escape(step)}</span></div>'
        )
    st.markdown(f'<div class="ms-process-steps">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_error_state(title: str, message: str, hint: str | None = None) -> None:
    hint_html = f'<small>{escape(hint)}</small>' if hint else ""
    st.markdown(
        f"""
        <div class="ms-error-state">
          <div class="ms-error-icon">!</div>
          <div><strong>{escape(title)}</strong><p>{escape(message)}</p>{hint_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def toast_once(key: str, message: str, icon: str = "✅") -> None:
    session_key = f"ux_toast_{key}"
    if not st.session_state.get(session_key):
        st.toast(message, icon=icon)
        st.session_state[session_key] = True
