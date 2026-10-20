"""Angebote und Auftragsbestätigungen: eigene Nummernkreise, PDF, E-Mail-Text, Umwandeln in AB bzw. Rechnung."""
import re

from conftest import kunde_anlegen, post
from test_leihgeraete import pdf_text


def entwurf(client, con, kid, typ, festschreiben=True, **extra):
    r = client.get(f"/dokumente/neu?typ={typ}&kunde_id={kid}")
    did = int(re.search(r"/dokumente/(\d+)", r.headers["Location"]).group(1))
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (did,)).fetchone()
    data = {"csrf": "test-token", "kunde_id": kid, "datum": "", "zahlungsziel_tage": "", "betreff": "Netzwerk einrichten",
            "einleitung": d["einleitung"], "schlusstext": d["schlusstext"], "hinweise": "",
            "aktion": "festschreiben" if festschreiben else "speichern",
            "p_bezeichnung": ["Router konfigurieren"], "p_beschreibung": [""], "p_menge": ["2"], "p_einheit": ["Std."],
            "p_preis": ["60,00"], "p_teilekosten": [""], "p_steuersatz": ["19"], "p_leistungsart": ["Sonstiges"],
            "p_artikel_id": [""], **extra}
    client.post(f"/dokumente/{did}", data=data)
    return did


def test_angebot_und_ab_mit_eigenen_nummern(client, con):
    kid = kunde_anlegen(client)
    a = entwurf(client, con, kid, "angebot")
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (a,)).fetchone()
    assert d["status"] == "festgeschrieben" and d["nummer"].startswith("AN-") and d["leistungsdatum"] is None
    text = pdf_text(client.get(f"/dokumente/{a}/pdf").data)
    assert "Angebot" in text and "Angebotsnummer" in text and "Gültig bis" in text and "Zahlungsinformationen" not in text
    mail = client.get(f"/dokumente/{a}/email").get_data(as_text=True)
    assert "Ihr Angebot AN-" in mail
    # Angebot → Auftragsbestätigung (mit Bezug) → Rechnung
    r = post(client, f"/dokumente/{a}/kopieren", typ="auftragsbestaetigung")
    ab = int(re.search(r"/dokumente/(\d+)", r.headers["Location"]).group(1))
    e = con.execute("SELECT * FROM dokumente WHERE id=?", (ab,)).fetchone()
    assert e["typ"] == "auftragsbestaetigung" and e["bezug_id"] == a and e["betreff"] == "Netzwerk einrichten"
    assert con.execute("SELECT COUNT(*) FROM positionen WHERE dokument_id=?", (ab,)).fetchone()[0] == 1
    ab2 = entwurf(client, con, kid, "auftragsbestaetigung", leistungsdatum="2026-11-03")
    e2 = con.execute("SELECT * FROM dokumente WHERE id=?", (ab2,)).fetchone()
    assert e2["nummer"].startswith("AB-") and e2["leistungsdatum"] == "2026-11-03"
    assert "Ausführung am" in pdf_text(client.get(f"/dokumente/{ab2}/pdf").data)
    r = post(client, f"/dokumente/{ab2}/kopieren")
    re_id = int(re.search(r"/dokumente/(\d+)", r.headers["Location"]).group(1))
    assert con.execute("SELECT typ FROM dokumente WHERE id=?", (re_id,)).fetchone()[0] == "rechnung"
    # Liste, Umsatz zählt nur Rechnungen
    liste = client.get("/verkauf/angebote").get_data(as_text=True)
    assert d["nummer"] in liste and e2["nummer"] in liste and "Angebote &amp; Auftragsbestätigungen" in liste
    assert d["nummer"] not in client.get("/verkauf/rechnungen").get_data(as_text=True)
    # kein automatischer Reparaturauftrag für Angebote
    assert not con.execute("SELECT 1 FROM auftraege").fetchone()


def test_praefixe_muessen_verschieden_sein(client, con):
    post(client, "/einstellungen/rechnung", praefix_rechnung="RE", praefix_gutschrift="GS", praefix_angebot="KV",
             praefix_ang="KV", praefix_auftrag="AB", nummern_format="{praefix}-{jahr}-{nummer:04d}",
             aufbewahrung_belege_jahre="8", aufbewahrung_briefe_jahre="6", steuer_modus="kleinunternehmer")
    from rsb import db as dbm
    assert dbm.einstellungen(con)["praefix_ang"] == "AN"  # nicht übernommen: gleiches Präfix wie KVA
