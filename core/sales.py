"""Vista de Aventureras: chat de ventas + pitch + objeciones + CTA.

Cuando la IA responde con [CONFIRMAR ...] (le faltó un dato), se registra un
'hueco' para que los admins lo llenen desde la Consola.
"""
from __future__ import annotations

import streamlit as st

from core import assistant
from utils import kb_store

PROGRAMAS = [
    "No estoy segura / orientación general",
    "Internados / Boarding Schools",
    "Intercambio académico con familia (~1 año)",
    "Campamentos de verano (Summers)",
    "Cursos de idiomas",
    "Viajes educativos grupales",
    "Educación superior (licenciatura/posgrado)",
    "Estudia y trabaja (+18)",
]


def _maybe_log_gap(user_text: str, reply: str, user: dict) -> None:
    if "[CONFIRMAR" in reply:
        kb_store.add_gap(pregunta=user_text, contexto=reply[:400], detectado_por=user.get("email", ""))


def render(user: dict) -> None:
    st.subheader("🧳 Asistente de Aventureras")
    st.caption("Tu copiloto para recomendar Venttur con tono premium (no de venta).")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("✍️ Arma un pitch", use_container_width=True):
        st.session_state["sales_tool"] = "pitch"
    if c2.button("🛡️ Maneja una objeción", use_container_width=True):
        st.session_state["sales_tool"] = "objecion"
    if c3.button("😬 Situación difícil", use_container_width=True):
        st.session_state["sales_tool"] = "dificil"
    if c4.button("📅 Mensaje para agendar", use_container_width=True):
        st.session_state["sales_tool"] = "cta"

    tool = st.session_state.get("sales_tool")
    if tool == "pitch":
        _pitch(user)
    elif tool == "objecion":
        _objecion(user)
    elif tool == "dificil":
        _dificil(user)
    elif tool == "cta":
        _cta(user)

    st.divider()
    _chat(user)


def _pitch(user: dict) -> None:
    with st.container(border=True):
        st.markdown("**✍️ Generador de pitch (mensaje para el padre y para el estudiante)**")
        col1, col2 = st.columns(2)
        edad = col1.number_input("Edad del estudiante", min_value=8, max_value=30, value=15)
        programa = col2.selectbox("Programa / interés", PROGRAMAS)
        perfil = st.text_area("Contexto de la familia (objetivo, idioma, preocupaciones)…", height=80)
        if st.button("Generar pitch", type="primary"):
            prompt = (f"La Aventurera quiere recomendarle un programa a un cliente. Datos del caso: "
                      f"edad del estudiante {edad}; programa/interés: {programa}; "
                      f"contexto de la familia: {perfil or 'sin detalle'}.\n"
                      "Entrégale a la Aventurera DOS borradores que ella pueda reenviar a su cliente, claramente "
                      "marcados: '📩 Mensaje para el PADRE/MADRE' y '📩 Mensaje para el ESTUDIANTE', cada uno "
                      "cerrando con la invitación a agendar la asesoría gratis de 45 min (presencial o virtual). "
                      "Tono premium, no vendedor. NUNCA menciones precios ni costos; si surge el tema, redirige a "
                      "la asesoría. Usa [CONFIRMAR: ...] solo si falta un dato de programa.")
            try:
                with st.spinner("Redactando…"):
                    out = assistant.complete(assistant.sales_system(), prompt)
                st.markdown(out)
                _maybe_log_gap(f"Pitch: {programa}, {edad} años", out, user)
            except assistant.AssistantError as e:
                st.warning(str(e))


def _objecion(user: dict) -> None:
    with st.container(border=True):
        st.markdown("**🛡️ Manejo de objeciones (método LAER)**")
        comunes = ["Está muy caro", "¿Y si no se adapta / le pasa algo?",
                   "Es mucho tiempo lejos", "Trámites/visa complicados", "Otra (escríbela)"]
        sel = st.selectbox("Objeción común", comunes)
        texto = st.text_input("…o escribe la objeción tal como te la dijeron", value="" if sel == "Otra (escríbela)" else sel)
        quien = st.radio("¿De quién viene?", ["Padre/Madre", "Estudiante", "No sé"], horizontal=True)
        if st.button("Responder con LAER", type="primary"):
            prompt = (f"Un cliente de la Aventurera puso esta objeción: \"{texto}\" (viene de: {quien}). "
                      "Explícale a la Aventurera cómo manejarla con el método LAER (muestra las 4 fases "
                      "etiquetadas) y dale al final un '📩 Mensaje que puedes enviarle a tu cliente' corto y listo. "
                      "NUNCA des precios, cifras ni descuentos; si la objeción es de precio, valida, reencuadra "
                      "como inversión y lleva a la asesoría (donde el asesor ve opciones y becas). "
                      "Usa [CONFIRMAR: ...] solo si falta un dato de programa.")
            try:
                with st.spinner("Pensando…"):
                    out = assistant.complete(assistant.sales_system(), prompt)
                st.markdown(out)
                _maybe_log_gap(f"Objeción: {texto}", out, user)
            except assistant.AssistantError as e:
                st.warning(str(e))


def _dificil(user: dict) -> None:
    with st.container(border=True):
        st.markdown("**😬 Situación difícil con un cliente**")
        st.caption("Describe qué está pasando y te doy cómo manejarlo + un mensaje listo para enviar.")
        comunes = [
            "El cliente dejó de responder (ghosting)",
            "Solo pide precio y no quiere agendar",
            "Está comparando con otra agencia",
            "Desconfía / no conoce la marca",
            "Quiere toda la info por chat, no una cita",
            "Se molestó o está frío",
            "Otra (descríbela)",
        ]
        sel = st.selectbox("Situación", comunes)
        detalle = st.text_area("Cuéntame el contexto (qué dijo, por qué canal, qué programa le interesa)…", height=90)
        quien = st.radio("¿De quién viene?", ["Padre/Madre", "Estudiante", "No sé"], horizontal=True)
        if st.button("Ayúdame con esto", type="primary"):
            situacion = detalle.strip() or (sel if sel != "Otra (descríbela)" else "")
            prompt = (
                f"La Aventurera enfrenta una situación difícil con su cliente. Situación: \"{sel}\". "
                f"Contexto: {situacion or 'sin detalle'}. Viene de: {quien}.\n"
                "Dale: (1) cómo leer lo que está pasando (qué siente/teme el cliente), (2) el tono y la "
                "estrategia para manejarlo, y (3) un '📩 Mensaje que puedes enviarle a tu cliente' corto, "
                "cálido y listo para copiar. El objetivo SIEMPRE es recuperar la conversación y agendar la "
                "cita GRATIS con el asesor — nunca cerrar la venta por chat ni dar precios. Usa LAER si aplica."
            )
            try:
                with st.spinner("Pensando…"):
                    out = assistant.complete(assistant.sales_system(), prompt)
                st.markdown(out)
                _maybe_log_gap(f"Situación difícil: {sel}", out, user)
            except assistant.AssistantError as e:
                st.warning(str(e))


def _cta(user: dict) -> None:
    with st.container(border=True):
        st.markdown("**📅 Mensaje para agendar la asesoría de 45 min**")
        canal = st.selectbox("Canal", ["WhatsApp", "Instagram DM", "Mensaje formal"])
        para = st.radio("Para", ["Padre/Madre", "Estudiante"], horizontal=True)
        if st.button("Generar variantes", type="primary"):
            prompt = (f"Dale a la Aventurera 3 variantes cortas y copiables de un mensaje que ELLA pueda enviarle "
                      f"a su cliente para invitarlo a agendar la asesoría diagnóstica gratuita de 45 minutos "
                      f"(presencial o virtual). Canal: {canal}. Destinatario: {para}. Tono White-Glove, no vendedor.")
            try:
                with st.spinner("Redactando…"):
                    out = assistant.complete(assistant.sales_system(), prompt, max_tokens=1200)
                st.markdown(out)
            except assistant.AssistantError as e:
                st.warning(str(e))


def _chat(user: dict) -> None:
    st.markdown("**💬 Pregúntame lo que sea sobre los programas**")
    msgs = st.session_state.setdefault("sales_msgs", [])
    if not msgs:
        st.chat_message("assistant", avatar="🧳").markdown(
            "¡Hola! Soy tu copiloto. Pregúntame sobre los programas, cómo presentarle Venttur a una "
            "familia, cómo responder cuando piden precio, o cómo manejar un cliente difícil. "
            "Recuerda: tu meta es **agendar la cita gratis** con el asesor — yo te ayudo a llevarlos ahí. 😊"
        )
    for m in msgs:
        st.chat_message(m["role"], avatar=("🧳" if m["role"] == "assistant" else "🧑")).markdown(m["content"])
    if prompt := st.chat_input("Escribe tu pregunta…", key="sales_chat_input"):
        msgs.append({"role": "user", "content": prompt})
        st.chat_message("user", avatar="🧑").markdown(prompt)
        with st.chat_message("assistant", avatar="🧳"):
            with st.spinner("Pensando…"):
                try:
                    reply = assistant.chat(msgs, assistant.sales_system())
                except assistant.AssistantError as e:
                    reply = f"⚠️ {e}"
            st.markdown(reply)
        msgs.append({"role": "assistant", "content": reply})
        _maybe_log_gap(prompt, reply, user)
