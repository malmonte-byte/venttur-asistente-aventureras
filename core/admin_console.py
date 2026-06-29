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
#  Mascota — planeta con cara (SVG + CSS, sin librerías extra)
#  Le da identidad visual al asistente. Animaciones: flota, parpadea,
#  saluda con las manitas y el anillo gira. Si el navegador no aplicara el
#  <style>, el planeta se ve igual (estático), nunca roto.
# --------------------------------------------------------------------------- #
def _mascota_planeta_html() -> str:
    return """
<div class="vt-mascota">
  <style>
    html,body{margin:0;background:transparent;}
    .vt-mascota{display:flex;justify-content:center;align-items:flex-start;padding-top:.5rem;}
    .vt-planet{width:128px;height:128px;animation:vt-float 4.5s ease-in-out infinite;}
    @keyframes vt-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-9px)}}
    .vt-ring{transform-box:view-box;transform-origin:65px 65px;animation:vt-spin 14s linear infinite;}
    @keyframes vt-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    .vt-eye{transform-box:fill-box;transform-origin:center;animation:vt-blink 5s infinite;}
    @keyframes vt-blink{0%,93%,100%{transform:scaleY(1)}96%{transform:scaleY(.12)}}
    .vt-hand-l{transform-box:view-box;transform-origin:24px 86px;animation:vt-wave-l 3.2s ease-in-out infinite;}
    .vt-hand-r{transform-box:view-box;transform-origin:106px 86px;animation:vt-wave-r 3.2s ease-in-out infinite;}
    @keyframes vt-wave-l{0%,100%{transform:rotate(0deg)}50%{transform:rotate(-22deg)}}
    @keyframes vt-wave-r{0%,100%{transform:rotate(0deg)}50%{transform:rotate(22deg)}}
  </style>
  <svg class="vt-planet" viewBox="0 0 130 130" xmlns="http://www.w3.org/2000/svg"
       role="img" aria-label="Asistente Venttur">
    <defs>
      <linearGradient id="vt-body" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#5c7cfa"/>
        <stop offset="1" stop-color="#3b5bdb"/>
      </linearGradient>
      <linearGradient id="vt-ring-g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#66d9e8"/>
        <stop offset="1" stop-color="#3bc9db"/>
      </linearGradient>
    </defs>

    <!-- anillo (detrás del planeta) -->
    <ellipse class="vt-ring" cx="65" cy="65" rx="58" ry="15"
             fill="none" stroke="url(#vt-ring-g)" stroke-width="5" opacity=".9"/>

    <!-- manitas -->
    <g class="vt-hand-l" fill="#3b5bdb">
      <rect x="20" y="80" width="7" height="16" rx="3.5"/>
      <circle cx="23.5" cy="80" r="6"/>
    </g>
    <g class="vt-hand-r" fill="#3b5bdb">
      <rect x="103" y="80" width="7" height="16" rx="3.5"/>
      <circle cx="106.5" cy="80" r="6"/>
    </g>

    <!-- cuerpo del planeta -->
    <circle cx="65" cy="65" r="37" fill="url(#vt-body)"/>
    <!-- continentes / textura -->
    <ellipse cx="50" cy="48" rx="11" ry="6" fill="#748ffc" opacity=".55"/>
    <ellipse cx="80" cy="82" rx="9" ry="5" fill="#748ffc" opacity=".5"/>
    <circle cx="86" cy="52" r="4" fill="#748ffc" opacity=".5"/>

    <!-- ojos -->
    <g>
      <ellipse class="vt-eye" cx="54" cy="62" rx="7" ry="9" fill="#fff"/>
      <ellipse class="vt-eye" cx="78" cy="62" rx="7" ry="9" fill="#fff"/>
      <circle cx="55.5" cy="64" r="3.4" fill="#1b2a4a"/>
      <circle cx="79.5" cy="64" r="3.4" fill="#1b2a4a"/>
      <circle cx="57" cy="61.5" r="1.2" fill="#fff"/>
      <circle cx="81" cy="61.5" r="1.2" fill="#fff"/>
    </g>

    <!-- boca (sonrisa) -->
    <path d="M55 78 Q65 87 77 78" fill="none" stroke="#1b2a4a"
          stroke-width="3" stroke-linecap="round"/>
    <!-- cachetitos -->
    <circle cx="47" cy="74" r="3.5" fill="#ff8787" opacity=".55"/>
    <circle cx="84" cy="74" r="3.5" fill="#ff8787" opacity=".55"/>
  </svg>
</div>
"""


def render(user: dict) -> None:
    col_title, col_mascota = st.columns([4, 1])
    with col_title:
        st.subheader("🧠 Consola de Conocimiento")
        _badge_backend()
        if st.button("🔄 Recargar conocimiento", help="Refresca lo que la IA tiene cargado"):
            st.cache_data.clear()
            st.rerun()
    with col_mascota:
        components.html(_mascota_planeta_html(), height=160)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["💬 Entrevista", "✏️ Corregir", f"📥 Huecos ({len(kb_store.list_gaps('abierto'))})", "✅ Revisar"]
    )
    with tab1:
        _entrevista(user)
    with tab2:
        _corregir(user)
    with tab3:
        _huecos(user)
    with tab4:
        _revisar(user)


# --------------------------------------------------------------------------- #
#  Modo 1 — Entrevista (la IA pregunta y propone entradas)
# --------------------------------------------------------------------------- #
def _entrevista(user: dict) -> None:
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
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Pensando…"):
                try:
                    reply = assistant.chat(msgs, assistant.admin_interview_system())
                except assistant.AssistantError as e:
                    reply = f"⚠️ {e}"
            st.markdown(reply)
        msgs.append({"role": "assistant", "content": reply})

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
