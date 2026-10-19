"""Ratenzahlung: eine Rechnung über den vollen Betrag mit Ratenplan.

Die Rechnung zeigt alle Raten mit Betrag und Fälligkeit. Vor jeder Fälligkeit schickt das Programm (wenn
eingeschaltet) eine Zahlungsaufforderung „Rate x von n“ mit der Rechnung im Anhang. Zahlungseingänge auf die
Rechnung haken die Raten der Reihe nach ab. Fälligkeit der Rechnung (Mahnwesen) = letzte Rate.
"""
import calendar
from datetime import date, timedelta

from . import db as dbm
from .hilfen import EingabeFehler, datum_de, euro, heute_datum

MIN_RATEN, MAX_RATEN = 2, 24


def monate_spaeter(tag, monate):
    m = tag.month - 1 + monate
    jahr, monat = tag.year + m // 12, m % 12 + 1
    return date(jahr, monat, min(tag.day, calendar.monthrange(jahr, monat)[1]))


def plan(brutto, anzahl, erste):
    """[{nr, faellig_am, betrag}] – gleiche Raten, Rundungsrest auf die erste Rate."""
    erste = erste if isinstance(erste, date) else date.fromisoformat(erste)
    grund = int(brutto) // anzahl
    rest = int(brutto) - grund * anzahl
    return [{"nr": i + 1, "faellig_am": monate_spaeter(erste, i).isoformat(), "betrag": grund + (rest if i == 0 else 0)}
            for i in range(anzahl)]


def pruefen(anzahl, erste, datum):
    """Eingaben aus dem Rechnungsformular prüfen. Gibt (anzahl, erste) zurück."""
    try:
        anzahl = int(anzahl)
    except (TypeError, ValueError):
        raise EingabeFehler("Bitte die Anzahl der Raten angeben.")
    if not MIN_RATEN <= anzahl <= MAX_RATEN:
        raise EingabeFehler(f"Ratenzahlung: zwischen {MIN_RATEN} und {MAX_RATEN} Raten.")
    try:
        erste_d = date.fromisoformat(erste)
    except (TypeError, ValueError):
        raise EingabeFehler("Bitte das Fälligkeitsdatum der ersten Rate angeben.")
    if erste_d < date.fromisoformat(datum):
        raise EingabeFehler("Die erste Rate kann nicht vor dem Rechnungsdatum fällig sein.")
    return anzahl, erste_d.isoformat()


def anlegen(con, dokument_id, raten):
    """Beim Festschreiben: Raten aus dem eingefrorenen Ratenplan speichern."""
    for r in raten:
        con.execute("INSERT INTO rechnung_raten (dokument_id, nr, faellig_am, betrag) VALUES (?,?,?,?)",
                    (dokument_id, r["nr"], r["faellig_am"], r["betrag"]))


def stand(con, dokument_id, heute=None):
    """Raten mit Status: bezahlt / teilweise / fällig / überfällig / offen (Zahlungen der Reihe nach angerechnet)."""
    heute = (heute or heute_datum()).isoformat()
    bezahlt = con.execute("SELECT COALESCE(SUM(betrag), 0) FROM zahlungen WHERE dokument_id=? AND storniert_am IS NULL",
                          (dokument_id,)).fetchone()[0]
    zeilen = con.execute("SELECT * FROM rechnung_raten WHERE dokument_id=? ORDER BY nr", (dokument_id,)).fetchall()
    # Nachträglich vereinbarte Raten decken nur den damals offenen Betrag – frühere Zahlungen zählen zuerst dafür
    brutto = con.execute("SELECT summe_brutto FROM dokumente WHERE id=?", (dokument_id,)).fetchone()[0] or 0
    vorab = max(0, brutto - sum(r["betrag"] for r in zeilen))
    erg, rest = [], max(0, bezahlt - vorab)
    for r in zeilen:
        anteil = max(0, min(rest, r["betrag"]))
        rest -= anteil
        if anteil >= r["betrag"]:
            status = "bezahlt"
        elif r["faellig_am"] < heute:
            status = "überfällig"
        elif r["faellig_am"] == heute:
            status = "fällig"
        else:
            status = "teilweise" if anteil else "offen"
        erg.append({**dict(r), "bezahlt": anteil, "offen": r["betrag"] - anteil, "status": status})
    return erg


def _planzeilen(raten):
    return "\n".join(f"  {r['nr']}. Rate am {datum_de(r['faellig_am'])}: {euro(r['betrag'])}"
                     + (" (bezahlt)" if r.get("status") == "bezahlt" else "") for r in raten)


def _text(einst, d, kunde, rate, anzahl, plan_liste):
    from .hilfen import anrede_brief
    return (f"{anrede_brief(kunde)}\n\nwie vereinbart zahlen Sie die Rechnung {d['nummer']} vom {datum_de(d['datum'])} "
            f"in {anzahl} Raten. Die {rate['nr']}. Rate über {euro(rate['offen'])} ist am "
            f"{datum_de(rate['faellig_am'])} fällig.\n\nIhr Ratenplan:\n{_planzeilen(plan_liste)}\n\n"
            + (f"Bitte überweisen Sie den Betrag auf {einst.get('kontoinhaber') or einst.get('firma_name')}, "
               f"IBAN {einst.get('iban')}, Verwendungszweck: {d['nummer']} Rate {rate['nr']}.\n\n"
               if einst.get("iban") else "")
            + "Die Rechnung mit dem vollständigen Ratenplan finden Sie im Anhang. Sollten Sie bereits gezahlt haben, "
            "betrachten Sie diese Nachricht bitte als gegenstandslos.\n\n"
            f"Mit freundlichen Grüßen\n{einst.get('inhaber') or ''}\n{einst.get('firma_name') or ''}")


def erinnerung_senden(con, daten_dir, rate_id, an=None):
    """Zahlungsaufforderung für eine Rate senden. Gibt die Empfängeradresse zurück."""
    from pathlib import Path
    from .mail import senden
    r = con.execute("SELECT * FROM rechnung_raten WHERE id=?", (rate_id,)).fetchone()
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (r["dokument_id"],)).fetchone()
    if d["status"] == "storniert" or d["storniert_durch"]:
        raise EingabeFehler("Die Rechnung ist storniert.")
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (d["kunde_id"],)).fetchone()
    an = an or (kunde["email"] if kunde else "")
    if not an:
        raise EingabeFehler("Beim Kunden ist keine E-Mail-Adresse hinterlegt.")
    plan_liste = stand(con, d["id"])
    s = next(x for x in plan_liste if x["id"] == rate_id)
    anzahl = len(plan_liste)
    einst = dbm.einstellungen(con)
    betreff = f"Rate {s['nr']} von {anzahl} zu Rechnung {d['nummer']} – fällig am {datum_de(s['faellig_am'])}"
    pdf = (Path(daten_dir) / d["pdf_pfad"]).read_bytes()
    senden(con, None, an, betreff, _text(einst, d, kunde, s, anzahl, plan_liste), pdf, f"{d['nummer']}.pdf",
           dokument_id=d["id"])
    with dbm.Transaktion(con):
        con.execute("UPDATE rechnung_raten SET erinnert_am=?, erinnert_an=?, fehler=NULL WHERE id=?",
                    (dbm.jetzt_berlin(), an, rate_id))
        dbm.protokollieren("rate_erinnert", "dokument", d["id"], {"rate": s["nr"], "an": an}, con=con)
    return an


def lauf(con, daten_dir, heute=None):
    """Täglich: Für Raten, die in den nächsten Tagen fällig werden, die Zahlungsaufforderung senden.

    Nur bei Rechnungen mit eingeschaltetem automatischem Versand, nur einmal je Rate und nie für bezahlte Raten.
    Die 1. Rate entfällt, wenn die Rechnung selbst schon per E-Mail verschickt wurde (sie enthält den Ratenplan).
    """
    heute = heute or heute_datum()
    einst = dbm.einstellungen(con)
    if not einst.get("smtp_host"):
        return {"gesendet": 0, "fehler": []}
    grenze = (heute + timedelta(days=int(einst.get("raten_vorlauf_tage") or 0))).isoformat()
    erg = {"gesendet": 0, "fehler": []}
    for r in con.execute(
            "SELECT r.id, r.dokument_id, r.nr, r.art, d.nummer, d.versendet_am FROM rechnung_raten r "
            "JOIN dokumente d ON d.id=r.dokument_id WHERE r.erinnert_am IS NULL AND r.faellig_am <= ? "
            "AND COALESCE(r.auto, d.raten_auto)=1 AND d.status<>'entwurf' AND d.storniert_durch IS NULL "
            "ORDER BY r.faellig_am", (grenze,)).fetchall():
        if r["nr"] == 1 and r["art"] == "rechnung" and r["versendet_am"]:
            continue
        s = next(x for x in stand(con, r["dokument_id"], heute) if x["id"] == r["id"])
        if s["status"] == "bezahlt":
            continue
        try:
            erinnerung_senden(con, daten_dir, r["id"])
            erg["gesendet"] += 1
        except Exception as e:  # z. B. keine E-Mail-Adresse oder Server nicht erreichbar – beim nächsten Lauf erneut
            with dbm.Transaktion(con):
                con.execute("UPDATE rechnung_raten SET fehler=? WHERE id=?", (str(e)[:300], r["id"]))
            erg["fehler"].append(f"{r['nummer']} Rate {r['nr']}: {e}")
    return erg


# ---------------------------------------------------------------- nachträglich vereinbart (festgeschriebene Rechnung)

def vereinbaren(con, dokument_id, anzahl, erste, auto, heute=None):
    """Ratenzahlung für eine bereits ausgestellte Rechnung über den offenen Betrag. Die Rechnung bleibt unverändert.

    Muss in einer Transaktion laufen. Gibt den Ratenplan zurück.
    """
    from .zahlungen import stand as zahlstand
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (dokument_id,)).fetchone()
    if not d or d["typ"] != "rechnung" or d["status"] == "entwurf":
        raise EingabeFehler("Ratenzahlung lässt sich nur für ausgestellte Rechnungen vereinbaren.")
    if d["status"] == "storniert" or d["storniert_durch"]:
        raise EingabeFehler("Die Rechnung ist storniert.")
    if con.execute("SELECT 1 FROM rechnung_raten WHERE dokument_id=?", (dokument_id,)).fetchone():
        raise EingabeFehler("Für diese Rechnung gibt es schon einen Ratenplan.")
    offen = zahlstand(con, d)["offen"]
    if offen <= 0:
        raise EingabeFehler("Die Rechnung ist bereits bezahlt.")
    heute = (heute or heute_datum()).isoformat()
    anzahl, erste = pruefen(anzahl, erste, heute)
    p = plan(offen, anzahl, erste)
    jetzt = dbm.jetzt_berlin()
    for r in p:
        con.execute("INSERT INTO rechnung_raten (dokument_id, nr, faellig_am, betrag, art, auto, vereinbart_am) "
                    "VALUES (?,?,?,?, 'vereinbarung', ?, ?)", (dokument_id, r["nr"], r["faellig_am"], r["betrag"],
                                                              1 if auto else 0, jetzt))
    dbm.protokollieren("raten_vereinbart", "dokument", dokument_id,
                       {"anzahl": anzahl, "erste": erste, "betrag": offen, "automatisch": bool(auto)}, con=con)
    return p


def aufheben(con, dokument_id):
    """Nachträglich vereinbarten Ratenplan aufheben (der Ratenplan auf einer Rechnung bleibt). Transaktion nötig."""
    n = con.execute("DELETE FROM rechnung_raten WHERE dokument_id=? AND art='vereinbarung'", (dokument_id,)).rowcount
    if not n:
        raise EingabeFehler("Der Ratenplan steht auf der Rechnung selbst und kann nicht aufgehoben werden.")
    dbm.protokollieren("raten_aufgehoben", "dokument", dokument_id, {"raten": n}, con=con)


def vereinbarung_senden(con, daten_dir, dokument_id):
    """Bestätigung der Ratenvereinbarung mit dem Ratenplan und der Rechnung im Anhang. Gibt die Adresse zurück."""
    from pathlib import Path
    from .hilfen import anrede_brief
    from .mail import senden
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (dokument_id,)).fetchone()
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (d["kunde_id"],)).fetchone()
    an = kunde["email"] if kunde else ""
    if not an:
        raise EingabeFehler("Beim Kunden ist keine E-Mail-Adresse hinterlegt.")
    plan_liste = stand(con, dokument_id)
    einst = dbm.einstellungen(con)
    text = (f"{anrede_brief(kunde)}\n\nwie besprochen können Sie die Rechnung {d['nummer']} vom {datum_de(d['datum'])} "
            f"in {len(plan_liste)} Raten bezahlen:\n\n{_planzeilen(plan_liste)}\n\n"
            + (f"Bankverbindung: {einst.get('kontoinhaber') or einst.get('firma_name')}, IBAN {einst.get('iban')}. "
               f"Verwendungszweck jeweils: {d['nummer']} Rate …\n\n" if einst.get("iban") else "")
            + "Vor jeder Fälligkeit erinnern wir Sie kurz per E-Mail. Die Rechnung finden Sie im Anhang.\n\n"
            f"Mit freundlichen Grüßen\n{einst.get('inhaber') or ''}\n{einst.get('firma_name') or ''}")
    pdf = (Path(daten_dir) / d["pdf_pfad"]).read_bytes()
    senden(con, None, an, f"Ratenzahlung zu Rechnung {d['nummer']}", text, pdf, f"{d['nummer']}.pdf",
           dokument_id=dokument_id)
    return an
