"""Garantie auf Reparaturen, Wiedererkennung von Geräten (SN/IMEI) und Garantiefälle.

Die hier verwaltete Garantie ist eine freiwillige Zusage der Werkstatt. Die gesetzlichen Mängelrechte des Kunden
(§§ 634 ff. BGB) bleiben davon unberührt – das steht auch so auf Rechnung und Abholschein.
"""
import calendar
import re
from datetime import date, datetime

from . import db as dbm
from .hilfen import datum_de

AUFTRAGSARTEN = {"reparatur": "Reparatur", "garantie": "Garantiefall"}


def standard_monate(einst):
    try:
        return max(0, int(einst.get("garantie_monate") or 0))
    except (TypeError, ValueError):
        return 12


def plus_monate(d, monate):
    m = d.month - 1 + monate
    jahr, monat = d.year + m // 12, m % 12 + 1
    return date(jahr, monat, min(d.day, calendar.monthrange(jahr, monat)[1]))


def _datum(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).date()
    except ValueError:
        return None


def monate(a, einst):
    if a["garantie_monate"] is not None:
        return int(a["garantie_monate"])
    return standard_monate(einst)


def status(a, einst, heute=None):
    """Garantie eines Auftrags: Beginn = Abholung (sonst „Erledigt“-Datum)."""
    heute = heute or date.today()
    m = monate(a, einst)
    beginn = _datum(a["abgeholt_am"]) or _datum(a["erledigt_am"])
    if a["auftragsart"] == "garantie":
        return {"monate": m, "beginn": beginn, "ende": None, "laeuft": False, "text": "Garantiefall (kostenlos)"}
    if not m:
        return {"monate": 0, "beginn": beginn, "ende": None, "laeuft": False, "text": "keine Garantie vereinbart"}
    if not beginn:
        return {"monate": m, "beginn": None, "ende": None, "laeuft": False,
                "text": f"{m} Monate ab Abholung (Gerät noch nicht fertig)"}
    ende = plus_monate(beginn, m)
    laeuft = ende >= heute
    return {"monate": m, "beginn": beginn, "ende": ende, "laeuft": laeuft,
            "text": f"{m} Monate bis {datum_de(ende.isoformat())}" + (" – läuft" if laeuft else " – abgelaufen")}


HINWEIS_GESETZ = "Ihre gesetzlichen Gewährleistungsrechte bleiben davon unberührt."


def text_fuer_auftrag(con, a, ab=None):
    """Satz für Abholschein/Rechnung. ab: Beginn (Standard: Abholung bzw. heute)."""
    einst = dbm.einstellungen(con)
    if a["auftragsart"] == "garantie":
        return "Garantiefall – kostenlose Nachbesserung." + (f" Bezug: Auftrag {bezug_nr(con, a)}."
                                                              if a["garantie_bezug_id"] else "")
    m = monate(a, einst)
    if not m:
        return ""
    beginn = ab or _datum(a["abgeholt_am"]) or date.today()
    return (f"{m} Monate Garantie auf die ausgeführte Reparatur (bis {datum_de(plus_monate(beginn, m).isoformat())}). "
            + HINWEIS_GESETZ)


def bezug_nr(con, a):
    r = con.execute("SELECT auftragsnr FROM auftraege WHERE id=?", (a["garantie_bezug_id"],)).fetchone()
    return r["auftragsnr"] if r else ""


def rechnungstext(con, dok):
    """Garantie-Satz für eine Rechnung, die zu einem Auftrag gehört (sonst leer)."""
    a = con.execute("SELECT * FROM auftraege WHERE rechnung_id=?", (dok["id"],)).fetchone()
    if not a:
        return ""
    einst = dbm.einstellungen(con)
    m = monate(a, einst)
    if not m or a["auftragsart"] == "garantie":
        return ""
    return f"Auf die ausgeführte Reparatur gewähren wir {m} Monate Garantie ab Übergabe des Geräts. " + HINWEIS_GESETZ


# ---------------------------------------------------------------------- Geräte wiedererkennen

def sn_normal(sn):
    return re.sub(r"[\s\-/.]", "", (sn or "")).upper()


SN_SQL = "upper(replace(replace(replace(replace(COALESCE(a.seriennummer,''),' ',''),'-',''),'/',''),'.',''))"


def vorbesuche(con, sn, ohne_id=None, heute=None):
    """Frühere Aufträge mit derselben Seriennummer/IMEI (neueste zuerst), mit Garantiestand."""
    n = sn_normal(sn)
    if len(n) < 4:
        return []
    einst = dbm.einstellungen(con)
    zeilen = con.execute(
        "SELECT a.*, k.kundennr, k.firma, k.vorname, k.nachname, k.typ AS ktyp, re.nummer AS re_nummer, "
        "re.status AS re_status, re.summe_brutto AS re_betrag, "
        "(SELECT COUNT(*) FROM auftrag_fotos f WHERE f.auftrag_id=a.id AND f.geloescht_am IS NULL) AS foto_anzahl "
        f"FROM auftraege a JOIN kunden k ON k.id=a.kunde_id LEFT JOIN dokumente re ON re.id=a.rechnung_id "
        f"WHERE {SN_SQL}=? AND a.id<>? ORDER BY a.eingang_am DESC", (n, ohne_id or 0)).fetchall()
    return [{"a": z, "garantie": status(z, einst, heute)} for z in zeilen]


def interne_kosten(con, a):
    """Interne Kosten eines Garantiefalls: manuell erfasste Kosten (+ später Lagerabgänge zum EK)."""
    summe = a["interne_kosten"] or 0
    try:
        from .lager import auftrag_materialkosten
        summe += auftrag_materialkosten(con, a["id"])
    except ImportError:
        pass
    return summe


def garantiefaelle_zu(con, auftrag_id):
    return con.execute("SELECT * FROM auftraege WHERE garantie_bezug_id=? ORDER BY eingang_am", (auftrag_id,)).fetchall()
