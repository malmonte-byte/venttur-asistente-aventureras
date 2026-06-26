"""Base de datos de Boarding Schools — SOLO LECTURA.

Lee una Google Sheet externa (BOARDING_SHEET_ID) y la entrega como texto compacto para
inyectarla al conocimiento. NUNCA escribe en esa hoja. Si no está configurada o no se puede
leer (no compartida con la cuenta de servicio), devuelve "" sin romper la app.
"""
from __future__ import annotations

import streamlit as st

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
_MAX_CHARS = 300000  # tope de seguridad; avisa si trunca

# ⛔ Columnas que NUNCA entran al conocimiento de la IA (precios) + ruido (timestamp).
# La herramienta jamás da precios; el costo lo ve el asesor en la cita.
_EXCLUDE = {
    "Marca temporal",
    "INTERNATIONAL BOARDING TUITION + FEES",
    "PLEASE SELECT THE CURRENCY OF YOUR TUITION + FEES",
}


# ID de la hoja de Boarding Schools. NO es una credencial: el acceso lo controla con quién está
# compartida la hoja (solo la cuenta de servicio, como Lector). Por eso puede ir por defecto en el
# código y así no depende de configurar un secret. Un secret BOARDING_SHEET_ID lo puede sobrescribir.
_DEFAULT_SHEET_ID = "1k2fiP24N9OO_wM8O7N7CHJ_wIcJDHlKeRptvKUSgCNo"


def _sheet_id() -> str:
    try:
        return str(st.secrets.get("BOARDING_SHEET_ID", "") or _DEFAULT_SHEET_ID).strip()
    except Exception:
        return _DEFAULT_SHEET_ID


@st.cache_data(ttl=600, show_spinner=False)
def load_boarding(_v: int = 2) -> str:
    sheet_id = _sheet_id()
    if not sheet_id:
        return ""
    try:
        if "gcp_service_account" not in st.secrets:
            return ""
        import gspread
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=_SCOPES
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1  # primera pestaña
        rows = ws.get_all_records()
    except Exception:
        return ""  # no compartida / sin acceso / error de red → silencioso

    if not rows:
        return ""

    headers = [h for h in rows[0].keys() if h not in _EXCLUDE]
    lines = []
    size = 0
    truncated = False
    for r in rows:
        cells = [f"{k}: {r[k]}" for k in headers if str(r.get(k, "")).strip()]
        if not cells:
            continue
        line = "- " + " · ".join(cells)
        if size + len(line) > _MAX_CHARS:
            truncated = True
            break
        lines.append(line)
        size += len(line)

    total = len(rows)
    shown = len(lines)
    header = (
        f"Catálogo interno de {shown} de {total} boarding schools (solo lectura). "
        "⛔ NO incluye precios a propósito: el costo lo ve el asesor en la cita. "
        "Úsalo para emparejar al estudiante con escuelas que encajen (país, idioma, diploma, "
        "deportes, perfil) y así justificar agendar la cita."
    )
    if truncated:
        header += " — lista recortada por tamaño; filtra por país/perfil o deriva a la cita."
    return header + "\n" + "\n".join(lines)
