"""
Pruebas automáticas. Ejecuta:  python -m pytest -v

No usan internet ni gastan créditos de la API: las respuestas externas
(wttr.in, yfinance y los LLM) se simulan con "mocks".
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

import pytest

import proveedores
from proveedores import AsistenteClaude, AsistenteOpenAICompatible, crear_asistente
from funciones_agente.obtener_clima import obtener_clima
from funciones_agente.obtener_precio_accion import obtener_precio_accion, resolver_ticker
from funciones_agente.obtener_hora import obtener_hora
from herramientas import ejecutar_herramienta


# ---------- Clima ----------

@patch("funciones_agente.obtener_clima.requests.get")
def test_clima_no_mutila_nombres(mock_get):
    """Bug de v1: 'Denver' se convertía en 'dver'. Ahora la ciudad llega intacta a la URL."""
    mock_get.return_value = MagicMock(status_code=200, text="Soleado, +12°C")
    resultado = obtener_clima("Denver")
    assert "Denver" in mock_get.call_args[0][0]
    assert resultado == "Denver: Soleado, +12°C"


@patch("funciones_agente.obtener_clima.requests.get")
def test_clima_ciudad_con_espacios_y_acentos(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="Nublado, +18°C")
    obtener_clima("Ciudad de México")
    url = mock_get.call_args[0][0]
    assert url == "https://wttr.in/Ciudad%20de%20M%C3%A9xico"


def test_clima_sin_ciudad():
    assert obtener_clima("  ").startswith("Error")


# ---------- Acciones ----------

def test_resolver_ticker():
    assert resolver_ticker("Microsoft") == "MSFT"
    assert resolver_ticker("nvda") == "NVDA"
    assert resolver_ticker("WALMEX.MX") == "WALMEX.MX"


@patch("funciones_agente.obtener_precio_accion.yf.Ticker")
def test_precio_accion(mock_ticker):
    datos = pd.DataFrame({"Close": [410.5]}, index=pd.to_datetime(["2026-10-30"]))
    mock_ticker.return_value.history.return_value = datos
    mock_ticker.return_value.fast_info = {"currency": "USD"}
    assert obtener_precio_accion("MSFT") == "MSFT: 410.50 USD (cierre del 2026-10-30)"


@patch("funciones_agente.obtener_precio_accion.yf.Ticker")
def test_precio_accion_ticker_invalido(mock_ticker):
    mock_ticker.return_value.history.return_value = pd.DataFrame()
    assert "No se encontraron" in obtener_precio_accion("XXXX")


# ---------- Hora ----------

def test_hora_en_beijing():
    from datetime import datetime, timezone
    momento = datetime(2026, 11, 5, 3, 40, tzinfo=timezone.utc)  # 21:40 del 4 nov en CDMX
    assert obtener_hora("Asia/Shanghai", ahora=momento) == (
        "Asia/Shanghai: jueves 5 de noviembre de 2026, 11:40 (UTC+08:00)")


def test_hora_en_cdmx_por_defecto():
    from datetime import datetime, timezone
    momento = datetime(2026, 11, 5, 3, 40, tzinfo=timezone.utc)
    assert obtener_hora(ahora=momento) == (
        "America/Mexico_City: miércoles 4 de noviembre de 2026, 21:40 (UTC-06:00)")


def test_hora_respeta_horario_de_verano():
    """La misma zona cambia de desfase según la fecha: lo resuelve tzdata, no el código."""
    from datetime import datetime, timezone
    invierno = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    verano = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    assert obtener_hora("Europe/Madrid", ahora=invierno).endswith("13:00 (UTC+01:00)")
    assert obtener_hora("Europe/Madrid", ahora=verano).endswith("14:00 (UTC+02:00)")
    # Tijuana sigue el horario de verano de EE. UU.; la Ciudad de México ya no lo usa
    assert obtener_hora("America/Tijuana", ahora=verano).endswith("(UTC-07:00)")
    assert obtener_hora("America/Mexico_City", ahora=verano).endswith("(UTC-06:00)")


def test_hora_zona_invalida():
    assert obtener_hora("Marte/Base_Alfa").startswith("Error")


# ---------- Registro de herramientas ----------

def test_herramienta_inexistente():
    assert "no existe" in ejecutar_herramienta("volar", {})


def test_herramienta_argumentos_invalidos():
    assert "argumentos inválidos" in ejecutar_herramienta("obtener_clima", {"pais": "MX"})


# ---------- Claude simulado ----------

def _bloque_texto(texto):
    return SimpleNamespace(type="text", text=texto)


def _bloque_tool(nombre, entrada):
    return SimpleNamespace(type="tool_use", id="tool_1", name=nombre, input=entrada)


@patch("proveedores.ejecutar_herramienta", return_value="Denver: Soleado, +12°C")
def test_claude_ciclo_tool_use(mock_ejecutar):
    cliente = MagicMock()
    cliente.messages.create.side_effect = [
        SimpleNamespace(stop_reason="tool_use",
                        content=[_bloque_tool("obtener_clima", {"ciudad": "Denver"})]),
        SimpleNamespace(stop_reason="end_turn",
                        content=[_bloque_texto("En Denver está soleado, 12 °C.")]),
    ]
    asistente = AsistenteClaude(cliente=cliente)

    assert asistente.preguntar("¿clima en Denver?") == "En Denver está soleado, 12 °C."
    mock_ejecutar.assert_called_once_with("obtener_clima", {"ciudad": "Denver"})
    # usuario -> asistente(tool_use) -> usuario(tool_result) -> asistente(texto)
    assert [m["role"] for m in asistente.historial] == ["user", "assistant", "user", "assistant"]
    assert asistente.historial[2]["content"][0]["tool_use_id"] == "tool_1"


# ---------- Gemini / Groq / Ollama simulados (formato OpenAI) ----------

def _respuesta_openai(contenido=None, tool_calls=None):
    mensaje = SimpleNamespace(content=contenido, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def _llamada(nombre, argumentos_json):
    return SimpleNamespace(id="call_1", type="function",
                           function=SimpleNamespace(name=nombre, arguments=argumentos_json))


def test_formato_openai_de_herramientas():
    convertidas = proveedores.herramientas_formato_openai()
    assert convertidas[0]["type"] == "function"
    assert convertidas[0]["function"]["parameters"]["required"] == ["ciudad"]


@patch("proveedores.ejecutar_herramienta", return_value="MSFT: 410.50 USD (cierre del 2026-10-30)")
def test_openai_compatible_ciclo_tool_use(mock_ejecutar):
    cliente = MagicMock()
    cliente.chat.completions.create.side_effect = [
        _respuesta_openai(tool_calls=[_llamada("obtener_precio_accion", '{"ticker": "MSFT"}')]),
        _respuesta_openai(contenido="Microsoft cerró en 410.50 USD."),
    ]
    asistente = AsistenteOpenAICompatible("groq", cliente=cliente)

    assert asistente.preguntar("¿precio de Microsoft?") == "Microsoft cerró en 410.50 USD."
    mock_ejecutar.assert_called_once_with("obtener_precio_accion", {"ticker": "MSFT"})
    assert [m["role"] for m in asistente.historial] == ["user", "assistant", "tool", "assistant"]
    # el system prompt siempre va primero en cada llamada
    mensajes_enviados = cliente.chat.completions.create.call_args.kwargs["messages"]
    assert mensajes_enviados[0]["role"] == "system"


def test_error_deshace_la_pregunta():
    cliente = MagicMock()
    cliente.chat.completions.create.side_effect = RuntimeError("límite alcanzado")
    asistente = AsistenteOpenAICompatible("gemini", cliente=cliente)
    with pytest.raises(RuntimeError):
        asistente.preguntar("hola")
    assert asistente.historial == []


def test_recortar_historial_empieza_en_pregunta():
    historial = []
    for i in range(15):
        historial += [{"role": "user", "content": f"pregunta {i}"},
                      {"role": "assistant", "content": "ok"}]
    recortado = proveedores._recortar(historial, proveedores._es_pregunta)
    assert len(recortado) <= proveedores.MAX_MENSAJES_HISTORIAL
    assert proveedores._es_pregunta(recortado[0])


# ---------- Selección de proveedor desde el .env ----------

def test_crear_asistente_sin_clave(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        crear_asistente("gemini")


def test_crear_asistente_proveedor_invalido():
    with pytest.raises(ValueError, match="no es válido"):
        crear_asistente("chatgpt-pirata")


def test_crear_asistente_ollama_no_necesita_clave():
    asistente = crear_asistente("ollama")
    assert asistente.nombre == "ollama" and asistente.modelo == "qwen3:4b"


def test_crear_asistente_respeta_modelo(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "clave-falsa")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")
    assert crear_asistente("groq").modelo == "llama-3.3-70b-versatile"


def test_conserva_firma_de_gemini():
    """Gemini 3 exige recibir de vuelta extra_content.google.thought_signature (si no: Error 400)."""
    from openai.types.chat import ChatCompletionMessage

    mensaje = ChatCompletionMessage.model_validate({
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1", "type": "function",
            "function": {"name": "obtener_precio_accion", "arguments": '{"ticker": "NVDA"}'},
            "extra_content": {"google": {"thought_signature": "firma-secreta"}},
        }],
    })
    datos = proveedores._mensaje_a_dict(mensaje)
    assert datos["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "firma-secreta"
    assert datos["role"] == "assistant" and datos["content"] == ""
