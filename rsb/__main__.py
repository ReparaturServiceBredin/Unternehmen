"""Startet das Programm: python -m rsb"""
import os
import threading
import time
import webbrowser
from datetime import datetime, timedelta

from waitress import serve

from . import create_app
from . import db as dbm
from .backup import auto_backup


def anfragen_hintergrund(app):
    """Prüft im Hintergrund regelmäßig das Postfach auf neue Kontaktformular-Anfragen."""
    from .anfragen import AbrufFehler, abruf_mit_protokoll

    while True:
        time.sleep(60)
        try:
            with app.app_context():
                con = dbm.verbinden(app.config["DB_PFAD"])
                try:
                    einst = dbm.einstellungen(con)
                    if not einst.get("anfragen_aktiv"):
                        continue
                    letzter = einst.get("anfragen_letzter_abruf")
                    intervall = max(int(einst.get("anfragen_intervall_min") or 5), 1)
                    if letzter and datetime.fromisoformat(letzter) > datetime.now() - timedelta(minutes=intervall):
                        continue
                    ergebnis = abruf_mit_protokoll(con)
                    if ergebnis and ergebnis["neu"]:
                        print(f"{datetime.now():%H:%M} Neue Anfragen: {ergebnis['neu']} "
                              f"(echt {ergebnis['echt']}, unsicher {ergebnis['unsicher']}, Spam {ergebnis['spam']})")
                finally:
                    con.close()
        except AbrufFehler as e:
            print(f"{datetime.now():%H:%M} Anfragen-Abruf: {e}")
        except Exception as e:  # Hintergrund darf nie abstürzen
            print(f"{datetime.now():%H:%M} Anfragen-Abruf unerwarteter Fehler: {e}")


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
    threading.Thread(target=anfragen_hintergrund, args=(app,), daemon=True).start()
    if not os.environ.get("RSB_KEIN_BROWSER"):
        threading.Timer(1.5, lambda: webbrowser.open(adresse)).start()
    serve(app, host=host, port=port, threads=4)


if __name__ == "__main__":
    main()
