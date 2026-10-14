"""Reparatur Service Bredin – Buchhaltung & Rechnungen."""
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, flash, redirect, request, session, url_for

from . import db as dbm
from .hilfen import EingabeFehler, datum_de, euro, kunde_name, menge_text, zeit_de
from .sicherheit import csrf_pruefen, csrf_token, sitzungs_schluessel

VERSION = "0.3.0 (Aufträge & KVA)"
PROJEKT = Path(__file__).resolve().parent.parent


def create_app(daten_dir=None, testing=False):
    daten = Path(daten_dir or os.environ.get("RSB_DATEN") or PROJEKT / "Daten").resolve()
    for unterordner in ("dokumente", "belege", "bilder", "backups", "geheim"):
        (daten / unterordner).mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(
        DATEN=str(daten),
        DB_PFAD=str(daten / "buchhaltung.db"),
        SECRET_KEY=sitzungs_schluessel(daten),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=10),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
        TESTING=testing,
    )
    dbm.initialisieren(app.config["DB_PFAD"])
    app.teardown_appcontext(dbm.schliessen)

    def tage_seit(iso):
        try:
            return (date.today() - datetime.fromisoformat(iso).date()).days
        except (TypeError, ValueError):
            return ""

    app.jinja_env.filters.update(euro=euro, datum=datum_de, zeit=zeit_de, menge=menge_text, kunde_name=kunde_name,
                                 tage_seit=tage_seit)
    app.jinja_env.globals.update(csrf_token=csrf_token, version=VERSION)

    from .views import bp
    app.register_blueprint(bp)

    offen = {"main.login", "main.einrichten", "static"}

    @app.before_request
    def anmeldung_pruefen():
        if request.endpoint in offen:
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
        except Exception:
            einst, offene_anfragen = {}, 0
        return {"einst": einst, "offene_anfragen": offene_anfragen}

    @app.errorhandler(EingabeFehler)
    def eingabefehler(e):
        flash(str(e), "fehler")
        return redirect(request.referrer or url_for("main.start"))

    return app
