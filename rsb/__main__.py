"""Startet das Programm: python -m rsb"""
import os
import threading
import webbrowser

from waitress import serve

from . import create_app
from .backup import auto_backup


def main():
    app = create_app()
    host = os.environ.get("RSB_HOST", "127.0.0.1")
    port = int(os.environ.get("RSB_PORT", "5000"))
    try:
        ziel = auto_backup(app.config["DATEN"], app.config["DB_PFAD"])
        if ziel:
            print(f"Automatisches Backup erstellt: {ziel}")
    except Exception as e:  # ein fehlgeschlagenes Backup darf den Start nicht verhindern
        print(f"WARNUNG: Automatisches Backup fehlgeschlagen: {e}")
    adresse = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}"
    print("=" * 60)
    print(" Reparatur Service Bredin – Buchhaltung")
    print(f" Läuft unter: {adresse}")
    print(f" Daten-Ordner: {app.config['DATEN']}")
    print(" Zum Beenden dieses Fenster schließen (oder Strg+C).")
    print("=" * 60)
    if not os.environ.get("RSB_KEIN_BROWSER"):
        threading.Timer(1.5, lambda: webbrowser.open(adresse)).start()
    serve(app, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()
