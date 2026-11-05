# Módulo para consultar precios de acciones usando yfinance
import yfinance as yf

# Respaldo por si llega un nombre en lugar de un ticker.
# (Normalmente Claude ya envía el ticker, p. ej. "AAPL").
COMPANY_TICKERS = {
    "microsoft": "MSFT",
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "nvidia": "NVDA",
    "tesla": "TSLA",
}


def resolver_ticker(empresa_o_ticker: str) -> str:
    """Convierte un nombre de empresa conocido en ticker; si no, lo usa tal cual en mayúsculas."""
    texto = (empresa_o_ticker or "").strip()
    return COMPANY_TICKERS.get(texto.lower(), texto.upper())


def obtener_precio_accion(ticker: str) -> str:
    """
    Retorna el precio de cierre más reciente de una acción.

    Argumentos:
        ticker: Símbolo bursátil (p. ej. "MSFT") o nombre de empresa conocido.

    Retorna:
        Texto con el precio y la moneda, o un mensaje explicativo.
    """
    simbolo = resolver_ticker(ticker)
    if not simbolo:
        return "Error: no se indicó ninguna empresa o ticker."

    try:
        accion = yf.Ticker(simbolo)
        # 5 días en lugar de 1: así hay datos aunque hoy sea fin de semana o día feriado
        data = accion.history(period="5d")
        if data.empty:
            return f"No se encontraron cotizaciones para '{simbolo}' (¿ticker incorrecto?)."

        precio = data["Close"].iloc[-1]
        fecha = data.index[-1].strftime("%Y-%m-%d")
        try:
            moneda = accion.fast_info.get("currency") or "USD"
        except Exception:
            moneda = "USD"
        return f"{simbolo}: {precio:.2f} {moneda} (cierre del {fecha})"
    except Exception as e:
        return f"Error al consultar el precio de '{simbolo}': {e}"
