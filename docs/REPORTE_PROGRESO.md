# Reporte de progreso — Asistente personal con IA

🌐 [English](PROGRESS_REPORT.md) · **Español**

Actualizado el 16 de noviembre de 2026 · Hugo Maldonado Caballero

## Resumen

El chatbot de la clase creció hasta convertirse en un **asistente personal privado** que funciona como bot de Telegram: entrega noticias personalizadas y vulnerabilidades explotadas activamente (CISA KEV), lee el Google Calendar del usuario y crea recordatorios solo después de que el usuario los confirma. Tiene **95 pruebas automáticas**, corre en Python 3.13 y cada push pasa por pruebas, Bandit y pip-audit.

- **Objetivo de la clase:** hacer fork del repositorio `automatizaci-n_simple` y construir un chatbot a partir de él (Fase 1, entregada).
- **Objetivo personal:** un asistente diario de noticias, agenda y vacantes alineadas con el perfil profesional.
- **Estado al 16 de noviembre de 2026:** Fases 1 a 4 terminadas. Se prepara la Fase 5 (vacantes): un buzón dedicado ya recibe las alertas de empleo de LinkedIn e Indeed.

| Fase | Qué agregó | Pruebas |
| --- | --- | --- |
| 4 — Calendario | Agenda de Google Calendar (hasta un año) y recordatorios con confirmación humana | 95 |
| 3 — Telegram | Bot privado con lista blanca por ID de chat y pregunta matutina | 66 |
| 2 — Noticias | Noticias RSS por tema, CISA KEV, personalización, defensas contra inyección | 44 |
| 1 — LLM | *Tool use*, 4 proveedores, clima, acciones, hora; errores de la clase corregidos | 22 |

Las secciones siguientes documentan a detalle la Fase 1 (el proyecto de la clase) y después las Fases 2 a 4.

## Origen del código

Este proyecto parte del repositorio [mendiolaleonel2002-debug/automatizaci-n_simple](https://github.com/mendiolaleonel2002-debug/automatizaci-n_simple), proporcionado como ejercicio en la clase de IA. Se hizo fork en [krma12/automatizaci-n_simple](https://github.com/krma12/automatizaci-n_simple), donde se desarrolló y entregó la v2.0. Después, el código que ya funcionaba se copió a este repositorio para seguir creciendo como proyecto personal.

- **Se conservó del original:** la idea de una habilidad por archivo en `funciones_agente/` y el uso de wttr.in (clima) y yfinance (acciones).
- **Se reescribió:** las dos funciones, `main.py` y las pruebas.
- **Es nuevo:** `proveedores.py`, `herramientas.py`, el soporte multi-proveedor y la configuración con `.env`.

## Proyecto original (v1.0)

El repositorio del profesor es un chatbot de consola en Python de unas 550 líneas con dos habilidades: consultar el clima y el precio de acciones. No usaba IA: detectaba la intención buscando palabras clave.

| Componente | Función en v1.0 |
| --- | --- |
| `main.py` | Chatbot de consola; detecta la intención con expresiones regulares (regex) |
| `agente_selenium.py` | Segunda versión que abre Chrome sin ventana (headless) con Selenium y detecta palabras clave |
| `funciones_agente/obtener_clima.py` | Consulta la temperatura en la API gratuita wttr.in |
| `funciones_agente/obtener_precio_accion.py` | Consulta el precio con la librería yfinance; tiene un diccionario de 11 nombres de empresa a ticker |
| `utils/sanitizar.py` | Quita prefijos como "precio de" o "la" para aislar el nombre de la empresa |
| `test_chatbot.py` | Imprime el precio de Microsoft; no verifica ningún resultado |
| `prueba_selenium.py` | Abre Google, Hybridge y OpenAI en Chrome como demostración |

**Lo que ya estaba bien hecho y se conservó:**

- **Modularidad:** cada habilidad vive en su propio archivo dentro de `funciones_agente/`.
- **Separación de la interfaz:** la misma función se puede llamar desde la consola o desde Selenium.
- **Manejo de errores:** `try/except` en el ciclo principal y en las llamadas a las API, con salida limpia usando Ctrl+C.
- **Documentación:** README con diagrama de arquitectura en Mermaid y una lista de mejoras sugeridas. La primera sugerencia era justamente reemplazar los regex por un LLM.

## Errores encontrados en el código original

Al probar la limpieza de texto con preguntas reales, ninguna de las 4 preguntas de ejemplo llegó correcta a la API. Los dos errores más graves hacían fallar incluso el ejemplo que el propio bot muestra al arrancar.

| Pregunta de prueba | Texto que llegaba a la API | Causa |
| --- | --- | --- |
| clima en Denver | `dver` | `obtener_clima` borraba "en" y "de" en cualquier parte de la palabra, no solo como palabras sueltas |
| temperatura en Benito Juárez | `bito juárez` | El mismo `.replace("en", "")` |
| ¿cuál es la temperatura actual en la Ciudad de México? | `¿cuál es la  actual  la ciudad  méxico?` | Solo se borraban palabras clave; el resto de la frase se enviaba completo |
| ¿cuál es el precio de una acción de Microsoft? | la frase completa como ticker | `main.py` no limpiaba el texto y `sanitizar` solo quita prefijos al inicio |

**Otros problemas:**

1. **Selenium sin uso:** `agente_selenium.py` abría Chrome y pasaba el navegador a las funciones, pero ninguna lo usaba. Solo hacía más lento el arranque.
2. **Archivos basura en el repositorio:** se subieron carpetas `__pycache__` aunque el `.gitignore` las excluía.
3. **Pruebas sin verificación:** `test_chatbot.py` solo imprimía un resultado; nunca comprobaba si era correcto.
4. **Precio vacío en fines de semana:** pedir 1 día de historial a yfinance puede no devolver datos cuando el mercado está cerrado.

## Mejoras y optimizaciones (v2.0)

El cambio central fue sustituir los regex por un modelo de lenguaje con *tool use*: el modelo entiende la pregunta, decide qué herramienta usar, extrae el parámetro limpio y redacta la respuesta. Las funciones de clima y acciones se conservaron y se convirtieron en herramientas.

| Área | v1.0 | v2.0 |
| --- | --- | --- |
| Comprensión | Regex y palabras clave | LLM con *tool use* |
| Proveedores de IA | Ninguno | Gemini, Groq, Ollama y Claude, elegibles con `LLM_PROVIDER` en `.env` |
| Memoria de la conversación | No | Sí, recortada a los 20 mensajes más recientes |
| Clima | Solo temperatura; nombres de ciudad alterados | Condición, temperatura, sensación térmica y humedad en español; ciudad intacta y codificada en la URL |
| Acciones | Precio de 1 día; 11 nombres en el diccionario | Historial de 5 días, con moneda y fecha de cierre; el modelo convierte cualquier empresa a su ticker |
| Pruebas | 1 script sin verificaciones | 18 pruebas con `pytest` y simulaciones (*mocks*), sin internet ni costo |
| Seguridad | Sin manejo de claves | Claves en `.env` excluido de Git, plantilla `.env.example` |
| Errores | Mensaje genérico | Muestra el detalle del servidor y deshace la pregunta fallida del historial |

**Archivos nuevos o reescritos:**

- **`herramientas.py` (nuevo):** registro central de herramientas. Cada una tiene una ficha (nombre, descripción y parámetros en JSON Schema) y su función de Python. Agregar una habilidad nueva es agregar una ficha.
- **`proveedores.py` (nuevo):** dos adaptadores, uno para la API nativa de Anthropic y otro para las API compatibles con OpenAI (Gemini, Groq, Ollama), más una función que elige el proveedor según el `.env`.
- **`main.py` (reescrito):** solo maneja la conversación; no depende de qué modelo hay detrás.
- **`agente_selenium.py` (ajustado):** sigue funcionando con las nuevas firmas de las funciones, por si se usa más adelante en la clase.
- **`README.md` (actualizado):** sección de cambios v2.0, tabla de proveedores e instrucciones de uso.

## Problemas durante la implementación

Surgieron 4 problemas al instalar y probar en Windows; los 4 quedaron resueltos y ninguna clave llegó a GitHub.

| Problema | Causa | Solución |
| --- | --- | --- |
| Error 400 de Gemini al usar una herramienta | Gemini 3 envía una "firma de razonamiento" oculta con cada llamada a herramienta y exige recibirla de vuelta; el código reconstruía el mensaje y la perdía | Guardar la respuesta del modelo tal como llega (`model_dump`), con una prueba que confirma que la firma se conserva |
| Clave de API compartida en un chat | Se pegó la clave en una conversación | Se trató como expuesta: se borró en Google AI Studio y se generó una nueva |
| Clave dentro de `.env.example` | Se pegó la clave en la plantilla, que sí se sube a GitHub | Se detectó por el tamaño del archivo (728 a 769 bytes) y se restauró la plantilla antes del primer commit |
| Entorno virtual `.Bot` no excluido | El `.gitignore` solo cubría nombres como `.venv` y `venv` | Se agregó `.bot/` al `.gitignore`, junto con el archivo de notas `cheetsheet` |

**Lección principal:** aunque Gemini, Groq y Ollama dicen ser "compatibles con OpenAI", cada proveedor tiene detalles propios. Un adaptador que conserva los campos que no conoce es más robusto que uno que reconstruye los mensajes a mano.

## Características actuales y estructura v2.0

La v2.0 responde en español, recuerda la conversación, usa herramientas solo cuando la pregunta lo requiere y nunca inventa temperaturas ni precios.

![Flujo de tool use: el modelo decide si necesita una herramienta antes de responder](flujo_tool_use.png)

Si el modelo pide una herramienta, Python la ejecuta y le devuelve el resultado; el ciclo se repite hasta 5 veces antes de responder.

**Estructura de archivos (fork de la clase):**

```
automatizaci-n_simple/
├── main.py               # Conversación por consola
├── proveedores.py        # Adaptadores de LLM + selección por .env  (nuevo)
├── herramientas.py       # Fichas y registro de herramientas        (nuevo)
├── funciones_agente/
│   ├── obtener_clima.py
│   └── obtener_precio_accion.py
├── utils/sanitizar.py    # Ya no lo usa main.py; lo usa agente_selenium.py
├── agente_selenium.py
├── test_chatbot.py       # 18 pruebas con pytest
├── REPORTE_PROGRESO.md   # Este reporte
├── docs/flujo_tool_use.png  # Diagrama del flujo
├── .env.example          # Plantilla pública (sin claves)
├── .env                  # Claves reales (excluido de Git)
└── requirements.txt
```

**Proveedores disponibles:**

| Proveedor | Costo | Modelo por defecto | Uso recomendado |
| --- | --- | --- | --- |
| Gemini | Gratis con límites | `gemini-3.5-flash` | Pruebas diarias (activo hoy) |
| Groq | Gratis con límites | `openai/gpt-oss-20b` | Alternativa rápida |
| Ollama | Gratis, local | `qwen3:4b` | Datos personales (Fase 3), por privacidad |
| Claude | De pago | `claude-haiku-5-5` | Producción |

**Entorno:** Windows, VS Code, proyecto en SSD externo (`D:\Proyectos`), entorno virtual `.Bot`.

## Fases 2 a 4 (asistente-personal)

### Fase 2 — Noticias e inteligencia de amenazas
- **Noticias por tema** desde una lista fija de fuentes RSS: ciberseguridad, IA, tecnología y geopolítica (fuentes de varias regiones para un panorama balanceado).
- **CISA KEV:** vulnerabilidades con explotación real confirmada, con enlace a NVD y aviso de uso en ransomware.
- **Personalización:** al modelo solo se le envían los intereses y el objetivo profesional de `perfil.yaml`, que es local.
- **Defensas contra inyección de prompts:** el texto externo se limpia, se recorta, se envuelve en delimitadores que no se pueden falsificar y se revisa en busca de frases de inyección; el modelo solo elige temas, nunca URLs.

### Fase 3 — Bot privado de Telegram
- Solo responde al ID de chat configurado; a los desconocidos los ignora y solo registra su ID.
- Pregunta diaria a las 08:00 con un botón para el resumen; comandos `/noticias` y `/reiniciar`.
- El token del bot nunca se imprime (se silencia el registro del cliente HTTP, porque las URL de Telegram lo contienen).

### Fase 4 — Google Calendar
- Lee la agenda (un día concreto o hasta un año, hasta 300 eventos, con paginación).
- **Recordatorios con confirmación humana:** el modelo solo puede proponer; el evento se crea cuando el usuario presiona **Crear**. Los avisos pueden ser con días de anticipación.
- Permiso mínimo de Google (`calendar.events`); credenciales en `secretos/`, excluida de Git.

### Calidad y seguridad
- Python 3.13 (la 3.10 llegó a su fin de vida), dependencias con versión fija y Dependabot.
- CI en GitHub Actions: pruebas en 3.12 y 3.13, Bandit y pip-audit.
- [Política de seguridad](SEGURIDAD.md) y [modelo de amenazas](MODELO_DE_AMENAZAS.md) alineados con el OWASP Top 10 para aplicaciones con LLM.

### Problemas resueltos en el camino

| Problema | Causa | Solución |
| --- | --- | --- |
| Gemini respondía **429 Too Many Requests** | Una agenda de un año se reenviaba en cada mensaje a través del historial | Se recortan los resultados viejos del historial; formato compacto de agenda; mensaje claro de límite en Telegram |
| Los eventos a partir de cierta fecha "no existían" | La consulta del calendario tenía un tope de 25 eventos | Paginación hasta 300 eventos, consultas por fecha concreta y aviso cuando la lista se corta |
| No se podía publicar la app de Google | La nueva Google Auth Platform pide página principal y política de privacidad para publicar | Seguir en modo Prueba (la autorización se renueva cada 7 días) |
| No se podía borrar el entorno virtual viejo | Windows mantenía bloqueado `python.exe` | Nuevo `.venv` con Python 3.13; borrar el viejo después de reiniciar |
| Archivos que regresaban a versiones viejas | VS Code guardaba pestañas abiertas encima de los archivos actualizados | Cerrar pestañas y desactivar Auto Save antes de editar desde fuera |
| CI en rojo tras la Fase 2 | Bandit marcaba los `assert` de las pruebas nuevas | Excluir `test_*.py` de Bandit |

## Próximos pasos

- [x] Fases 1 a 4
- [x] Política de seguridad y modelo de amenazas
- [ ] **Fase 5, vacantes:** leer el buzón dedicado de alertas de empleo (alertas de LinkedIn e Indeed redirigidas desde Outlook) y calificar las vacantes contra el perfil local; Iberoamérica, incluido Brasil
- [ ] Mover el bot a un servidor dedicado en casa (Lenovo ThinkCentre M920q) y endurecerlo
- [ ] Opcional: publicar la app de OAuth de Google con una página de privacidad en GitHub Pages
