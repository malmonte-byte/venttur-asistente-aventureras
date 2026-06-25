"""Autenticación por correo + roles (admin / aventurera).

- Admins: definidos en [users."correo@..."] de secrets.toml (correo + password + role).
  Tienen acceso a la Consola de Conocimiento.
- Aventureras: entran con cualquier correo + la contraseña compartida AVENTURERA_PASSWORD.
  Solo ven el chat de ventas.
"""
from __future__ import annotations

import streamlit as st


def _users() -> dict:
    try:
        return dict(st.secrets.get("users", {}))
    except Exception:
        return {}


def authenticate(email: str, password: str) -> dict | None:
    """Devuelve {email, name, role} o None si las credenciales no son válidas."""
    email = (email or "").strip().lower()
    if not password:
        return None

    # 1) ¿Es un administrador registrado?
    users = _users()
    entry = users.get(email)
    if entry and password == str(entry.get("password", "")):
        return {
            "email": email,
            "name": entry.get("name", email),
            "role": entry.get("role", "admin"),
        }

    # 2) ¿Contraseña compartida de Aventureras?
    avent_pw = ""
    try:
        avent_pw = str(st.secrets.get("AVENTURERA_PASSWORD", ""))
    except Exception:
        avent_pw = ""
    if avent_pw and password == avent_pw:
        return {
            "email": email or "aventurera",
            "name": (email.split("@")[0] if email else "Aventurera"),
            "role": "aventurera",
        }

    return None
