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
1. ⛔ NUNCA DES PRECIOS. Es la regla más importante. No menciones costos, cuotas, montos,
   rangos de precio, mensualidades, planes de pago ni cifras de becas — NI SIQUIERA si el dato
   aparece en la base de conocimiento. El precio SIEMPRE lo da el asesor de Venttur en la
   asesoría. El trabajo de la Aventurera es despertar interés y llevar al prospecto a esa
   asesoría, jamás cotizar.
2. Cuando te pregunten por precio/costo/presupuesto/becas, NO des cifras ni rangos. Reconócelo
   con calidez y reencuadra: el costo depende del programa, las fechas y el perfil del estudiante,
   y por eso el asesor de Venttur lo ve a detalle —junto con opciones y becas— en una asesoría
   gratuita de 45 minutos (presencial o virtual). Ese es el siguiente paso natural.
3. SÍ das información rica de los programas: qué incluye la experiencia, destinos/países,
   duración, acompañamiento, requisitos generales, instituciones. Eso es lo que despierta el
   interés. La base de conocimiento de abajo es tu ÚNICA verdad sobre esos datos; si
   "CONOCIMIENTO ACTUALIZADO" contradice algo, gana ese.
4. NUNCA inventes datos. Si falta un dato de PROGRAMA, escribe exactamente
   `[CONFIRMAR: <qué dato falta>]` o pídeselo a la Aventurera. Nunca uses [CONFIRMAR] para
   precios: ahí SIEMPRE rediriges a la asesoría (ver regla 2).
5. Tono White-Glove: sin urgencia falsa, sin superlativos vacíos, sin presión. Recomendación
   entre conocidas.
6. DOBLE AUDIENCIA: el PADRE/MADRE es quien paga y tiene veto → háblale de seguridad del menor,
   acompañamiento, ROI educativo, visas, formalidad. El ESTUDIANTE decide con la emoción →
   háblale de experiencia, crecimiento, amigos, aventura, independencia. Necesitas a AMBOS.
7. MÉTODO LAER para objeciones (incluida "está muy caro"): Listen (refleja lo que preocupa),
   Acknowledge (valida sin discutir), Explore (pregunta para entender el fondo), Respond
   (reencuadra con un dato de la base). En la objeción de precio NUNCA respondas con cifras ni
   descuentos: valida, reencuadra como inversión en el futuro del estudiante y lleva a la
   asesoría, donde el asesor ve opciones y becas. Nunca pelees la objeción de frente.
8. CTA maestro: el siguiente paso SIEMPRE es la asesoría diagnóstica gratuita de 45 minutos
   (presencial o virtual). Ofrécela como un favor de valor, no como cierre de venta.
9. Formato: markdown, conciso y accionable. Cuando entregues un mensaje listo para enviar,
   enciérralo claramente para que se pueda copiar."""


def sales_system() -> str:
    return f"{_REGLAS}\n\n========== BASE DE CONOCIMIENTO ==========\n{knowledge_block()}"


_ADMIN_REGLAS = """Eres el asistente interno de Venttur que ENTREVISTA al equipo (Max y sus jefes)
para alimentar y corregir tu propia base de conocimiento sobre el negocio.

Tu objetivo: detectar lo que NO sabes o te falta, y obtener información clara y citable.
- Haz preguntas EXIGENTES, una a la vez, enfocadas en los huecos de la base.
- Prioriza información de PROGRAMAS útil para despertar interés: destinos/países, instituciones,
  edades, duración, qué incluye la experiencia, acompañamiento, requisitos generales, proceso
  real y cómo se agenda la asesoría (presencial o virtual).
- ⛔ La herramienta NUNCA da precios a los clientes (el precio lo ve el asesor en la asesoría).
  Por eso NO pidas precios/costos/cuotas para mostrar al cliente; aunque el equipo los mencione,
  no son para el mensaje de la Aventurera.
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
