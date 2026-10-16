"""Phase 10: Datenschutz – Löschfristen und Löschlauf, Auskunft (Art. 15), Löschanfrage mit Protokoll, VVT (Art. 30)."""
import io
import json
import sqlite3
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from rsb import datenschutz as ds
from rsb import db as dbm

from conftest import kunde_anlegen, post, rechnung_anlegen
from test_annahme import auftrag_mit_annahme, unterschreiben
from test_auftrag_detail import bild, foto_hochladen


def vor(tage):
    return (date.today() - timedelta(days=tage)).isoformat() + "T10:00:00"


def test_auskunft_art15(client, con, app):
    kid = kunde_anlegen(client)
    aid = auftrag_mit_annahme(client, kid)
    foto_hochladen(client, f"/auftraege/{aid}/fotos", bild())
    unterschreiben(client, aid)
    rechnung_anlegen(client, kid, festschreiben=True)
    r = client.get(f"/kunden/{kid}/auskunft")
    assert r.status_code == 200 and r.mimetype == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.data))
    namen = z.namelist()
    assert "Auskunft_Art15_DSGVO.pdf" in namen and "gespeicherte_Daten.json" in namen
    assert any(n.startswith("Belege/") for n in namen) and any(n.startswith("Fotos/") for n in namen)
    assert any(n.startswith("Annahme_Abholscheine/") for n in namen)
    daten = json.loads(z.read("gespeicherte_Daten.json"))
    assert daten["kunde"]["nachname"] == "Müller" and daten["auftraege"][0]["zugangsdaten_gespeichert"].startswith("ja")
    assert "4711" not in z.read("gespeicherte_Daten.json").decode()  # Zugangsdaten nie im Klartext
    assert z.read("Auskunft_Art15_DSGVO.pdf").startswith(b"%PDF")
    assert con.execute("SELECT 1 FROM protokoll WHERE aktion='datenschutz_auskunft'").fetchone()


def test_loeschanfrage_mit_protokoll(client, con):
    kid = kunde_anlegen(client)
    rechnung_anlegen(client, kid, festschreiben=True)
    r = post(client, f"/kunden/{kid}/loeschen", anfrage="1")
    assert "#protokolle" in r.headers["Location"]
    p = con.execute("SELECT * FROM loeschprotokolle").fetchone()
    assert p["anlass"].startswith("Löschanfrage") and p["betroffen"].endswith("A. Müller")
    behalten = json.loads(p["behalten"])
    assert behalten and "Dokument" in behalten[0]["was"] and p["bis"]
    assert "Stammdaten" in " ".join(json.loads(p["geloescht"]))
    assert client.get(f"/datenschutz/protokoll/{p['id']}.pdf").data.startswith(b"%PDF")
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("DELETE FROM loeschprotokolle")
    # Kunde ohne Belege: vollständig gelöscht, Protokoll trotzdem da
    kid2 = kunde_anlegen(client, vorname="Bert", nachname="Ohne")
    post(client, f"/kunden/{kid2}/loeschen")
    assert not con.execute("SELECT 1 FROM kunden WHERE id=?", (kid2,)).fetchone()
    assert con.execute("SELECT COUNT(*) FROM loeschprotokolle").fetchone()[0] == 2


def test_loeschlauf_fristen(client, con, app):
    # inaktiver Kunde mit Rechnung → anonymisiert; inaktiver ohne → gelöscht; aktiver bleibt
    alt = kunde_anlegen(client, vorname="Alt", nachname="Kunde")
    rechnung_anlegen(client, alt, festschreiben=True)
    con.execute("UPDATE dokumente SET bezahlt_betrag=summe_brutto WHERE kunde_id=?", (alt,))
    ohne = kunde_anlegen(client, vorname="Leer", nachname="Kunde")
    aktiv = kunde_anlegen(client, vorname="Neu", nachname="Kunde")
    con.execute("UPDATE kunden SET geaendert_am=?, erstellt_am=? WHERE id IN (?, ?)", (vor(4 * 365), vor(4 * 365), alt, ohne))
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"ds_kunde_inaktiv_jahre": 3}, con)
    k = ds.kandidaten(con, heute=date.today() + timedelta(days=4 * 365))
    ids = {x["k"]["id"] for x in k["kunden"]}
    assert alt in ids and ohne in ids and aktiv in ids  # in 4 Jahren wären alle inaktiv
    k = ds.kandidaten(con)
    assert {x["k"]["id"] for x in k["kunden"]} == {ohne}  # heute nur der ohne Aktivität

    # Fotos und Zugangsdaten
    aid = auftrag_mit_annahme(client, aktiv)
    foto_hochladen(client, f"/auftraege/{aid}/fotos", bild())
    post(client, f"/auftraege/{aid}/status", status="erledigt", ohne_kva="1")
    con.execute("UPDATE auftraege SET erledigt_am=? WHERE id=?", (vor(800), aid))
    aid2 = auftrag_mit_annahme(client, aktiv)
    con.execute("UPDATE auftraege SET eingang_am=? WHERE id=?", (vor(100), aid2))
    f = con.execute("SELECT * FROM auftrag_fotos WHERE auftrag_id=?", (aid,)).fetchone()
    pfad = Path(app.config["DATEN"]) / f["pfad"]
    assert pfad.is_file()
    seite = client.get("/datenschutz").get_data(as_text=True)
    assert "Heute fällig" in seite
    post(client, "/datenschutz")
    assert not con.execute("SELECT 1 FROM kunden WHERE id=?", (ohne,)).fetchone()
    f = con.execute("SELECT * FROM auftrag_fotos WHERE id=?", (f["id"],)).fetchone()
    assert f["geloescht_am"] and f["geloescht_von"] == "Löschfrist" and not pfad.exists()
    assert con.execute("SELECT zugang_geheim FROM auftraege WHERE id=?", (aid2,)).fetchone()[0] is None
    assert con.execute("SELECT 1 FROM kunden WHERE id=?", (aktiv,)).fetchone()
    assert con.execute("SELECT COUNT(*) FROM loeschprotokolle").fetchone()[0] >= 2
    assert dbm.einstellungen(con)["ds_letzter_lauf"]


def test_verzeichnis_und_einstellungen(client, con):
    kunde_anlegen(client)
    seite = client.get("/datenschutz/verzeichnis").get_data(as_text=True)
    assert "Verarbeitungstätigkeiten" in seite and "Gerätezugangsdaten" in seite and "1 Kunden" in seite
    assert client.get("/datenschutz/verzeichnis?pdf=1").data.startswith(b"%PDF")
    post(client, "/einstellungen?bereich=datenschutz", ds_auto="1", interessent_loeschen_monate="6",
         ds_kunde_inaktiv_jahre="0", ds_fotos_monate="36", ds_zugang_tage="60", ds_email_jahre="0", ds_verantwortlicher="")
    e = dbm.einstellungen(con)
    assert e["ds_auto"] is True and e["ds_fotos_monate"] == 36 and e["ds_kunde_inaktiv_jahre"] == 0
    assert ds.kandidaten(con)["kunden"] == []  # 0 = aus
