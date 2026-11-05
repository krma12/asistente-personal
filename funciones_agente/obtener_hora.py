# Módulo para consultar la fecha y hora actual en cualquier zona horaria
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ZONA_POR_DEFECTO = "America/Mexico_City"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def obtener_hora(zona_horaria: str = ZONA_POR_DEFECTO, ahora: datetime | None = None) -> str:
    """
    Devuelve la fecha y hora actual en una zona horaria IANA.

    No usa internet: Python calcula la hora con la base de datos de zonas horarias
    (en Windows la aporta el paquete `tzdata` de requirements.txt).

    Argumentos:
        zona_horaria: Nombre IANA, p. ej. "Asia/Shanghai", "Europe/Madrid".
        ahora: Solo para pruebas; permite fijar el momento "actual".

    Retorna:
        Texto con día, fecha, hora y diferencia con UTC, o un mensaje de error.
    """
    zona_horaria = (zona_horaria or ZONA_POR_DEFECTO).strip()
    try:
        zona = ZoneInfo(zona_horaria)
    except (ZoneInfoNotFoundError, ValueError):
        return (f"Error: la zona horaria '{zona_horaria}' no existe. "
                "Usa un nombre IANA como 'Asia/Shanghai' o 'America/Sao_Paulo'.")

    momento = (ahora or datetime.now(tz=zona)).astimezone(zona)
    desfase = momento.strftime("%z")  # p. ej. +0800
    utc = f"UTC{desfase[:3]}:{desfase[3:]}"
    return (f"{zona_horaria}: {DIAS[momento.weekday()]} {momento.day} de "
            f"{MESES[momento.month - 1]} de {momento.year}, "
            f"{momento.strftime('%H:%M')} ({utc})")
