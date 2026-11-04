"""Arbeitskalender: Arbeiten, Termine, Zeiterfassung, Anfahrt, Nebenkosten, Abrechnung, Terminvorschlag."""
import io
import json
import re

from rsb import arbeitskalender as ak
from rsb import db as dbm

from conftest import kunde_anlegen, post
from test_auftraege import auftrag_anlegen
from test_benachrichtigung import smtp  # noqa: F401 (Fixture)


def arbeit_anlegen(client, kid=None, **felder):
    daten = {"typ": "reparatur", "status": "offen", "prioritaet": "", "titel": "Heizungssteuerung prüfen",
             "beschreibung": "Steuerung fällt nachts aus", "name": "Anna Müller", "adresse": "Hauptstraße 5, 74219 Möckmühl",
             "telefon": "0151 2345678", "email": "anna@example.com", "kunde_id": str(kid or "")}
    daten.update(felder)
    r = post(client, "/kalender/neu", **daten)
    assert r.status_code == 302, r.get_data(as_text=True)[:500]
    return int(re.search(r"/kalender/(\d+)", r.headers["Location"]).group(1))


def termin_anlegen(client, aid, datum="2026-11-10", beginn="09:00", dauer="1:30", art="Besichtigung"):
    post(client, f"/kalender/{aid}/termin", datum=datum, beginn=beginn, dauer=dauer, art=art, notiz="")


def termine(con, aid):
    return con.execute("SELECT * FROM arbeit_termine WHERE arbeit_id=? ORDER BY datum, beginn", (aid,)).fetchall()


def regelbesteuerung(con):
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"steuer_modus": "regel", "regel_steuersatz": 19}, con)


def test_anlegen_termine_und_ansichten(client, con):
    kid = kunde_anlegen(client)
    assert "Arbeitskalender" in client.get("/").get_data(as_text=True)  # Menüpunkt
    seite = client.get(f"/kalender/neu?kunde_id={kid}").get_data(as_text=True)
    assert 'value="Hauptstraße 5, 74219 Möckmühl"' in seite and "Anna Müller" in seite
    aid = arbeit_anlegen(client, kid, prioritaet="hoch")
    a = con.execute("SELECT * FROM arbeiten WHERE id=?", (aid,)).fetchone()
    assert a["kunde_id"] == kid and a["status"] == "offen" and a["prioritaet"] == "hoch"
    termin_anlegen(client, aid)
    termin_anlegen(client, aid, datum="2026-11-12", beginn="14:00", dauer="3:00", art="Reparatur")
    assert con.execute("SELECT status FROM arbeiten WHERE id=?", (aid,)).fetchone()[0] == "geplant"
    t = termine(con, aid)
    assert [(x["datum"], x["beginn"], x["dauer_min"]) for x in t] == [("2026-11-10", "09:00", 90),
                                                                    ("2026-11-12", "14:00", 180)]
    woche = client.get("/kalender/?ansicht=woche&datum=2026-11-11").get_data(as_text=True)
    assert "KW 46" in woche and woche.count(f"/kalender/{aid}#termin-") == 2 and "typ-reparatur" in woche
    def raster(url):
        return client.get(url).get_data(as_text=True).split("Offene Arbeiten")[0]
    assert "Anna Müller" in raster("/kalender/?ansicht=tag&datum=2026-11-10")
    assert "Anna Müller" not in raster("/kalender/?ansicht=tag&datum=2026-11-11")
    monat = client.get("/kalender/?ansicht=monat&datum=2026-11-01").get_data(as_text=True)
    assert "November 2026" in monat and monat.count("st-geplant") >= 2
    assert client.get(f"/kalender/{aid}").status_code == 200
    assert client.get("/kalender/?datum=kaputt").status_code == 200


def test_zeiterfassung_anfahrt_kosten_und_abrechnung(client, con):
    regelbesteuerung(con)
    aid = arbeit_anlegen(client, stundensatz="80,00")
    termin_anlegen(client, aid)
    tid = termine(con, aid)[0]["id"]
    # tatsächliche Zeit aus Start/Ende, Anfahrt 30 km, Fahrzeit 0:30 berechnen
    post(client, f"/kalender/termin/{tid}", datum="2026-11-10", beginn="09:00", dauer="1:30", art="Besichtigung",
         status="erledigt", ist_beginn="09:10", ist_ende="11:25", ist_dauer="", anfahrt="km", km="30",
         fahrzeit="0:30", fahrzeit_berechnen="1", anfahrt_weiter="1")
    t = termine(con, aid)[0]
    assert t["ist_minuten"] == 135 and t["km"] == 30
    # Nebenkosten: Verpflegung pauschal (>8 Std.), Übernachtung 2 × 89 €, Parken intern, Material, Sonstiges
    post(client, f"/kalender/{aid}/kosten", kategorie="verpflegung", modus="pauschale", abwesenheit="9",
         datum="2026-11-10", weiterberechnen="1", termin_id=str(tid))
    post(client, f"/kalender/{aid}/kosten", kategorie="uebernachtung", modus="naechte", naechte="2",
         preis_nacht="89,00", weiterberechnen="1")
    post(client, f"/kalender/{aid}/kosten", kategorie="parken", betrag="4,50")  # nicht angehakt = intern
    post(client, f"/kalender/{aid}/kosten", kategorie="material", betrag="23,90", bezeichnung="Relais",
         weiterberechnen="1")
    r = post(client, f"/kalender/{aid}/kosten", kategorie="sonstiges", betrag="5")  # ohne Bezeichnung: Fehler
    assert r.status_code == 302
    kosten = con.execute("SELECT kategorie, betrag, weiterberechnen FROM arbeit_kosten WHERE arbeit_id=? ORDER BY id",
                         (aid,)).fetchall()
    assert [tuple(k) for k in kosten] == [("verpflegung", 1400, 1), ("uebernachtung", 17800, 1), ("parken", 450, 0),
                                          ("material", 2390, 1)]
    a = con.execute("SELECT * FROM arbeiten WHERE id=?", (aid,)).fetchone()
    r = ak.abrechnung(con, a)
    # Arbeit 135 min × 80 € = 180,00; Anfahrt 30 × 0,50 = 15,00; Fahrzeit 30 min × 60 € = 30,00
    erwartet_netto = 18000 + 1500 + 3000 + 1400 + 17800 + 2390
    assert r["netto"] == erwartet_netto and r["intern"] == 450
    assert r["mwst"] == round(erwartet_netto * 0.19) and r["brutto"] == erwartet_netto + r["mwst"]
    assert r["geplant_min"] == 90 and r["ist_min"] == 135
    assert r["kategorien"]["arbeitszeit"]["weiter"] == 18000 and r["kategorien"]["parken"]["intern"] == 450
    seite = client.get(f"/kalender/{aid}").get_data(as_text=True)
    assert "MwSt. 19 %" in seite and "2:15 Std." in seite and "Relais" in seite
    # Sätze aus den Einstellungen – nichts fest im Code
    post(client, "/kalender/einstellungen", ak_stundensatz="70", ak_km_satz="0,30", ak_anfahrt_pauschale="25",
         ak_fahrzeit_satz="40", ak_verpflegung_8h="15", ak_verpflegung_24h="30", ak_verpflegung_anreise="15",
         ak_anfahrt="km", ak_standard_dauer="45", ak_tag_beginn="6", ak_tag_ende="20",
         ak_vorschlag_betreff="", ak_vorschlag_text="")
    r2 = ak.abrechnung(con, a)
    assert r2["kategorien"]["anfahrt"]["weiter"] == 900 and r2["kategorien"]["fahrzeit"]["weiter"] == 2000
    assert r2["stundensatz"] == 8000  # eigener Satz der Arbeit bleibt
    # Kleinunternehmer: keine MwSt.
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"steuer_modus": "kleinunternehmer"}, con)
    r3 = ak.abrechnung(con, a)
    assert r3["mwst"] == 0 and r3["brutto"] == r3["netto"]


def test_timer_und_pauschalen(client, con):
    aid = arbeit_anlegen(client)
    termin_anlegen(client, aid)
    tid = termine(con, aid)[0]["id"]
    post(client, f"/kalender/termin/{tid}/timer", aktion="start")
    t = termine(con, aid)[0]
    assert t["timer_start"] and t["ist_beginn"]
    assert con.execute("SELECT status FROM arbeiten WHERE id=?", (aid,)).fetchone()[0] == "in_arbeit"
    with dbm.Transaktion(con):  # 40 Minuten zurückdatieren
        con.execute("UPDATE arbeit_termine SET timer_start=datetime(timer_start, '-40 minutes') WHERE id=?", (tid,))
    assert "läuft" in client.get(f"/kalender/{aid}").get_data(as_text=True)
    post(client, f"/kalender/termin/{tid}/timer", aktion="stopp")
    t = termine(con, aid)[0]
    assert t["timer_start"] is None and t["ist_minuten"] in (40, 41)
    post(client, f"/kalender/termin/{tid}/timer", aktion="start")
    post(client, f"/kalender/termin/{tid}/timer", aktion="stopp")
    assert termine(con, aid)[0]["ist_minuten"] in (40, 41)  # zweiter Lauf addiert (hier 0 Min.)
    einst = dbm.einstellungen(con)
    assert ak.verpflegung_pauschale(einst, 6) == 0
    assert ak.verpflegung_pauschale(einst, 8.5) == einst["ak_verpflegung_8h"]
    assert ak.verpflegung_pauschale(einst, 24) == einst["ak_verpflegung_24h"]
    assert ak.verpflegung_pauschale(einst, 3, anreisetag=True) == einst["ak_verpflegung_anreise"]
    assert ak.minuten_aus("1:45") == 105 and ak.minuten_aus("1,5") == 90 and ak.minuten_aus("") is None


def test_terminvorschlag_email_ics_whatsapp_bestaetigung(client, con, smtp):  # noqa: F811
    aid = arbeit_anlegen(client)
    termin_anlegen(client, aid, datum="2026-11-10", beginn="09:00")
    termin_anlegen(client, aid, datum="2026-11-11", beginn="15:30")
    termin_anlegen(client, aid, datum="2026-11-20", beginn="08:00", art="Reparatur")
    t1, t2, t3 = [t["id"] for t in termine(con, aid)]
    seite = client.get(f"/kalender/{aid}/vorschlag?termin={t1}&termin={t2}").get_data(as_text=True)
    assert "1) Di, 10.11.2026, 09:00–10:30 Uhr" in seite and "2) Mi, 11.11.2026, 15:30–17:00 Uhr" in seite
    assert "Hauptstraße 5" in seite and "welcher Termin Ihnen passt" in seite
    assert 'const telefon = "491512345678"' in seite
    r = client.get(f"/kalender/{aid}/vorschlag/text?termin={t3}").get_json()
    assert "Fr, 20.11.2026, 08:00" in r["text"] and "1)" not in r["text"]
    r = post(client, f"/kalender/{aid}/vorschlag", an="anna@example.com", betreff="Terminvorschlag",
             text="Hallo, passt 1) oder 2)?", termin=[str(t1), str(t2)])
    assert r.status_code == 302
    msg = smtp.gesendet[-1]
    anhaenge = [p for p in msg.iter_attachments()]
    assert [p.get_filename() for p in anhaenge] == ["Termin_2026-11-10_0900.ics", "Termin_2026-11-11_1530.ics"]
    assert anhaenge[0].get_content_type() == "text/calendar"
    ics = anhaenge[0].get_content()
    if isinstance(ics, bytes):
        ics = ics.decode()
    assert "DTSTART:20261110T080000Z" in ics and "DTEND:20261110T093000Z" in ics  # 09:00 MEZ = 08:00 UTC
    assert "LOCATION:Hauptstraße 5\\, 74219 Möckmühl" in ics.replace("\r\n ", "")
    ts = {t["id"]: t for t in termine(con, aid)}
    assert ts[t1]["status"] == "vorschlag" and ts[t1]["vorgeschlagen_per"] == "E-Mail" and ts[t3]["status"] == "geplant"
    # Kunde wählt Termin 2 → Termin 1 (aus derselben Nachricht) wird abgesagt, Termin 3 bleibt
    post(client, f"/kalender/termin/{t2}/bestaetigt", andere_absagen="1")
    ts = {t["id"]: t for t in termine(con, aid)}
    assert ts[t2]["status"] == "bestaetigt" and ts[t2]["bestaetigt_am"]
    assert ts[t1]["status"] == "abgesagt" and ts[t3]["status"] == "geplant"
    post(client, f"/kalender/termin/{t2}/bestaetigt", zuruecknehmen="1")
    assert termine(con, aid)[1]["status"] == "vorschlag"
    # WhatsApp: nur vermerken
    r = client.post(f"/kalender/{aid}/vorschlag/vermerken", headers={"X-Requested-With": "fetch"},
                    data={"csrf": "test-token", "kanal": "whatsapp", "an": "", "betreff": "", "text": "x",
                          "termin": [str(t3)]})
    assert r.get_json() == {"ok": True}
    n = con.execute("SELECT * FROM arbeit_nachrichten WHERE arbeit_id=? ORDER BY id", (aid,)).fetchall()
    assert [x["kanal"] for x in n] == ["email", "whatsapp"] and json.loads(n[1]["termin_ids"]) == [t3]
    assert termine(con, aid)[2]["vorgeschlagen_per"] == "WhatsApp"
    # .ics zum Herunterladen
    r = client.get(f"/kalender/termin/{t3}.ics")
    assert r.mimetype == "text/calendar" and b"BEGIN:VEVENT" in r.data


def test_uebernehmen_und_uebersicht(client, con):
    regelbesteuerung(con)
    kid = kunde_anlegen(client)
    auftrag = auftrag_anlegen(client, kid, geraet="Spülmaschine")
    seite = client.get("/kalender/offen").get_data(as_text=True)
    assert "Spülmaschine" in seite and "Übernehmen" in seite
    r = post(client, "/kalender/uebernehmen", auftrag_id=str(auftrag))
    aid = int(re.search(r"/kalender/(\d+)", r.headers["Location"]).group(1))
    a = con.execute("SELECT * FROM arbeiten WHERE id=?", (aid,)).fetchone()
    assert a["auftrag_id"] == auftrag and "Spülmaschine" in a["titel"] and a["kunde_id"] == kid
    assert post(client, "/kalender/uebernehmen", auftrag_id=str(auftrag)).headers["Location"].endswith(f"/{aid}")
    andere = arbeit_anlegen(client, typ="kva", titel="Angebot Badsanierung", name="Bernd Beispiel")
    termin_anlegen(client, andere, datum="2026-12-01")
    tid = termine(con, andere)[0]["id"]
    post(client, f"/kalender/termin/{tid}", datum="2026-12-01", beginn="09:00", dauer="1:00", art="", status="erledigt",
         ist_beginn="", ist_ende="", ist_dauer="2:00", anfahrt="pauschale", km="", fahrzeit="", anfahrt_weiter="1")
    seite = client.get("/kalender/offen").get_data(as_text=True)
    assert "Summe (2 Arbeiten)" in seite and "Angebot Badsanierung" in seite
    # 2 Std. × 60 € + Pauschale 25 € = 145 € netto, 172,55 € brutto
    assert "145,00 €" in seite and "172,55 €" in seite
    assert f'href="/kalender/{aid}"' not in client.get("/kalender/offen?typ=kva").get_data(as_text=True)
    assert "Bernd" in client.get("/kalender/offen?kunde=bernd").get_data(as_text=True)
    gefiltert = client.get("/kalender/offen?von=2026-12-01&bis=2026-12-31").get_data(as_text=True)
    assert "Badsanierung" in gefiltert
    post(client, f"/kalender/{andere}", **{"typ": "kva", "status": "abgerechnet", "prioritaet": "",
                                           "titel": "Angebot Badsanierung", "name": "Bernd Beispiel"})
    assert "Badsanierung" not in client.get("/kalender/offen").get_data(as_text=True).split("uebernehmen")[0]
    assert "Badsanierung" in client.get("/kalender/offen?status=alle").get_data(as_text=True)
    # Auftrag selbst unverändert, Löschen der Arbeit lässt ihn bestehen
    post(client, f"/kalender/{aid}/loeschen")
    assert con.execute("SELECT COUNT(*) FROM auftraege WHERE id=?", (auftrag,)).fetchone()[0] == 1


def test_belegfoto_und_rechte(app, client, con):
    aid = arbeit_anlegen(client)
    r = client.post(f"/kalender/{aid}/kosten", data={
        "csrf": "test-token", "kategorie": "maut", "betrag": "12,40", "weiterberechnen": "1",
        "foto": (io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "quittung.png")}, content_type="multipart/form-data")
    assert r.status_code == 302
    k = con.execute("SELECT * FROM arbeit_kosten WHERE arbeit_id=?", (aid,)).fetchone()
    assert k["foto"].endswith(".png") and client.get(f"/kalender/kosten/{k['id']}/foto").status_code == 200
    r = client.post(f"/kalender/{aid}/kosten", data={
        "csrf": "test-token", "kategorie": "maut", "betrag": "1", "foto": (io.BytesIO(b"x"), "boese.exe")},
        content_type="multipart/form-data")
    assert con.execute("SELECT COUNT(*) FROM arbeit_kosten").fetchone()[0] == 1
    post(client, f"/kalender/kosten/{k['id']}/loeschen")
    assert con.execute("SELECT COUNT(*) FROM arbeit_kosten").fetchone()[0] == 0
    from werkzeug.security import generate_password_hash
    from rsb import benutzer as bn
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"passwort_hash": generate_password_hash("geheim123"), "login_aktiv": True}, con)
        bn.anlegen(con, "max", "Max", "mitarbeiter", "passwort-1", "passwort-1")
    m = app.test_client()
    m.post("/login", data={"benutzer": "max", "passwort": "passwort-1"})
    assert m.get("/kalender/einstellungen").status_code == 403
    assert m.get("/kalender/").status_code == 200 and "Sätze &amp; Vorlagen" not in m.get("/kalender/").get_data(as_text=True)


def test_ics_falten_und_sonderzeichen(client, con):
    aid = arbeit_anlegen(client, titel="Sehr langer Titel; mit, Sonderzeichen " + "ä" * 60)
    termin_anlegen(client, aid, datum="2026-07-01", beginn="10:00")  # Sommerzeit
    t = termine(con, aid)[0]
    daten = ak.ics(t, ak.laden(con, aid), dbm.einstellungen(con)).decode()
    assert all(len(z.encode()) <= 75 for z in daten.split("\r\n"))
    assert "DTSTART:20260701T080000Z" in daten  # 10:00 MESZ = 08:00 UTC
    assert "\\;" in daten and "\\," in daten
