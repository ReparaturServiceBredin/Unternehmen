"""Arbeitskalender: offene Arbeiten (KVA / Reparatur) mit Terminen, Zeiterfassung, Anfahrt und Nebenkosten.

Eigenständiges Modul mit eigenen Tabellen (arbeiten, arbeit_termine, arbeit_kosten, arbeit_nachrichten). Eine Arbeit
kann auf einen Kunden, einen Reparaturauftrag oder einen KVA verweisen – diese werden nur gelesen, nie geändert.
Alle Sätze und Pauschalen stehen in den Einstellungen (Schlüssel „ak_…“), nichts ist fest im Code.
Beträge in Cent netto; die MwSt. richtet sich nach den Rechnungs-Einstellungen (Regelbesteuerung / Kleinunternehmer).
"""
import json
from datetime import date, datetime, timedelta, timezone

from . import db as dbm
from .hilfen import BERLIN, EingabeFehler, anrede_brief, datum_de, euro, heute_datum, jetzt_dt, kunde_name

TYPEN = {"kva": "Kostenvoranschlag", "reparatur": "Reparaturauftrag"}
STATUS = {"offen": "offen", "geplant": "geplant", "in_arbeit": "in Arbeit", "erledigt": "erledigt",
          "abgerechnet": "abgerechnet"}
OFFEN = ("offen", "geplant", "in_arbeit")
PRIORITAETEN = {"": "–", "niedrig": "niedrig", "normal": "normal", "hoch": "hoch", "dringend": "dringend"}
TERMIN_STATUS = {"geplant": "geplant", "vorschlag": "vorgeschlagen", "bestaetigt": "bestätigt",
                 "erledigt": "erledigt", "abgesagt": "abgesagt"}
TERMIN_ARTEN = ["Besichtigung", "Reparatur", "Wartung", "Abholung", "Lieferung", "Sonstiges"]
ANFAHRT = {"km": "Kilometer × Kilometersatz", "pauschale": "Anfahrtspauschale", "keine": "keine Anfahrt"}
KATEGORIEN = {"verpflegung": "Verpflegung", "uebernachtung": "Übernachtung", "parken": "Parkgebühren",
              "maut": "Maut", "material": "Material/Ersatzteile", "sonstiges": "Sonstiges"}
KANAELE = {"email": "E-Mail", "whatsapp": "WhatsApp", "sms": "SMS", "kopiert": "Text kopiert"}

STANDARD_BETREFF = "Terminvorschlag: {arbeit} – {firma_name}"
STANDARD_TEXT = ("{anrede}\n\ngern komme ich für folgende Arbeit zu Ihnen: {arbeit}.\n{beschreibung}\n\n"
                 "{termine_einleitung}\n{termine}\n\nAdresse: {adresse}\n\n{termine_schluss}\n\n"
                 "Mit freundlichen Grüßen\n{inhaber}\n{firma_name}\n{firma_telefon}")


def einstellungs_standard():
    """Standardwerte (für db.STANDARD_EINSTELLUNGEN). Beträge in Cent netto."""
    return {"ak_stundensatz": 6000, "ak_anfahrt": "km", "ak_km_satz": 50, "ak_anfahrt_pauschale": 2500,
            "ak_fahrzeit_satz": 6000, "ak_verpflegung_8h": 1400, "ak_verpflegung_24h": 2800,
            "ak_verpflegung_anreise": 1400, "ak_standard_dauer": 60, "ak_tag_beginn": 7, "ak_tag_ende": 19,
            "ak_vorschlag_betreff": STANDARD_BETREFF, "ak_vorschlag_text": STANDARD_TEXT}


# ---------------------------------------------------------------------- Zeit

def minuten_aus(text):
    """„1:30“ / „90“ / „1,5“ (Stunden mit Komma) → Minuten; leer → None."""
    t = (text or "").strip().replace(" ", "")
    if not t:
        return None
    try:
        if ":" in t:
            h, m = t.split(":", 1)
            return int(h or 0) * 60 + int(m or 0)
        if "," in t or "." in t:
            return int(round(float(t.replace(",", ".")) * 60))
        return int(t)
    except ValueError:
        raise EingabeFehler(f"„{text}“ ist keine gültige Dauer (z. B. 90 oder 1:30).")


def dauer_text(minuten):
    if minuten is None:
        return "–"
    h, m = divmod(int(minuten), 60)
    return f"{h}:{m:02d} Std."


def uhrzeit(text, pflicht=True):
    t = (text or "").strip()
    if not t and not pflicht:
        return None
    try:
        return datetime.strptime(t, "%H:%M").strftime("%H:%M")
    except ValueError:
        raise EingabeFehler(f"„{text}“ ist keine gültige Uhrzeit (z. B. 09:30).")


def ende(t):
    start = datetime.fromisoformat(f"{t['datum']}T{t['beginn']}")
    return (start + timedelta(minutes=t["dauer_min"] or 0)).strftime("%H:%M")


def ist_minuten(t):
    """Tatsächliche Arbeitszeit: erfasste Minuten, sonst aus Start/Ende; plus ein laufender Timer."""
    minuten = t["ist_minuten"]
    if minuten is None and t["ist_beginn"] and t["ist_ende"]:
        a = datetime.strptime(t["ist_beginn"], "%H:%M")
        b = datetime.strptime(t["ist_ende"], "%H:%M")
        minuten = int((b - a).total_seconds() // 60) % (24 * 60)
    if t["timer_start"]:
        laufend = int((jetzt_dt() - datetime.fromisoformat(t["timer_start"])).total_seconds() // 60)
        minuten = (minuten or 0) + max(laufend, 0)
    return minuten


# ---------------------------------------------------------------------- Berechnung

def steuersatz(einst):
    return float(einst.get("regel_steuersatz") or 0) if einst.get("steuer_modus") == "regel" else 0.0


def verpflegung_pauschale(einst, stunden, anreisetag=False):
    """Pauschale nach Abwesenheitsdauer (Sätze aus den Einstellungen)."""
    if anreisetag:
        return int(einst.get("ak_verpflegung_anreise") or 0)
    if stunden >= 24:
        return int(einst.get("ak_verpflegung_24h") or 0)
    if stunden > 8:
        return int(einst.get("ak_verpflegung_8h") or 0)
    return 0


def termin_rechnung(t, satz, einst):
    """Positionen eines Termins: [(kategorie, text, cent, weiterberechnen)]."""
    pos = []
    minuten = ist_minuten(t)
    if minuten:
        pos.append(("arbeitszeit", f"Arbeitszeit {dauer_text(minuten)} × {euro(satz)}/Std.",
                    round(minuten * satz / 60), True))
    art = t["anfahrt"] or einst.get("ak_anfahrt") or "km"
    weiter = bool(t["anfahrt_weiter"])
    if art == "km" and t["km"]:
        km_satz = int(einst.get("ak_km_satz") or 0)
        km = float(t["km"])
        pos.append(("anfahrt", f"Anfahrt {km:g} km × {euro(km_satz)}", round(km * km_satz), weiter))
    elif art == "pauschale" and (t["km"] or t["fahrzeit_min"] or t["ist_minuten"] or t["ist_beginn"]
                                 or t["status"] == "erledigt"):
        pos.append(("anfahrt", "Anfahrtspauschale", int(einst.get("ak_anfahrt_pauschale") or 0), weiter))
    if t["fahrzeit_berechnen"] and t["fahrzeit_min"]:
        fz_satz = int(einst.get("ak_fahrzeit_satz") or 0)
        pos.append(("fahrzeit", f"Fahrzeit {dauer_text(t['fahrzeit_min'])} × {euro(fz_satz)}/Std.",
                    round(t["fahrzeit_min"] * fz_satz / 60), weiter))
    return pos


def stundensatz(arbeit, einst):
    return int(arbeit["stundensatz"] if arbeit["stundensatz"] is not None else einst.get("ak_stundensatz") or 0)


def abrechnung(con, arbeit, einst=None):
    """Übersicht einer Arbeit: Zeiten (geplant/tatsächlich), Kosten je Kategorie, Summen netto/MwSt./brutto."""
    einst = einst or dbm.einstellungen(con)
    satz = stundensatz(arbeit, einst)
    termine = termine_von(con, arbeit["id"])
    kosten = con.execute("SELECT * FROM arbeit_kosten WHERE arbeit_id=? ORDER BY datum, id", (arbeit["id"],)).fetchall()
    zeilen = []
    for t in termine:
        if t["status"] == "abgesagt":
            continue
        for kat, text, cent, weiter in termin_rechnung(t, satz, einst):
            zeilen.append({"kategorie": kat, "text": f"{datum_de(t['datum'])}: {text}", "cent": cent,
                           "weiter": weiter, "termin_id": t["id"]})
    for k in kosten:
        zeilen.append({"kategorie": k["kategorie"], "text": kosten_text(k), "cent": k["betrag"],
                       "weiter": bool(k["weiterberechnen"]), "termin_id": k["termin_id"], "kosten_id": k["id"]})
    namen = {"arbeitszeit": "Arbeitszeit", "anfahrt": "Anfahrt", "fahrzeit": "Fahrzeit", **KATEGORIEN}
    je_kategorie = {}
    for z in zeilen:
        e = je_kategorie.setdefault(z["kategorie"], {"name": namen.get(z["kategorie"], z["kategorie"]),
                                                    "weiter": 0, "intern": 0})
        e["weiter" if z["weiter"] else "intern"] += z["cent"]
    netto = sum(z["cent"] for z in zeilen if z["weiter"])
    prozent = steuersatz(einst)
    mwst = round(netto * prozent / 100)
    aktiv = [t for t in termine if t["status"] != "abgesagt"]
    return {"stundensatz": satz, "zeilen": zeilen, "kategorien": je_kategorie, "netto": netto,
            "intern": sum(z["cent"] for z in zeilen if not z["weiter"]), "steuersatz": prozent, "mwst": mwst,
            "brutto": netto + mwst, "geplant_min": sum(t["dauer_min"] or 0 for t in aktiv),
            "ist_min": sum(ist_minuten(t) or 0 for t in aktiv),
            "kleinunternehmer": einst.get("steuer_modus") != "regel"}


def kosten_text(k):
    name = KATEGORIEN.get(k["kategorie"], k["kategorie"])
    if k["kategorie"] == "sonstiges" and k["bezeichnung"]:
        name = k["bezeichnung"]
    elif k["bezeichnung"]:
        name += f" – {k['bezeichnung']}"
    if k["modus"] == "pauschale" and k["menge"]:
        name += f" (Pauschale, {k['menge']:g} Std. abwesend)"
    elif k["modus"] == "naechte" and k["menge"]:
        name += f" ({k['menge']:g} Nächte × {euro(k['einzel'])})"
    return (f"{datum_de(k['datum'])}: " if k["datum"] else "") + name


def kosten_betrag(einst, kategorie, modus, menge, einzel, betrag, anreisetag=False):
    """Betrag einer Nebenkosten-Position aus den Angaben im Formular."""
    if kategorie == "verpflegung" and modus == "pauschale":
        return verpflegung_pauschale(einst, menge or 0, anreisetag)
    if kategorie == "uebernachtung" and modus == "naechte":
        return round((menge or 0) * (einzel or 0))
    return betrag or 0


# ---------------------------------------------------------------------- Abfragen

def laden(con, aid):
    a = con.execute("SELECT * FROM arbeiten WHERE id=?", (aid,)).fetchone()
    if not a:
        raise EingabeFehler("Diese Arbeit gibt es nicht (mehr).")
    return a


def termine_von(con, aid):
    return con.execute("SELECT * FROM arbeit_termine WHERE arbeit_id=? ORDER BY datum, beginn", (aid,)).fetchall()


def termine_zeitraum(con, von, bis):
    return con.execute(
        "SELECT t.*, a.typ, a.titel, a.name, a.status AS arbeit_status, a.prioritaet FROM arbeit_termine t "
        "JOIN arbeiten a ON a.id=t.arbeit_id WHERE t.datum BETWEEN ? AND ? ORDER BY t.datum, t.beginn",
        (von, bis)).fetchall()


def liste(con, status=None, kunde=None, von=None, bis=None, typ=None):
    """Arbeiten mit nächstem Termin; status=None → alle offenen (offen/geplant/in Arbeit)."""
    sql = ("SELECT a.*, (SELECT MIN(t.datum || ' ' || t.beginn) FROM arbeit_termine t WHERE t.arbeit_id=a.id "
           "AND t.status NOT IN ('abgesagt', 'erledigt') AND t.datum >= ?) AS naechster FROM arbeiten a WHERE 1=1 ")
    args = [heute_datum().isoformat()]
    if status == "alle":
        pass
    elif status in STATUS:
        sql += "AND a.status=? "
        args.append(status)
    else:
        sql += f"AND a.status IN ({','.join('?' * len(OFFEN))}) "
        args += list(OFFEN)
    if typ in TYPEN:
        sql += "AND a.typ=? "
        args.append(typ)
    if kunde:
        sql += "AND (a.name LIKE ? OR a.adresse LIKE ? OR a.titel LIKE ?) "
        args += [f"%{kunde}%"] * 3
    if von or bis:  # Termine im Zeitraum, sonst angelegt im Zeitraum
        v, b = von or "0000-01-01", bis or "9999-12-31"
        sql += ("AND (EXISTS (SELECT 1 FROM arbeit_termine t WHERE t.arbeit_id=a.id AND t.datum BETWEEN ? AND ?) "
                "OR substr(a.erstellt_am, 1, 10) BETWEEN ? AND ?) ")
        args += [v, b, v, b]
    sql += "ORDER BY naechster IS NULL, naechster, CASE a.prioritaet WHEN 'dringend' THEN 0 WHEN 'hoch' THEN 1 " \
           "ELSE 2 END, a.id DESC"
    return con.execute(sql, args).fetchall()


def kandidaten(con):
    """Offene Reparaturaufträge und KVAs, die noch nicht im Kalender stehen (zum Übernehmen)."""
    auftraege = con.execute(
        "SELECT a.*, k.kundennr, k.firma, k.vorname, k.nachname, k.typ AS ktyp FROM auftraege a "
        "JOIN kunden k ON k.id=a.kunde_id WHERE a.status<>'erledigt' "
        "AND NOT EXISTS (SELECT 1 FROM arbeiten w WHERE w.auftrag_id=a.id) ORDER BY a.eingang_am DESC LIMIT 100"
    ).fetchall()
    kvas = con.execute(
        "SELECT d.*, k.kundennr, k.firma, k.vorname, k.nachname, k.typ AS ktyp FROM dokumente d "
        "JOIN kunden k ON k.id=d.kunde_id WHERE d.typ='kva' AND d.status<>'storniert' "
        "AND d.datum >= date(?, '-180 day') AND NOT EXISTS (SELECT 1 FROM arbeiten w WHERE w.dokument_id=d.id) "
        "AND NOT EXISTS (SELECT 1 FROM auftraege x WHERE x.kva_id=d.id AND x.status='erledigt') "
        "ORDER BY d.datum DESC LIMIT 100", (heute_datum().isoformat(),)).fetchall()
    return auftraege, kvas


def kunde_felder(k):
    if not k:
        return {"name": "", "adresse": "", "telefon": "", "email": ""}
    ort = " ".join(x for x in (k["plz"], k["ort"]) if x)
    return {"name": kunde_name(k), "adresse": ", ".join(x for x in (k["strasse"], ort) if x),
            "telefon": k["telefon"] or "", "email": k["email"] or ""}


def anlegen(con, werte):
    jetzt = dbm.jetzt()
    cur = con.execute(
        "INSERT INTO arbeiten (typ, kunde_id, name, adresse, telefon, email, titel, beschreibung, status, prioritaet, "
        "stundensatz, auftrag_id, dokument_id, erstellt_am, geaendert_am) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (werte.get("typ") or "reparatur", werte.get("kunde_id"), werte.get("name"), werte.get("adresse"),
         werte.get("telefon"), werte.get("email"), werte["titel"], werte.get("beschreibung"),
         werte.get("status") or "offen", werte.get("prioritaet") or None, werte.get("stundensatz"),
         werte.get("auftrag_id"), werte.get("dokument_id"), jetzt, jetzt))
    dbm.protokollieren("arbeit_angelegt", "arbeit", cur.lastrowid, {"titel": werte["titel"]}, con=con)
    return cur.lastrowid


def uebernehmen(con, auftrag_id=None, dokument_id=None):
    """Bestehenden Reparaturauftrag bzw. KVA in den Kalender übernehmen (nur lesend verknüpft)."""
    if auftrag_id:
        a = con.execute("SELECT * FROM auftraege WHERE id=?", (auftrag_id,)).fetchone()
        if not a:
            raise EingabeFehler("Auftrag nicht gefunden.")
        vorhanden = con.execute("SELECT id FROM arbeiten WHERE auftrag_id=?", (auftrag_id,)).fetchone()
        if vorhanden:
            return vorhanden[0]
        k = con.execute("SELECT * FROM kunden WHERE id=?", (a["kunde_id"],)).fetchone()
        return anlegen(con, {"typ": "reparatur", "kunde_id": a["kunde_id"], **kunde_felder(k),
                             "titel": f"{a['auftragsnr']} · {a['geraet'] or 'Reparatur'}",
                             "beschreibung": a["fehler"] or "", "auftrag_id": auftrag_id})
    d = con.execute("SELECT * FROM dokumente WHERE id=? AND typ='kva'", (dokument_id,)).fetchone()
    if not d:
        raise EingabeFehler("KVA nicht gefunden.")
    vorhanden = con.execute("SELECT id FROM arbeiten WHERE dokument_id=?", (dokument_id,)).fetchone()
    if vorhanden:
        return vorhanden[0]
    k = con.execute("SELECT * FROM kunden WHERE id=?", (d["kunde_id"],)).fetchone()
    return anlegen(con, {"typ": "kva", "kunde_id": d["kunde_id"], **kunde_felder(k),
                         "titel": f"{d['nummer'] or 'KVA-Entwurf'} · {d['betreff'] or 'Kostenvoranschlag'}",
                         "dokument_id": dokument_id})


def status_nachziehen(con, aid):
    """Erster Termin → „geplant“ (nur aus „offen“; manuelle Status bleiben)."""
    a = laden(con, aid)
    if a["status"] == "offen" and con.execute(
            "SELECT 1 FROM arbeit_termine WHERE arbeit_id=? AND status<>'abgesagt'", (aid,)).fetchone():
        con.execute("UPDATE arbeiten SET status='geplant', geaendert_am=? WHERE id=?", (dbm.jetzt(), aid))


def timer(con, tid, aktion):
    t = con.execute("SELECT * FROM arbeit_termine WHERE id=?", (tid,)).fetchone()
    if not t:
        raise EingabeFehler("Termin nicht gefunden.")
    jetzt = jetzt_dt().replace(microsecond=0)
    if aktion == "start" and not t["timer_start"]:
        con.execute("UPDATE arbeit_termine SET timer_start=?, ist_beginn=COALESCE(ist_beginn, ?) WHERE id=?",
                    (jetzt.isoformat(), jetzt.strftime("%H:%M"), tid))
        a = laden(con, t["arbeit_id"])
        if a["status"] in ("offen", "geplant"):
            con.execute("UPDATE arbeiten SET status='in_arbeit', geaendert_am=? WHERE id=?", (dbm.jetzt(), a["id"]))
    elif aktion == "stopp" and t["timer_start"]:
        bisher = t["ist_minuten"]
        if bisher is None and t["ist_beginn"] and t["ist_ende"]:
            bisher = ist_minuten({**dict(t), "timer_start": None})
        laufend = int((jetzt - datetime.fromisoformat(t["timer_start"])).total_seconds() // 60)
        con.execute("UPDATE arbeit_termine SET timer_start=NULL, ist_minuten=?, ist_ende=? WHERE id=?",
                    ((bisher or 0) + max(laufend, 0), jetzt.strftime("%H:%M"), tid))


# ---------------------------------------------------------------------- Terminvorschlag

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def wochentag(datum_iso):
    return WOCHENTAGE[date.fromisoformat(datum_iso).weekday()]


def termin_zeile(t):
    d = date.fromisoformat(t["datum"])
    return (f"{WOCHENTAGE[d.weekday()]}, {d:%d.%m.%Y}, {t['beginn']}–{ende(t)} Uhr "
            f"(ca. {dauer_text(t['dauer_min'])})" + (f" – {t['art']}" if t["art"] else ""))


def vorschlag_texte(con, arbeit, termine, einst=None):
    einst = einst or dbm.einstellungen(con)
    k = con.execute("SELECT * FROM kunden WHERE id=?", (arbeit["kunde_id"],)).fetchone() if arbeit["kunde_id"] \
        else None
    mehrere = len(termine) > 1
    werte = {
        "anrede": anrede_brief(k) if k else (f"Guten Tag {arbeit['name']}," if arbeit["name"] else "Guten Tag,"),
        "arbeit": arbeit["titel"], "beschreibung": arbeit["beschreibung"] or "", "adresse": arbeit["adresse"] or "",
        "termine": "\n".join((f"{i}) " if mehrere else "") + termin_zeile(t) for i, t in enumerate(termine, 1)),
        "termine_einleitung": "Ich kann Ihnen folgende Termine anbieten:" if mehrere else
        "Mein Terminvorschlag:",
        "termine_schluss": "Bitte geben Sie mir kurz Bescheid, welcher Termin Ihnen passt." if mehrere else
        "Bitte bestätigen Sie mir den Termin kurz – den Termin können Sie über die angehängte Kalenderdatei direkt "
        "in Ihren Kalender übernehmen.",
        "dauer": dauer_text(sum(t["dauer_min"] or 0 for t in termine[:1])),
        "firma_name": einst.get("firma_name", ""), "inhaber": einst.get("inhaber", ""),
        "firma_telefon": einst.get("telefon", ""),
    }
    if mehrere:
        werte["termine_schluss"] += " Die angehängten Kalenderdateien können Sie für den gewählten Termin nutzen."

    def ersetzen(text):
        for name, wert in werte.items():
            text = text.replace("{" + name + "}", wert)
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.replace("\n\n\n", "\n\n")

    betreff = ersetzen(einst.get("ak_vorschlag_betreff") or STANDARD_BETREFF)
    text = ersetzen(einst.get("ak_vorschlag_text") or STANDARD_TEXT).replace(".\n\n\n", ".\n\n")
    return betreff, "\n".join(z.rstrip() for z in text.split("\n")).replace("\n\n\n", "\n\n")


def _ics_text(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _falten(zeile):
    """Zeilen > 75 Bytes falten (RFC 5545)."""
    roh = zeile.encode("utf-8")
    if len(roh) <= 75:
        return zeile
    teile, aktuell = [], b""
    for zeichen in zeile:
        b = zeichen.encode("utf-8")
        if len(aktuell) + len(b) > (75 if not teile else 74):
            teile.append(aktuell.decode("utf-8"))
            aktuell = b""
        aktuell += b
    teile.append(aktuell.decode("utf-8"))
    return "\r\n ".join(teile)


def ics(t, arbeit, einst):
    """Kalenderdatei (.ics) für einen Termin – Zeiten in UTC, damit jeder Kalender richtig umrechnet."""
    start = datetime.fromisoformat(f"{t['datum']}T{t['beginn']}")
    if BERLIN:
        start = start.replace(tzinfo=BERLIN)
    start_utc = start.astimezone(timezone.utc)
    ende_utc = start_utc + timedelta(minutes=t["dauer_min"] or 60)
    domain = (einst.get("absender_email") or "rsb.local").split("@")[-1]
    firma = einst.get("firma_name") or ""
    beschreibung = "\n".join(x for x in (arbeit["beschreibung"], f"{firma} · {einst.get('telefon') or ''}") if x)
    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{_ics_text(firma) or 'RSB'}//Arbeitskalender//DE",
              "METHOD:PUBLISH", "CALSCALE:GREGORIAN", "BEGIN:VEVENT", f"UID:termin-{t['id']}@{domain}",
              f"DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}", f"DTSTART:{start_utc:%Y%m%dT%H%M%SZ}",
              f"DTEND:{ende_utc:%Y%m%dT%H%M%SZ}",
              f"SUMMARY:{_ics_text((t['art'] + ': ' if t['art'] else '') + arbeit['titel'] + (' – ' + firma if firma else ''))}",
              f"LOCATION:{_ics_text(arbeit['adresse'])}", f"DESCRIPTION:{_ics_text(beschreibung)}",
              "STATUS:TENTATIVE", "END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(_falten(z) for z in zeilen) + "\r\n").encode("utf-8")


def ics_name(t):
    return f"Termin_{t['datum']}_{t['beginn'].replace(':', '')}.ics"


def nachricht_vermerken(con, aid, kanal, an, betreff, text, termin_ids):
    jetzt = dbm.jetzt_berlin()
    con.execute("INSERT INTO arbeit_nachrichten (arbeit_id, zeitpunkt, kanal, an, betreff, text, termin_ids, benutzer) "
                "VALUES (?,?,?,?,?,?,?,?)", (aid, jetzt, kanal, an, betreff, text, json.dumps(termin_ids),
                                             dbm.aktueller_benutzer()))
    for tid in termin_ids:
        con.execute("UPDATE arbeit_termine SET vorgeschlagen_am=?, vorgeschlagen_per=?, "
                    "status=CASE WHEN status='geplant' THEN 'vorschlag' ELSE status END WHERE id=? AND arbeit_id=?",
                    (jetzt, KANAELE.get(kanal, kanal), tid, aid))
    dbm.protokollieren("arbeit_terminvorschlag", "arbeit", aid, {"kanal": kanal, "an": an, "termine": termin_ids},
                       con=con)


def bestaetigen(con, tid, andere_absagen=True):
    """Kunde hat den Termin bestätigt; übrige Vorschläge derselben Nachricht werden abgesagt."""
    t = con.execute("SELECT * FROM arbeit_termine WHERE id=?", (tid,)).fetchone()
    if not t:
        raise EingabeFehler("Termin nicht gefunden.")
    con.execute("UPDATE arbeit_termine SET status='bestaetigt', bestaetigt_am=? WHERE id=?", (dbm.jetzt_berlin(), tid))
    if andere_absagen:
        for n in con.execute("SELECT termin_ids FROM arbeit_nachrichten WHERE arbeit_id=? ORDER BY id DESC",
                             (t["arbeit_id"],)).fetchall():
            ids = json.loads(n["termin_ids"] or "[]")
            if tid in ids:
                andere = [i for i in ids if i != tid]
                if andere:
                    con.execute(f"UPDATE arbeit_termine SET status='abgesagt' WHERE status='vorschlag' AND "
                                f"id IN ({','.join('?' * len(andere))})", andere)
                break
    status_nachziehen(con, t["arbeit_id"])


def telefon_international(nummer):
    """Für WhatsApp-/SMS-Links: 0151 234 → 49151234."""
    n = "".join(c for c in (nummer or "") if c.isdigit() or c == "+")
    if n.startswith("+"):
        return n[1:]
    if n.startswith("00"):
        return n[2:]
    if n.startswith("0"):
        return "49" + n[1:]
    return n
