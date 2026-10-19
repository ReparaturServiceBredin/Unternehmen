"""Ratenzahlung: eine Rechnung mit Ratenplan, Zahlungsaufforderungen je Rate, Anrechnung der Zahlungen."""
import re
from datetime import date

from rsb import db as dbm
from rsb import raten as rtn

from conftest import kunde_anlegen, post
from test_leihgeraete import pdf_text
from test_versand_backup import FalscherServer


def raten_rechnung(client, kid, preis="200,03", anzahl="4", erste="2026-11-01", auto="1", aktion="festschreiben"):
    r = client.get(f"/dokumente/neu?kunde_id={kid}")
    did = int(re.search(r"/dokumente/(\d+)", r.headers["Location"]).group(1))
    data = {"csrf": "test-token", "kunde_id": kid, "datum": "2026-10-19", "leistungsdatum": "2026-10-18",
            "leistungsdatum_bis": "", "zahlungsziel_tage": "", "betreff": "Reparatur Laptop", "einleitung": "",
            "schlusstext": "", "hinweise": "", "aktion": aktion, "p_bezeichnung": ["Mainboard-Reparatur"],
            "p_beschreibung": [""], "p_menge": ["1"], "p_einheit": ["Stk."], "p_preis": [preis],
            "p_teilekosten": ["80,00"], "p_steuersatz": ["19"], "p_leistungsart": ["PC/Laptop"], "p_artikel_id": [""],
            "raten_aktiv": "1", "raten_anzahl": anzahl, "raten_erste": erste}
    if auto:
        data["raten_auto"] = auto
    client.post(f"/dokumente/{did}", data=data)
    return did


def lauf(app, con, tag):
    with app.app_context():
        return rtn.lauf(con, app.config["DATEN"], tag)


def test_plan_rundung_und_monatsende():
    p = rtn.plan(20003, 4, date(2026, 1, 31))
    assert [r["betrag"] for r in p] == [5003, 5000, 5000, 5000]
    assert [r["faellig_am"] for r in p] == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"]


def test_rechnung_mit_ratenplan(client, con, app):
    kid = kunde_anlegen(client)
    did = raten_rechnung(client, kid)
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (did,)).fetchone()
    assert d["status"] == "festgeschrieben" and d["raten_anzahl"] == 4 and d["faellig_am"] == "2027-02-01"
    raten = con.execute("SELECT nr, faellig_am, betrag FROM rechnung_raten WHERE dokument_id=? ORDER BY nr",
                        (did,)).fetchall()
    assert [tuple(r) for r in raten] == [(1, "2026-11-01", 5003), (2, "2026-12-01", 5000), (3, "2027-01-01", 5000),
                                         (4, "2027-02-01", 5000)]
    text = pdf_text(client.get(f"/dokumente/{did}/pdf").data)
    assert "Ratenzahlung" in text and "in 4 Raten" in text and "01.02.2027" in text and "Rate 1" in text
    seite = client.get(f"/dokumente/{did}").get_data(as_text=True)
    assert "0 von 4 Raten bezahlt" in seite
    # Zahlungen werden der Reihe nach angerechnet
    post(client, f"/dokumente/{did}/zahlung", datum="2026-10-19", betrag="75,03", zahlart="ueberweisung")
    s = rtn.stand(con, did, date(2026, 12, 15))
    assert [x["status"] for x in s] == ["bezahlt", "überfällig", "offen", "offen"] and s[1]["offen"] == 2500


def test_automatische_zahlungsaufforderung(client, con, app, monkeypatch):
    monkeypatch.setattr("rsb.mail.smtplib.SMTP", FalscherServer)
    post(client, "/einstellungen/email", smtp_host="smtp.example.com", smtp_port="587", smtp_sicherheit="starttls",
         smtp_benutzer="a@example.com", smtp_passwort="x", absender_name="RSB", absender_email="a@example.com")
    kid = kunde_anlegen(client)
    did = raten_rechnung(client, kid)
    # 3 Tage Vorlauf: am 28.10. wird Rate 1 fällig gemeldet, Rate 2 noch nicht
    assert lauf(app, con, date(2026, 10, 27))["gesendet"] == 0
    e = lauf(app, con, date(2026, 10, 29))
    assert e["gesendet"] == 1, e
    r1 = con.execute("SELECT * FROM rechnung_raten WHERE dokument_id=? AND nr=1", (did,)).fetchone()
    assert r1["erinnert_am"] and r1["erinnert_an"] == "anna@example.com"
    assert lauf(app, con, date(2026, 10, 30))["gesendet"] == 0  # nur einmal je Rate
    v = con.execute("SELECT * FROM versandprotokoll WHERE dokument_id=? ORDER BY id DESC", (did,)).fetchone()
    assert "Rate 1 von 4" in v["betreff"]
    # bezahlte Rate: keine Aufforderung
    post(client, f"/dokumente/{did}/zahlung", datum="2026-10-19", betrag="100,03", zahlart="bar")  # Rate 1 + 2
    assert lauf(app, con, date(2026, 11, 29))["gesendet"] == 0
    # von Hand senden
    rid = con.execute("SELECT id FROM rechnung_raten WHERE dokument_id=? AND nr=3", (did,)).fetchone()[0]
    r = post(client, f"/raten/{rid}/erinnern")
    assert r.status_code == 302
    assert con.execute("SELECT erinnert_am FROM rechnung_raten WHERE id=?", (rid,)).fetchone()[0]


def test_ohne_automatik_und_eingaben_pruefen(client, con, app, monkeypatch):
    monkeypatch.setattr("rsb.mail.smtplib.SMTP", FalscherServer)
    dbm.einstellungen_speichern({"smtp_host": "smtp.example.com"}, con=con)
    con.commit()
    kid = kunde_anlegen(client)
    did = raten_rechnung(client, kid, auto="")
    assert con.execute("SELECT raten_auto FROM dokumente WHERE id=?", (did,)).fetchone()[0] == 0
    assert lauf(app, con, date(2027, 3, 1))["gesendet"] == 0
    # ungültig: 1 Rate bzw. erste Rate vor dem Rechnungsdatum → Entwurf bleibt Entwurf
    for anzahl, erste in (("1", "2026-11-01"), ("4", "2026-01-01")):
        did2 = raten_rechnung(client, kid, anzahl=anzahl, erste=erste)
        assert con.execute("SELECT status FROM dokumente WHERE id=?", (did2,)).fetchone()[0] == "entwurf"


def test_nachtraeglich_vereinbaren_bei_ausgestellter_rechnung(client, con, app, monkeypatch):
    from conftest import rechnung_anlegen
    from rsb import mahnwesen as mw
    monkeypatch.setattr("rsb.mail.smtplib.SMTP", FalscherServer)
    post(client, "/einstellungen/email", smtp_host="smtp.example.com", smtp_port="587", smtp_sicherheit="starttls",
         smtp_benutzer="a@example.com", smtp_passwort="x", absender_name="RSB", absender_email="a@example.com")
    kid = kunde_anlegen(client)
    did = rechnung_anlegen(client, kid, (("Displaytausch", "300,00", "1"),), festschreiben=True)
    con.execute("UPDATE dokumente SET versendet_am='2026-10-19T10:00:00' WHERE id=?", (did,))
    con.commit()
    post(client, f"/dokumente/{did}/zahlung", datum="2026-10-19", betrag="60,00", zahlart="bar")
    seite = client.get(f"/dokumente/{did}").get_data(as_text=True)
    assert "Ratenzahlung vereinbaren" in seite and "240,00" in seite
    r = post(client, f"/dokumente/{did}/raten", raten_anzahl="3", raten_erste="2026-11-15", raten_auto="1",
             bestaetigen="1")
    assert r.status_code == 302
    raten = con.execute("SELECT nr, faellig_am, betrag, art FROM rechnung_raten WHERE dokument_id=? ORDER BY nr",
                        (did,)).fetchall()
    assert [tuple(x) for x in raten] == [(1, "2026-11-15", 8000, "vereinbarung"), (2, "2026-12-15", 8000, "vereinbarung"),
                                         (3, "2027-01-15", 8000, "vereinbarung")]
    assert con.execute("SELECT COUNT(*) FROM versandprotokoll WHERE betreff LIKE 'Ratenzahlung zu Rechnung%'"
                       ).fetchone()[0] == 1
    # frühere Zahlung (60 €) deckt den Teil vor der Vereinbarung → alle Raten offen
    assert [x["status"] for x in rtn.stand(con, did, date(2026, 11, 1))] == ["offen", "offen", "offen"]
    # Fälligkeit/Mahnwesen erst nach der letzten Rate
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (did,)).fetchone()
    from rsb import zahlungen as zlg
    assert zlg.stand(con, d, "2026-12-01")["status"] != "ueberfaellig"
    assert not mw.vorschlaege(con, "2026-12-20")
    # Rate 1 wird trotz bereits versandter Rechnung angemahnt (Vereinbarung kam später)
    assert lauf(app, con, date(2026, 11, 13))["gesendet"] == 1
    # aufheben
    post(client, f"/dokumente/{did}/raten", aktion="aufheben")
    assert not con.execute("SELECT 1 FROM rechnung_raten WHERE dokument_id=?", (did,)).fetchone()
