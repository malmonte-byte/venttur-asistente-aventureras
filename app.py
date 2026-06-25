"""
Asistente de Aventureras — Venttur
==================================
Una app con dos vistas según el rol:
  - admin (Max + jefes): Consola de Conocimiento (alimenta/corrige la IA) + puede probar el chat.
  - aventurera: chat de ventas + pitch + objeciones + CTA.

Punto de entrada de Streamlit.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import admin_console, sales  # noqa: E402
from utils.auth import authenticate  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "venttur_logo.png"

st.set_page_config(
    page_title="Asistente de Aventureras · Venttur",
    page_icon=str(LOGO) if LOGO.exists() else "🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)


def login_view() -> None:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.write("")
        if LOGO.exists():
            st.image(str(LOGO), use_container_width=True)
        st.markdown("<p style='text-align:center;color:#5a6478'>Asistente de Aventureras</p>",
                    unsafe_allow_html=True)
        with st.form("login", border=True):
            st.markdown("##### Iniciar sesión")
            email = st.text_input("Correo")
            pw = st.text_input("Contraseña", type="password")
            ok = st.form_submit_button("Entrar", use_container_width=True)
        if ok:
            user = authenticate(email, pw)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Correo o contraseña incorrectos.")
        st.caption("Admins: usa tu correo @venttur.com. Aventureras: tu correo + la contraseña del equipo.")


def main() -> None:
    user = st.session_state["user"]
    with st.sidebar:
        if LOGO.exists():
            st.image(str(LOGO), use_container_width=True)
        st.markdown(f"**{user['name']}**")
        rol = "👑 Administrador" if user["role"] == "admin" else "🧳 Aventurera"
        st.caption(rol)
        st.divider()
        if user["role"] == "admin":
            vista = st.radio("Vista", ["🧠 Consola de Conocimiento", "🧳 Probar chat de Aventurera"])
        else:
            vista = "🧳 Aventurera"
        st.divider()
        if st.button("Cerrar sesión", use_container_width=True):
            for k in ("user", "admin_msgs", "sales_msgs", "sales_tool"):
                st.session_state.pop(k, None)
            st.rerun()

    if user["role"] == "admin" and vista.startswith("🧠"):
        admin_console.render(user)
    else:
        sales.render(user)


if __name__ == "__main__":
    if "user" not in st.session_state:
        login_view()
    else:
        main()
