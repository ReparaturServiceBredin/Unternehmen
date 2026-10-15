"""Reparatur Service Bredin – Buchhaltung & Rechnungen."""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, flash, redirect, request, session, url_for

from . import db as dbm
from .hilfen import EingabeFehler, datum_de, euro, kunde_name, menge_text, zeit_de
from .sicherheit import csrf_pruefen, csrf_token, sitzungs_schluessel

VERSION_NUMMER = "0.11.0"
VERSION = VERSION_NUMMER
if getattr(sys, "frozen", False):
    # EXE-Version: der Ordner „Daten“ liegt direkt neben RSB-Buchhaltung.exe
    PROJEKT = Path(sys.executable).resolve().parent
else:
    PROJEKT = Path(__file__).resolve().parent.parent


def create_app(daten_dir=None, testing=False):
    daten = Path(daten_dir or os.environ.get("RSB_DATEN") or PROJEKT / "Daten").resolve()
    for unterordner in ("dokumente", "belege", "bilder", "backups", "geheim", "fotos"):
        (daten / unterordner).mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        DATEN=str(daten),
        DB_PFAD=str(daten / "buchhaltung.db"),
        SECRET_KEY=sitzungs_schluessel(daten),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=10),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        MAX_CONTENT_LENGTH=60 * 1024 * 1024,  # Fotos vom Handy können groß sein
        TESTING=testing,
    )
    dbm.initialisieren(app.config["DB_PFAD"])
    app.teardown_appcontext(dbm.schliessen)

    def tage_seit(iso):
        try:
            return (date.today() - datetime.fromisoformat(iso).date()).days
        except (TypeError, ValueError):
            return ""

    def zeit_sek(iso):
        """ISO-Zeitstempel -> 15.10.2026 14:03:27 (mit Sekunden)."""
        try:
            return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M:%S")
        except (TypeError, ValueError):
            return iso or ""

    app.jinja_env.filters.update(zeit_sek=zeit_sek, euro=euro, datum=datum_de, zeit=zeit_de, menge=menge_text, kunde_name=kunde_name,
                                 tage_seit=tage_seit)
    app.jinja_env.globals.update(csrf_token=csrf_token, version=VERSION)

    from .views import bp
    app.register_blueprint(bp)

    offen = {"main.login", "main.einrichten", "main.version_info", "static"}

    @app.before_request
    def anmeldung_pruefen():
        if request.endpoint in offen:
            return None
        if not dbm.einstellung("login_aktiv"):
            # Passwortschutz ausgeschaltet: direkt angemeldet (Programm ist nur am eigenen PC erreichbar)
            session["angemeldet"] = True
            session["benutzer"] = "inhaber"
            csrf_pruefen()
            return None
        if not dbm.einstellung("passwort_hash"):
            return redirect(url_for("main.einrichten"))
        if not session.get("angemeldet"):
            return redirect(url_for("main.login", weiter=request.path))
        csrf_pruefen()
        return None

    @app.context_processor
    def globale_werte():
        if request.endpoint in ("static",):
            return {}
        try:
            einst = dbm.einstellungen()
            offene_anfragen = dbm.get_db().execute(
                "SELECT COUNT(*) FROM anfragen WHERE status='neu' AND einstufung<>'spam'").fetchone()[0]
            leihen_ueberfaellig = dbm.get_db().execute(
                "SELECT COUNT(*) FROM leihen WHERE rueckgabe_am IS NULL AND storniert_am IS NULL "
                "AND rueckgabe_geplant < date('now', 'localtime')").fetchone()[0]
        except Exception:
            einst, offene_anfragen, leihen_ueberfaellig = {}, 0, 0
        from .update import ist_exe, ist_neuer
        update_da = einst.get("update_verfuegbar") if ist_neuer(einst.get("update_verfuegbar"), VERSION_NUMMER) \
            else None
        return {"einst": einst, "offene_anfragen": offene_anfragen, "leihen_ueberfaellig": leihen_ueberfaellig, "update_da": update_da, "ist_exe": ist_exe()}

    @app.errorhandler(EingabeFehler)
    def eingabefehler(e):
        flash(str(e), "fehler")
        return redirect(request.referrer or url_for("main.start"))

    return app
