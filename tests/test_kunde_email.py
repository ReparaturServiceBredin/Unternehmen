"""Freie E-Mail an einen Kunden mit Textbausteinen (Kunde → „E-Mail schreiben“)."""
import json
import re

from rsb import db as dbm

from conftest import kunde_anlegen, post
from test_auftraege import auftrag_anlegen
from test_benachrichtigung import smtp  # noqa: F401 (Fixture)


def seiten_daten(html):
    vorlagen = json.loads(re.search(r"const vorlagen = (\[.*?\]), werte", html, re.S).group(1))
    werte = json.loads(re.search(r"werte = (\{.*?\});", html, re.S).group(1))
    return vorlagen, werte


def test_kunde_email_mit_vorlage_und_auftrag(client, con, smtp):  # noqa: F811
    kid = kunde_anlegen(client)
    aid = auftrag_anlegen(client, kid, geraet="iPhone 13")
    nr = con.execute("SELECT auftragsnr FROM auftraege WHERE id=?", (aid,)).fetchone()[0]
    assert "E-Mail schreiben" in client.get(f"/kunden/{kid}").get_data(as_text=True)
    html = client.get(f"/kunden/{kid}/email").get_data(as_text=True)
    assert 'value="anna@example.com"' in html and f'value="{aid}" selected' in html  # offener Auftrag vorgewählt
    vorlagen, werte = seiten_daten(html)
    ersatz = next(v for v in vorlagen if v["name"] == "Warten auf Ersatzteil")
    assert ersatz["betreff"].startswith("Ihre Reparatur {auftragsnr}") and not ersatz["text"].startswith("Betreff")
    assert werte[str(aid)]["geraet"] == "iPhone 13" and werte[str(aid)]["anrede_brief"] == "Sehr geehrte Frau Müller,"
    assert any(v["name"].startswith("Leer") for v in vorlagen)

    text = "Sehr geehrte Frau Müller,\n\nwir warten noch auf ein Ersatzteil für Ihr iPhone 13.\n\nMfG"
    r = post(client, f"/kunden/{kid}/email?zurueck=auftrag", an="anna@example.com",
             betreff=f"Ihre Reparatur {nr}", text=text, auftrag_id=str(aid))
    assert r.status_code == 302 and r.headers["Location"].endswith(f"/auftraege/{aid}")
    msg = smtp.gesendet[-1]
    assert msg["To"] == "anna@example.com" and msg["Subject"] == f"Ihre Reparatur {nr}"
    assert "Ersatzteil" in msg.get_body().get_content()
    v = con.execute("SELECT * FROM auftrag_verlauf WHERE auftrag_id=? AND ereignis='E-Mail an Kunden'", (aid,)).fetchone()
    assert v and v["details"] == f"Ihre Reparatur {nr}"
    assert con.execute("SELECT COUNT(*) FROM protokoll WHERE aktion='kunde_email' AND objekt_id=?", (kid,)).fetchone()[0]
    assert con.execute("SELECT status FROM versandprotokoll ORDER BY id DESC").fetchone()[0] == "gesendet"


def test_kunde_email_fehler_behaelt_text(client, con):
    kid = kunde_anlegen(client)
    r = post(client, f"/kunden/{kid}/email", an="anna@example.com", betreff="Hallo", text="Mein eigener Text")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "NICHT gesendet" in html and "Mein eigener Text" in html
    r = post(client, f"/kunden/{kid}/email", an="", betreff="x", text="y")
    assert r.status_code == 302  # Eingabefehler


def test_eigene_vorlage_mit_betreff_zeile(client, con):
    kid = kunde_anlegen(client)
    with dbm.Transaktion(con):
        con.execute("INSERT INTO textbausteine (kategorie, dokumenttyp, name, text, standard) VALUES "
                    "('email_text', 'kunde_email', 'Termin', 'Betreff: Ihr Termin\n{anrede_brief}\n\nbis morgen', 0)")
    vorlagen, _ = seiten_daten(client.get(f"/kunden/{kid}/email").get_data(as_text=True))
    t = next(v for v in vorlagen if v["name"] == "Termin")
    assert t["betreff"] == "Ihr Termin" and t["text"] == "{anrede_brief}\n\nbis morgen"
    assert "Freie E-Mail an Kunden" in client.get("/textbausteine").get_data(as_text=True)
