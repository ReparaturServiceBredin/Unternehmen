"""Reparaturaufträge: Tafel mit den Spalten offen / in Arbeit / erledigt.

Wird ein Auftrag auf „erledigt“ gezogen, entsteht automatisch ein Rechnungsentwurf
mit den Positionen aus dem Kostenvoranschlag (falls vorhanden).
"""
from datetime import date

from . import db as dbm
from . import logik
from .hilfen import EingabeFehler

STATUS = {"offen": "Offen", "in_arbeit": "In Arbeit", "erledigt": "Erledigt"}


def naechste_auftragsnr(con):
    jahr = date.today().year
    praefix = f"RA-{jahr}-"
    nr = 0
    for r in con.execute("SELECT auftragsnr FROM auftraege WHERE auftragsnr LIKE ?", (praefix + "%",)):
        try:
            nr = max(nr, int(r["auftragsnr"].rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            pass
    return f"{praefix}{nr + 1:04d}"


def anlegen(con, kunde_id, geraet="", fehler="", leistungsart="", seriennummer="", zubehoer="", notizen="",
            anfrage_id=None):
    """Legt einen Auftrag in der Spalte „offen“ an. Muss in einer Transaktion laufen."""
    if not con.execute("SELECT 1 FROM kunden WHERE id=?", (kunde_id,)).fetchone():
        raise EingabeFehler("Bitte einen Kunden auswählen.")
    nr = naechste_auftragsnr(con)
    reihenfolge = (con.execute("SELECT MAX(reihenfolge) FROM auftraege WHERE status='offen'").fetchone()[0] or 0) + 1
    cur = con.execute(
        "INSERT INTO auftraege (auftragsnr, kunde_id, anfrage_id, status, geraet, leistungsart, seriennummer, zubehoer, "
        "fehler, notizen, reihenfolge, eingang_am, erstellt_am, geaendert_am) "
        "VALUES (?,?,?,'offen',?,?,?,?,?,?,?,?,?,?)",
        (nr, kunde_id, anfrage_id, geraet, leistungsart, seriennummer, zubehoer, fehler, notizen, reihenfolge,
         dbm.jetzt(), dbm.jetzt(), dbm.jetzt()))
    dbm.protokollieren("auftrag_angelegt", "auftrag", cur.lastrowid, {"auftragsnr": nr}, con=con)
    return cur.lastrowid


def betreff(a):
    teile = [a["geraet"] or "Reparatur"]
    if a["seriennummer"]:
        teile.append(f"SN/IMEI {a['seriennummer']}")
    return f"Reparatur {', '.join(teile)} (Auftrag {a['auftragsnr']})" if a["geraet"] else \
        f"Reparatur (Auftrag {a['auftragsnr']})"


def kva_erstellen(con, auftrag_id):
    """Legt einen KVA-Entwurf zum Auftrag an (oder gibt den vorhandenen zurück)."""
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (auftrag_id,)).fetchone()
    if a["kva_id"]:
        return a["kva_id"]
    did = logik.neuer_entwurf(con, dbm.einstellungen(con), "kva", a["kunde_id"], betreff(a))
    if a["fehler"]:
        con.execute("UPDATE dokumente SET hinweise=? WHERE id=?", (f"Fehlerbeschreibung: {a['fehler']}", did))
    con.execute("UPDATE auftraege SET kva_id=?, geaendert_am=? WHERE id=?", (did, dbm.jetzt(), auftrag_id))
    return did


def rechnung_erstellen(con, auftrag_id):
    """Legt den Rechnungsentwurf an – mit den Positionen des Kostenvoranschlags, falls vorhanden.

    Gibt (dokument_id, neu) zurück. Gibt es schon eine (nicht stornierte) Rechnung, wird diese verwendet.
    """
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (auftrag_id,)).fetchone()
    if a["rechnung_id"]:
        r = con.execute("SELECT status FROM dokumente WHERE id=?", (a["rechnung_id"],)).fetchone()
        if r and r["status"] != "storniert":
            return a["rechnung_id"], False
    positionen = []
    if a["kva_id"]:
        positionen = con.execute("SELECT * FROM positionen WHERE dokument_id=? ORDER BY pos", (a["kva_id"],)).fetchall()
    did = logik.neuer_entwurf(con, dbm.einstellungen(con), "rechnung", a["kunde_id"], betreff(a), positionen,
                              leistungsdatum=date.today().isoformat())
    con.execute("UPDATE auftraege SET rechnung_id=?, geaendert_am=? WHERE id=?", (did, dbm.jetzt(), auftrag_id))
    return did, True


def status_setzen(con, auftrag_id, status, vor_id=None):
    """Verschiebt einen Auftrag in eine Spalte (optional vor eine andere Karte).

    Gibt die ID eines neu erzeugten Rechnungsentwurfs zurück (nur beim Wechsel nach „erledigt“).
    """
    if status not in STATUS:
        raise EingabeFehler("Unbekannter Status.")
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (auftrag_id,)).fetchone()
    if not a:
        raise EingabeFehler("Auftrag nicht gefunden.")
    # Reihenfolge: vor die Karte vor_id, sonst ans Ende der Spalte
    if vor_id:
        ziel = con.execute("SELECT reihenfolge FROM auftraege WHERE id=? AND status=?", (vor_id, status)).fetchone()
    else:
        ziel = None
    if ziel:
        davor = con.execute("SELECT MAX(reihenfolge) FROM auftraege WHERE status=? AND reihenfolge<? AND id<>?",
                            (status, ziel["reihenfolge"], auftrag_id)).fetchone()[0]
        reihenfolge = ((davor if davor is not None else ziel["reihenfolge"] - 1) + ziel["reihenfolge"]) / 2
    else:
        reihenfolge = (con.execute("SELECT MAX(reihenfolge) FROM auftraege WHERE status=? AND id<>?",
                                   (status, auftrag_id)).fetchone()[0] or 0) + 1
    felder = {"status": status, "reihenfolge": reihenfolge, "geaendert_am": dbm.jetzt()}
    if status == "in_arbeit" and not a["begonnen_am"]:
        felder["begonnen_am"] = dbm.jetzt()
    felder["erledigt_am"] = dbm.jetzt() if status == "erledigt" else None
    con.execute(f"UPDATE auftraege SET {', '.join(f'{k}=?' for k in felder)} WHERE id=?",
                (*felder.values(), auftrag_id))
    neue_rechnung = None
    if status != a["status"]:
        dbm.protokollieren("auftrag_status", "auftrag", auftrag_id, {"von": a["status"], "nach": status}, con=con)
        if status == "erledigt":
            did, neu = rechnung_erstellen(con, auftrag_id)
            if neu:
                neue_rechnung = did
    return neue_rechnung
