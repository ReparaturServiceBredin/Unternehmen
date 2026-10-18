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
    assert k["plz"] == "" and k["ort"] == "" and k["strasse"] == ""  # nie „None“ in Formularen
    assert "None" not in client.get("/kunden").get_data(as_text=True)
    assert 'value="None"' not in client.get(f"/kunden/{k['id']}").get_data(as_text=True)
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


def kva_festschreiben(client, con, kid, betreff="Kostenvoranschlag Samsung S21"):
    client.get(f"/dokumente/neu?typ=kva&kunde_id={kid}")
    did = con.execute("SELECT MAX(id) FROM dokumente WHERE typ='kva'").fetchone()[0]
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (did,)).fetchone()
    r = client.post(f"/dokumente/{did}", data={
        "csrf": "test-token", "kunde_id": kid, "datum": "", "zahlungsziel_tage": "", "betreff": betreff,
        "einleitung": d["einleitung"], "schlusstext": d["schlusstext"], "hinweise": "", "aktion": "festschreiben",
        "p_bezeichnung": ["Displaytausch"], "p_beschreibung": [""], "p_menge": ["1"], "p_einheit": ["pauschal"],
        "p_preis": ["149,00"], "p_teilekosten": ["70,00"], "p_steuersatz": ["19"], "p_leistungsart": ["Smartphone"],
        "p_artikel_id": [""]}, follow_redirects=True)
    return did, r.get_data(as_text=True)


def test_kva_festschreiben_legt_auftrag_an_oder_verknuepft(client, con):
    kid = kunde_anlegen(client)
    did, seite = kva_festschreiben(client, con, kid)
    a = con.execute("SELECT * FROM auftraege WHERE kva_id=?", (did,)).fetchone()
    assert a and a["geraet"] == "Samsung S21" and a["kunde_id"] == kid
    assert "wurde automatisch angelegt" in seite and a["auftragsnr"] in seite
    verlauf = [v["ereignis"] for v in con.execute("SELECT ereignis FROM auftrag_verlauf WHERE auftrag_id=?",
                                                    (a["id"],))]
    assert "Auftrag automatisch aus Kostenvoranschlag angelegt" in verlauf and "KVA festgeschrieben" in verlauf
    # Kunde hat genau einen offenen Auftrag ohne KVA → dieser wird verknüpft, kein neuer
    kid2 = kunde_anlegen(client, nachname="Berg", email="berg@example.com")
    post(client, "/auftraege/neu", kunde_id=str(kid2), geraet="Pixel 8", fehler="Akku")
    vorher = con.execute("SELECT COUNT(*) FROM auftraege").fetchone()[0]
    did2, seite = kva_festschreiben(client, con, kid2, "Kostenvoranschlag Akku")
    assert con.execute("SELECT COUNT(*) FROM auftraege").fetchone()[0] == vorher
    assert con.execute("SELECT geraet FROM auftraege WHERE kva_id=?", (did2,)).fetchone()[0] == "Pixel 8"
    assert "wurde mit diesem KVA verknüpft" in seite
    # weiterer KVA: kein offener Auftrag ohne KVA mehr → neuer Auftrag
    aid = con.execute("SELECT id FROM auftraege WHERE kva_id=?", (did2,)).fetchone()[0]
    did3, _ = kva_festschreiben(client, con, kid2, "Zweiter KVA")
    assert con.execute("SELECT COUNT(*) FROM auftraege WHERE kunde_id=?", (kid2,)).fetchone()[0] == 2
    assert aid
