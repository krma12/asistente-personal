# Módulo para obtener noticias recientes desde fuentes RSS fijas, organizadas por tema
import calendar
from datetime import datetime, timedelta, timezone

import feedparser

from funciones_agente.contenido_externo import (
    DescargaError, descargar, enlace_seguro, envolver, limpiar_texto, parece_inyeccion,
)

# Lista blanca de fuentes. El LLM solo elige el TEMA, nunca la URL:
# así no puede ser engañado para descargar direcciones arbitrarias (SSRF).
# Si una fuente cambia su URL, se edita aquí.
FUENTES = {
    "ciberseguridad": {
        "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
        "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
        "Krebs on Security": "https://krebsonsecurity.com/feed/",
    },
    "ia": {
        "MIT Technology Review (IA)": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "The Verge (IA)": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    },
    "tecnologia": {
        "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
        "Xataka": "https://feeds.weblogssl.com/xataka2",
    },
    # Varias regiones para un panorama más balanceado
    "geopolitica": {
        "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "France 24 (español)": "https://www.france24.com/es/rss",
        "DW (español)": "https://rss.dw.com/xml/rss-sp-all",
    },
}
TEMAS = list(FUENTES)

MAX_BYTES_POR_FUENTE = 2_000_000
MAX_TITULO = 200
MAX_RESUMEN = 300


def _fecha(entrada):
    """Fecha de publicación en UTC (o None si la fuente no la trae)."""
    estructura = entrada.get("published_parsed") or entrada.get("updated_parsed")
    if not estructura:
        return None
    return datetime.fromtimestamp(calendar.timegm(estructura), tz=timezone.utc)


def leer_fuente(nombre: str, url: str, desde: datetime, descargador=descargar) -> list[dict]:
    """Descarga y limpia las noticias de una fuente publicadas después de `desde`."""
    feed = feedparser.parse(descargador(url, MAX_BYTES_POR_FUENTE))
    noticias = []
    for entrada in feed.entries:
        fecha = _fecha(entrada)
        if fecha is not None and fecha < desde:
            continue
        titulo = limpiar_texto(entrada.get("title"), MAX_TITULO)
        if not titulo:
            continue
        resumen = limpiar_texto(entrada.get("summary"), MAX_RESUMEN)
        noticias.append({
            "titulo": titulo,
            "resumen": resumen,
            "fuente": nombre,
            "enlace": enlace_seguro(entrada.get("link")),
            "fecha": fecha,
            "sospechosa": parece_inyeccion(titulo, resumen),
        })
    return noticias


def obtener_noticias(tema: str = "ciberseguridad", max_noticias: int = 8, dias: int = 2,
                     ahora: datetime | None = None, descargador=descargar) -> str:
    """
    Devuelve las noticias más recientes de un tema, listas para que el LLM las seleccione.

    Argumentos:
        tema: uno de FUENTES ("ciberseguridad", "ia", "tecnologia", "geopolitica").
        max_noticias: cuántas noticias devolver (1 a 15).
        dias: antigüedad máxima en días (1 a 7).
        ahora, descargador: solo para pruebas.
    """
    tema = (tema or "").strip().lower()
    if tema not in FUENTES:
        return f"Error: tema '{tema}' no disponible. Opciones: {', '.join(TEMAS)}."
    max_noticias = min(max(int(max_noticias), 1), 15)
    dias = min(max(int(dias), 1), 7)
    desde = (ahora or datetime.now(timezone.utc)) - timedelta(days=dias)

    noticias, errores = [], []
    for nombre, url in FUENTES[tema].items():
        try:
            noticias.extend(leer_fuente(nombre, url, desde, descargador))
        except DescargaError as e:
            errores.append(f"{nombre}: {e}")
        except Exception as e:  # una fuente rota no debe tumbar a las demás
            errores.append(f"{nombre}: no se pudo leer ({type(e).__name__})")

    # Más recientes primero; sin fecha al final. Sin títulos repetidos.
    minimo = datetime.min.replace(tzinfo=timezone.utc)
    noticias.sort(key=lambda n: n["fecha"] or minimo, reverse=True)
    vistas, unicas = set(), []
    for n in noticias:
        clave = n["titulo"].lower()
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(n)
    unicas = unicas[:max_noticias]

    encabezado = f"NOTICIAS — tema: {tema}, últimos {dias} día(s): {len(unicas)} encontradas."
    if not unicas:
        texto = encabezado + "\nNo se encontraron noticias recientes."
    else:
        lineas = []
        for i, n in enumerate(unicas, 1):
            fecha = n["fecha"].strftime("%Y-%m-%d") if n["fecha"] else "sin fecha"
            lineas.append(f"[{i}] {n['titulo']} | {n['fuente']} | {fecha} | {n['enlace'] or 'sin enlace'}")
            if n["resumen"]:
                lineas.append(f"    {n['resumen']}")
            if n["sospechosa"]:
                lineas.append("    ⚠ ALERTA: este texto contiene frases típicas de inyección de instrucciones.")
        texto = encabezado + "\n" + envolver(lineas)
    if errores:
        texto += "\nFuentes con error: " + "; ".join(errores)
    return texto
