# Política de seguridad

🌐 [English](../SECURITY.md) · **Español**

Este es un proyecto personal de portafolio, pero la seguridad es un requisito de primera clase: el asistente lee contenido no confiable de internet, tiene acceso a un calendario personal y se comunica con el exterior a través de Telegram.

## Versiones con soporte

Solo el último commit de `main`. Las dependencias tienen versión fija en `requirements.txt` y Dependabot las mantiene al día; cada push ejecuta las pruebas, Bandit (análisis estático) y pip-audit (vulnerabilidades conocidas) en GitHub Actions.

## Cómo reportar una vulnerabilidad

Por favor, **no abras un issue público** para problemas de seguridad.

Usa el reporte privado de vulnerabilidades de GitHub: en la pestaña **Security** de este repositorio, da clic en **Report a vulnerability**. Incluye:

- qué encontraste y dónde (archivo, función o comportamiento),
- los pasos para reproducirlo,
- el impacto que crees que tiene.

Recibirás una confirmación en un máximo de 7 días. Las correcciones se publican en `main` y se da crédito a quien reporta en el mensaje del commit, salvo que prefiera el anonimato.

## Alcance

Dentro del alcance:

- Inyecciones de prompt que hagan que el asistente actúe contra el usuario (por ejemplo, crear eventos sin confirmación o filtrar el perfil).
- Saltarse la lista blanca de Telegram.
- Filtración de secretos (claves de API, token de Telegram, tokens de OAuth de Google) en el código, los registros o los mensajes de error.
- Falsificación de peticiones del lado del servidor (SSRF) o descargas fuera de la lista fija de fuentes.
- Dependencias vulnerables que pip-audit todavía no detecte.

Fuera del alcance:

- Límites de uso o disponibilidad de servicios de terceros (Gemini, Telegram, Google, fuentes RSS).
- Ataques que requieran acceso previo a la computadora o a las cuentas del usuario.
- La exactitud de las noticias o de las respuestas del modelo.

## Diseño

El modelo de amenazas, las fronteras de confianza, las mitigaciones y los riesgos residuales conocidos están en [MODELO_DE_AMENAZAS.md](MODELO_DE_AMENAZAS.md).
