from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st


FRONTEND_DIR = Path(__file__).resolve().parents[1]
STYLES_PATH = FRONTEND_DIR / "assets" / "styles.css"
LOGO_DIR = FRONTEND_DIR / "assets" / "logo"


def apply_custom_theme() -> None:
    """Load the Phase 9 visual system from the shared stylesheet."""
    if not STYLES_PATH.exists():
        st.warning(f"Stylesheet not found: {STYLES_PATH}")
        return
    css = STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def find_logo(*names: str) -> Optional[Path]:
    """Return the first matching logo asset, if the user has added it."""
    for name in names:
        path = LOGO_DIR / name
        if path.exists():
            return path
    return None


def image_data_uri(path: Path) -> str:
    """Convert a local PNG/JPG/SVG file to an embeddable data URI."""
    suffix = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_sidebar_brand() -> None:
    """Render the logo area with a safe fallback when assets are missing."""
    logo = find_logo(
        "medisimplify_icon.png",
        "favicon.png",
        "app_icon_512.png",
    )
    image = (
        f'<img class="ms-sidebar-logo" src="{image_data_uri(logo)}" alt="MediSimplify AI">'
        if logo
        else '<div class="ms-sidebar-logo" style="display:grid;place-items:center;font-size:1.7rem">🩺</div>'
    )
    st.markdown(
        f"""<div class="ms-sidebar-brand">{image}<div><div class="ms-sidebar-name">MediSimplify AI</div><div class="ms-sidebar-phase">Phase 9 · Frontend Enhancement</div></div></div>""",
        unsafe_allow_html=True,
    )


def render_dashboard_hero() -> None:
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    st.markdown(
        f"""<section class="ms-hero"><div class="ms-kicker">AI-powered medical report companion</div><h1>{greeting}. Understand your health. <span>Simply.</span></h1><p>Upload a blood report, prescription or radiology report, review the extracted text, and ask questions naturally using text or voice—in English, Hindi or Punjabi.</p><div class="ms-feature-row"><span class="ms-chip">✓ Multilingual explanations</span><span class="ms-chip">✓ Grandma Mode</span><span class="ms-chip">✓ Voice assistant</span><span class="ms-chip">✓ Report-aware RAG</span></div></section>""",
        unsafe_allow_html=True,
    )


def render_dashboard_stats(api_online: bool, provider_count: int = 3) -> None:
    online_value = "Online" if api_online else "Offline"
    online_class = "ms-online" if api_online else ""
    st.markdown(
        f"""<div class="ms-stat-grid">
        <div class="ms-stat-card"><div class="ms-stat-top"><span class="ms-stat-label">REPORT TYPES</span><span class="ms-stat-icon">📄</span></div><div class="ms-stat-value">3</div><div class="ms-stat-note">Blood, prescription & radiology</div></div>
        <div class="ms-stat-card"><div class="ms-stat-top"><span class="ms-stat-label">LANGUAGES</span><span class="ms-stat-icon">🌍</span></div><div class="ms-stat-value">3</div><div class="ms-stat-note">English, Hindi & Punjabi</div></div>
        <div class="ms-stat-card"><div class="ms-stat-top"><span class="ms-stat-label">AI PROVIDERS</span><span class="ms-stat-icon">🤖</span></div><div class="ms-stat-value">{provider_count}</div><div class="ms-stat-note">Gemini, Groq & Ollama</div></div>
        <div class="ms-stat-card"><div class="ms-stat-top"><span class="ms-stat-label">SYSTEM STATUS</span><span class="ms-stat-icon">〽️</span></div><div class="ms-stat-value {online_class}">{online_value}</div><div class="ms-stat-note">FastAPI backend connection</div></div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="ms-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ms-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def render_upload_header() -> None:
    """Render the visual heading and format guide for the report uploader."""
    st.markdown(
        """
        <div class="ms-upload-header">
            <div class="ms-upload-icon">⇧</div>
            <div>
                <span class="ms-step-pill">STEP 1 · UPLOAD</span>
                <h2>Add your medical report</h2>
                <p>
                    Upload a document or take a clear photo. Your report will be
                    extracted first, then shown for mandatory review.
                </p>
            </div>
        </div>
        <div class="ms-format-row">
            <span>PDF</span><span>DOCX</span><span>TXT</span>
            <span>JPG</span><span>PNG</span><span>WEBP</span>
            <small>Maximum 5 MB</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_selected_file(filename: str, size_bytes: int, content_type: str) -> None:
    """Render a compact selected-file summary card."""
    size_kb = size_bytes / 1024
    size_text = f"{size_kb / 1024:.2f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"
    extension = Path(filename).suffix.replace(".", "").upper() or "FILE"
    st.markdown(
        f"""
        <div class="ms-selected-file">
            <div class="ms-file-icon">📄</div>
            <div class="ms-file-copy">
                <strong>{filename}</strong>
                <span>{extension} · {size_text} · {content_type or 'medical document'}</span>
            </div>
            <div class="ms-file-ready">READY</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """<div class="ms-footer"><strong>MediSimplify AI</strong> · Educational medical report assistant<br>This application does not replace diagnosis or advice from a qualified healthcare professional.</div>""",
        unsafe_allow_html=True,
    )
