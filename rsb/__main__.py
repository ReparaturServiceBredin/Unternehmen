"""Startet das Programm: python -m rsb  (bzw. Doppelklick auf RSB-Buchhaltung.exe)"""
import os
import socket
import sys
import threading
import time
from datetime import datetime, timedelta

from waitress import serve

from . import VERSION, VERSION_NUMMER, create_app
from . import db as dbm
from . import fenster, konfig, update
from .backup import auto_backup, backup_erstellen
from .logbuch import einrichten as log_einrichten
from .logbuch import log
from .hilfen import jetzt_dt

UPDATE_INTERVALL_STUNDEN = 6


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
                    from .email_historie import abgleich_mit_protokoll, faellig
                    if faellig(einst):  # E-Mail-Historie: gleiches Intervall wie der Anfragen-Abruf
                        e, fehler = abgleich_mit_protokoll(con)
                        if e and e["neu"]:
                            log.info(f"{jetzt_dt():%H:%M} E-Mail-Historie: {e['neu']} neue Mail(s) bei Kunden")
                        if fehler:
                            log.info(f"{jetzt_dt():%H:%M} E-Mail-Historie: {fehler}")
                    if not einst.get("anfragen_aktiv"):
                        continue
                    letzter = einst.get("anfragen_letzter_abruf")
                    intervall = max(int(einst.get("anfragen_intervall_min") or 5), 1)
                    if letzter and datetime.fromisoformat(letzter) > jetzt_dt() - timedelta(minutes=intervall):
                        continue
                    ergebnis = abruf_mit_protokoll(con)
                    if ergebnis and ergebnis["neu"]:
                        log.info(f"{jetzt_dt():%H:%M} Neue Anfragen: {ergebnis['neu']} "
                              f"(echt {ergebnis['echt']}, unsicher {ergebnis['unsicher']}, Spam {ergebnis['spam']})")
                finally:
                    con.close()
        except AbrufFehler as e:
            log.info(f"{jetzt_dt():%H:%M} Anfragen-Abruf: {e}")
        except Exception as e:  # Hintergrund darf nie abstürzen
            log.info(f"{jetzt_dt():%H:%M} Anfragen-Abruf unerwarteter Fehler: {e}")


def vertraege_hintergrund(app):
    """Einmal täglich fällige Verträge abrechnen (beim Start und danach stündlich prüfen)."""
    from .vertraege import abrechnungslauf

    while True:
        try:
            con = dbm.verbinden(app.config["DB_PFAD"])
            try:
                letzter = dbm.einstellungen(con).get("abo_letzter_lauf") or ""
                if letzter[:10] != jetzt_dt().date().isoformat():
                    with app.app_context():
                        e = abrechnungslauf(con, app.config["DATEN"])
                    if e["rechnungen"]:
                        log.info(f"{jetzt_dt():%H:%M} Verträge abgerechnet: {e['rechnungen']} Rechnung(en), "
                              f"{e['versendet']} versendet")
                    for f in e["fehler"]:
                        log.info(f"{jetzt_dt():%H:%M} Vertragsabrechnung: {f}")
            finally:
                con.close()
        except Exception as e:  # Hintergrund darf nie abstürzen
            log.info(f"{jetzt_dt():%H:%M} Vertragsabrechnung fehlgeschlagen: {e}")
        datenschutz_lauf(app)
        raten_lauf(app)
        time.sleep(3600)


def raten_lauf(app):
    """Einmal täglich: Zahlungsaufforderungen für bald fällige Raten senden."""
    from .raten import lauf
    try:
        con = dbm.verbinden(app.config["DB_PFAD"])
        try:
            if (dbm.einstellungen(con).get("raten_letzter_lauf") or "")[:10] != jetzt_dt().date().isoformat():
                with app.app_context():
                    e = lauf(con, app.config["DATEN"])
                with dbm.Transaktion(con):
                    dbm.einstellungen_speichern({"raten_letzter_lauf": jetzt_dt().isoformat(timespec="seconds")},
                                                con=con)
                if e["gesendet"]:
                    log.info(f"{jetzt_dt():%H:%M} Ratenzahlung: {e['gesendet']} Zahlungsaufforderung(en) gesendet")
                for f in e["fehler"]:
                    log.info(f"{jetzt_dt():%H:%M} Ratenzahlung: {f}")
        finally:
            con.close()
    except Exception as e:  # Hintergrund darf nie abstürzen
        log.info(f"{jetzt_dt():%H:%M} Ratenzahlung fehlgeschlagen: {e}")


def datenschutz_lauf(app):
    """Einmal täglich die Löschfristen anwenden, wenn in den Einstellungen eingeschaltet."""
    from .datenschutz import loeschlauf
    try:
        con = dbm.verbinden(app.config["DB_PFAD"])
        try:
            einst = dbm.einstellungen(con)
            if einst.get("ds_auto") and (einst.get("ds_letzter_lauf") or "")[:10] != jetzt_dt().date().isoformat():
                with app.app_context(), dbm.Transaktion(con):
                    z = loeschlauf(con, app.config["DATEN"])
                if any(z.values()):
                    log.info(f"{jetzt_dt():%H:%M} Datenschutz-Löschlauf: {z}")
        finally:
            con.close()
    except Exception as e:  # Hintergrund darf nie abstürzen
        log.info(f"{jetzt_dt():%H:%M} Datenschutz-Löschlauf fehlgeschlagen: {e}")


def update_pruefen(app):
    """Fragt die neueste Version ab und merkt sie sich (für den Hinweis in der Oberfläche)."""
    con = dbm.verbinden(app.config["DB_PFAD"])
    try:
        try:
            info = update.neueste_version()
            werte = {"update_letzte_pruefung": dbm.jetzt(), "update_fehler": "",
                     "update_verfuegbar": info["version"] if update.ist_neuer(info["version"], VERSION_NUMMER) else "",
                     "update_hinweise": info["hinweise"][:4000]}
        except update.UpdateFehler as e:
            info, werte = None, {"update_letzte_pruefung": dbm.jetzt(), "update_fehler": str(e)}
        dbm.einstellungen_speichern(werte, con)
        return info
    finally:
        con.close()


def update_beim_start(app):
    """Installiert eine neue Version direkt beim Start (vor dem Arbeiten), wenn automatisch erlaubt."""
    if not update.ist_exe() or os.environ.get("RSB_KEIN_UPDATE"):
        return
    con = dbm.verbinden(app.config["DB_PFAD"])
    try:
        auto = dbm.einstellungen(con).get("update_auto")
    finally:
        con.close()
    log.info("Suche nach Updates …")
    info = update_pruefen(app)
    if not info or not update.ist_neuer(info["version"], VERSION_NUMMER):
        log.info("Programm ist aktuell." if info else "Update-Prüfung nicht möglich (offline?) – es geht trotzdem los.")
        return
    if not auto:
        log.info(f"Neue Version {info['version']} verfügbar (automatische Installation ist ausgeschaltet).")
        return
    log.info(f"Neue Version {info['version']} gefunden – wird installiert …")
    try:
        update.installieren(info, vor_austausch=lambda: _backup_vor_update(app, info["version"]))
    except update.UpdateFehler as e:
        log.info(f"Update fehlgeschlagen, es geht mit der bisherigen Version weiter: {e}")
        return
    log.info("Update installiert – Programm startet neu …")
    update.neu_starten(verzoegerung=0.5)
    time.sleep(30)  # neu_starten beendet diesen Prozess


def _backup_vor_update(app, version):
    con = dbm.verbinden(app.config["DB_PFAD"])
    try:
        einst = dbm.einstellungen(con)
        ziel, _ = backup_erstellen(app.config["DATEN"], app.config["DB_PFAD"], einst)
        dbm.protokollieren("backup_vor_update", "system", None,
                           {"datei": ziel.name, "von": VERSION_NUMMER, "nach": version}, con=con)
    finally:
        con.close()
        dbm.festschreiben(app.config["DB_PFAD"])


def update_hintergrund(app):
    while True:
        time.sleep(UPDATE_INTERVALL_STUNDEN * 3600)
        try:
            info = update_pruefen(app)
            if info and update.ist_neuer(info["version"], VERSION_NUMMER):
                log.info(f"{jetzt_dt():%H:%M} Neue Version {info['version']} verfügbar – "
                      "wird beim nächsten Start installiert (oder in der Oberfläche auf „Jetzt aktualisieren“).")
        except Exception as e:
            log.info(f"{jetzt_dt():%H:%M} Update-Prüfung fehlgeschlagen: {e}")


def _beenden(app):
    dbm.festschreiben(app.config["DB_PFAD"])
    os._exit(0)


def port_belegt(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port)) == 0


def fenster_modus(db_pfad):
    try:
        con = dbm.verbinden(db_pfad)
        try:
            return dbm.einstellungen(con).get("fenster_modus") or "app"
        finally:
            con.close()
    except Exception:
        return "app"


def im_netz(db_pfad):
    """Einstellung „Programm im WLAN erreichbar machen“ (für QR-Codes am Handy)."""
    try:
        con = dbm.verbinden(db_pfad)
        try:
            return bool(dbm.einstellungen(con).get("handy_im_netz"))
        finally:
            con.close()
    except Exception:
        return False


def erstes_passwort(app):
    """Server-Modus: Passwort aus RSB_ERSTES_PASSWORT setzen, solange noch keins eingerichtet ist."""
    from werkzeug.security import generate_password_hash
    pw = os.environ.get("RSB_ERSTES_PASSWORT") or ""
    con = dbm.verbinden(app.config["DB_PFAD"])
    try:
        einst = dbm.einstellungen(con)
        if einst.get("passwort_hash"):
            if pw:
                log.warning("RSB_ERSTES_PASSWORT ist noch gesetzt, wird aber nicht mehr gebraucht – bitte entfernen.")
            if not einst.get("login_aktiv"):
                with dbm.Transaktion(con):
                    dbm.einstellungen_speichern({"login_aktiv": True}, con)
            return
        if len(pw) < 8:
            log.warning("Noch kein Passwort eingerichtet. Bitte RSB_ERSTES_PASSWORT (mindestens 8 Zeichen) setzen "
                        "und neu starten – bis dahin ist kein Zugriff aus dem Netzwerk möglich.")
            return
        with dbm.Transaktion(con):
            dbm.einstellungen_speichern({"passwort_hash": generate_password_hash(pw), "login_aktiv": True}, con)
            dbm.protokollieren("passwort_eingerichtet", "system", None, {"quelle": "RSB_ERSTES_PASSWORT"}, con=con)
        log.info("Passwort aus RSB_ERSTES_PASSWORT eingerichtet. Bitte die Variable jetzt aus der .env entfernen.")
    finally:
        con.close()


def hintergrund_starten(app):
    """Hintergrundaufgaben nur in einem Prozess je Datenordner (siehe rsb/sperre.py)."""
    from .sperre import Sperre
    sperre = Sperre(app.config["DATEN"])
    if not sperre.erwerben():
        log.warning("Hintergrundaufgaben laufen bereits in einem anderen Prozess mit diesem Datenordner – "
                    "hier nur die Oberfläche.")
        return None
    threading.Thread(target=anfragen_hintergrund, args=(app,), daemon=True).start()
    threading.Thread(target=vertraege_hintergrund, args=(app,), daemon=True).start()
    return sperre


def main():
    from .datenort import ermitteln
    env_datei = konfig.laden()
    server = konfig.server_modus()
    if server:  # kein Fenster, kein Symbol, kein EXE-Update
        for k in ("RSB_KEIN_BROWSER", "RSB_KEIN_SYMBOL", "RSB_KEIN_UPDATE"):
            os.environ.setdefault(k, "1")
    os.environ["RSB_DATEN"] = str(ermitteln())  # ein fester Datenordner – auch für Neustart nach Update
    log_datei = log_einrichten(os.environ["RSB_DATEN"])
    if env_datei:
        log.info(f"Einstellungen aus {env_datei} übernommen.")
    daten_db = os.path.join(os.environ["RSB_DATEN"], "buchhaltung.db")
    host = os.environ.get("RSB_HOST") or ("0.0.0.0" if server or (os.path.exists(daten_db) and im_netz(daten_db))
                                          else "127.0.0.1")
    port = int(os.environ.get("RSB_PORT", "5000"))
    adresse = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}"

    if server and port_belegt(host, port):
        log.error(f"Port {port} ist bereits belegt – läuft das Programm schon? Abbruch.")
        sys.exit(1)
    if os.environ.get("RSB_WARTE_AUF_PORT"):
        # Neustart nach Update: warten, bis die alte Version den Port freigegeben hat
        for _ in range(60):
            if not port_belegt(host, port):
                break
            time.sleep(0.5)
    elif port_belegt(host, port):
        log.info("Das Programm läuft bereits – öffne das Fenster.")
        fenster.oeffnen(adresse, fenster_modus(daten_db))
        time.sleep(1)
        return

    if not server:
        update.alte_versionen_aufraeumen()
    app = create_app()
    if server:
        erstes_passwort(app)
    else:
        update_beim_start(app)
    app.config["SERVER_HOST"], app.config["SERVER_PORT"] = host, port
    try:
        ziel = auto_backup(app.config["DATEN"], app.config["DB_PFAD"])
        if ziel:
            log.info(f"Automatisches Backup erstellt: {ziel}")
    except Exception as e:  # ein fehlgeschlagenes Backup darf den Start nicht verhindern
        log.info(f"WARNUNG: Automatisches Backup fehlgeschlagen: {e}")
    log.info("=" * 60)
    log.info(f" Reparatur Service Bredin – Buchhaltung, Version {VERSION}")
    log.info(f" Läuft unter: {adresse}")
    log.info(f" Daten-Ordner: {app.config['DATEN']}")
    log.info(f" Protokolldatei: {log_datei}" + (" · Server-Modus" if server else ""))
    log.info("=" * 60)
    sperre = hintergrund_starten(app)
    if update.ist_exe() and not os.environ.get("RSB_KEIN_UPDATE"):
        threading.Thread(target=update_hintergrund, args=(app,), daemon=True).start()

    if server:
        import signal

        def stopp(*_):
            log.info("Beenden angefordert – Datenbank wird sauber geschlossen.")
            if sperre:
                sperre.freigeben()
            _beenden(app)
        signal.signal(signal.SIGTERM, stopp)
        signal.signal(signal.SIGINT, stopp)
        threads = int(os.environ.get("RSB_THREADS") or 8)
        serve(app, host=host, port=port, threads=threads, ident="RSB")  # blockiert bis SIGTERM
        return

    server_thread = threading.Thread(target=serve, args=(app,), kwargs={"host": host, "port": port, "threads": 4},
                                     daemon=True)
    server_thread.start()
    if not os.environ.get("RSB_KEIN_BROWSER"):
        threading.Timer(1.5, lambda: fenster.oeffnen(adresse, fenster_modus(app.config["DB_PFAD"]))).start()

    # Symbol neben der Uhr (blockiert bis „Beenden“). Ohne Symbol läuft der Server einfach weiter.
    if not os.environ.get("RSB_KEIN_SYMBOL") and fenster.symbol_anzeigen(
            f"Reparatur Service Bredin – Buchhaltung {VERSION_NUMMER}", adresse, app.config["DATEN"],
            lambda: fenster_modus(app.config["DB_PFAD"]), lambda: _beenden(app)):
        os._exit(0)
    try:
        while server_thread.is_alive():
            server_thread.join(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
