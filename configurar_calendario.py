"""
Configuración única de Google Calendar.

Ejecuta:  python configurar_calendario.py

Abre el navegador para que autorices el acceso a tu calendario y guarda el permiso en
secretos/google_token.json (ignorado por Git). Solo hace falta repetirlo si revocas el
acceso o si el permiso expira.

Antes necesitas secretos/google_credentials.json (ver README, sección "Google Calendar").
"""
from funciones_agente.calendario import CARPETA_SECRETOS, RUTA_CREDENCIALES, RUTA_TOKEN, SCOPES


def main() -> None:
    CARPETA_SECRETOS.mkdir(exist_ok=True)
    if not RUTA_CREDENCIALES.is_file():
        print(f"No encontré {RUTA_CREDENCIALES}.\n"
              "Descarga el archivo de credenciales OAuth (tipo 'App de escritorio') desde "
              "Google Cloud Console y guárdalo con ese nombre. Los pasos están en el README.")
        raise SystemExit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flujo = InstalledAppFlow.from_client_secrets_file(str(RUTA_CREDENCIALES), SCOPES)
    credenciales = flujo.run_local_server(port=0, open_browser=True)
    RUTA_TOKEN.write_text(credenciales.to_json(), encoding="utf-8")
    print(f"Listo. Permiso guardado en {RUTA_TOKEN}. Ya puedes usar el calendario.")


if __name__ == "__main__":
    main()
