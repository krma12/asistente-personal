"""
Pruebas del bot de Telegram. No se conectan a Telegram: el bot y los mensajes se simulan.
"""
import asyncio
from datetime import time as dtime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

import bot_telegram as bot
from proveedores import construir_system_prompt

TOKEN_FALSO = "123456789:AAH_token_de_prueba_ficticio_123"
MI_CHAT = 111
EXTRANO = 999


def config(chat_id=MI_CHAT):
    return bot.Config(token=TOKEN_FALSO, chat_id=chat_id,
                      hora_resumen=dtime(8, 0, tzinfo=ZoneInfo("America/Mexico_City")))


def contexto(cfg, respuesta="Respuesta del asistente"):
    asistente = MagicMock()
    asistente.preguntar.return_value = respuesta
    asistente.historial = ["algo"]
    return SimpleNamespace(
        bot_data={"config": cfg, "asistente": asistente, "candado": asyncio.Lock()},
        bot=SimpleNamespace(send_message=AsyncMock(), send_chat_action=AsyncMock()),
    )


def mensaje(chat_id, texto="hola"):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_message=SimpleNamespace(text=texto, reply_text=AsyncMock()),
    )


# ---------- Configuración ----------

def test_config_valida():
    cfg = bot.leer_config({"TELEGRAM_BOT_TOKEN": TOKEN_FALSO, "TELEGRAM_CHAT_ID": "111",
                           "HORA_RESUMEN": "7:30"})
    assert cfg.chat_id == 111 and cfg.hora_resumen.hour == 7 and cfg.hora_resumen.minute == 30
    assert cfg.hora_resumen.tzinfo == ZoneInfo("America/Mexico_City")


@pytest.mark.parametrize("entorno, error", [
    ({}, "Falta TELEGRAM_BOT_TOKEN"),
    ({"TELEGRAM_BOT_TOKEN": "tu_token_aqui"}, "Falta TELEGRAM_BOT_TOKEN"),
    ({"TELEGRAM_BOT_TOKEN": "no-es-un-token"}, "formato"),
    ({"TELEGRAM_BOT_TOKEN": TOKEN_FALSO, "TELEGRAM_CHAT_ID": "abc"}, "número"),
    ({"TELEGRAM_BOT_TOKEN": TOKEN_FALSO, "HORA_RESUMEN": "25:00"}, "HH:MM"),
    ({"TELEGRAM_BOT_TOKEN": TOKEN_FALSO, "ZONA_HORARIA": "Marte/Base"}, "ZONA_HORARIA"),
])
def test_config_invalida(entorno, error):
    with pytest.raises(ValueError, match=error):
        bot.leer_config(entorno)


def test_sin_chat_id_es_modo_primer_uso():
    assert bot.leer_config({"TELEGRAM_BOT_TOKEN": TOKEN_FALSO}).chat_id is None


def test_el_token_no_aparece_en_los_errores():
    with pytest.raises(ValueError) as error:
        bot.leer_config({"TELEGRAM_BOT_TOKEN": TOKEN_FALSO, "TELEGRAM_CHAT_ID": "x"})
    assert TOKEN_FALSO not in str(error.value)


# ---------- Lista blanca ----------

def test_ignora_a_extranos():
    ctx = contexto(config())
    update = mensaje(EXTRANO, "gasta la cuota de Hugo")
    asyncio.run(bot.mensaje_texto(update, ctx))
    ctx.bot_data["asistente"].preguntar.assert_not_called()
    ctx.bot.send_message.assert_not_called()


def test_responde_al_chat_autorizado():
    ctx = contexto(config(), "En CDMX hay 18 °C")
    asyncio.run(bot.mensaje_texto(mensaje(MI_CHAT, "¿clima en CDMX?"), ctx))
    ctx.bot_data["asistente"].preguntar.assert_called_once_with("¿clima en CDMX?")
    ctx.bot.send_message.assert_awaited_once()
    assert ctx.bot.send_message.call_args.kwargs["text"] == "En CDMX hay 18 °C"
    assert ctx.bot.send_message.call_args.kwargs["chat_id"] == MI_CHAT


def test_sin_chat_id_no_responde_a_nadie():
    ctx = contexto(config(chat_id=None))
    asyncio.run(bot.mensaje_texto(mensaje(MI_CHAT), ctx))
    ctx.bot_data["asistente"].preguntar.assert_not_called()


def test_primer_uso_start_muestra_el_id():
    ctx = contexto(config(chat_id=None))
    update = mensaje(MI_CHAT)
    asyncio.run(bot.cmd_start(update, ctx))
    texto = update.effective_message.reply_text.call_args.args[0]
    assert f"TELEGRAM_CHAT_ID={MI_CHAT}" in texto


def test_extrano_no_puede_reiniciar_la_conversacion():
    ctx = contexto(config())
    asyncio.run(bot.cmd_reiniciar(mensaje(EXTRANO), ctx))
    assert ctx.bot_data["asistente"].historial == ["algo"]


def test_boton_de_extrano_no_dispara_el_resumen():
    ctx = contexto(config())
    consulta = SimpleNamespace(data="resumen:si", answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=EXTRANO), callback_query=consulta)
    asyncio.run(bot.boton_resumen(update, ctx))
    ctx.bot_data["asistente"].preguntar.assert_not_called()
    consulta.edit_message_text.assert_not_called()


def test_boton_si_pide_el_resumen():
    ctx = contexto(config())
    consulta = SimpleNamespace(data="resumen:si", answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=MI_CHAT), callback_query=consulta)
    asyncio.run(bot.boton_resumen(update, ctx))
    ctx.bot_data["asistente"].preguntar.assert_called_once_with(bot.PEDIDO_RESUMEN)


# ---------- Errores y mensajes largos ----------

def test_error_del_modelo_da_mensaje_amable():
    ctx = contexto(config())
    ctx.bot_data["asistente"].preguntar.side_effect = RuntimeError("429 límite")
    asyncio.run(bot.mensaje_texto(mensaje(MI_CHAT), ctx))
    assert "No pude responder" in ctx.bot.send_message.call_args.kwargs["text"]


def test_dividir_mensaje_respeta_el_limite():
    texto = "\n".join(f"Línea {i} " + "x" * 80 for i in range(200))  # ~18,000 caracteres
    partes = bot.dividir_mensaje(texto)
    assert len(partes) > 1 and all(len(p) <= bot.LIMITE_TELEGRAM for p in partes)
    assert "".join(p.replace("\n", "") for p in partes) == texto.replace("\n", "")


def test_mensaje_corto_no_se_divide():
    assert bot.dividir_mensaje("hola") == ["hola"]


# ---------- Arranque ----------

def test_construir_app_registra_la_pregunta_matutina():
    app = bot.construir_app(config(), MagicMock())
    trabajos = app.job_queue.get_jobs_by_name("pregunta_matutina")
    assert len(trabajos) == 1
    assert app.bot_data["config"].chat_id == MI_CHAT


def test_primer_uso_no_programa_pregunta_matutina():
    app = bot.construir_app(config(chat_id=None), MagicMock())
    assert app.job_queue.get_jobs_by_name("pregunta_matutina") == ()


def test_prompt_de_telegram_pide_texto_plano():
    prompt = construir_system_prompt("temas de interés: IA", bot.NOTAS_TELEGRAM)
    assert "PERFIL DEL USUARIO" in prompt and "sin Markdown" in prompt
