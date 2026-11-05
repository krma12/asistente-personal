# Módulo encargado de la integración con el servicio meteorológico wttr.in
import requests


def obtener_clima(ciudad: str) -> str:
    """
    Obtiene el clima actual de una ciudad usando wttr.in.

    Ahora recibe el nombre de la ciudad YA LIMPIO (lo extrae Claude),
    así que no hace falta borrar palabras como "en" o "de" del texto.
    (La versión anterior hacía .replace("en", "") y convertía "Denver" en "dver").

    Argumentos:
        ciudad: Nombre de la ciudad, p. ej. "Ciudad de México" o "Denver".

    Retorna:
        Texto con condición y temperatura, o un mensaje de error.
    """
    ciudad = (ciudad or "").strip()
    if not ciudad:
        return "Error: no se indicó ninguna ciudad."

    try:
        # requests codifica la URL por nosotros (espacios, acentos, etc.)
        response = requests.get(
            f"https://wttr.in/{requests.utils.quote(ciudad)}",
            params={"format": "%C, %t (sensación %f), humedad %h", "lang": "es"},
            timeout=10,
        )
        if response.status_code == 200 and response.text.strip():
            return f"{ciudad}: {response.text.strip()}"
        return f"No se pudo obtener el clima de '{ciudad}' (código {response.status_code})."
    except requests.RequestException as e:
        return f"Error de red al obtener el clima: {e}"
