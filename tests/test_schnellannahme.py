"""Schnellannahme: Kunde im Auftragsformular, Annahmeschein per E-Mail, Auftrag aus einem KVA."""
import re
from pathlib import Path

from conftest import kunde_anlegen, post
from test_versand_backup import FalscherServer


def neuer_auftrag(client, **extra):
    daten = {"kunde_id": "neu", "neu_vorname": "Lisa", "neu_nachname": "Lang", "neu_telefon": "0151 / 222 333 44",
             "neu_email": "Lisa.Lang@example.com", "geraet": "iPhone 13", "fehler": "Display gebrochen",
             "leistungsart": "Smartphone", "annahme_felder": "1", "kva_gebuehr": "19,00"}
    daten.update(extra)
    r = post(client, "/auftraege/neu", **daten)
    assert r.status_code == 302, r.get_data(as_text=True)[:400]
    return int(re.search(r"/auftraege/(\d+)", r.headers["Location"]).group(1))


def test_neuer_kunde_direkt_im_auftrag_ohne_doppelte(client, con):
    aid = neuer_auftrag(client)
    k = con.execute("SELECT k.* FROM auftraege a JOIN kunden k ON k.id=a.kunde_id WHERE a.id=?", (aid,)).fetchone()
    assert (k["vorname"], k["nachname"], k["email"], k["quelle"]) == ("Lisa", "Lang", "lisa.lang@example.com",
                                                                      "Auftragsannahme")
    # gleiche Telefonnummer anders geschrieben → derselbe Kunde, kein doppelter
    aid2 = neuer_auftrag(client, neu_email="", neu_telefon="015122233344", neu_nachname="Lang")
    assert con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0] == 1
    assert con.execute("SELECT kunde_id FROM auftraege WHERE id=?", (aid2,)).fetchone()[0] == k["id"]
    # Pflicht: Nachname oder Firma
    r = post(client, "/auftraege/neu", kunde_id="neu", neu_vorname="Nur", annahme_felder="1")
    assert r.status_code == 200 and "Nachname oder Firma" in r.get_data(as_text=True)


def test_annahmeschein_per_email_ohne_unterschrift(client, con, app, monkeypatch):
    monkeypatch.setattr("rsb.mail.smtplib.SMTP", FalscherServer)
    post(client, "/einstellungen/email", smtp_host="smtp.example.com", smtp_port="587", smtp_sicherheit="starttls",
         smtp_benutzer="a@example.com", smtp_passwort="x", absender_name="RSB", absender_email="a@example.com")
    aid = neuer_auftrag(client)
    assert "Schein fehlt" in client.get("/auftraege").get_data(as_text=True)
    seite = client.get(f"/auftraege/{aid}/annahme-email").get_data(as_text=True)
    assert "lisa.lang@example.com" in seite and "19,00" in seite and "Einverstanden" in seite
    r = post(client, f"/auftraege/{aid}/annahme-email", an="lisa.lang@example.com", betreff="Annahmeschein",
             text="Hallo")
    assert r.status_code == 302
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (aid,)).fetchone()
    assert a["annahme_gesendet_an"] == "lisa.lang@example.com" and a["annahme_gesendet_am"]
    pdf = Path(app.config["DATEN"]) / a["annahme_gesendet_pdf"]
    assert pdf.read_bytes().startswith(b"%PDF")
    assert client.get(f"/auftraege/{aid}/annahme-email.pdf").data.startswith(b"%PDF")
    tafel = client.get("/auftraege").get_data(as_text=True)
    assert "Schein fehlt" not in tafel and "✉ Schein" in tafel
    verlauf = [v["ereignis"] for v in con.execute("SELECT ereignis FROM auftrag_verlauf WHERE auftrag_id=?", (aid,))]
    assert "Annahmeschein per E-Mail gesendet (ohne Unterschrift)" in verlauf
    assert "Per E-Mail gesendet am" in client.get(f"/auftraege/{aid}").get_data(as_text=True)


def test_auftrag_aus_kva_anlegen(client, con):
    kid = kunde_anlegen(client)
    client.get(f"/dokumente/neu?typ=kva&kunde_id={kid}")
    did = con.execute("SELECT id FROM dokumente WHERE typ='kva'").fetchone()[0]
    con.execute("UPDATE dokumente SET betreff='Kostenvoranschlag Samsung S21' WHERE id=?", (did,))
    con.commit()
    seite = client.get(f"/dokumente/{did}").get_data(as_text=True)
    assert "Auftrag daraus anlegen" in seite
    r = post(client, f"/dokumente/{did}/auftrag-anlegen")
    aid = int(re.search(r"/auftraege/(\d+)", r.headers["Location"]).group(1))
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (aid,)).fetchone()
    assert a["kva_id"] == did and a["kunde_id"] == kid and a["geraet"] == "Samsung S21"
    # zweiter Klick legt keinen zweiten Auftrag an
    post(client, f"/dokumente/{did}/auftrag-anlegen")
    assert con.execute("SELECT COUNT(*) FROM auftraege").fetchone()[0] == 1
