# Asistente personal con IA

Asistente de consola en Python que usa un LLM con *tool use* para responder con datos en tiempo real. La meta es convertirlo en un asistente diario: **noticias relevantes** (tecnología, ciberseguridad, IA, geopolítica) y **vacantes de empleo** alineadas con un perfil profesional, sin tener que buscarlas a mano.

> Proyecto en desarrollo. Nació a partir de un ejercicio de clase de chatbots
> ([automatizaci-n_simple](https://github.com/krma12/automatizaci-n_simple)) y evoluciona aquí como proyecto independiente.

![Flujo de tool use](docs/flujo_tool_use.png)

## Cómo funciona

1. El usuario escribe una pregunta en lenguaje natural.
2. El modelo decide si necesita una herramienta (clima, acciones, y próximamente noticias y vacantes).
3. Python ejecuta la herramienta y le devuelve el resultado al modelo.
4. El modelo redacta la respuesta final en español, sin inventar datos.

## Proveedores de IA intercambiables

Se elige el modelo con una línea en `.env`, sin tocar el código:

| `LLM_PROVIDER` | Costo | Notas |
| --- | --- | --- |
| `gemini` | Gratis con límites | Clave en Google AI Studio |
| `groq` | Gratis con límites | Modelos abiertos, muy rápido |
| `ollama` | Gratis, local | Los datos no salen de tu computadora |
| `claude` | De pago | API de Anthropic |

`proveedores.py` tiene dos adaptadores: uno para la API nativa de Anthropic y otro para las API compatibles con OpenAI (Gemini, Groq, Ollama).

## Hoja de ruta

- [x] **Fase 1:** LLM con *tool use*, multi-proveedor, herramientas de clima y acciones, pruebas con `pytest`
- [ ] **Fase 2:** herramienta de noticias desde fuentes RSS, filtradas por intereses
- [ ] **Fase 3:** vacantes leídas desde alertas de empleo por correo y calificadas contra un perfil local (Iberoamérica, incluido Brasil)
- [ ] **Fase 4:** resumen diario automático

## Decisiones de diseño y seguridad

- **Sin scraping de LinkedIn ni Indeed:** sus términos de uso lo prohíben. Las vacantes se obtendrán de las alertas de empleo que esas plataformas envían por correo al propio usuario.
- **Datos personales fuera del repositorio:** el perfil real (`perfil.yaml`), las claves (`.env`) y las salidas generadas están en `.gitignore`. El repo solo incluye plantillas con datos ficticios.
- **Privacidad por proveedor:** para analizar el perfil personal se recomienda Ollama (local), porque los niveles gratuitos de algunas API pueden usar los datos enviados para mejorar sus productos.
- **Compatibilidad real entre proveedores:** Gemini 3 exige recibir de vuelta una firma de razonamiento en cada llamada a herramienta. El adaptador conserva todos los campos de la respuesta en lugar de reconstruir los mensajes.

## Instalación (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # elige LLM_PROVIDER y pon su clave
copy perfil.example.yaml perfil.yaml   # (para la Fase 3) tus datos reales
python main.py
```

## Pruebas

```powershell
python -m pytest -v
```

Las pruebas usan simulaciones (*mocks*): no necesitan internet ni gastan créditos de API.

## Estructura

```
asistente-personal/
├── main.py                 # Conversación por consola
├── proveedores.py          # Adaptadores de LLM + selección por .env
├── herramientas.py         # Registro de herramientas (fichas JSON Schema)
├── funciones_agente/       # Una habilidad por archivo
│   ├── obtener_clima.py
│   └── obtener_precio_accion.py
├── test_asistente.py
├── .env.example            # Plantilla de claves (sin datos reales)
├── perfil.example.yaml     # Plantilla de perfil (datos ficticios)
└── docs/
```
