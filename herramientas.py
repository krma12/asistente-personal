"""
Registro de herramientas (tools) que Claude puede usar.

Cada herramienta tiene dos partes:
  1. Su "ficha" (nombre, descripción y parámetros en JSON Schema) que se le envía a Claude
     para que sepa CUÁNDO y CÓMO usarla.
  2. La función de Python que realmente se ejecuta.

Para agregar una habilidad nueva (p. ej. obtener_noticias):
  - crea su archivo en funciones_agente/
  - agrega su ficha a TOOLS y su función a FUNCIONES.
"""
from funciones_agente.obtener_clima import obtener_clima
from funciones_agente.obtener_precio_accion import obtener_precio_accion
from funciones_agente.obtener_hora import obtener_hora

TOOLS = [
    {
        "name": "obtener_clima",
        "description": (
            "Obtiene el clima actual (condición, temperatura, sensación térmica y humedad) "
            "de una ciudad. Úsala cuando el usuario pregunte por clima, temperatura o tiempo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ciudad": {
                    "type": "string",
                    "description": "Nombre de la ciudad, p. ej. 'Ciudad de México', 'Madrid', 'São Paulo'.",
                }
            },
            "required": ["ciudad"],
        },
    },
    {
        "name": "obtener_precio_accion",
        "description": (
            "Obtiene el precio de cierre más reciente de una acción en bolsa. "
            "Si el usuario da el nombre de una empresa, conviértelo tú al ticker correcto "
            "(Microsoft -> MSFT, Apple -> AAPL, Walmex -> WALMEX.MX)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Símbolo bursátil, p. ej. 'AAPL', 'NVDA', 'WALMEX.MX'.",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "obtener_hora",
        "description": (
            "Obtiene la fecha, el día de la semana y la hora actual en una zona horaria. "
            "Úsala cuando pregunten la hora o la fecha de un lugar, o cuando necesites saber "
            "qué día es hoy. Convierte tú la ciudad o país a su zona IANA "
            "(Beijing -> Asia/Shanghai, Madrid -> Europe/Madrid, São Paulo -> America/Sao_Paulo). "
            "Si no indican lugar, usa America/Mexico_City."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "zona_horaria": {
                    "type": "string",
                    "description": "Nombre IANA de la zona horaria, p. ej. 'Asia/Shanghai'.",
                }
            },
            "required": ["zona_horaria"],
        },
    },
]

FUNCIONES = {
    "obtener_clima": obtener_clima,
    "obtener_precio_accion": obtener_precio_accion,
    "obtener_hora": obtener_hora,
}


def ejecutar_herramienta(nombre: str, argumentos: dict) -> str:
    """Ejecuta la herramienta que pidió Claude y devuelve el resultado como texto."""
    funcion = FUNCIONES.get(nombre)
    if funcion is None:
        return f"Error: la herramienta '{nombre}' no existe."
    try:
        return str(funcion(**argumentos))
    except TypeError as e:
        return f"Error: argumentos inválidos para '{nombre}': {e}"
