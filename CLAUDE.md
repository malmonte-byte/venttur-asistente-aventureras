# Asistente de Aventureras — Contexto para Claude

## Qué es
App Streamlit (molde Venttur) con dos vistas por rol: **admin** (Consola de Conocimiento para
alimentar/corregir la IA) y **aventurera** (chat de ventas + pitch + objeciones + CTA).

## Reglas de oro
0. AUDIENCIA: la IA habla con la **Aventurera o el equipo**, NUNCA con el cliente final (este no
   usa la herramienta). Le da info + frases para que ella sepa qué decirle a sus prospectos; solo
   entrega borradores marcados "para enviar" cuando se los piden. No le habla directo al padre.
1. ⛔ La IA NUNCA da precios/costos/becas con montos (ni aunque estén en la base): redirige a la
   asesoría con el asesor de Venttur. La Aventurera despierta interés y agenda la asesoría, no cotiza.
2. La IA NO inventa datos: usa `[CONFIRMAR: ...]` (solo para datos de programa, nunca precios). Esos
   casos se registran como "huecos" en `utils/kb_store.py` para que los admins los llenen.
3. Modelo: `claude-opus-4-8` (Anthropic SDK). No cambiar sin pedir.
4. Tono White-Glove (no vendedor) + método LAER + doble audiencia (cómo hablarle al padre vs al
   estudiante). Todo eso vive en `core/assistant.py` (`_REGLAS`).
4. Antes de tocar código: preguntar si va solo a local o también al deploy (git push).
5. Secretos nunca en el código (van en `.streamlit/secrets.toml`, gitignored).

## Base de conocimiento (3 capas, en orden de precedencia)
1. Entradas vivas aprobadas (Google Sheets) — las cargan los admins. `utils/kb_store.py`.
2. Semilla `knowledge/*.md`.
3. PDFs en `fuentes/` (opcional) — `core/sources.py`.
Si no hay Google Sheets configurado, kb_store usa respaldo local `data/kb_local.json` (no persiste en la nube).

## Admins (rol admin)
9 correos @venttur.com definidos en `[users.*]` de secrets. Aventureras entran con `AVENTURERA_PASSWORD`.

## Despliegue
Streamlit Cloud vía git push (cuenta `malmonte-byte`). Compartir la Google Sheet con el
`client_email` de la cuenta de servicio. Luego registrar en el Portal Herramientas IA.

## Pendientes / roadmap
- Fase 3: integrar Clientify (registrar lead referido + atribución por Aventurera) y Meta Ads.
- Tool-use para que la IA proponga entradas estructuradas automáticamente (hoy el admin las guarda a mano).
- Cargar PDFs reales de programas a `fuentes/` y/o llenar `knowledge/programas.md`.
