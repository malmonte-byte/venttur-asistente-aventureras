"""Conexión con Claude + construcción de los system prompts.

Modelo: claude-opus-4-8 (regla del molde Venttur).
"""
from __future__ import annotations

import streamlit as st

from core import knowledge, sources
from utils import kb_store

MODEL = "claude-opus-4-8"


class AssistantError(Exception):
    """Error amigable para mostrar en la UI (p. ej. falta API key)."""


def _client():
    try:
        key = str(st.secrets.get("ANTHROPIC_API_KEY", ""))
    except Exception:
        key = ""
    if not key:
        raise AssistantError(
            "Falta configurar `ANTHROPIC_API_KEY` en los Secrets para que la IA responda."
        )
    import anthropic

    return anthropic.Anthropic(api_key=key)


# --------------------------------------------------------------------------- #
#  Bloque de conocimiento (3 capas, en orden de precedencia)
# --------------------------------------------------------------------------- #
def knowledge_block() -> str:
    vivo = kb_store.approved_knowledge_text()
    semilla = knowledge.load_seed()
    pdfs = sources.load_sources()
    bloques = []
    if vivo:
        bloques.append("=== CONOCIMIENTO ACTUALIZADO (máxima prioridad) ===\n" + vivo)
    if semilla:
        bloques.append("=== CONOCIMIENTO BASE ===\n" + semilla)
    if pdfs:
        bloques.append("=== FUENTES (PDFs de respaldo) ===\n" + pdfs[:60000])
    return "\n\n".join(bloques) if bloques else "(La base de conocimiento aún está vacía.)"


# --------------------------------------------------------------------------- #
#  System prompts
# --------------------------------------------------------------------------- #
_REGLAS = """Eres el copiloto de las "Aventureras" de Venttur (agencia premium de educación
internacional). Tu trabajo es que la Aventurera quede como una conocida bien informada que
RECOMIENDA algo valioso — NUNCA como una vendedora. Escribe en español de México, cálido y premium.

REGLAS NO NEGOCIABLES:
1. La base de conocimiento de abajo es tu ÚNICA verdad sobre programas, precios, requisitos,
   instituciones, becas y fechas. Si "CONOCIMIENTO ACTUALIZADO" contradice algo, gana ese.
2. NUNCA inventes datos. Si un dato no está en la base, escribe exactamente
   `[CONFIRMAR: <qué dato falta>]` en el lugar donde iría, o pídeselo a la Aventurera.
   Es preferible un mensaje con [CONFIRMAR] que un dato inventado.
3. Tono White-Glove: sin urgencia falsa, sin superlativos vacíos, sin presión. Recomendación
   entre conocidas.
4. DOBLE AUDIENCIA: el PADRE/MADRE es quien paga y tiene veto → háblale de seguridad del menor,
   acompañamiento, ROI educativo, visas, formalidad. El ESTUDIANTE decide con la emoción →
   háblale de experiencia, crecimiento, amigos, aventura, independencia. Necesitas a AMBOS.
5. MÉTODO LAER para objeciones: Listen (refleja lo que preocupa), Acknowledge (valida sin
   discutir), Explore (pregunta para entender el fondo), Respond (responde con un dato de la
   base + un reencuadre). Nunca pelees la objeción de frente.
6. CTA maestro: el siguiente paso SIEMPRE es la asesoría diagnóstica gratuita de 45 minutos.
   Ofrécela como un favor de valor, no como cierre de venta.
7. Formato: markdown, conciso y accionable. Cuando entregues un mensaje listo para enviar,
   enciérralo claramente para que se pueda copiar."""


def sales_system() -> str:
    return f"{_REGLAS}\n\n========== BASE DE CONOCIMIENTO ==========\n{knowledge_block()}"


_ADMIN_REGLAS = """Eres el asistente interno de Venttur que ENTREVISTA al equipo (Max y sus jefes)
para alimentar y corregir tu propia base de conocimiento sobre el negocio.

Tu objetivo: detectar lo que NO sabes o te falta, y obtener información clara y citable.
- Haz preguntas EXIGENTES, una a la vez, enfocadas en los huecos de la base.
- Prioriza datos duros que hoy faltan o están como [CONFIRMAR]: precios/rangos, requisitos,
  países e instituciones, fechas, becas, comisiones de Aventureras, proceso real.
- Cuando obtengas información nueva y concreta, PROPÓN una entrada estructurada así, en un bloque:
      CATEGORÍA: <programa o tema>
      TEMA: <título corto>
      CONTENIDO: <el dato, redactado claro y citable>
  y pide confirmación antes de darla por buena. No inventes; si algo no te queda claro, pregunta.
Tono: profesional, directo, colaborador. Español de México."""


def admin_interview_system() -> str:
    return f"{_ADMIN_REGLAS}\n\n========== BASE DE CONOCIMIENTO ACTUAL ==========\n{knowledge_block()}"


# --------------------------------------------------------------------------- #
#  Llamadas a Claude
# --------------------------------------------------------------------------- #
def chat(messages: list[dict], system: str, max_tokens: int = 3000) -> str:
    """messages = [{'role':'user'|'assistant', 'content': str}, ...] → texto del asistente."""
    client = _client()
    try:
        resp = client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=system, messages=messages,
        )
    except Exception as e:  # noqa: BLE001
        raise AssistantError(f"Error al consultar a la IA: {e}") from e
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def complete(system: str, user: str, max_tokens: int = 3000) -> str:
    """Atajo de un solo turno."""
    return chat([{"role": "user", "content": user}], system, max_tokens=max_tokens)
