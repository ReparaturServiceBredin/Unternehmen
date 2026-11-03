"""Benachrichtigungen jederzeit von Hand anstoßen, „Gerät versendet“ mit Sendungsnummer und Zusatztexten."""
from rsb import benachrichtigung as ben
from rsb import db as dbm

from conftest import kunde_anlegen, post
from test_auftraege import auftrag_anlegen
from test_benachrichtigung import smtp  # noqa: F401 (Fixture)


def offen(con, aid, anlass):
    return con.execute("SELECT * FROM benachrichtigungen WHERE auftrag_id=? AND anlass=? AND status='offen'",
                       (aid, anlass)).fetchall()


def test_zusatz_einfuegen_und_versandzeile():
    assert ben.zusatz_einfuegen("A\n\n{Zusatz}\n\nMit freundlichen Grüßen\nX", "Z") == "A\n\nZ\n\nMit freundlichen Grüßen\nX"
    assert ben.zusatz_einfuegen("A\n\n{Zusatz}\n\nMit freundlichen Grüßen", "") == "A\n\nMit freundlichen Grüßen"
    assert ben.zusatz_einfuegen("A\n\nMit freundlichen Grüßen\nX", "Z") == "A\n\nZ\n\nMit freundlichen Grüßen\nX"
    assert ben.zusatz_einfuegen("A", "Z") == "A\n\nZ"
    z = ben.versand_zeile("DHL", "0034 0434")
    assert z.startswith("Versand mit DHL, Sendungsnummer 00340434") and "piececode=00340434" in z
    assert ben.versand_zeile("Deutsche Post", "") == "Versand mit Deutsche Post"
    assert ben.versand_zeile("", "") == ""


def test_jederzeit_manuell_auch_nach_versand(client, con, smtp):  # noqa: F811
    kid = kunde_anlegen(client)
    aid = auftrag_anlegen(client, kid)
    with dbm.Transaktion(con):
        con.execute("UPDATE benachrichtigungen SET status='gesendet' WHERE auftrag_id=?", (aid,))
        dbm.einstellungen_speichern({"ben_fertig_aktiv": False}, con)
    post(client, f"/auftraege/{aid}/benachrichtigen", anlass="fertig")
    assert len(offen(con, aid, "fertig")) == 1
    post(client, f"/auftraege/{aid}/benachrichtigen", anlass="fertig", zusatz="Bitte Ladekabel mitbringen.")
    neu = offen(con, aid, "fertig")
    assert len(neu) == 1 and "Bitte Ladekabel mitbringen." in neu[0]["text"]  # ältere Vorschau ersetzt
    assert neu[0]["text"].index("Ladekabel") < neu[0]["text"].index("Mit freundlichen Grüßen")


def test_versendet_mit_sendungsnummer_bausteinen_und_vermerk(client, con, smtp):  # noqa: F811
    kid = kunde_anlegen(client)
    aid = auftrag_anlegen(client, kid, geraet="iPhone 13")
    with dbm.Transaktion(con):
        assert ben.vorschlagen(con, aid, "versendet") is None  # nie automatisch
        con.execute("UPDATE auftraege SET status='erledigt', erledigt_am='2026-10-01T10:00:00' WHERE id=?", (aid,))
        ben.erinnerungen_pruefen(con, "2026-10-20")
    assert offen(con, aid, "erinnerung")
    bausteine = {r["name"]: r["id"] for r in con.execute(
        "SELECT id, name FROM textbausteine WHERE dokumenttyp='benachrichtigung'")}
    assert "Rechnung liegt bei" in bausteine
    html = client.get(f"/auftraege/{aid}").get_data(as_text=True)
    assert "Sendungsnummer" in html and "Rechnung liegt bei" in html and 'value="versendet"' in html
    client.post(f"/auftraege/{aid}/benachrichtigen", data={
        "csrf": "test-token", "anlass": "versendet", "versanddienst": "DHL", "sendungsnummer": "00340434123",
        "als_versendet": "1", "baustein": [str(bausteine["Rechnung liegt bei"]), str(bausteine["Bewertung"])],
        "zusatz": "Viele Grüße an die Familie!"})
    b = offen(con, aid, "versendet")[0]
    for teil in ("iPhone 13", "Versand mit DHL, Sendungsnummer 00340434123", "piececode=00340434123",
                 "Die Rechnung liegt dem Paket bei.", "kurze Bewertung", "Viele Grüße an die Familie!"):
        assert teil in b["text"], teil
    assert "{Zusatz}" not in b["text"]
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (aid,)).fetchone()
    assert a["abgeholt_am"]
    assert not offen(con, aid, "erinnerung")
    assert con.execute("SELECT 1 FROM auftrag_verlauf WHERE auftrag_id=? AND ereignis='Gerät versendet' "
                       "AND details LIKE '%00340434123%'", (aid,)).fetchone()
    # Vorschau wird beim Laden neu erzeugt – der Zusatz bleibt erhalten
    with dbm.Transaktion(con):
        ben.offene(con, aid)
    assert "00340434123" in offen(con, aid, "versendet")[0]["text"]
    # Senden
    r = post(client, f"/benachrichtigungen/{b['id']}/senden", an="anna@example.com", betreff=b["betreff"],
             text=b["text"])
    assert r.status_code == 302 and "00340434123" in smtp.gesendet[-1].get_body().get_content()
    # Vorschau bietet Textbausteine zum Einfügen
    post(client, f"/auftraege/{aid}/benachrichtigen", anlass="fertig")
    assert "Textbaustein einfügen" in client.get(f"/auftraege/{aid}").get_data(as_text=True)


def test_einstellungen_zeigen_versendet(client):
    html = client.get("/einstellungen/benachrichtigung").get_data(as_text=True)
    assert "Gerät versendet" in html and 'name="ben_versendet_text"' in html
    assert 'name="ben_versendet_aktiv"' not in html
