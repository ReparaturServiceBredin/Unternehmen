"""Weitere Benutzer, Anmeldeschutz und Server-Funktionen (Sicherung hochladen, Anmeldung immer an)."""
import io
import zipfile

import pytest
from werkzeug.security import generate_password_hash

from rsb import benutzer as bn
from rsb import create_app
from rsb import db as dbm
from tests.conftest import post


@pytest.fixture(autouse=True)
def anmeldung_an(app):
    """Passwortschutz eingeschaltet (Inhaber-Passwort geheim123)."""
    con = dbm.verbinden(app.config["DB_PFAD"])
    dbm.einstellungen_speichern({"passwort_hash": generate_password_hash("geheim123"), "login_aktiv": True}, con)
    con.commit()
    con.close()


@pytest.fixture(autouse=True)
def sperren_leeren():
    bn._versuche.clear()
    yield
    bn._versuche.clear()


def anmelden(app, name, pw, adresse="198.51.100.1"):
    c = app.test_client()
    r = c.post("/login", data={"benutzer": name, "passwort": pw}, environ_base={"REMOTE_ADDR": adresse})
    with c.session_transaction() as s:
        s["csrf"] = "test-token"
    return c, r


def test_benutzer_anlegen_anmelden_rechte_und_protokoll(app, con):
    client, _ = anmelden(app, "", "geheim123", adresse="198.51.100.9")
    r = post(client, "/benutzer/neu", name="Max", anzeigename="Max Muster", rolle="mitarbeiter", passwort="passwort-1",
             passwort2="passwort-1")
    assert r.status_code == 302
    b = con.execute("SELECT * FROM benutzer").fetchone()
    assert b["name"] == "max" and b["rolle"] == "mitarbeiter" and b["passwort_hash"] != "passwort-1"
    # Name doppelt / reserviert / Passwort zu kurz
    for name, pw in (("max", "passwort-1"), ("inhaber", "passwort-1"), ("anna", "kurz")):
        post(client, "/benutzer/neu", name=name, rolle="mitarbeiter", passwort=pw, passwort2=pw)
    assert con.execute("SELECT COUNT(*) FROM benutzer").fetchone()[0] == 1

    assert "Benutzername" in app.test_client().get("/login").get_data(as_text=True)
    m, r = anmelden(app, "max", "falsch")
    assert r.status_code == 200 and "falsch" in r.get_data(as_text=True)
    m, r = anmelden(app, "MAX ", "passwort-1")
    assert r.status_code == 302
    assert m.get("/kunden").status_code == 200
    assert m.get("/einstellungen/firma").status_code == 403
    assert m.get("/protokoll").status_code == 403
    assert m.get("/einstellungen/logo.png").status_code in (200, 404)
    assert "Einstellungen" not in m.get("/kunden").get_data(as_text=True).split("nav-unten")[1][:400]
    post(m, "/kunden/neu", typ="privat", vorname="Eva", nachname="Test", land="Deutschland")
    zeile = con.execute("SELECT benutzer FROM protokoll WHERE aktion LIKE '%kunde%' ORDER BY id DESC").fetchone()
    assert zeile["benutzer"] == "max"
    # Inhaber meldet sich weiter ohne Benutzernamen an
    i, r = anmelden(app, "", "geheim123")
    assert r.status_code == 302 and i.get("/einstellungen/firma").status_code == 200

    # Deaktivieren bzw. neues Passwort beendet bestehende Sitzungen
    bid = b["id"]
    post(client, f"/benutzer/{bid}", passwort="neues-pass-1", passwort2="neues-pass-1")
    assert m.get("/kunden").status_code == 302
    m, r = anmelden(app, "max", "neues-pass-1")
    assert m.get("/kunden").status_code == 200
    post(client, f"/benutzer/{bid}", anzeigename="Max", rolle="mitarbeiter")  # aktiv nicht angehakt
    assert m.get("/kunden").status_code == 302
    assert anmelden(app, "max", "neues-pass-1")[1].status_code == 200  # Anmeldung abgelehnt
    # Rolle Inhaber: alle Rechte
    post(client, f"/benutzer/{bid}", anzeigename="Max", rolle="inhaber", aktiv="1")
    m, r = anmelden(app, "max", "neues-pass-1")
    assert m.get("/einstellungen/firma").status_code == 200


def test_anmeldeschutz_sperrt_nach_fehlversuchen(app):
    for _ in range(bn.FEHLVERSUCHE):
        assert anmelden(app, "", "falsch")[1].status_code == 200
    c, r = anmelden(app, "", "geheim123")
    assert r.status_code == 429 and "Zu viele" in r.get_data(as_text=True)
    assert anmelden(app, "", "geheim123", adresse="198.51.100.2")[1].status_code == 302  # andere Adresse
    bn._versuche.clear()
    assert anmelden(app, "", "geheim123")[1].status_code == 302


@pytest.fixture
def server_app(tmp_path, monkeypatch):
    monkeypatch.setenv("RSB_MODUS", "server")
    app = create_app(tmp_path / "Daten", testing=True)
    con = dbm.verbinden(app.config["DB_PFAD"])
    dbm.einstellungen_speichern({"passwort_hash": generate_password_hash("geheim123"), "login_aktiv": False}, con)
    con.commit()
    con.close()
    return app


def test_server_login_ohne_schleife_und_schutz_nicht_abschaltbar(server_app):
    c = server_app.test_client()
    assert c.get("/login").status_code == 200  # früher: Weiterleitung zur Startseite → Schleife
    c, r = anmelden(server_app, "", "geheim123")
    assert r.status_code == 302 and c.get("/kunden").status_code == 200
    r = post(c, "/einstellungen/passwort", aktion="aus")
    assert r.status_code == 302
    assert not dbm.einstellung("login_aktiv", dbm.verbinden(server_app.config["DB_PFAD"]))
    assert c.get("/kunden").status_code == 200  # weiterhin angemeldet, Anmeldung bleibt Pflicht
    assert "ausschalten" not in c.get("/einstellungen/sicherheit").get_data(as_text=True)


def test_sicherung_hochladen_und_im_server_einspielen(server_app, tmp_path):
    c, _ = anmelden(server_app, "", "geheim123")
    # keine Sicherung
    r = c.post("/einstellungen/backup/hochladen", data={"csrf": "test-token",
                                                         "sicherung": (io.BytesIO(b"kein zip"), "x.zip")})
    assert r.status_code == 302
    daten = tmp_path / "Daten"
    assert not list((daten / "backups").glob("hochgeladen_*"))
    # echte Sicherung eines anderen Rechners: Datenbank + Schlüssel
    quelle = create_app(tmp_path / "Alt", testing=True)
    con = dbm.verbinden(quelle.config["DB_PFAD"])
    dbm.einstellungen_speichern({"firma_name": "Alte Firma"}, con)
    con.commit()
    con.close()
    from rsb.backup import backup_erstellen
    zip_pfad, _ = backup_erstellen(tmp_path / "Alt", quelle.config["DB_PFAD"])
    with zipfile.ZipFile(zip_pfad) as z:
        assert "geheim/schluessel.key" in z.namelist() or not (tmp_path / "Alt/geheim/schluessel.key").exists()
    r = c.post("/einstellungen/backup/hochladen", data={"csrf": "test-token",
                                                         "sicherung": (open(zip_pfad, "rb"), "backup.zip")})
    assert r.status_code == 302
    hoch = list((daten / "backups").glob("hochgeladen_*.zip"))
    assert len(hoch) == 1
    seite = c.get("/einstellungen/backup").get_data(as_text=True)
    assert "Hochgeladen" in seite and "Alte Firma" in seite
    r = post(c, "/einstellungen/backup/wiederherstellen", quelle=str(hoch[0]))
    assert r.status_code == 200 and "docker compose restart" in r.get_data(as_text=True)
    from rsb import wiederherstellung as wh
    assert wh.vorgemerkt(daten)["quelle"] == str(hoch[0])
    bericht = wh.ausfuehren(daten)
    assert bericht["ok"] and bericht["inhalt"]["firma"] == "Alte Firma"


def test_backup_enthaelt_schluessel(app):
    from rsb.sicherheit import verschluesseln
    with app.app_context():
        verschluesseln("x")  # legt den Schlüssel an
    from rsb.backup import backup_erstellen
    ziel, _ = backup_erstellen(app.config["DATEN"], app.config["DB_PFAD"])
    with zipfile.ZipFile(ziel) as z:
        assert "geheim/schluessel.key" in z.namelist()
        assert "geheim/sitzung.key" not in z.namelist()


def test_qr_adresse_im_server_modus():
    from rsb.annahme import basis_url
    assert basis_url({}, 5000, "https://buchhaltung.example.de/") == "https://buchhaltung.example.de"
    assert basis_url({"handy_adresse": "192.168.0.5:5000"}, 5000, "https://x") == "http://192.168.0.5:5000"


def test_wiederherstellung_ohne_passwort_sperrt_nicht_aus(server_app, tmp_path):
    from rsb import wiederherstellung as wh
    from rsb.backup import backup_erstellen
    quelle = create_app(tmp_path / "PC", testing=True)  # Windows-PC ohne Passwortschutz
    zip_pfad, _ = backup_erstellen(tmp_path / "PC", quelle.config["DB_PFAD"])
    daten = tmp_path / "Daten"
    ziel = daten / "backups" / zip_pfad.name.replace("backup_", "hochgeladen_")
    ziel.write_bytes(zip_pfad.read_bytes())
    wh.vormerken(daten, str(ziel))
    assert wh.ausfuehren(daten)["ok"]
    c, r = anmelden(server_app, "", "geheim123")
    assert r.status_code == 302
