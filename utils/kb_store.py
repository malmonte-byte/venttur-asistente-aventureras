"""Base de conocimiento VIVA del Asistente de Aventureras.

Guarda dos colecciones:
  - "conocimiento": entradas curadas por los admins (lo que alimenta a la IA).
  - "huecos": preguntas que la IA no supo responder ([CONFIRMAR]) para que los
    admins las llenen.

Backend:
  - Google Sheets (si KB_SHEET_ID + [gcp_service_account] están en Secrets).
  - Respaldo LOCAL en data/kb_local.json si no hay Sheets (para probar; NO
    persiste en Streamlit Cloud).

Todas las funciones fallan en silencio (no rompen la UI) y registran un aviso.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

_TZ = timezone(timedelta(hours=-6))  # CDMX
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LOCAL_FILE = _DATA_DIR / "kb_local.json"

KB_HEADERS = ["id", "categoria", "tema", "contenido", "estado", "fuente", "actualizado_por", "fecha"]
GAP_HEADERS = ["id", "pregunta", "contexto", "detectado_por", "estado", "fecha"]


# --------------------------------------------------------------------------- #
#  Utilidades
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%d %H:%M")


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(_TZ).strftime('%y%m%d%H%M%S')}-{random.randint(100, 999)}"


def backend() -> str:
    """'sheets' si está configurado Google Sheets; si no, 'local'."""
    try:
        if str(st.secrets.get("KB_SHEET_ID", "")) and "gcp_service_account" in st.secrets:
            return "sheets"
    except Exception:
        pass
    return "local"


# --------------------------------------------------------------------------- #
#  Backend: Google Sheets
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def _spreadsheet():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(str(st.secrets["KB_SHEET_ID"]))


def _worksheet(name: str, headers: list[str]):
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(name)
    except Exception:
        ws = sh.add_worksheet(title=name, rows=200, cols=max(8, len(headers)))
        ws.append_row(headers)
    return ws


# --------------------------------------------------------------------------- #
#  Backend: local JSON
# --------------------------------------------------------------------------- #
def _local_load() -> dict:
    if _LOCAL_FILE.exists():
        try:
            return json.loads(_LOCAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"conocimiento": [], "huecos": []}


def _local_save(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _LOCAL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Lectura (cacheada)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=20, show_spinner=False)
def _load_all() -> dict:
    """Devuelve {'conocimiento': [...], 'huecos': [...]} desde el backend activo."""
    if backend() == "sheets":
        try:
            con = _worksheet("conocimiento", KB_HEADERS).get_all_records()
            gaps = _worksheet("huecos", GAP_HEADERS).get_all_records()
            return {"conocimiento": con, "huecos": gaps}
        except Exception as e:  # noqa: BLE001
            st.warning(f"No se pudo leer Google Sheets ({e}). Usando datos vacíos.")
            return {"conocimiento": [], "huecos": []}
    return _local_load()


def _refresh() -> None:
    _load_all.clear()


# --------------------------------------------------------------------------- #
#  API pública — Conocimiento
# --------------------------------------------------------------------------- #
def list_entries(estado: str | None = None, include_archived: bool = False) -> list[dict]:
    rows = list(_load_all().get("conocimiento", []))
    out = []
    for r in rows:
        est = str(r.get("estado", "")).strip().lower()
        if not include_archived and est == "archivado":
            continue
        if estado and est != estado:
            continue
        out.append(r)
    return out


def add_entry(categoria: str, tema: str, contenido: str,
              actualizado_por: str, estado: str = "aprobado", fuente: str = "consola") -> dict:
    row = {
        "id": _gen_id("k"), "categoria": categoria.strip(), "tema": tema.strip(),
        "contenido": contenido.strip(), "estado": estado, "fuente": fuente,
        "actualizado_por": actualizado_por, "fecha": _now(),
    }
    try:
        if backend() == "sheets":
            _worksheet("conocimiento", KB_HEADERS).append_row([row[h] for h in KB_HEADERS])
        else:
            data = _local_load()
            data.setdefault("conocimiento", []).append(row)
            _local_save(data)
        _refresh()
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo guardar la entrada: {e}")
    return row


def update_entry(entry_id: str, **fields) -> bool:
    """Actualiza contenido/categoria/tema/estado de una entrada por id."""
    fields = {k: v for k, v in fields.items() if k in KB_HEADERS}
    try:
        if backend() == "sheets":
            ws = _worksheet("conocimiento", KB_HEADERS)
            records = ws.get_all_records()
            for i, r in enumerate(records):
                if str(r.get("id")) == entry_id:
                    r.update(fields)
                    r["actualizado_por"] = fields.get("actualizado_por", r.get("actualizado_por", ""))
                    r["fecha"] = _now()
                    ws.update(f"A{i + 2}:H{i + 2}", [[r.get(h, "") for h in KB_HEADERS]])
                    _refresh()
                    return True
            return False
        else:
            data = _local_load()
            for r in data.get("conocimiento", []):
                if str(r.get("id")) == entry_id:
                    r.update(fields)
                    r["fecha"] = _now()
                    _local_save(data)
                    _refresh()
                    return True
            return False
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo actualizar la entrada: {e}")
        return False


# --------------------------------------------------------------------------- #
#  API pública — Huecos (preguntas sin responder)
# --------------------------------------------------------------------------- #
def list_gaps(estado: str | None = "abierto") -> list[dict]:
    rows = list(_load_all().get("huecos", []))
    if estado is None:
        return rows
    return [r for r in rows if str(r.get("estado", "")).strip().lower() == estado]


def add_gap(pregunta: str, contexto: str = "", detectado_por: str = "") -> None:
    row = {
        "id": _gen_id("h"), "pregunta": pregunta.strip()[:500], "contexto": contexto.strip()[:500],
        "detectado_por": detectado_por, "estado": "abierto", "fecha": _now(),
    }
    try:
        if backend() == "sheets":
            _worksheet("huecos", GAP_HEADERS).append_row([row[h] for h in GAP_HEADERS])
        else:
            data = _local_load()
            data.setdefault("huecos", []).append(row)
            _local_save(data)
        _refresh()
    except Exception:  # noqa: BLE001 — nunca romper la UX por el registro de un hueco
        pass


def resolve_gap(gap_id: str) -> bool:
    try:
        if backend() == "sheets":
            ws = _worksheet("huecos", GAP_HEADERS)
            records = ws.get_all_records()
            for i, r in enumerate(records):
                if str(r.get("id")) == gap_id:
                    r["estado"] = "resuelto"
                    ws.update(f"A{i + 2}:F{i + 2}", [[r.get(h, "") for h in GAP_HEADERS]])
                    _refresh()
                    return True
            return False
        else:
            data = _local_load()
            for r in data.get("huecos", []):
                if str(r.get("id")) == gap_id:
                    r["estado"] = "resuelto"
                    _local_save(data)
                    _refresh()
                    return True
            return False
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
#  Texto del conocimiento aprobado (para inyectar al system prompt)
# --------------------------------------------------------------------------- #
def approved_knowledge_text() -> str:
    entries = list_entries(estado="aprobado")
    if not entries:
        return ""
    parts = []
    for e in entries:
        cat = e.get("categoria", "general")
        tema = e.get("tema", "")
        parts.append(f"### [{cat}] {tema}\n{e.get('contenido', '')}")
    return "\n\n".join(parts)
