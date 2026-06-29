"""Consola de Conocimiento (rol admin): alimentar y corregir a la IA.

4 modos: Entrevista · Corregir · Cola de huecos · Revisar/Aprobar.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from core import assistant
from utils import kb_store


def _badge_backend():
    b = kb_store.backend()
    if b == "sheets":
        st.caption("🟢 Conocimiento guardado en Google Sheets (persistente).")
    else:
        st.caption("🟡 Modo local de prueba: el conocimiento se guarda en `data/kb_local.json` "
                   "y NO persiste en la nube. Configura `KB_SHEET_ID` + cuenta de servicio para producción.")


# --------------------------------------------------------------------------- #
#  Mascota — Tierra con cara (SVG + CSS, sin librerías extra)
#  Le da identidad visual al asistente. 3 estados:
#    · idle     → flota, parpadea, saluda, el anillo (atmósfera) gira
#    · thinking → burbuja de pensamiento con puntitos (mientras la IA responde)
#    · saving   → abre la "tapa" de su cabeza, saca el cerebro, lo limpia con
#                 destellos y lo vuelve a guardar (cuando guarda en memoria)
#  Se renderiza con components.html (iframe aislado) para que el CSS corra bien.
# --------------------------------------------------------------------------- #
_MASCOTA_HEIGHT = 270


def _mascota_html(state: str = "idle") -> str:
    return f"""
<div class="vt-mascota">
  <style>
    html,body{{margin:0;background:transparent;overflow:hidden;}}
    .vt-mascota{{display:flex;justify-content:center;align-items:flex-start;}}
    .vt-planet{{width:228px;height:auto;display:block;animation:vt-float 4.5s ease-in-out infinite;}}
    @keyframes vt-float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-10px)}}}}

    /* atmósfera que orbita */
    .vt-ring{{transform-box:view-box;transform-origin:100px 146px;animation:vt-spin 16s linear infinite;}}
    @keyframes vt-spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}

    /* parpadeo (siempre) */
    .vt-eye{{transform-box:fill-box;transform-origin:center;animation:vt-blink 5s infinite;}}
    @keyframes vt-blink{{0%,93%,100%{{transform:scaleY(1)}}96%{{transform:scaleY(.1)}}}}

    /* saludo con manitas (solo idle) */
    .vt-hand-l{{transform-box:view-box;transform-origin:44px 154px;}}
    .vt-hand-r{{transform-box:view-box;transform-origin:156px 154px;}}
    .state-idle .vt-hand-l{{animation:vt-wave-l 3.2s ease-in-out infinite;}}
    .state-idle .vt-hand-r{{animation:vt-wave-r 3.2s ease-in-out infinite;}}
    @keyframes vt-wave-l{{0%,100%{{transform:rotate(0deg)}}50%{{transform:rotate(-20deg)}}}}
    @keyframes vt-wave-r{{0%,100%{{transform:rotate(0deg)}}50%{{transform:rotate(20deg)}}}}

    /* pensando: burbuja con puntitos */
    .vt-think{{opacity:0;transition:opacity .25s;}}
    .state-thinking .vt-think{{opacity:1;}}
    .vt-dot{{transform-box:fill-box;transform-origin:center;animation:vt-dot 1.3s ease-in-out infinite;}}
    .vt-dot.d2{{animation-delay:.18s;}} .vt-dot.d3{{animation-delay:.36s;}}
    @keyframes vt-dot{{0%,75%,100%{{transform:translateY(0);opacity:.45}}38%{{transform:translateY(-5px);opacity:1}}}}

    /* guardando en memoria: tapa + cerebro + destellos (una sola vez) */
    .vt-brain{{opacity:0;}}
    .vt-lid{{transform-box:view-box;transform-origin:100px 118px;}}
    .vt-spark{{transform-box:fill-box;transform-origin:center;opacity:0;}}
    .state-saving .vt-brain{{animation:vt-extract 4.4s ease-in-out forwards;}}
    .state-saving .vt-lid{{animation:vt-lid 4.4s ease-in-out forwards;}}
    .state-saving .vt-spark{{animation:vt-twinkle 4.4s ease-in-out forwards;}}
    .state-saving .vt-spark.s2{{animation-delay:.25s;}}
    .state-saving .vt-spark.s3{{animation-delay:.5s;}}
    @keyframes vt-lid{{
      0%{{transform:translateY(0) rotate(0)}}
      11%{{transform:translateY(-18px) rotate(-12deg)}}
      72%{{transform:translateY(-18px) rotate(-12deg)}}
      88%,100%{{transform:translateY(0) rotate(0)}}
    }}
    @keyframes vt-extract{{
      0%{{opacity:0;transform:translateY(26px) scale(.15)}}
      12%{{opacity:0;transform:translateY(22px) scale(.2)}}
      22%{{opacity:1;transform:translateY(0) scale(.55)}}
      40%{{opacity:1;transform:translateY(-74px) scale(1)}}
      60%{{opacity:1;transform:translateY(-74px) scale(1)}}
      78%{{opacity:1;transform:translateY(0) scale(.55)}}
      90%{{opacity:0;transform:translateY(22px) scale(.2)}}
      100%{{opacity:0;transform:translateY(26px) scale(.15)}}
    }}
    @keyframes vt-twinkle{{
      0%,34%{{opacity:0;transform:scale(.3)}}
      44%{{opacity:1;transform:scale(1)}}
      52%{{opacity:.4;transform:scale(.7)}}
      60%{{opacity:1;transform:scale(1.15)}}
      66%,100%{{opacity:0;transform:scale(.3)}}
    }}
  </style>

  <svg class="vt-planet state-{state}" viewBox="0 0 200 224" xmlns="http://www.w3.org/2000/svg"
       role="img" aria-label="Asistente Venttur">
    <defs>
      <radialGradient id="vt-ocean" cx="35%" cy="28%" r="75%">
        <stop offset="0" stop-color="#74c0fc"/>
        <stop offset="55%" stop-color="#1c7ed6"/>
        <stop offset="100%" stop-color="#1864ab"/>
      </radialGradient>
      <linearGradient id="vt-land" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#69db7c"/>
        <stop offset="1" stop-color="#2f9e44"/>
      </linearGradient>
      <linearGradient id="vt-atmos" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#a5d8ff"/>
        <stop offset="1" stop-color="#3bc9db"/>
      </linearGradient>
      <linearGradient id="vt-brainpink" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#ffc9d4"/>
        <stop offset="1" stop-color="#faa2b8"/>
      </linearGradient>
    </defs>

    <!-- atmósfera / órbita (detrás) -->
    <ellipse class="vt-ring" cx="100" cy="146" rx="92" ry="22"
             fill="none" stroke="url(#vt-atmos)" stroke-width="5" opacity=".85"/>

    <!-- manitas -->
    <g class="vt-hand-l" fill="#1c7ed6">
      <rect x="22" y="150" width="24" height="8" rx="4"/>
      <circle cx="22" cy="154" r="8"/>
    </g>
    <g class="vt-hand-r" fill="#1c7ed6">
      <rect x="154" y="150" width="24" height="8" rx="4"/>
      <circle cx="178" cy="154" r="8"/>
    </g>

    <!-- cuerpo: océano -->
    <circle cx="100" cy="146" r="58" fill="url(#vt-ocean)"/>
    <!-- continentes (verde) -->
    <g fill="url(#vt-land)">
      <path d="M68 124 q16 -7 23 6 q5 13 -8 20 q-18 5 -21 -10 q-2 -11 6 -16 z"/>
      <path d="M64 170 q9 -4 13 7 q3 16 -7 22 q-11 2 -13 -11 q-1 -13 7 -18 z"/>
      <path d="M122 126 q18 -5 23 11 q2 15 -11 19 q-18 3 -18 -13 q0 -13 6 -17 z"/>
      <path d="M118 176 q11 -3 14 7 q1 11 -9 13 q-13 1 -12 -10 q1 -8 7 -10 z"/>
      <ellipse cx="150" cy="160" rx="6" ry="4"/>
    </g>
    <!-- nubes -->
    <g fill="#ffffff" opacity=".42">
      <ellipse cx="92" cy="190" rx="16" ry="4.5"/>
      <ellipse cx="124" cy="112" rx="13" ry="4"/>
    </g>
    <!-- brillo -->
    <ellipse cx="78" cy="118" rx="20" ry="12" fill="#ffffff" opacity=".18"/>

    <!-- cara -->
    <circle cx="66" cy="158" r="6" fill="#ff8787" opacity=".5"/>
    <circle cx="134" cy="158" r="6" fill="#ff8787" opacity=".5"/>
    <ellipse class="vt-eye" cx="80" cy="140" rx="10" ry="13" fill="#fff"/>
    <ellipse class="vt-eye" cx="120" cy="140" rx="10" ry="13" fill="#fff"/>
    <circle cx="82" cy="143" r="5" fill="#16314f"/>
    <circle cx="122" cy="143" r="5" fill="#16314f"/>
    <circle cx="84.5" cy="140" r="1.8" fill="#fff"/>
    <circle cx="124.5" cy="140" r="1.8" fill="#fff"/>
    <path d="M84 166 Q100 181 116 166" fill="none" stroke="#16314f"
          stroke-width="4" stroke-linecap="round"/>

    <!-- tapa (cap superior del planeta; se levanta al guardar) -->
    <path class="vt-lid" d="M49.2 118 A58 58 0 0 1 150.8 118 Z" fill="url(#vt-ocean)"/>
    <path class="vt-lid" d="M49.2 118 h101.6" fill="none" stroke="#1864ab"
          stroke-width="2" opacity=".5" stroke-linecap="round"/>

    <!-- cerebro (sale, se limpia y se guarda) -->
    <g class="vt-brain">
      <ellipse cx="100" cy="94" rx="20" ry="15" fill="url(#vt-brainpink)"/>
      <path d="M100 80 v28 M88 84 q-6 10 2 18 M112 84 q6 10 -2 18 M84 94 q8 -4 14 2 M118 94 q-8 -4 -14 2"
            fill="none" stroke="#f06595" stroke-width="2" stroke-linecap="round" opacity=".8"/>
      <rect x="95" y="106" width="10" height="6" rx="3" fill="#faa2b8"/>
      <!-- destellos de limpieza -->
      <g fill="#fff3bf">
        <path class="vt-spark s1" d="M74 78 l1.6 5 5 1.6 -5 1.6 -1.6 5 -1.6 -5 -5 -1.6 5 -1.6 z"/>
        <path class="vt-spark s2" d="M126 80 l1.4 4.4 4.4 1.4 -4.4 1.4 -1.4 4.4 -1.4 -4.4 -4.4 -1.4 4.4 -1.4 z"/>
        <path class="vt-spark s3" d="M100 64 l1.3 4 4 1.3 -4 1.3 -1.3 4 -1.3 -4 -4 -1.3 4 -1.3 z"/>
      </g>
    </g>

    <!-- burbuja de pensamiento -->
    <g class="vt-think">
      <circle cx="150" cy="96" r="4" fill="#fff" stroke="#adb5bd" stroke-width="1.5"/>
      <circle cx="158" cy="86" r="6" fill="#fff" stroke="#adb5bd" stroke-width="1.5"/>
      <rect x="150" y="58" width="46" height="26" rx="13" fill="#fff" stroke="#adb5bd" stroke-width="1.5"/>
      <circle class="vt-dot d1" cx="162" cy="71" r="3.2" fill="#1c7ed6"/>
      <circle class="vt-dot d2" cx="173" cy="71" r="3.2" fill="#1c7ed6"/>
      <circle class="vt-dot d3" cx="184" cy="71" r="3.2" fill="#1c7ed6"/>
    </g>
  </svg>
</div>
"""


def _render_mascota(slot, state: str = "idle") -> None:
    """Dibuja (o redibuja) la mascota en su placeholder con el estado dado."""
    with slot:
        components.html(_mascota_html(state), height=_MASCOTA_HEIGHT)


def _flag_saved() -> None:
    """Marca que se acaba de guardar algo: la mascota hará la animación de memoria."""
    st.session_state["mascota_saved"] = True


def render(user: dict) -> None:
    col_title, col_mascota = st.columns([3, 1])
    with col_title:
        st.subheader("🧠 Consola de Conocimiento")
        _badge_backend()
        if st.button("🔄 Recargar conocimiento", help="Refresca lo que la IA tiene cargado"):
            st.cache_data.clear()
            st.rerun()
    mascota = col_mascota.empty()
    estado = "saving" if st.session_state.pop("mascota_saved", False) else "idle"
    _render_mascota(mascota, estado)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["💬 Entrevista", "✏️ Corregir", f"📥 Huecos ({len(kb_store.list_gaps('abierto'))})", "✅ Revisar"]
    )
    with tab1:
        _entrevista(user, mascota)
    with tab2:
        _corregir(user)
    with tab3:
        _huecos(user)
    with tab4:
        _revisar(user)


# --------------------------------------------------------------------------- #
#  Modo 1 — Entrevista (la IA pregunta y propone entradas)
# --------------------------------------------------------------------------- #
def _entrevista(user: dict, mascota=None) -> None:
    st.markdown("Conversa con la IA: te hará preguntas para llenar lo que le falta. "
                "Cuando te proponga una entrada, guárdala abajo.")
    msgs = st.session_state.setdefault("admin_msgs", [])

    if not msgs:
        st.chat_message("assistant", avatar="🧠").markdown(
            f"Hola **{user['name']}** 👋 Soy tu asistente para alimentar el conocimiento de Venttur. "
            "Cuéntame de un programa, política o dato que quieras que aprenda — o pregúntame qué me falta."
        )
    for m in msgs:
        st.chat_message(m["role"], avatar=("🧠" if m["role"] == "assistant" else "🧑")).markdown(m["content"])

    if prompt := st.chat_input("Escribe aquí…", key="admin_chat_input"):
        msgs.append({"role": "user", "content": prompt})
        st.chat_message("user", avatar="🧑").markdown(prompt)
        if mascota is not None:
            _render_mascota(mascota, "thinking")  # el planeta "piensa" mientras responde
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Pensando…"):
                try:
                    reply = assistant.chat(msgs, assistant.admin_interview_system())
                except assistant.AssistantError as e:
                    reply = f"⚠️ {e}"
            st.markdown(reply)
        msgs.append({"role": "assistant", "content": reply})
        if mascota is not None:
            _render_mascota(mascota, "idle")

    st.divider()
    st.markdown("**➕ Guardar una entrada en el conocimiento**")
    with st.form("add_entry", clear_on_submit=True):
        cat = st.text_input("Categoría / programa", placeholder="ej. Summers, Boardings, Comisiones…")
        tema = st.text_input("Tema", placeholder="ej. Rango de precios Summer USA 2026")
        contenido = st.text_area("Contenido (el dato, claro y citable)", height=120)
        if st.form_submit_button("Guardar (queda aprobado)", use_container_width=True):
            if cat.strip() and tema.strip() and contenido.strip():
                kb_store.add_entry(cat, tema, contenido, actualizado_por=user["email"])
                st.success("Guardado ✅ La IA ya lo usará.")
                _flag_saved()
                st.rerun()
            else:
                st.warning("Completa categoría, tema y contenido.")


# --------------------------------------------------------------------------- #
#  Modo 2 — Corregir
# --------------------------------------------------------------------------- #
def _corregir(user: dict) -> None:
    entries = kb_store.list_entries(estado="aprobado")
    if not entries:
        st.info("Aún no hay entradas aprobadas que corregir.")
        return
    labels = {f"[{e.get('categoria','')}] {e.get('tema','')}": e for e in entries}
    pick = st.selectbox("Elige la entrada a corregir", list(labels.keys()))
    e = labels[pick]
    nuevo = st.text_area("Contenido", value=e.get("contenido", ""), height=160, key=f"edit_{e.get('id')}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Guardar corrección", use_container_width=True):
            if kb_store.update_entry(e.get("id"), contenido=nuevo, actualizado_por=user["email"]):
                st.success("Corregido ✅")
                _flag_saved()
                st.rerun()
    with col2:
        if st.button("🗄️ Archivar entrada", use_container_width=True):
            if kb_store.update_entry(e.get("id"), estado="archivado", actualizado_por=user["email"]):
                st.success("Archivada.")
                st.rerun()

    with st.expander("🤖 Pedir a la IA que proponga la corrección"):
        problema = st.text_input("¿Qué está mal o qué cambió?", key=f"fix_{e.get('id')}")
        if st.button("Proponer corrección", key=f"btnfix_{e.get('id')}"):
            sysp = assistant.admin_interview_system()
            user_msg = (f"Esta entrada de la base dice:\n\nCATEGORÍA: {e.get('categoria')}\n"
                        f"TEMA: {e.get('tema')}\nCONTENIDO: {e.get('contenido')}\n\n"
                        f"Corrígela según esto (sin inventar; usa [CONFIRMAR] si falta un dato): {problema}\n\n"
                        "Devuelve SOLO el nuevo CONTENIDO corregido.")
            try:
                with st.spinner("Pensando…"):
                    propuesta = assistant.complete(sysp, user_msg)
                st.text_area("Propuesta (cópiala arriba si te sirve):", value=propuesta, height=140)
            except assistant.AssistantError as ex:
                st.warning(str(ex))


# --------------------------------------------------------------------------- #
#  Modo 3 — Cola de huecos
# --------------------------------------------------------------------------- #
def _huecos(user: dict) -> None:
    gaps = kb_store.list_gaps("abierto")
    st.markdown("Preguntas reales que la IA **no supo responder**. Llénalas para cerrarlas.")
    if not gaps:
        st.success("🎉 No hay huecos abiertos.")
        return
    for g in gaps:
        with st.container(border=True):
            st.markdown(f"**❓ {g.get('pregunta','')}**")
            if g.get("contexto"):
                st.caption(f"Contexto: {g.get('contexto')}")
            with st.form(f"gap_{g.get('id')}", clear_on_submit=True):
                cat = st.text_input("Categoría / programa", key=f"gc_{g.get('id')}")
                tema = st.text_input("Tema", value=g.get("pregunta", "")[:60], key=f"gt_{g.get('id')}")
                cont = st.text_area("Respuesta / dato", key=f"gco_{g.get('id')}", height=100)
                if st.form_submit_button("Guardar y cerrar hueco"):
                    if cont.strip():
                        kb_store.add_entry(cat or "general", tema or g.get("pregunta", ""),
                                           cont, actualizado_por=user["email"])
                        kb_store.resolve_gap(g.get("id"))
                        st.success("Hueco cerrado ✅")
                        _flag_saved()
                        st.rerun()
                    else:
                        st.warning("Escribe la respuesta.")


# --------------------------------------------------------------------------- #
#  Modo 4 — Revisar / Aprobar
# --------------------------------------------------------------------------- #
def _revisar(user: dict) -> None:
    pendientes = kb_store.list_entries(estado="pendiente")
    st.markdown(f"**Pendientes de aprobar: {len(pendientes)}**")
    for e in pendientes:
        with st.container(border=True):
            st.markdown(f"**[{e.get('categoria','')}] {e.get('tema','')}**")
            st.write(e.get("contenido", ""))
            c1, c2 = st.columns(2)
            if c1.button("✅ Aprobar", key=f"ap_{e.get('id')}"):
                kb_store.update_entry(e.get("id"), estado="aprobado", actualizado_por=user["email"])
                _flag_saved()
                st.rerun()
            if c2.button("🗄️ Archivar", key=f"ar_{e.get('id')}"):
                kb_store.update_entry(e.get("id"), estado="archivado", actualizado_por=user["email"])
                st.rerun()

    st.divider()
    aprobadas = kb_store.list_entries(estado="aprobado")
    st.markdown(f"**Conocimiento aprobado: {len(aprobadas)} entradas**")
    if aprobadas:
        st.dataframe(
            [{"Categoría": e.get("categoria"), "Tema": e.get("tema"),
              "Actualizado por": e.get("actualizado_por"), "Fecha": e.get("fecha")} for e in aprobadas],
            use_container_width=True, hide_index=True,
        )
