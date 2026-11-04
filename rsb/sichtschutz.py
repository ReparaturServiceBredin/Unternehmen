"""Sichtschutz (Diskretionsmodus): Namen, Kontaktdaten und Beträge anderer Kunden unscharf anzeigen.

Der Zustand steht in einem Cookie (bleibt beim Seitenwechsel und Neuladen erhalten). Ist er aktiv, liefert der
Server die Liste schützenswerter Begriffe (Kundennamen, Straßen, E-Mail-Adressen, Telefonnummern); static/sichtschutz.js
macht diese sowie alle Beträge, E-Mails und Telefonnummern auf jeder Seite unscharf – ohne bestehende Seiten zu ändern.
Ein Kunde kann ausgenommen werden („Diesen Kunden zeigen“).
"""
from flask import request

COOKIE = "rsb_sichtschutz"
COOKIE_KUNDE = "rsb_sichtschutz_kunde"


def aktiv():
    return request.cookies.get(COOKIE) == "1"


def ausgenommen():
    k = request.cookies.get(COOKIE_KUNDE) or ""
    return int(k) if k.isdigit() else None


def begriffe(con, ausgenommen_id=None):
    """Schützenswerte Begriffe aller Kunden (außer dem ausgenommenen), längste zuerst."""
    werte = set()
    for k in con.execute("SELECT id, firma, vorname, nachname, strasse, email, telefon, email_weitere FROM kunden "
                         "WHERE anonymisiert_am IS NULL").fetchall():
        if ausgenommen_id and k["id"] == ausgenommen_id:
            continue
        person = " ".join(x for x in (k["vorname"], k["nachname"]) if x)
        for w in (k["firma"], person, k["nachname"], k["strasse"], k["email"], k["telefon"]):
            w = (w or "").strip()
            if len(w) >= 3:
                werte.add(w)
        for w in (k["email_weitere"] or "").replace(";", ",").split(","):
            if "@" in w:
                werte.add(w.strip())
    for a in con.execute("SELECT name, adresse, telefon, email FROM arbeiten WHERE kunde_id IS NULL "
                         "OR kunde_id<>?", (ausgenommen_id or 0,)).fetchall():
        for w in (a["name"], a["adresse"], a["telefon"], a["email"]):
            w = (w or "").strip()
            if len(w) >= 3:
                werte.add(w)
    return sorted(werte, key=len, reverse=True)
