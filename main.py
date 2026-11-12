"""
Asistente personal — punto de entrada por consola.

Un LLM (Gemini, Groq, Ollama o Claude) entiende la pregunta en lenguaje natural,
decide qué herramienta usar, extrae los parámetros y redacta la respuesta final.

El proveedor se elige en el archivo .env con LLM_PROVIDER (ver .env.example).
La lógica de cada proveedor está en proveedores.py; las herramientas en herramientas.py.
"""
import sys

from dotenv import load_dotenv

from funciones_agente import calendario
from perfil import cargar_intereses
from proveedores import crear_asistente

load_dotenv()  # Lee LLM_PROVIDER y las claves desde el archivo .env

SALIDAS = {"salir", "exit", "quit", "adiós", "adios"}


def revisar_recordatorios_pendientes(leer=input):
    """Confirmación humana: nada se crea en el calendario sin un 's' explícito del usuario."""
    for propuesta in calendario.pendientes():
        print(calendario.describir(propuesta))
        respuesta = leer("¿Confirmas? (s/n): ").strip().lower()
        if respuesta in {"s", "si", "sí"}:
            print(calendario.confirmar_recordatorio(propuesta["id"]) + "\n")
        else:
            print(calendario.descartar_recordatorio(propuesta["id"]) + "\n")


def chatbot():
    try:
        intereses = cargar_intereses()
        asistente = crear_asistente(intereses=intereses)
    except ValueError as e:
        print(f"Error de configuración: {e}")
        print("Copia .env.example como .env y completa los datos del proveedor que quieras usar.")
        sys.exit(1)

    print(f"*** Asistente personal v0.4 (proveedor: {asistente.nombre}, modelo: {asistente.modelo}) ***")
    print("Perfil: " + ("cargado desde perfil.yaml" if intereses else "no encontrado (respuestas sin personalizar)"))
    print("Puedo darte clima, precios de acciones, la hora en cualquier lugar, noticias")
    print("(ciberseguridad, IA, tecnología, geopolítica), vulnerabilidades explotadas (CISA KEV),")
    print("tu agenda de Google Calendar y recordatorios (siempre te pido confirmación).")
    print("Ejemplos: '¿qué tengo esta semana?', 'recuérdame el viernes a las 5 ir al banco'")
    print("Escribe 'salir' para terminar.\n")

    while True:
        try:
            user_input = input("--> ").strip()
            if not user_input:
                continue
            if user_input.lower() in SALIDAS:
                print(">>> ¡Hasta luego!")
                break
            print(f">>> {asistente.preguntar(user_input)}\n")
            revisar_recordatorios_pendientes()

        except KeyboardInterrupt:
            print("\n>>> ¡Hasta luego!")
            break
        except Exception as e:
            # Errores de red, clave inválida, límite de uso alcanzado, modelo inexistente...
            # (el asistente ya deshizo la pregunta fallida de su historial)
            print(f">>> Error al consultar al modelo: {e}")
            detalle = getattr(e, "body", None)  # el SDK guarda aquí la explicación del servidor
            if detalle:
                print(f"    Detalle: {detalle}")
            print()


if __name__ == "__main__":
    chatbot()
