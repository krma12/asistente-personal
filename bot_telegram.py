"""
Bot de Telegram para el asistente personal.

Ejecuta:  python bot_telegram.py   (debe quedarse corriendo; Ctrl+C para detenerlo)

Seguridad:
  - Lista blanca: SOLO responde al chat de TELEGRAM_CHAT_ID. Cualquier otra persona que
    encuentre el bot es ignorada (así nadie puede gastar tu cuota de la API ni leer tu perfil).
  - El token nunca se imprime: se silencia el registro de httpx, que por defecto muestra
    las URL de la API de Telegram, y el token va dentro de esas URL.
  - Sin modo administrador ni comandos peligrosos: el bot solo conversa con el asistente,
    cuyas herramientas son de solo lectura.

Primer uso: si TELEGRAM_CHAT_ID no está en .env, el bot responde a /start con tu ID
para que lo copies al .env. Después de reiniciar, ya solo te responde a ti.
"""
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import time as dtime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
)

from funciones_agente import calendario
from perfil import cargar_intereses
from proveedores import crear_asistente

LIMITE_TELEGRAM = 4096  # caracteres máximos por mensaje
VALORES_DE_PLANTILLA = {"", "tu_token_aqui"}  # lo que trae .env.example: no es un token real

NOTAS_TELEGRAM = (
    "CANAL: Telegram en el celular. Responde en texto plano, sin Markdown (nada de **, # ni "
    "tablas); usa saltos de línea y viñetas con '•'. Pon los enlaces completos para que se "
    "puedan tocar. Sé breve."
)

PEDIDO_RESUMEN = (
    "Dame mi resumen de hoy. Primero mi agenda de hoy y los próximos 3 días (si el calendario "
    "no está configurado, omítela sin insistir). Después lo más relevante para mis intereses en "
    "ciberseguridad (incluye las vulnerabilidades explotadas recientes de CISA KEV), "
    "inteligencia artificial, tecnología y geopolítica. Máximo 3 noticias por tema."
)

log = logging.getLogger("asistente.telegram")


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
@dataclass
class Config:
    token: str
    chat_id: int | None      # None = modo "primer uso": solo dice el ID con /start
    hora_resumen: dtime      # hora local de la pregunta matutina


def leer_config(entorno=os.environ) -> Config:
    """Lee y valida la configuración del .env. Lanza ValueError con un mensaje claro."""
    token = (entorno.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if token in VALORES_DE_PLANTILLA:
        raise ValueError("Falta TELEGRAM_BOT_TOKEN en tu archivo .env (te lo da @BotFather).")
    if not re.fullmatch(r"\d+:[\w-]{20,}", token):
        raise ValueError("TELEGRAM_BOT_TOKEN no tiene el formato esperado (números:letras).")

    chat_texto = (entorno.get("TELEGRAM_CHAT_ID") or "").strip()
    chat_id = None
    if chat_texto:
        if not re.fullmatch(r"-?\d+", chat_texto):
            raise ValueError("TELEGRAM_CHAT_ID debe ser un número.")
        chat_id = int(chat_texto)

    zona_texto = (entorno.get("ZONA_HORARIA") or "America/Mexico_City").strip()
    try:
        zona = ZoneInfo(zona_texto)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"ZONA_HORARIA '{zona_texto}' no es válida.") from e

    hora_texto = (entorno.get("HORA_RESUMEN") or "08:00").strip()
    coincide = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", hora_texto)
    if not coincide:
        raise ValueError("HORA_RESUMEN debe tener formato HH:MM, por ejemplo 08:00.")
    hora = dtime(int(coincide.group(1)), int(coincide.group(2)), tzinfo=zona)

    return Config(token=token, chat_id=chat_id, hora_resumen=hora)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def autorizado(update: Update, cfg: Config) -> bool:
    """True solo si el mensaje viene del chat permitido."""
    chat = update.effective_chat
    permitido = cfg.chat_id is not None and chat is not None and chat.id == cfg.chat_id
    if not permitido and chat is not None:
        # Solo se registra el ID, nunca el contenido del mensaje
        log.warning("Mensaje ignorado de un chat no autorizado (id %s).", chat.id)
    return permitido


def dividir_mensaje(texto: str, limite: int = LIMITE_TELEGRAM) -> list[str]:
    """Parte un texto largo en trozos que Telegram acepte, cortando de preferencia en saltos de línea."""
    texto = texto.strip() or "(respuesta vacía)"
    partes = []
    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)
        if corte < limite // 2:  # sin salto de línea útil: corta en un espacio o a la fuerza
            corte = texto.rfind(" ", 0, limite)
        if corte <= 0:
            corte = limite
        partes.append(texto[:corte].rstrip())
        texto = texto[corte:].lstrip()
    partes.append(texto)
    return partes


def mensaje_de_error(error: Exception) -> str:
    """Explica el error en palabras simples, sin mostrar detalles internos."""
    if type(error).__name__ == "RateLimitError" or "429" in str(error):
        return ("Llegué al límite gratuito de peticiones por minuto del modelo de IA. "
                "Espera uno o dos minutos y vuelve a intentarlo. Si pasa seguido, "
                "pregunta por rangos de fechas más cortos.")
    if type(error).__name__ in {"AuthenticationError", "PermissionDeniedError"}:
        return "La clave de la API del modelo no es válida o expiró. Revisa tu archivo .env."
    if type(error).__name__ in {"APIConnectionError", "APITimeoutError"}:
        return "No pude conectarme al modelo de IA. Revisa tu conexión a internet."
    return ("No pude responder ahora (error al consultar el modelo). "
            "Si se repite, revisa la consola donde corre el bot.")


def teclado_resumen() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Sí, dame mi resumen", callback_data="resumen:si"),
        InlineKeyboardButton("Hoy no", callback_data="resumen:no"),
    ]])


async def preguntar_al_asistente(context: ContextTypes.DEFAULT_TYPE, chat_id: int, texto: str) -> None:
    """Envía la pregunta al asistente (en otro hilo, para no congelar el bot) y responde."""
    asistente = context.bot_data["asistente"]
    candado = context.bot_data["candado"]
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        async with candado:  # una pregunta a la vez: el historial no se mezcla
            respuesta = await asyncio.to_thread(asistente.preguntar, texto)
    except Exception as e:
        log.error("Error al consultar al modelo: %s", type(e).__name__)
        respuesta = mensaje_de_error(e)
    for parte in dividir_mensaje(respuesta):
        await context.bot.send_message(chat_id=chat_id, text=parte, disable_web_page_preview=True)
    await mostrar_recordatorios_pendientes(context, chat_id)


def teclado_recordatorio(identificador: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Crear", callback_data=f"rec:si:{identificador}"),
        InlineKeyboardButton("❌ Cancelar", callback_data=f"rec:no:{identificador}"),
    ]])


async def mostrar_recordatorios_pendientes(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Confirmación humana: cada recordatorio propuesto se muestra con botones Crear/Cancelar."""
    ya_mostrados = context.bot_data.setdefault("recordatorios_mostrados", set())
    for propuesta in calendario.pendientes():
        if propuesta["id"] in ya_mostrados:
            continue
        ya_mostrados.add(propuesta["id"])
        await context.bot.send_message(chat_id=chat_id, text=calendario.describir(propuesta),
                                       reply_markup=teclado_recordatorio(propuesta["id"]))


# ---------------------------------------------------------------------------
# Manejadores
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = context.bot_data["config"]
    if cfg.chat_id is None:
        await update.effective_message.reply_text(
            f"Tu ID de chat es: {update.effective_chat.id}\n\n"
            "Agrégalo a tu archivo .env así:\n"
            f"TELEGRAM_CHAT_ID={update.effective_chat.id}\n\n"
            "Luego reinicia el bot. A partir de ahí solo te responderé a ti."
        )
        return
    if not autorizado(update, cfg):
        return
    await update.effective_message.reply_text(
        "¡Hola! Soy tu asistente personal.\n\n"
        "Escríbeme lo que necesites: clima, precio de acciones, la hora en cualquier lugar, "
        "noticias, vulnerabilidades explotadas, tu agenda o un recordatorio (por ejemplo: "
        "'recuérdame el viernes a las 5 ir al banco'). Siempre te pediré confirmar antes de "
        "crear algo en tu calendario.\n\n"
        f"Cada día a las {cfg.hora_resumen.strftime('%H:%M')} te preguntaré si quieres tu "
        "resumen (agenda y noticias).\n\n"
        "Comandos:\n/noticias – resumen de hoy (agenda y noticias)\n/reiniciar – borrar la conversación"
    )


async def cmd_noticias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if autorizado(update, context.bot_data["config"]):
        await preguntar_al_asistente(context, update.effective_chat.id, PEDIDO_RESUMEN)


async def cmd_reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if autorizado(update, context.bot_data["config"]):
        context.bot_data["asistente"].historial.clear()
        await update.effective_message.reply_text("Listo, empecemos de cero.")


async def mensaje_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if autorizado(update, context.bot_data["config"]):
        await preguntar_al_asistente(context, update.effective_chat.id, update.effective_message.text)


async def boton_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    consulta = update.callback_query
    if not autorizado(update, context.bot_data["config"]):
        await consulta.answer()
        return
    await consulta.answer()
    if consulta.data == "resumen:si":
        await consulta.edit_message_text("¡Va! Preparando tu resumen…")
        await preguntar_al_asistente(context, update.effective_chat.id, PEDIDO_RESUMEN)
    else:
        await consulta.edit_message_text("Está bien, hoy no. Si cambias de opinión, usa /noticias.")


async def boton_recordatorio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    consulta = update.callback_query
    await consulta.answer()
    if not autorizado(update, context.bot_data["config"]):
        return
    _, decision, identificador = consulta.data.split(":")
    if decision == "si":
        resultado = await asyncio.to_thread(calendario.confirmar_recordatorio, identificador)
    else:
        resultado = calendario.descartar_recordatorio(identificador)
    await consulta.edit_message_text(resultado, disable_web_page_preview=True)


async def pregunta_matutina(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="¡Buenos días! ¿Quieres tu resumen de hoy (agenda y noticias)?",
        reply_markup=teclado_resumen(),
    )


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------
def construir_app(cfg: Config, asistente) -> Application:
    app = Application.builder().token(cfg.token).build()
    app.bot_data.update(config=cfg, asistente=asistente, candado=asyncio.Lock())
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("noticias", cmd_noticias))
    app.add_handler(CommandHandler("reiniciar", cmd_reiniciar))
    app.add_handler(CallbackQueryHandler(boton_resumen, pattern=r"^resumen:(si|no)$"))
    app.add_handler(CallbackQueryHandler(boton_recordatorio, pattern=r"^rec:(si|no):[0-9a-f]{8}$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_texto))
    if cfg.chat_id is not None:
        app.job_queue.run_daily(pregunta_matutina, time=cfg.hora_resumen,
                                chat_id=cfg.chat_id, name="pregunta_matutina")
    return app


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    # httpx registra cada URL de la API, y la URL de Telegram contiene el token: se silencia.
    # (La librería de OpenAI usa httpx2, que también registra cada petición.)
    for registro in ("httpx", "httpx2", "openai"):
        logging.getLogger(registro).setLevel(logging.WARNING)
    load_dotenv()

    try:
        cfg = leer_config()
        asistente = crear_asistente(intereses=cargar_intereses(), notas_extra=NOTAS_TELEGRAM)
    except ValueError as e:
        print(f"Error de configuración: {e}")
        raise SystemExit(1) from e

    if cfg.chat_id is None:
        print("Modo primer uso: abre tu bot en Telegram y envía /start para conocer tu ID.")
    else:
        print(f"Bot listo (proveedor: {asistente.nombre}). Pregunta matutina a las "
              f"{cfg.hora_resumen.strftime('%H:%M')}. Ctrl+C para detener.")
    construir_app(cfg, asistente).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
