"""
Proveedores de LLM intercambiables.

El chatbot no sabe (ni le importa) qué modelo hay detrás: solo llama a
asistente.preguntar(texto). Cambias de proveedor con una línea en el .env:

    LLM_PROVIDER=gemini    # gratis (Google AI Studio)
    LLM_PROVIDER=groq      # gratis (console.groq.com)
    LLM_PROVIDER=ollama    # gratis y local (ollama.com)
    LLM_PROVIDER=claude    # de pago (console.anthropic.com)

Hay dos "adaptadores":
  - AsistenteClaude: usa el SDK oficial de Anthropic.
  - AsistenteOpenAICompatible: Gemini, Groq y Ollama aceptan el formato de la API
    de OpenAI, así que un solo adaptador sirve para los tres; solo cambia la URL.
"""
import json
import os

from herramientas import TOOLS, ejecutar_herramienta

SYSTEM_PROMPT = (
    "Eres un asistente personal que responde en español de forma breve y clara. "
    "Tienes herramientas para consultar el clima, el precio de acciones y la fecha y hora "
    "de cualquier zona horaria. "
    "Úsalas cuando la pregunta lo requiera; nunca inventes temperaturas, precios, fechas ni horas. "
    "Si una herramienta devuelve un error, explícaselo al usuario con palabras simples. "
    "Si te preguntan algo fuera de tus herramientas, responde con tu conocimiento general "
    "y aclara que no tienes datos en tiempo real sobre ese tema."
)

MAX_PASOS_HERRAMIENTAS = 5   # Evita ciclos infinitos si algo sale mal
MAX_MENSAJES_HISTORIAL = 20  # Para no mandar conversaciones enormes a la API

# Configuración de cada proveedor compatible con OpenAI.
# Los modelos se pueden cambiar con LLM_MODEL en el .env (los catálogos cambian seguido).
PROVEEDORES_OPENAI = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "variable_clave": "GEMINI_API_KEY",
        "modelo": "gemini-3.5-flash",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "variable_clave": "GROQ_API_KEY",
        "modelo": "openai/gpt-oss-20b",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "variable_clave": None,  # Ollama corre en tu PC: no necesita clave
        "modelo": "qwen3:4b",
    },
}


def _registrar_uso(nombre, argumentos):
    print(f"   [usando {nombre}({argumentos})]")


def _recortar(historial, es_pregunta):
    """Conserva los mensajes recientes, empezando siempre en una pregunta del usuario."""
    if len(historial) <= MAX_MENSAJES_HISTORIAL:
        return historial
    recortado = historial[-MAX_MENSAJES_HISTORIAL:]
    while recortado and not es_pregunta(recortado[0]):
        recortado.pop(0)
    return recortado


def _es_pregunta(mensaje):
    return mensaje["role"] == "user" and isinstance(mensaje["content"], str)


# ----------------------------------------------------------------------------
# Claude (formato nativo de Anthropic)
# ----------------------------------------------------------------------------
class AsistenteClaude:
    nombre = "claude"

    def __init__(self, cliente=None, modelo=None):
        if cliente is None:
            import anthropic
            cliente = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
        self.cliente = cliente
        self.modelo = modelo or "claude-haiku-5-5"
        self.historial = []

    def preguntar(self, texto: str) -> str:
        inicio = len(self.historial)
        self.historial.append({"role": "user", "content": texto})
        try:
            respuesta = self._resolver()
        except Exception:
            del self.historial[inicio:]  # si algo falla, deshacemos esta pregunta completa
            raise
        self.historial = _recortar(self.historial, _es_pregunta)
        return respuesta

    def _resolver(self) -> str:
        for _ in range(MAX_PASOS_HERRAMIENTAS):
            respuesta = self.cliente.messages.create(
                model=self.modelo,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.historial,
            )
            self.historial.append({"role": "assistant", "content": respuesta.content})

            if respuesta.stop_reason != "tool_use":
                return "".join(b.text for b in respuesta.content if b.type == "text").strip()

            resultados = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    _registrar_uso(bloque.name, bloque.input)
                    resultados.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": ejecutar_herramienta(bloque.name, bloque.input),
                    })
            self.historial.append({"role": "user", "content": resultados})

        return "Lo siento, no pude completar la consulta (demasiados pasos)."


# ----------------------------------------------------------------------------
# Gemini / Groq / Ollama (formato compatible con OpenAI)
# ----------------------------------------------------------------------------
def herramientas_formato_openai(tools=TOOLS):
    """Convierte nuestras fichas (formato Anthropic) al formato de OpenAI."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


def _mensaje_a_dict(mensaje):
    """
    Convierte la respuesta del modelo en un dict para el historial SIN perder campos extra.

    Importante con Gemini 3: cada llamada a herramienta trae una "firma de razonamiento"
    (extra_content.google.thought_signature) que hay que devolver en el siguiente turno;
    si se pierde, Gemini responde con Error 400. model_dump() conserva esos campos extra.
    """
    if hasattr(mensaje, "model_dump"):
        datos = mensaje.model_dump(exclude_none=True)
    else:  # objetos simples (p. ej. en las pruebas)
        datos = {
            "role": "assistant",
            "tool_calls": [
                {"id": ll.id, "type": "function",
                 "function": {"name": ll.function.name, "arguments": ll.function.arguments}}
                for ll in mensaje.tool_calls
            ],
        }
    datos["role"] = "assistant"
    datos["content"] = datos.get("content") or ""
    return datos


class AsistenteOpenAICompatible:
    def __init__(self, nombre, cliente=None, modelo=None):
        config = PROVEEDORES_OPENAI[nombre]
        self.nombre = nombre
        if cliente is None:
            from openai import OpenAI
            clave = os.getenv(config["variable_clave"]) if config["variable_clave"] else "ollama"
            cliente = OpenAI(api_key=clave, base_url=config["base_url"])
        self.cliente = cliente
        self.modelo = modelo or config["modelo"]
        self.tools = herramientas_formato_openai()
        self.historial = []  # el system prompt se agrega en cada llamada

    def preguntar(self, texto: str) -> str:
        inicio = len(self.historial)
        self.historial.append({"role": "user", "content": texto})
        try:
            respuesta = self._resolver()
        except Exception:
            del self.historial[inicio:]  # si algo falla, deshacemos esta pregunta completa
            raise
        self.historial = _recortar(self.historial, _es_pregunta)
        return respuesta

    def _resolver(self) -> str:
        for _ in range(MAX_PASOS_HERRAMIENTAS):
            respuesta = self.cliente.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.historial,
                tools=self.tools,
            )
            mensaje = respuesta.choices[0].message
            llamadas = mensaje.tool_calls or []

            if not llamadas:
                texto = (mensaje.content or "").strip()
                self.historial.append({"role": "assistant", "content": texto})
                return texto

            # Guardamos el pedido de herramientas del modelo TAL CUAL llegó...
            self.historial.append(_mensaje_a_dict(mensaje))
            # ...y la respuesta de cada herramienta
            for ll in llamadas:
                try:
                    argumentos = json.loads(ll.function.arguments or "{}")
                except json.JSONDecodeError:
                    argumentos = {}
                _registrar_uso(ll.function.name, argumentos)
                self.historial.append({
                    "role": "tool",
                    "tool_call_id": ll.id,
                    "content": ejecutar_herramienta(ll.function.name, argumentos),
                })

        return "Lo siento, no pude completar la consulta (demasiados pasos)."


# ----------------------------------------------------------------------------
# Fábrica: elige el proveedor según el .env
# ----------------------------------------------------------------------------
def crear_asistente(proveedor=None, modelo=None):
    """Crea el asistente según LLM_PROVIDER. Lanza ValueError si falta configuración."""
    proveedor = (proveedor or os.getenv("LLM_PROVIDER", "gemini")).strip().lower()
    modelo = modelo or os.getenv("LLM_MODEL") or None

    if proveedor == "claude":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("Falta ANTHROPIC_API_KEY en tu archivo .env")
        return AsistenteClaude(modelo=modelo)

    if proveedor in PROVEEDORES_OPENAI:
        variable = PROVEEDORES_OPENAI[proveedor]["variable_clave"]
        if variable and not os.getenv(variable):
            raise ValueError(f"Falta {variable} en tu archivo .env")
        return AsistenteOpenAICompatible(proveedor, modelo=modelo)

    opciones = ", ".join(["claude", *PROVEEDORES_OPENAI])
    raise ValueError(f"LLM_PROVIDER='{proveedor}' no es válido. Opciones: {opciones}")
