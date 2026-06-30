"""Regenera el Google Doc de conocimiento (uso: GitHub Action programado o manual).

Lee la configuración desde `.streamlit/secrets.toml` (que el workflow recrea a partir de un
secret de GitHub). No imprime credenciales: solo el resultado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import doc_export  # noqa: E402

if __name__ == "__main__":
    try:
        url = doc_export.regenerate()
        print("OK · documento regenerado:", url)
    except Exception as e:  # noqa: BLE001
        print("FALLO al regenerar el documento:", e)
        sys.exit(1)
