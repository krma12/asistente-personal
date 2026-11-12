"""
Integración con Google Calendar: leer la agenda y proponer recordatorios.

Seguridad:
  - Permiso mínimo: solo eventos del calendario (calendar.events). Sin acceso a correo,
    Drive ni a la configuración de la cuenta.
  - Confirmación humana para escribir: el modelo solo PROPONE un recordatorio. Nada se crea
    hasta que el usuario lo confirma (botón en Telegram o "s" en la consola). Así, una
    inyección de prompt en una noticia o en una invitación no puede crear eventos sola.
  - Los títulos y descripciones de eventos se tratan como contenido NO confiable: cualquiera
    puede enviarte una invitación con texto malicioso.
  - Las credenciales viven en la carpeta secretos/ (ignorada por Git).
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from funciones_agente.contenido_externo import envolver, limpiar_texto, parece_inyeccion

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CARPETA_SECRETOS = Path(__file__).resolve().parent.parent / "secretos"
RUTA_CREDENCIALES = CARPETA_SECRETOS / "google_credentials.json"
RUTA_TOKEN = CARPETA_SECRETOS / "google_token.json"

MAX_PENDIENTES = 5
MAX_AVISO_MINUTOS = 40320  # 4 semanas: el máximo que acepta Google Calendar
AVISOS_POR_DEFECTO = [1440, 60]  # un día antes y una hora antes

# Recordatorios propuestos por el modelo, esperando confirmación del usuario
_pendientes: dict[str, dict] = {}


class CalendarioNoConfigurado(Exception):
    pass


def zona_local() -> ZoneInfo:
    return ZoneInfo(os.getenv("ZONA_HORARIA", "America/Mexico_City"))


def calendario_id() -> str:
    return os.getenv("CALENDARIO_ID", "primary")


def obtener_servicio():
    """Devuelve el cliente de Google Calendar usando el token guardado (sin abrir el navegador)."""
    if not RUTA_TOKEN.is_file():
        raise CalendarioNoConfigurado(
            "El calendario no está configurado. Ejecuta una vez: python configurar_calendario.py")
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credenciales = Credentials.from_authorized_user_file(str(RUTA_TOKEN), SCOPES)
    if not credenciales.valid:
        if credenciales.expired and credenciales.refresh_token:
            try:
                credenciales.refresh(Request())
            except RefreshError as e:
                raise CalendarioNoConfigurado(
                    "El permiso de Google expiró o fue revocado. Vuelve a ejecutar: "
                    "python configurar_calendario.py") from e
            RUTA_TOKEN.write_text(credenciales.to_json(), encoding="utf-8")
        else:
            raise CalendarioNoConfigurado("El token de Google no es válido. Ejecuta: python configurar_calendario.py")
    return build("calendar", "v3", credentials=credenciales, cache_discovery=False)


# ---------------------------------------------------------------------------
# Lectura de la agenda
# ---------------------------------------------------------------------------
def _formatear_inicio(evento: dict, zona: ZoneInfo) -> str:
    inicio = evento.get("start", {})
    if "dateTime" in inicio:
        momento = datetime.fromisoformat(inicio["dateTime"]).astimezone(zona)
        return momento.strftime("%Y-%m-%d %H:%M")
    return f"{inicio.get('date', 'sin fecha')} (todo el día)"


MAX_EVENTOS = 300  # tope total, aunque Google entregue más páginas


def obtener_eventos(dias: int = 7, desde_fecha: str | None = None,
                    ahora: datetime | None = None, servicio=None) -> str:
    """
    Lista los eventos del calendario.

    Sin desde_fecha: desde este momento y los siguientes `dias` (1 a 366, un año).
    Con desde_fecha (AAAA-MM-DD): desde el inicio de ese día, por `dias` días. Sirve para
    preguntas como "¿qué tengo el 20 de noviembre?" (desde_fecha=2026-11-20, dias=1).
    """
    dias = min(max(int(dias), 1), 366)
    zona = zona_local()
    if desde_fecha:
        try:
            dia = datetime.fromisoformat(str(desde_fecha).strip()[:10])
        except ValueError:
            return "Error: desde_fecha debe tener formato AAAA-MM-DD, por ejemplo 2026-11-20."
        desde = dia.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=zona)
    else:
        desde = (ahora or datetime.now(timezone.utc)).astimezone(zona)
    hasta = desde + timedelta(days=dias)

    try:
        servicio = servicio or obtener_servicio()
    except CalendarioNoConfigurado as e:
        return str(e)

    eventos, pagina, truncado = [], None, False
    try:
        while True:
            respuesta = servicio.events().list(
                calendarId=calendario_id(), timeMin=desde.isoformat(), timeMax=hasta.isoformat(),
                singleEvents=True, orderBy="startTime", maxResults=100, pageToken=pagina,
            ).execute()
            eventos.extend(respuesta.get("items", []))
            pagina = respuesta.get("nextPageToken")
            if not pagina:
                break
            if len(eventos) >= MAX_EVENTOS:
                truncado = True
                break
    except Exception as e:
        return f"Error al leer el calendario ({type(e).__name__})."
    if len(eventos) > MAX_EVENTOS:
        eventos, truncado = eventos[:MAX_EVENTOS], True

    rango = f"{desde.strftime('%Y-%m-%d')} a {hasta.strftime('%Y-%m-%d')}"
    encabezado = f"AGENDA — del {rango} (zona {zona.key}): {len(eventos)} evento(s)."
    if truncado:
        encabezado += (f" ATENCIÓN: hay más de {MAX_EVENTOS} eventos; solo se muestran los primeros. "
                       "Para fechas posteriores, consulta con desde_fecha.")
    if not eventos:
        return encabezado + "\nNo hay eventos en ese rango."
    # Con muchos eventos se omiten las descripciones: ahorra tokens del modelo
    compacto = len(eventos) > 40
    if compacto:
        encabezado += " (formato compacto: sin descripciones)"
    lineas = []
    for evento in eventos:
        titulo = limpiar_texto(evento.get("summary") or "(sin título)", 150)
        lugar = limpiar_texto(evento.get("location"), 100)
        descripcion = "" if compacto else limpiar_texto(evento.get("description"), 200)
        linea = f"- {_formatear_inicio(evento, zona)} | {titulo}"
        if lugar:
            linea += f" | {lugar}"
        lineas.append(linea)
        if descripcion:
            lineas.append(f"    {descripcion}")
        if parece_inyeccion(titulo, lugar, descripcion):
            lineas.append("    ⚠ ALERTA: este evento contiene frases típicas de inyección de instrucciones.")
    return encabezado + "\n" + envolver(lineas)


# ---------------------------------------------------------------------------
# Recordatorios con confirmación humana
# ---------------------------------------------------------------------------
def proponer_recordatorio(titulo: str, fecha_hora: str, duracion_minutos: int = 30,
                          avisos_minutos_antes: list | None = None, lugar: str = "",
                          ahora: datetime | None = None) -> str:
    """
    Prepara un recordatorio SIN crearlo. Queda pendiente hasta que el usuario lo confirme.

    fecha_hora: "AAAA-MM-DDTHH:MM" en hora local del usuario (ZONA_HORARIA).
    avisos_minutos_antes: notificaciones de Google Calendar (p. ej. [1440, 60] = 1 día y 1 hora antes).
    """
    zona = zona_local()
    titulo = limpiar_texto(titulo, 100)
    if not titulo:
        return "Error: el recordatorio necesita un título."
    try:
        inicio = datetime.fromisoformat(str(fecha_hora).strip())
    except ValueError:
        return "Error: fecha_hora debe tener formato AAAA-MM-DDTHH:MM, por ejemplo 2026-11-20T17:30."
    inicio = inicio.replace(tzinfo=zona) if inicio.tzinfo is None else inicio.astimezone(zona)

    ahora = (ahora or datetime.now(timezone.utc)).astimezone(zona)
    if inicio < ahora:
        return "Error: la fecha ya pasó. Pide al usuario una fecha futura."
    if inicio > ahora + timedelta(days=366):
        return "Error: solo se pueden crear recordatorios dentro del próximo año."

    duracion = min(max(int(duracion_minutos), 5), 1440)
    avisos = AVISOS_POR_DEFECTO if avisos_minutos_antes is None else avisos_minutos_antes
    try:
        avisos = sorted({int(a) for a in avisos}, reverse=True)[:5]
    except (TypeError, ValueError):
        return "Error: avisos_minutos_antes debe ser una lista de minutos, por ejemplo [1440, 60]."
    if any(a < 0 or a > MAX_AVISO_MINUTOS for a in avisos):
        return f"Error: cada aviso debe estar entre 0 y {MAX_AVISO_MINUTOS} minutos (4 semanas)."

    if len(_pendientes) >= MAX_PENDIENTES:
        return "Error: ya hay varios recordatorios esperando confirmación. Que el usuario confirme o cancele antes."

    identificador = secrets.token_hex(4)
    _pendientes[identificador] = {
        "id": identificador, "titulo": titulo, "inicio": inicio,
        "fin": inicio + timedelta(minutes=duracion), "avisos": avisos,
        "lugar": limpiar_texto(lugar, 100),
    }
    return (f"Recordatorio PREPARADO pero NO creado (id {identificador}): '{titulo}' el "
            f"{inicio.strftime('%Y-%m-%d a las %H:%M')}. El usuario debe confirmarlo; "
            "dile que revise y confirme, no afirmes que ya está en su calendario.")


def describir(propuesta: dict) -> str:
    """Texto para que el usuario revise antes de confirmar."""
    avisos = ", ".join(_texto_aviso(a) for a in propuesta["avisos"]) or "sin avisos"
    texto = (f"📅 ¿Creo este recordatorio en tu Google Calendar?\n\n"
             f"• {propuesta['titulo']}\n"
             f"• {propuesta['inicio'].strftime('%Y-%m-%d %H:%M')} a {propuesta['fin'].strftime('%H:%M')}\n"
             f"• Avisos: {avisos}")
    if propuesta["lugar"]:
        texto += f"\n• Lugar: {propuesta['lugar']}"
    return texto


def _texto_aviso(minutos: int) -> str:
    if minutos == 0:
        return "a la hora"
    if minutos % 1440 == 0:
        dias = minutos // 1440
        return f"{dias} día{'s' if dias > 1 else ''} antes"
    if minutos % 60 == 0:
        horas = minutos // 60
        return f"{horas} hora{'s' if horas > 1 else ''} antes"
    return f"{minutos} min antes"


def pendientes() -> list[dict]:
    return list(_pendientes.values())


def descartar_recordatorio(identificador: str) -> str:
    propuesta = _pendientes.pop(identificador, None)
    return f"Cancelado: '{propuesta['titulo']}'." if propuesta else "Ese recordatorio ya no está pendiente."


def confirmar_recordatorio(identificador: str, servicio=None) -> str:
    """Crea en Google Calendar un recordatorio que el usuario ya confirmó."""
    propuesta = _pendientes.get(identificador)
    if propuesta is None:
        return "Ese recordatorio ya no está pendiente (ya se creó o se canceló)."
    try:
        servicio = servicio or obtener_servicio()
    except CalendarioNoConfigurado as e:
        return str(e)

    zona = zona_local()
    cuerpo = {
        "summary": propuesta["titulo"],
        "start": {"dateTime": propuesta["inicio"].isoformat(), "timeZone": zona.key},
        "end": {"dateTime": propuesta["fin"].isoformat(), "timeZone": zona.key},
        "reminders": {"useDefault": False,
                      "overrides": [{"method": "popup", "minutes": a} for a in propuesta["avisos"]]},
        "description": "Creado por mi asistente personal (confirmado por mí).",
    }
    if propuesta["lugar"]:
        cuerpo["location"] = propuesta["lugar"]
    try:
        evento = servicio.events().insert(calendarId=calendario_id(), body=cuerpo).execute()
    except Exception as e:
        return f"No se pudo crear el recordatorio ({type(e).__name__}). Sigue pendiente; intenta de nuevo."
    _pendientes.pop(identificador, None)
    return f"✅ Listo, quedó en tu calendario: '{propuesta['titulo']}'. {evento.get('htmlLink', '')}".strip()
