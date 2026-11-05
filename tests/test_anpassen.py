"""Anpassbare Oberfläche: Bausteine (Übersicht, Finanzen), Tabellenspalten, Auswahllisten mit eigenem Eintrag."""
import json
import re
from html.parser import HTMLParser

from conftest import post
from rsb import db as dbm
from test_arbeitskalender import arbeit_anlegen

LEERE_TAGS = {"br", "img", "input", "meta", "link", "hr", "source", "col", "wbr"}


class Kinder(HTMLParser):
    """Direkte Kinder des Elements mit data-anpassbar (Tag + Attribute) und Prüfung der Verschachtelung."""

    def __init__(self):
        super().__init__()
        self.stapel, self.kinder, self.tiefe_rahmen = [], [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in LEERE_TAGS:
            return
        if self.tiefe_rahmen is not None and len(self.stapel) == self.tiefe_rahmen + 1:
            self.kinder.append((tag, a))
        if "data-anpassbar" in a:
            self.tiefe_rahmen = len(self.stapel)
        self.stapel.append(tag)

    def handle_endtag(self, tag):
        if tag in LEERE_TAGS:
            return
        assert self.stapel and self.stapel[-1] == tag, f"falsch verschachtelt: </{tag}> nach {self.stapel[-3:]}"
        self.stapel.pop()
        if self.tiefe_rahmen is not None and len(self.stapel) == self.tiefe_rahmen:
            self.tiefe_rahmen = -1  # Rahmen geschlossen


def bausteine(seite):
    p = Kinder()
    p.feed(seite)
    assert p.kinder, "kein anpassbarer Bereich gefunden"
    return p.kinder


def test_uebersicht_aus_bausteinen(client):
    kinder = bausteine(client.get("/").get_data(as_text=True))
    ids = [a.get("data-kachel") for _, a in kinder]
    assert all(ids), f"Element ohne data-kachel im anpassbaren Bereich: {kinder}"
    assert len(ids) == len(set(ids))
    assert {"auftraege_offen", "umsatz_jahr", "zuletzt"} <= set(ids)
    aus = {a["data-kachel"] for _, a in kinder if a.get("data-standard") == "aus"}
    assert {"anfragen", "lager", "schnellzugriff"} <= aus  # zusätzliche Kacheln zum Einblenden
    assert all(a.get("data-titel") and a.get("data-breite") in ("3", "4", "6", "8", "12") for _, a in kinder)


def test_finanzen_aus_bausteinen(client):
    kinder = bausteine(client.get("/finanzen").get_data(as_text=True))
    ids = [a.get("data-kachel") for _, a in kinder]
    assert all(ids) and len(ids) == len(set(ids))
    assert {"kpi_umsatz", "einnahmen", "diagramme", "monate", "breakeven", "vorschau"} <= set(ids)


def test_layout_und_spalten_speichern(client, con):
    r = client.post("/oberflaeche", json={"layout": {"seite": "start", "reihe": ["zuletzt", "umsatz_jahr", "<x>"],
                                                     "aus": ["kunden"], "breite": {"zuletzt": "6", "kunden": "99"}}},
                    headers={"X-CSRF": "test-token"})
    assert r.status_code == 200
    client.post("/oberflaeche", json={"spalten": {"tabelle": "/kunden#0", "aus": ["E-Mail", "<b>"]}},
                headers={"X-CSRF": "test-token"})
    ui = dbm.einstellung("oberflaeche:inhaber", con)
    assert ui["layouts"]["start"] == {"reihe": ["zuletzt", "umsatz_jahr"], "aus": ["kunden"], "breite": {"zuletzt": "6"}}
    assert ui["spalten"] == {"/kunden#0": ["E-Mail"]}
    seite = client.get("/").get_data(as_text=True)
    zustand = json.loads(re.search(r"window\.UI_ZUSTAND = (.*?);</script>", seite).group(1))
    assert zustand["layouts"]["start"]["aus"] == ["kunden"] and zustand["spalten"]["/kunden#0"] == ["E-Mail"]
    assert "anpassen.js" in seite
    client.post("/oberflaeche", json={"layout": {"seite": "start", "zuruecksetzen": True}}, headers={"X-CSRF": "test-token"})
    assert "start" not in dbm.einstellung("oberflaeche:inhaber", con)["layouts"]


def test_eigener_eintrag_wird_vorgabe(client, con):
    r = post(client, "/artikel/neu", name="Workshop", preis="500,00", einheit="pauschal", steuersatz="19",
             leistungsart="Strategieberatung", _neue_vorgabe="leistungsarten|Strategieberatung")
    assert r.status_code == 302
    assert con.execute("SELECT leistungsart FROM artikel WHERE name='Workshop'").fetchone()[0] == "Strategieberatung"
    assert "Strategieberatung" in dbm.einstellung("leistungsarten", con).split(", ")
    # erscheint jetzt in der Auswahl, doppelt wird nichts übernommen
    assert re.search(r"<option[^>]*>Strategieberatung</option>", client.get("/artikel/neu").get_data(as_text=True))
    post(client, "/artikel/neu", name="Workshop 2", preis="1,00", einheit="pauschal", steuersatz="19",
         leistungsart="strategieberatung", _neue_vorgabe="leistungsarten|strategieberatung")
    assert dbm.einstellung("leistungsarten", con).lower().count("strategieberatung") == 1
    # unbekannte Listen werden ignoriert
    post(client, "/artikel/neu", name="X", preis="1,00", einheit="pauschal", steuersatz="19",
         _neue_vorgabe="passwort_hash|abc")
    assert dbm.einstellung("passwort_hash", con) == ""


def test_kein_eintrag_bei_eingabefehler(client, con):
    post(client, "/artikel/neu", name="", preis="", leistungsart="Neu", _neue_vorgabe="kostenarten|Fehlerfall")
    assert "Fehlerfall" not in dbm.einstellung("kostenarten", con)


def test_auswahllisten_mit_eigenem_eintrag(client):
    seite = client.get("/artikel/neu").get_data(as_text=True)
    assert re.search(r'<select name="leistungsart" data-frei data-vorgabe="leistungsarten"', seite)
    assert 'name="anrede" data-frei' in client.get("/kunden/neu").get_data(as_text=True)
    # feste Programm-Logik bleibt eine feste Auswahl (z. B. Kundentyp, Steuer)
    assert 'name="typ" id="typ" data-frei' not in client.get("/kunden/neu").get_data(as_text=True)


def test_eigene_kostenkategorie_im_arbeitskalender(client, con):
    aid = arbeit_anlegen(client)
    r = post(client, f"/kalender/{aid}/kosten", kategorie="Mautgebühr", betrag="12,30")
    assert r.status_code == 302
    k = con.execute("SELECT kategorie, betrag FROM arbeit_kosten WHERE arbeit_id=?", (aid,)).fetchone()
    assert (k["kategorie"], k["betrag"]) == ("Mautgebühr", 1230)
