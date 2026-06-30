"""Exporta TODO el conocimiento de la herramienta a un Google Doc (on-demand).

La Consola tiene un botón que llama a `regenerate()`: arma el documento (reglas + semilla +
entradas vivas + huecos + catálogo de boarding) y reescribe el Google Doc destino.

Usa la MISMA cuenta de servicio que ya lee Sheets (no agrega credenciales nuevas), pero con
scope de Docs/Drive. Requisito de una sola vez (ver mensaje de error si falla):
  1. Habilitar la Google Docs API en el proyecto de la cuenta de servicio.
  2. Compartir el documento como *Editor* con el client_email de la cuenta de servicio.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

from core import assistant, boarding
from utils import kb_store

# Documento destino (NO es secreto: el acceso lo controla con quién está compartido).
# Un secret KB_DOC_ID lo puede sobrescribir.
_DEFAULT_DOC_ID = "1etZniSj0rSHFecOLPh_UetDQ3r1kvKKyUzj-G0EU8yI"
_SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]
_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
_TZ = timezone(timedelta(hours=-6))  # CDMX


class DocExportError(Exception):
    """Error amigable para mostrar en la Consola."""


def doc_id() -> str:
    try:
        return str(st.secrets.get("KB_DOC_ID", "") or _DEFAULT_DOC_ID).strip()
    except Exception:
        return _DEFAULT_DOC_ID


def doc_url() -> str:
    return f"https://docs.google.com/document/d/{doc_id()}/edit"


def service_account_email() -> str:
    try:
        return str(st.secrets["gcp_service_account"].get("client_email", "(desconocido)"))
    except Exception:
        return "(no configurado)"


# --------------------------------------------------------------------------- #
#  Armado del texto (limpio, sin símbolos de markdown)
# --------------------------------------------------------------------------- #
def _clean_md(md: str, drop_title: bool = True) -> str:
    out: list[str] = []
    for ln in md.splitlines():
        s = ln.rstrip()
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            level, txt = len(m.group(1)), m.group(2).strip().replace("**", "").replace("`", "")
            if level == 1:
                if drop_title:
                    continue
                out.append(txt.upper())
            elif level == 2:
                out += ["", "● " + txt]
            else:
                out.append("   ▸ " + txt)
            continue
        s = re.sub(r"^(\s*)[-*+]\s+", lambda mm: mm.group(1) + "• ", s)
        s = re.sub(r"^>\s?", "", s)
        s = s.replace("**", "").replace("`", "")
        out.append(s)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _H(title: str) -> str:
    bar = "═" * 64
    return f"\n\n{bar}\n{title.upper()}\n{bar}\n"


def _read(name: str) -> str:
    p = _KNOWLEDGE_DIR / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def build_text() -> str:
    """Ensambla todo el conocimiento vigente en un solo texto."""
    fecha = datetime.now(_TZ).strftime("%Y-%m-%d %H:%M")
    parts: list[str] = []

    parts.append(
        "VENTTUR · BASE DE CONOCIMIENTO DEL ASISTENTE DE AVENTURERAS\n"
        f"Documento regenerado automáticamente desde la herramienta el {fecha} (CDMX).\n\n"
        "Contiene TODO lo que el Asistente de Aventureras tiene cargado sobre Venttur:\n"
        "las reglas con las que opera, el conocimiento base (semilla), las entradas vivas\n"
        "aprobadas por el equipo (Google Sheets), los pendientes por confirmar y el\n"
        "catálogo completo de boarding schools.\n\n"
        "⛔ Nota clave: la herramienta NUNCA da precios; siempre deriva a la asesoría gratis."
    )

    reglas = assistant._REGLAS.replace("**", "").replace("`", "")
    admin = assistant._ADMIN_REGLAS.replace("**", "").replace("`", "")
    parts.append(_H("0 · Cómo opera la IA — reglas no negociables"))
    parts.append("Instrucciones permanentes del copiloto de ventas (modo Aventurera):\n\n" + reglas)
    parts.append("\n\nInstrucciones del modo Consola de Conocimiento (entrevista al equipo):\n\n" + admin)

    secciones = [
        ("1 · Empresa", "empresa.md"),
        ("2 · Marca", "marca.md"),
        ("3 · Programas", "programas.md"),
        ("4 · Ecosistemas educativos (países y currículos)", "ecosistemas_educativos.md"),
        ("5 · Perfil del cliente premium", "perfil_cliente.md"),
        ("6 · Proceso, rol de la Aventurera y la cita", "proceso.md"),
        ("7 · Tono de la Aventurera y persuasión", "tono_aventurera.md"),
        ("8 · Objeciones y situaciones difíciles (LAER)", "objeciones.md"),
    ]
    for titulo, archivo in secciones:
        parts.append(_H(titulo))
        parts.append(_clean_md(_read(archivo)))

    # Conocimiento vivo aprobado
    aprob = kb_store.list_entries(estado="aprobado")
    parts.append(_H("9 · Conocimiento vivo aprobado (Google Sheets)"))
    if aprob:
        parts.append(f"Entradas aprobadas por el equipo y en uso por la IA ({len(aprob)}):\n")
        for e in aprob:
            parts.append(
                f"\n● [{e.get('categoria','')}] {e.get('tema','')}\n"
                f"{str(e.get('contenido','')).strip()}\n"
                f"   (actualizado por {e.get('actualizado_por','')} · {e.get('fecha','')})"
            )
    else:
        parts.append("(Sin entradas vivas aprobadas todavía.)")

    # Huecos abiertos
    gaps = kb_store.list_gaps("abierto")
    parts.append(_H("10 · Pendientes por confirmar (huecos abiertos)"))
    if gaps:
        parts.append("Preguntas reales que la IA no supo responder con certeza; el equipo debe llenarlas:\n")
        for g in gaps:
            parts.append(
                f"\n• {str(g.get('pregunta','')).strip()}\n"
                f"   (detectado por {g.get('detectado_por','')} · {g.get('fecha','')})"
            )
    else:
        parts.append("🎉 No hay huecos abiertos.")

    # Apéndice: catálogo de boarding schools
    cat = boarding.load_boarding() or "(Catálogo de boarding schools no disponible.)"
    parts.append(_H("Apéndice A · Catálogo de Boarding Schools (solo lectura)"))
    parts.append(re.sub(r"^- ", "• ", cat, flags=re.M))

    return "\n".join(parts).strip() + "\n"


# --------------------------------------------------------------------------- #
#  Escritura en el Google Doc (API REST + cuenta de servicio)
# --------------------------------------------------------------------------- #
def _token() -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials
    except Exception as e:  # noqa: BLE001
        raise DocExportError(f"Faltan librerías de Google ({e}).") from e
    if "gcp_service_account" not in st.secrets:
        raise DocExportError("No hay cuenta de servicio configurada (`gcp_service_account`).")
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=_SCOPES)
    creds.refresh(Request())
    return creds.token


def _api(method: str, url: str, tk: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tk)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _utf16_len(s: str) -> int:
    """Longitud en unidades UTF-16 (así indexa la Docs API)."""
    return len(s.encode("utf-16-le")) // 2


def _explain(code: int, res: dict) -> str:
    sa = service_account_email()
    msg = str(res.get("error", {}).get("message", res))[:300]
    if code in (403, 404):
        return (
            "No pude escribir el documento. Para que la herramienta lo actualice, falta (una sola vez):\n"
            "1) Habilitar la **Google Docs API** en el proyecto de la cuenta de servicio.\n"
            f"2) Compartir el documento como **Editor** con: `{sa}`\n\n"
            f"(Detalle técnico {code}: {msg})"
        )
    return f"Error al actualizar el documento ({code}): {msg}"


def regenerate() -> str:
    """Reconstruye el Google Doc con el conocimiento vigente. Devuelve la URL."""
    # Datos frescos (ignora cachés)
    try:
        st.cache_data.clear()
    except Exception:  # noqa: BLE001
        pass

    text = build_text()
    did = doc_id()
    tk = _token()

    # 1) Leer el doc para conocer su rango actual
    code, doc = _api("GET", f"https://docs.googleapis.com/v1/documents/{did}", tk)
    if code != 200:
        raise DocExportError(_explain(code, doc))

    end = doc["body"]["content"][-1]["endIndex"] - 1

    # 2) Vaciar el contenido actual (si lo hay)
    if end > 1:
        code, r = _api(
            "POST", f"https://docs.googleapis.com/v1/documents/{did}:batchUpdate", tk,
            {"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end}}}]},
        )
        if code != 200:
            raise DocExportError(_explain(code, r))

    # 3) Insertar el texto nuevo por bloques (índice en unidades UTF-16, sin drift)
    CHUNK = 40000
    idx = 1
    for i in range(0, len(text), CHUNK):
        chunk = text[i:i + CHUNK]
        code, r = _api(
            "POST", f"https://docs.googleapis.com/v1/documents/{did}:batchUpdate", tk,
            {"requests": [{"insertText": {"location": {"index": idx}, "text": chunk}}]},
        )
        if code != 200:
            raise DocExportError(_explain(code, r))
        idx += _utf16_len(chunk)

    return doc_url()
