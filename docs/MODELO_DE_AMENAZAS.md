# Modelo de amenazas

🌐 [English](THREAT_MODEL.md) · **Español**

Última revisión: noviembre de 2026 (hasta la Fase 4: Telegram + Google Calendar).

El mayor riesgo del asistente no es un ataque web clásico: es **un modelo de lenguaje que lee texto no confiable y puede usar herramientas**. Cualquiera que controle una noticia, una fuente RSS o una invitación de calendario puede intentar manipularlo. El diseño parte de que el modelo *a veces* será engañado, y limita lo que un modelo engañado puede hacer.

## Activos

| Activo | Dónde vive | Por qué importa |
| --- | --- | --- |
| Claves de API de modelos (Gemini, Groq, Claude) | `.env` (ignorado por Git) | Abuso de cuota y cobros |
| Token del bot de Telegram | `.env` | Control total del bot |
| Token de OAuth de Google (`calendar.events`) | `secretos/` (ignorado por Git) | Leer y escribir el calendario del usuario |
| Perfil personal | `perfil.yaml` (ignorado por Git) | Objetivos profesionales e intereses |
| Contenido del calendario | Google Calendar | Vida diaria, lugares, personas |
| La atención y confianza del usuario | Chat de Telegram | Un asistente engañado puede confundir al usuario |

## Fronteras de confianza

1. **Usuario ↔ asistente:** solo el ID de chat de Telegram configurado en `.env`, o la consola local, puede dar instrucciones.
2. **Asistente ↔ proveedor del modelo:** los prompts, los intereses del perfil y los resultados de las herramientas salen de la computadora y llegan a los servidores del proveedor.
3. **Asistente ↔ contenido externo:** las fuentes RSS, el catálogo CISA KEV y los eventos del calendario (incluidas invitaciones de cualquier persona) son **datos no confiables**.
4. **Asistente ↔ Google Calendar:** el único lugar donde el asistente puede *escribir*.

## Amenazas y mitigaciones

| # | Amenaza | Mitigación | Dónde está en el código |
| --- | --- | --- | --- |
| T1 | **Inyección de prompt indirecta** en una noticia o invitación ("ignora tus instrucciones y…") | El texto no confiable se limpia de HTML y caracteres de control, se recorta, se envuelve en delimitadores que no puede falsificar y se revisa en busca de frases típicas de inyección (que se le señalan al usuario). El prompt del sistema indica tratarlo como datos. | `funciones_agente/contenido_externo.py`, `proveedores.py` |
| T2 | **Agencia excesiva:** un modelo engañado crea eventos en el calendario | El modelo solo puede *proponer* un recordatorio; se crea únicamente cuando el usuario presiona **Crear** (Telegram) o escribe `s` (consola). A propósito no existe una herramienta para confirmar. Las demás herramientas son de solo lectura. | `funciones_agente/calendario.py`, `herramientas.py`, `bot_telegram.py`, `main.py` |
| T3 | **Falsificación de peticiones (SSRF):** engañar al modelo para descargar URLs internas o arbitrarias | El modelo elige un tema de una lista fija, nunca una URL. Cualquier parámetro que no esté declarado en la ficha de una herramienta se rechaza antes de ejecutarla. | `funciones_agente/obtener_noticias.py`, `herramientas.py` |
| T4 | **Uso no autorizado del bot:** un desconocido lo encuentra y gasta la cuota o lee datos | Lista blanca por ID de chat de Telegram; a los desconocidos se les ignora y solo se registra su ID, nunca su mensaje. Sin un ID configurado, el bot no responde a nadie salvo a `/start`. | `bot_telegram.py` |
| T5 | **Filtración de secretos** en el repositorio o en los registros | `.env`, `perfil.yaml` y `secretos/` están en `.gitignore`; las plantillas tienen valores falsos; Push Protection de GitHub está activado. Se silencia el registro del cliente HTTP porque las URL de la API de Telegram contienen el token. Los mensajes de error al usuario nunca incluyen detalles internos. | `.gitignore`, `bot_telegram.py` |
| T6 | **Respuestas maliciosas o gigantes** de una fuente comprometida | Límites de tiempo y tamaño en cada descarga; una fuente que falla no tumba a las demás; los feeds y el JSON se procesan de forma defensiva. | `funciones_agente/contenido_externo.py` |
| T7 | **Deserialización insegura** del archivo de perfil | Solo `yaml.safe_load`; una prueba confirma que se rechaza un YAML malicioso. | `perfil.py`, `test_noticias.py` |
| T8 | **Enlaces peligrosos** en noticias o eventos | Solo se conservan enlaces `http(s)`; se descartan `javascript:` y `data:`. Los mensajes de Telegram se envían como texto plano, nunca se interpretan como HTML ni Markdown. | `funciones_agente/contenido_externo.py`, `bot_telegram.py` |
| T9 | **Vulnerabilidades en la cadena de suministro** (dependencias) | Versiones fijas, actualizaciones semanales de Dependabot, pip-audit y Bandit en cada push. | `requirements.txt`, `.github/` |
| T10 | **Consumo sin límite:** resultados enormes agotan la cuota de la API | Límites de tamaño en los resultados, formato compacto de agenda con más de 40 eventos y recorte de resultados viejos en el historial de la conversación. | `proveedores.py`, `funciones_agente/calendario.py` |
| T11 | **Exceso de datos enviados al proveedor del modelo** | Minimización de datos: del perfil solo se toman los intereses y el objetivo profesional; lo demás nunca sale de la computadora. | `perfil.py` |

## Cobertura del OWASP Top 10 para aplicaciones con LLM (2025)

| Punto de OWASP | Cubierto por |
| --- | --- |
| LLM01 Inyección de prompt | T1, T2, T3 |
| LLM02 Divulgación de información sensible | T5, T11 |
| LLM03 Cadena de suministro | T9 |
| LLM05 Manejo inadecuado de la salida | T8 |
| LLM06 Agencia excesiva | T2, T3 |
| LLM07 Filtración del prompt del sistema | El prompt del sistema no contiene secretos, así que filtrarlo no tiene impacto |
| LLM10 Consumo sin límite | T4, T10 |

## Riesgos residuales (conocidos y aceptados)

- **La detección de inyecciones es heurística.** Un atacante creativo puede redactar una inyección que no se marque. La protección real es que las herramientas son de solo lectura y escribir requiere confirmación humana; el peor caso realista es una respuesta engañosa.
- **Datos enviados al proveedor del modelo.** Los títulos del calendario, las noticias y los intereses del perfil llegan al proveedor. Algunos niveles gratuitos pueden usar los datos enviados para mejorar sus productos. Para uso sensible, conviene cambiar a Ollama (local) o a un plan de pago con términos de datos empresariales.
- **Los chats con bots de Telegram no tienen cifrado de extremo a extremo;** los mensajes pasan por los servidores de Telegram.
- **Los secretos se guardan como archivos** protegidos solo por la cuenta del sistema operativo. Recomendado: cifrado de disco completo (BitLocker) en la computadora y en el SSD externo.
- **La app de OAuth de Google está en modo Prueba,** así que la autorización vence cada 7 días y se renueva con `configurar_calendario.py`.
- **Las dependencias están fijadas por versión, no por hash.**
- **La disponibilidad** depende de que la laptop del usuario esté prendida; no hay redundancia.

## Mejoras planeadas

- La Fase 5 (alertas de empleo) leerá un **buzón dedicado** que solo recibe alertas de empleo, para que el asistente nunca tenga acceso al correo personal ni al del trabajo.
- Mover el bot a un servidor dedicado en casa y endurecerlo (SSH solo con llaves, firewall, actualizaciones automáticas, usuario de servicio sin privilegios).
- Opcional: dependencias fijadas por hash.
