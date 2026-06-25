# Asistente de Aventureras — Venttur

App Streamlit con **dos vistas según el rol**:

- 👑 **Admin** (Max + jefes): **Consola de Conocimiento** para conversar con la IA, alimentarla,
  corregirla y llenar lo que le falta. El conocimiento se guarda en **Google Sheets** (vivo).
- 🧳 **Aventurera**: chat de ventas + generador de **pitch** (mensaje para padre y para estudiante),
  manejo de **objeciones** (método LAER) y **CTA** para agendar la asesoría de 45 min.

La IA nunca inventa datos: si le falta algo responde `[CONFIRMAR: ...]` y queda registrado como un
"hueco" para que los admins lo llenen desde la Consola.

---

## ▶️ Probar en local

```bash
cd "Asistente-Aventureras"
pip install -r requirements.txt
streamlit run app.py
```

- Sin `KB_SHEET_ID` configurado, el conocimiento se guarda en `data/kb_local.json` (solo local).
- Sin `ANTHROPIC_API_KEY`, la app abre y permite navegar, pero la IA avisará que falta la key.

## 🔑 Secretos (`.streamlit/secrets.toml` local y panel de Streamlit Cloud)

| Clave | Para qué |
|------|----------|
| `ANTHROPIC_API_KEY` | Que la IA responda (Claude `claude-opus-4-8`). |
| `AVENTURERA_PASSWORD` | Contraseña compartida del rol Aventurera. |
| `[users."correo@venttur.com"]` | Admins (correo + password + role). |
| `KB_SHEET_ID` + `[gcp_service_account]` | Base de conocimiento viva en Google Sheets. |

## ☁️ Desplegar (Streamlit Cloud)

1. Sube esta carpeta a un repo de GitHub (privado de preferencia). `secrets.toml` y `*.json` no se suben.
2. share.streamlit.io → Create app → repo, rama `main`, archivo `app.py`.
3. Advanced settings → Secrets → pega el contenido de tu `secrets.toml`.
4. Crea una Google Sheet, copia su ID a `KB_SHEET_ID`, y compártela con el `client_email` de la
   cuenta de servicio como **Editor**.
5. Deploy. Luego puedes agregarla al **Portal Herramientas IA**.

## 🗂️ Estructura

```
Asistente-Aventureras/
├── app.py                 # login + ruteo por rol
├── core/
│   ├── assistant.py       # system prompts (LAER, doble audiencia) + Claude
│   ├── knowledge.py       # carga knowledge/*.md (semilla)
│   ├── sources.py         # carga PDFs de fuentes/ (opcional)
│   ├── admin_console.py   # Consola de Conocimiento (4 modos)
│   └── sales.py           # chat + pitch + objeciones + CTA
├── utils/
│   ├── auth.py            # login por correo + roles
│   └── kb_store.py        # base de conocimiento viva (Sheets + respaldo local)
├── knowledge/*.md         # conocimiento semilla (editable)
├── fuentes/               # PDFs de respaldo (opcional)
└── .streamlit/            # config.toml + secrets.toml (gitignored)
```
