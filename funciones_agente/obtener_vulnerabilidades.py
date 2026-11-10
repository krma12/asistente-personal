# Módulo para consultar vulnerabilidades explotadas activamente (catálogo CISA KEV)
import json
from datetime import date, timedelta

from funciones_agente.contenido_externo import DescargaError, descargar, envolver, limpiar_texto

# Catálogo oficial de la agencia de ciberseguridad de EE. UU. (CISA): vulnerabilidades
# con evidencia de explotación real. URL fija: el LLM no puede cambiarla.
URL_KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
MAX_BYTES_KEV = 15_000_000


def obtener_vulnerabilidades_explotadas(dias: int = 7, max_resultados: int = 10,
                                        hoy: date | None = None, descargador=descargar) -> str:
    """
    Lista las vulnerabilidades agregadas al catálogo CISA KEV en los últimos días.

    Argumentos:
        dias: ventana de búsqueda (1 a 30).
        max_resultados: cuántas devolver (1 a 20).
        hoy, descargador: solo para pruebas.
    """
    dias = min(max(int(dias), 1), 30)
    max_resultados = min(max(int(max_resultados), 1), 20)
    desde = (hoy or date.today()) - timedelta(days=dias)

    try:
        catalogo = json.loads(descargador(URL_KEV, MAX_BYTES_KEV))
    except DescargaError as e:
        return f"Error al descargar el catálogo CISA KEV: {e}"
    except (json.JSONDecodeError, UnicodeDecodeError):
        return "Error: el catálogo CISA KEV no tiene el formato esperado."

    recientes = []
    for v in catalogo.get("vulnerabilities", []):
        try:
            agregada = date.fromisoformat(str(v.get("dateAdded", "")))
        except ValueError:
            continue
        if agregada >= desde:
            recientes.append((agregada, v))
    recientes.sort(key=lambda par: par[0], reverse=True)

    total = len(recientes)
    encabezado = f"CISA KEV — vulnerabilidades explotadas agregadas en los últimos {dias} día(s): {total}."
    if not recientes:
        return encabezado + "\nNinguna en este periodo."

    lineas = []
    for agregada, v in recientes[:max_resultados]:
        cve = limpiar_texto(v.get("cveID"), 30)
        producto = limpiar_texto(f"{v.get('vendorProject', '')} {v.get('product', '')}", 100)
        nombre = limpiar_texto(v.get("vulnerabilityName"), 150)
        descripcion = limpiar_texto(v.get("shortDescription"), 250)
        ransomware = "sí" if str(v.get("knownRansomwareCampaignUse", "")).lower() == "known" else "no conocido"
        limite = limpiar_texto(v.get("dueDate"), 12)
        lineas.append(f"- {cve} | {producto} | agregada {agregada} | plazo de parche (agencias de EE. UU.): {limite} | ransomware: {ransomware}")
        lineas.append(f"    {nombre}. {descripcion}")
        lineas.append(f"    https://nvd.nist.gov/vuln/detail/{cve}")
    extra = f"\n(Se muestran {max_resultados} de {total}.)" if total > max_resultados else ""
    return encabezado + "\n" + envolver(lineas) + extra
