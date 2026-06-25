"""Carga texto de los PDFs de respaldo en fuentes/ (opcional)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

_FUENTES_DIR = Path(__file__).resolve().parent.parent / "fuentes"


@st.cache_data(ttl=600, show_spinner=False)
def load_sources() -> str:
    """Extrae y concatena el texto de todos los PDFs en fuentes/. Vacío si no hay."""
    if not _FUENTES_DIR.exists():
        return ""
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    parts = []
    for pdf in sorted(_FUENTES_DIR.glob("*.pdf")):
        try:
            reader = PdfReader(str(pdf))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                parts.append(f"=== FUENTE: {pdf.stem} ===\n{text.strip()}")
        except Exception:
            continue
    return "\n\n".join(parts)
