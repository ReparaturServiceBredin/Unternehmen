"""Weitere Benutzer neben dem Inhaber und Schutz der Anmeldung gegen Passwort-Raten.

Der Inhaber meldet sich wie bisher mit dem Passwort aus den Einstellungen an (Benutzername leer oder „inhaber“).
Weitere Personen bekommen eigene Zugänge; das Protokoll nennt dann den Namen. Rollen:
  inhaber     – alle Rechte
  mitarbeiter – alles außer Einstellungen, Backup, Protokoll und Benutzerverwaltung
"""
import re
import threading
import time

from werkzeug.security import check_password_hash, generate_password_hash

from . import db as dbm
from .hilfen import EingabeFehler

INHABER = "inhaber"
ROLLEN = {"inhaber": "Inhaber (alle Rechte)", "mitarbeiter": "Mitarbeiter (ohne Einstellungen)"}
NAME_MUSTER = re.compile(r"^[a-z0-9][a-z0-9._-]{1,29}$")

# Anmeldeschutz: nach FEHLVERSUCHE falschen Passwörtern innerhalb von SPERRE_SEK ist die Anmeldung von dieser Adresse
# für SPERRE_SEK gesperrt (im Speicher – ein Neustart hebt die Sperre auf).
FEHLVERSUCHE = 5
SPERRE_SEK = 15 * 60
_versuche = {}
_sperre = threading.Lock()


def gesperrt_sek(adresse):
    """Restliche Sperrzeit in Sekunden (0 = nicht gesperrt)."""
    jetzt = time.monotonic()
    with _sperre:
        liste = [t for t in _versuche.get(adresse, []) if jetzt - t < SPERRE_SEK]
        _versuche[adresse] = liste
        if len(liste) < FEHLVERSUCHE:
            return 0
        return int(SPERRE_SEK - (jetzt - liste[-FEHLVERSUCHE])) + 1


def fehlversuch(adresse):
    with _sperre:
        _versuche.setdefault(adresse, []).append(time.monotonic())
        if len(_versuche) > 10000:  # Speicher begrenzen
            _versuche.clear()


def erfolg(adresse):
    with _sperre:
        _versuche.pop(adresse, None)


def _passwort_pruefen(pw, pw2):
    if len(pw) < 8 or pw != pw2:
        raise EingabeFehler("Das Passwort muss mindestens 8 Zeichen haben und zweimal gleich eingegeben werden.")


def alle(con):
    return con.execute("SELECT * FROM benutzer ORDER BY aktiv DESC, name").fetchall()


def laden(con, bid):
    return con.execute("SELECT * FROM benutzer WHERE id=?", (bid,)).fetchone()


def anzahl_aktiv(con):
    return con.execute("SELECT COUNT(*) FROM benutzer WHERE aktiv=1").fetchone()[0]


def anlegen(con, name, anzeigename, rolle, pw, pw2):
    name = (name or "").strip().lower()
    if not NAME_MUSTER.match(name) or name == INHABER:
        raise EingabeFehler("Benutzername: 2–30 Zeichen, nur Kleinbuchstaben, Ziffern, Punkt, Binde- und Unterstrich "
                            "(nicht „inhaber“).")
    if rolle not in ROLLEN:
        raise EingabeFehler("Unbekannte Rolle.")
    if con.execute("SELECT 1 FROM benutzer WHERE name=?", (name,)).fetchone():
        raise EingabeFehler(f"Den Benutzer „{name}“ gibt es schon.")
    _passwort_pruefen(pw, pw2)
    cur = con.execute("INSERT INTO benutzer (name, anzeigename, rolle, passwort_hash, aktiv, angelegt_am) "
                      "VALUES (?,?,?,?,1,?)", (name, (anzeigename or "").strip() or name, rolle,
                                               generate_password_hash(pw), dbm.jetzt_berlin()))
    dbm.protokollieren("benutzer_angelegt", "benutzer", cur.lastrowid, {"name": name, "rolle": rolle}, con=con)
    return cur.lastrowid


def aendern(con, bid, anzeigename, rolle, aktiv):
    b = laden(con, bid)
    if not b:
        raise EingabeFehler("Benutzer nicht gefunden.")
    if rolle not in ROLLEN:
        raise EingabeFehler("Unbekannte Rolle.")
    con.execute("UPDATE benutzer SET anzeigename=?, rolle=?, aktiv=? WHERE id=?",
                ((anzeigename or "").strip() or b["name"], rolle, 1 if aktiv else 0, bid))
    dbm.protokollieren("benutzer_geaendert", "benutzer", bid, {"name": b["name"], "rolle": rolle,
                                                              "aktiv": bool(aktiv)}, con=con)


def passwort_setzen(con, bid, pw, pw2):
    b = laden(con, bid)
    if not b:
        raise EingabeFehler("Benutzer nicht gefunden.")
    _passwort_pruefen(pw, pw2)
    con.execute("UPDATE benutzer SET passwort_hash=? WHERE id=?", (generate_password_hash(pw), bid))
    dbm.protokollieren("benutzer_passwort", "benutzer", bid, {"name": b["name"]}, con=con)


def pruefen(con, name, pw):
    """Anmeldedaten prüfen. Gibt ein dict für die Sitzung zurück oder None."""
    name = (name or "").strip().lower()
    if name in ("", INHABER):
        if check_password_hash(dbm.einstellung("passwort_hash", con) or "", pw):
            return {"benutzer": INHABER, "rolle": "inhaber"}
        return None
    b = con.execute("SELECT * FROM benutzer WHERE name=? AND aktiv=1", (name,)).fetchone()
    if b and check_password_hash(b["passwort_hash"], pw):
        con.execute("UPDATE benutzer SET letzte_anmeldung=? WHERE id=?", (dbm.jetzt_berlin(), b["id"]))
        return {"benutzer": b["name"], "rolle": b["rolle"], "benutzer_id": b["id"], "pw_stand": stand(b)}
    return None


def stand(b):
    """Kennung des aktuellen Passworts – ändert es sich, enden bestehende Sitzungen dieses Benutzers."""
    return b["passwort_hash"][-12:]


def sitzung_gueltig(con, sitzung):
    """Weitere Benutzer: noch aktiv und Passwort unverändert? Aktualisiert die Rolle in der Sitzung."""
    bid = sitzung.get("benutzer_id")
    if not bid:
        return True
    b = laden(con, bid)
    if not b or not b["aktiv"] or stand(b) != sitzung.get("pw_stand"):
        return False
    sitzung["rolle"] = b["rolle"]
    return True
