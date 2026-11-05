"""Auswahllisten mit eigenen Einträgen: neue Einträge wandern automatisch in die Vorgabenliste.

In Formularen schickt eine Auswahl mit „✎ Eigener Eintrag …“ (static/anpassen.js) zusätzlich das Feld
`_neue_vorgabe` = „liste|Wert“. Nach erfolgreichem Speichern wird der Wert an die Liste in den Einstellungen
angehängt – so steht er beim nächsten Mal zur Auswahl. Bearbeiten/Löschen: Einstellungen (Suche nach dem Listennamen).
"""
from . import db as dbm

# Einstellung → Trennzeichen der Liste
LISTEN = {"leistungsarten": ",", "kostenarten": "\n", "fixkosten_kategorien": "\n"}
MAX_LAENGE = 80


def eintraege(text, trenner):
    return [x.strip() for x in (text or "").split(trenner) if x.strip()]


def merken(con, werte):
    """werte: Liste „liste|Wert“. Gibt die tatsächlich ergänzten (liste, wert) zurück."""
    neu = []
    einst = dbm.einstellungen(con)
    for roh in werte:
        liste, _, wert = str(roh).partition("|")
        wert = " ".join(wert.replace(",", " ").split()) if LISTEN.get(liste) == "," else " ".join(wert.split())
        if liste not in LISTEN or not wert or len(wert) > MAX_LAENGE:
            continue
        trenner = LISTEN[liste]
        vorhanden = eintraege(einst.get(liste), trenner)
        if wert.lower() in {v.lower() for v in vorhanden}:
            continue
        vorhanden.append(wert)
        einst[liste] = (", " if trenner == "," else "\n").join(vorhanden)
        dbm.einstellungen_speichern({liste: einst[liste]}, con)
        dbm.protokollieren("vorgabe_ergaenzt", "einstellung", None, {"liste": liste, "wert": wert}, con=con)
        neu.append((liste, wert))
    return neu
