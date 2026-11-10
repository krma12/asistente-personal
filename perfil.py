"""
Lectura del perfil personal (perfil.yaml) para personalizar las respuestas.

Privacidad (minimización de datos): al LLM solo se le envían los intereses y el
objetivo profesional, no el resto del perfil. perfil.yaml nunca se sube a GitHub.
"""
from pathlib import Path

import yaml

RUTA_PERFIL = Path(__file__).parent / "perfil.yaml"


def cargar_intereses(ruta: Path | str = RUTA_PERFIL) -> str | None:
    """Devuelve una línea con los intereses del usuario, o None si no hay perfil."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    try:
        # safe_load: nunca yaml.load, que puede ejecutar código si el archivo es malicioso
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(datos, dict):
        return None

    partes = []
    intereses = datos.get("intereses_noticias")
    if isinstance(intereses, list) and intereses:
        partes.append("temas de interés: " + ", ".join(str(i) for i in intereses[:15]))
    objetivo = datos.get("objetivo_profesional")
    if isinstance(objetivo, str) and objetivo.strip():
        partes.append("objetivo profesional: " + " ".join(objetivo.split())[:300])
    return "; ".join(partes) or None
