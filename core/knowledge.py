"""Carga el conocimiento SEMILLA (archivos knowledge/*.md)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
_FILES = ["empresa.md", "programas.md", "ecosistemas_educativos.md", "tono_aventurera.md",
          "objeciones.md", "proceso.md", "marca.md"]


@st.cache_data(ttl=300, show_spinner=False)
def load_seed() -> str:
    """Concatena los .md semilla en un solo bloque de texto."""
    parts = []
    for name in _FILES:
        p = _KNOWLEDGE_DIR / name
        if p.exists():
            parts.append(f"## {name}\n{p.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(parts)
