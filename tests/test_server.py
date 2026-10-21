"""Server-Betrieb: .env-Konfiguration, Sperre für Hintergrundaufgaben, Anmeldepflicht, Proxy, Sicherheits-Header."""
import os
import time

import pytest

from rsb import create_app, konfig
from rsb import db as dbm
from rsb.sperre import ABGELAUFEN_SEK, Sperre


def test_env_datei_lesen_und_laden(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# Kommentar\nRSB_PORT=5055\nexport RSB_MODUS="server"\nRSB_HOST=0.0.0.0  # Netz\nKAPUTT\n',
                   encoding="utf-8")
    assert konfig.lesen(env) == {"RSB_PORT": "5055", "RSB_MODUS": "server", "RSB_HOST": "0.0.0.0"}
    monkeypatch.setenv("RSB_PORT", "6000")  # gesetzte Umgebung gewinnt
    vorher = {k: os.environ.pop(k, None) for k in ("RSB_MODUS", "RSB_HOST")}
    try:
        assert konfig.laden([tmp_path / "fehlt.env", env]) == env
        assert os.environ["RSB_PORT"] == "6000" and konfig.server_modus() and os.environ["RSB_HOST"] == "0.0.0.0"
    finally:
        for k, v in vorher.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_sperre_nur_ein_besitzer_und_verwaist(tmp_path):
    a, b = Sperre(tmp_path), Sperre(tmp_path)
    assert a.erwerben() and not b.erwerben()
    a.freigeben()
    assert b.erwerben()
    alt = time.time() - ABGELAUFEN_SEK - 10  # abgestürzter Besitzer: Sperre ist zu alt
    os.utime(b.pfad, (alt, alt))
    b._halten = False
    c = Sperre(tmp_path)
    assert c.erwerben()
    c.freigeben()


@pytest.fixture
def server_app(tmp_path, monkeypatch):
    monkeypatch.setenv("RSB_MODUS", "server")
    monkeypatch.setenv("RSB_HINTER_PROXY", "1")
    monkeypatch.setenv("RSB_SICHERE_COOKIES", "1")
    app = create_app(tmp_path / "Daten", testing=True)
    yield app


def test_server_modus_anmeldung_pflicht_und_header(server_app):
    c = server_app.test_client()
    # ohne Passwort: kein Zugriff, auch nicht „von localhost“ (Reverse-Proxy) – nur die Versionsabfrage
    assert c.get("/", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code == 403
    v = c.get("/version")
    assert v.status_code == 200 and v.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Strict-Transport-Security" in v.headers
    # Passwort gesetzt, Anmeldung in den Einstellungen „aus“ → trotzdem Login nötig
    from werkzeug.security import generate_password_hash
    con = dbm.verbinden(server_app.config["DB_PFAD"])
    dbm.einstellungen_speichern({"passwort_hash": generate_password_hash("geheim123"), "login_aktiv": False}, con)
    con.commit()
    con.close()
    r = c.get("/", headers={"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https"})
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert server_app.config["SESSION_COOKIE_SECURE"]


def test_erstes_passwort(server_app, monkeypatch):
    from rsb.__main__ import erstes_passwort
    monkeypatch.setenv("RSB_ERSTES_PASSWORT", "kurz")
    erstes_passwort(server_app)
    con = dbm.verbinden(server_app.config["DB_PFAD"])
    assert not dbm.einstellungen(con).get("passwort_hash")
    monkeypatch.setenv("RSB_ERSTES_PASSWORT", "langes-passwort")
    erstes_passwort(server_app)
    e = dbm.einstellungen(con)
    assert e["passwort_hash"] and e["login_aktiv"] is True
    con.close()


def test_logbuch(tmp_path):
    from rsb.logbuch import einrichten, log
    datei = einrichten(tmp_path)
    log.info("Testeintrag Umlaute äöü")
    for h in __import__("logging").getLogger().handlers:
        h.flush()
    assert "Testeintrag Umlaute äöü" in datei.read_text(encoding="utf-8")
