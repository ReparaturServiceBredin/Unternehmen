"""Geschäftslogik für Dokumente: Summen, Nummernvergabe, Festschreiben, Storno."""
import hashlib
import json
from datetime import date
from pathlib import Path

from . import db as dbm
from .hilfen import (EingabeFehler, anrede_brief, anschrift_zeilen, datum_de, euro, kunde_name,
                     platzhalter_ersetzen)

DOKUMENTTYPEN = {
    # typ: (Titel, Präfix-Einstellung)
    "rechnung": ("Rechnung", "praefix_rechnung"),
    "storno": ("Stornorechnung", "praefix_rechnung"),
}

FIRMA_FELDER = ["firma_name", "firma_zusatz", "inhaber", "strasse", "plz", "ort", "land", "telefon", "email",
                "web", "steuernummer", "ust_idnr", "bank_name", "kontoinhaber", "iban", "bic"]
LAYOUT_FELDER = ["farbe_primaer", "farbe_sekundaer", "schrift", "schriftgroesse", "logo_datei", "logo_breite_mm",
                 "logo_position", "kopfzeile_text", "fusszeile_text", "faltmarken", "girocode"]


def titel(typ):
    return DOKUMENTTYPEN.get(typ, (typ.capitalize(), None))[0]


# ---------------------------------------------------------------- Summen / Steuer

def positions_betrag(menge, einzelpreis):
    return int(round(float(menge) * int(einzelpreis)))


def summen_berechnen(positionen, steuer_modus):
    """Berechnet Netto, Steuer je Steuersatz und Brutto (alles in Cent).

    Kleinunternehmer: keine Umsatzsteuer, der Positionsbetrag ist der Endbetrag.
    Regelbesteuerung: Preise sind Nettopreise, Steuer wird je Steuersatz aufaddiert.
    """
    netto = 0
    gruppen = {}
    for p in positionen:
        betrag = positions_betrag(p["menge"], p["einzelpreis"])
        netto += betrag
        if steuer_modus == "regel":
            satz = float(p["steuersatz"] or 0)
            gruppen[satz] = gruppen.get(satz, 0) + betrag
    steuer_gruppen = []
    steuer = 0
    for satz in sorted(gruppen):
        s = int(round(gruppen[satz] * satz / 100))
        steuer += s
        steuer_gruppen.append({"satz": satz, "netto": gruppen[satz], "steuer": s})
    return {"netto": netto, "steuer": steuer, "brutto": netto + steuer, "gruppen": steuer_gruppen}


def summen_speichern(con, dok_id):
    dok = con.execute("SELECT * FROM dokumente WHERE id=?", (dok_id,)).fetchone()
    pos = con.execute("SELECT * FROM positionen WHERE dokument_id=? ORDER BY pos", (dok_id,)).fetchall()
    s = summen_berechnen(pos, dok["steuer_modus"])
    con.execute("UPDATE dokumente SET summe_netto=?, summe_steuer=?, summe_brutto=? WHERE id=?",
                (s["netto"], s["steuer"], s["brutto"], dok_id))
    return s


# ---------------------------------------------------------------- Nummern

def nummer_formatieren(fmt, praefix, jahr, nummer):
    try:
        return fmt.format(praefix=praefix, jahr=jahr, nummer=nummer)
    except (KeyError, ValueError, IndexError):
        return f"{praefix}-{jahr}-{nummer:04d}"


def naechste_nummer(con, praefix, jahr, fmt, nur_vorschau=False):
    """Vergibt die nächste fortlaufende Nummer. Muss innerhalb einer Transaktion aufgerufen werden."""
    r = con.execute("SELECT letzte_nummer, format FROM nummernkreise WHERE praefix=? AND jahr=?",
                    (praefix, jahr)).fetchone()
    neu = (r["letzte_nummer"] if r else 0) + 1
    if r:
        fmt = r["format"]  # innerhalb eines Jahres bleibt das Format gleich
    if not nur_vorschau:
        if r:
            con.execute("UPDATE nummernkreise SET letzte_nummer=? WHERE praefix=? AND jahr=?", (neu, praefix, jahr))
        else:
            con.execute("INSERT INTO nummernkreise (praefix, jahr, letzte_nummer, format) VALUES (?,?,?,?)",
                        (praefix, jahr, neu, fmt))
    return nummer_formatieren(fmt, praefix, jahr, neu)


def naechste_kundennr(con, einst):
    praefix = einst.get("praefix_kunde") or "K"
    nr = 0
    for r in con.execute("SELECT kundennr FROM kunden WHERE kundennr LIKE ?", (praefix + "-%",)):
        try:
            nr = max(nr, int(r["kundennr"].rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            pass
    return f"{praefix}-{nr + 1:04d}"


# ---------------------------------------------------------------- Platzhalter / Snapshot

def platzhalter_werte(dok, kunde, einst, nummer=None, bezug=None):
    dok = dict(dok)
    return {
        "anrede_brief": anrede_brief(kunde),
        "kunde_name": kunde_name(kunde),
        "kundennr": (dict(kunde).get("kundennr") if kunde else "") or "",
        "nummer": nummer or dok.get("nummer") or "(Entwurf)",
        "datum": datum_de(dok.get("datum")),
        "faellig_am": datum_de(dok.get("faellig_am")),
        "zahlungsziel_tage": dok.get("zahlungsziel_tage") or "",
        "betrag": euro(dok.get("summe_brutto")),
        "bezug_nummer": (bezug["nummer"] if bezug else "") or "",
        "bezug_datum": datum_de(bezug["datum"]) if bezug else "",
        "firma_name": einst.get("firma_name", ""),
        "inhaber": einst.get("inhaber", ""),
        "firma_telefon": einst.get("telefon", ""),
        "firma_web": einst.get("web", ""),
    }


def snapshot_bauen(con, dok_id, nummer=None):
    """Stellt alle Daten zusammen, die auf dem Dokument erscheinen. Wird beim Festschreiben eingefroren."""
    einst = dbm.einstellungen(con)
    dok = con.execute("SELECT * FROM dokumente WHERE id=?", (dok_id,)).fetchone()
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (dok["kunde_id"],)).fetchone() if dok["kunde_id"] else None
    bezug = con.execute("SELECT * FROM dokumente WHERE id=?", (dok["bezug_id"],)).fetchone() if dok["bezug_id"] else None
    pos = con.execute("SELECT * FROM positionen WHERE dokument_id=? ORDER BY pos", (dok_id,)).fetchall()
    s = summen_berechnen(pos, dok["steuer_modus"])
    werte = platzhalter_werte({**dict(dok), "summe_brutto": s["brutto"]}, kunde, einst, nummer, bezug)
    return {
        "version": 1,
        "typ": dok["typ"],
        "titel": titel(dok["typ"]),
        "nummer": nummer or dok["nummer"],
        "datum": dok["datum"],
        "leistungsdatum": dok["leistungsdatum"],
        "leistungsdatum_bis": dok["leistungsdatum_bis"],
        "faellig_am": dok["faellig_am"],
        "zahlungsziel_tage": dok["zahlungsziel_tage"],
        "betreff": platzhalter_ersetzen(dok["betreff"], werte),
        "einleitung": platzhalter_ersetzen(dok["einleitung"], werte),
        "schlusstext": platzhalter_ersetzen(dok["schlusstext"], werte),
        "hinweise": platzhalter_ersetzen(dok["hinweise"], werte),
        "steuer_modus": dok["steuer_modus"],
        "kleinunternehmer_hinweis": einst["kleinunternehmer_hinweis"] if dok["steuer_modus"] == "kleinunternehmer" else "",
        "zahlungsarten_text": einst["zahlungsarten_text"],
        "bezug": {"nummer": bezug["nummer"], "datum": bezug["datum"]} if bezug else None,
        "kunde": {
            "kundennr": kunde["kundennr"] if kunde else "",
            "name": kunde_name(kunde),
            "anschrift": anschrift_zeilen(kunde),
            "ust_idnr": (kunde["ust_idnr"] or "") if kunde else "",
            "typ": kunde["typ"] if kunde else "",
        },
        "firma": {k: einst.get(k, "") for k in FIRMA_FELDER},
        "layout": {k: einst.get(k) for k in LAYOUT_FELDER},
        "positionen": [
            {
                "pos": p["pos"], "bezeichnung": p["bezeichnung"], "beschreibung": p["beschreibung"] or "",
                "menge": p["menge"], "einheit": p["einheit"] or "", "einzelpreis": p["einzelpreis"],
                "steuersatz": p["steuersatz"], "betrag": positions_betrag(p["menge"], p["einzelpreis"]),
            }
            for p in pos
        ],
        "summen": s,
    }


# ---------------------------------------------------------------- Festschreiben

def _pruefen_vor_festschreiben(con, dok, einst):
    if dok["status"] != "entwurf":
        raise EingabeFehler("Das Dokument ist bereits festgeschrieben.")
    if not dok["kunde_id"]:
        raise EingabeFehler("Bitte zuerst einen Kunden auswählen.")
    anzahl = con.execute("SELECT COUNT(*) FROM positionen WHERE dokument_id=?", (dok["id"],)).fetchone()[0]
    if anzahl == 0:
        raise EingabeFehler("Das Dokument hat keine Positionen.")
    if not dok["datum"]:
        raise EingabeFehler("Bitte ein Rechnungsdatum angeben.")
    if dok["typ"] in ("rechnung",) and not dok["leistungsdatum"]:
        raise EingabeFehler("Bitte das Leistungsdatum (Datum der Reparatur) angeben.")
    if date.fromisoformat(dok["datum"]) > date.today():
        raise EingabeFehler("Das Rechnungsdatum darf nicht in der Zukunft liegen.")
    praefix = einst[DOKUMENTTYPEN[dok["typ"]][1]]
    letzte = con.execute(
        "SELECT MAX(datum) FROM dokumente WHERE status<>'entwurf' AND typ IN "
        f"({','.join('?' * len(_typen_mit_praefix(einst, praefix)))})",
        _typen_mit_praefix(einst, praefix),
    ).fetchone()[0]
    if letzte and dok["datum"] < letzte:
        raise EingabeFehler(
            f"Das Datum liegt vor dem letzten festgeschriebenen Dokument dieses Nummernkreises ({datum_de(letzte)}). "
            "Nummern und Datum müssen in derselben Reihenfolge laufen.")
    return praefix


def _typen_mit_praefix(einst, praefix):
    return [t for t, (_, key) in DOKUMENTTYPEN.items() if einst.get(key) == praefix]


def festschreiben(con, dok_id, daten_dir):
    """Vergibt die Nummer, friert den Inhalt ein, erzeugt und archiviert das PDF.

    Alles geschieht in einer Transaktion: Schlägt ein Schritt fehl, wird nichts gespeichert
    und auch keine Nummer verbraucht (lückenlose Nummernfolge).
    """
    from .pdf import pdf_erzeugen

    einst = dbm.einstellungen(con)
    with dbm.Transaktion(con):
        dok = con.execute("SELECT * FROM dokumente WHERE id=?", (dok_id,)).fetchone()
        if dok is None:
            raise EingabeFehler("Dokument nicht gefunden.")
        praefix = _pruefen_vor_festschreiben(con, dok, einst)
        jahr = int(dok["datum"][:4])
        nummer = naechste_nummer(con, praefix, jahr, einst["nummern_format"])
        summen_speichern(con, dok_id)
        snap = snapshot_bauen(con, dok_id, nummer)
        pdf = pdf_erzeugen(snap, daten_dir=daten_dir, entwurf=False)
        sha = hashlib.sha256(pdf).hexdigest()
        rel = Path("dokumente") / str(jahr) / f"{nummer}.pdf"
        ziel = Path(daten_dir) / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(pdf)
        con.execute(
            "UPDATE dokumente SET status='festgeschrieben', nummer=?, snapshot_json=?, pdf_pfad=?, pdf_sha256=?, "
            "festgeschrieben_am=?, geaendert_am=? WHERE id=?",
            (nummer, json.dumps(snap, ensure_ascii=False), rel.as_posix(), sha, dbm.jetzt(), dbm.jetzt(), dok_id),
        )
        con.execute("UPDATE kunden SET interessent=0 WHERE id=?", (dok["kunde_id"],))  # jetzt echter Kunde
        dbm.protokollieren("festgeschrieben", "dokument", dok_id,
                           {"nummer": nummer, "betrag": snap["summen"]["brutto"], "pdf_sha256": sha}, con=con)
    return nummer


def stornieren(con, dok_id, daten_dir, grund=""):
    """Erstellt eine Stornorechnung mit negativen Beträgen und schreibt sie sofort fest."""
    einst = dbm.einstellungen(con)
    orig = con.execute("SELECT * FROM dokumente WHERE id=?", (dok_id,)).fetchone()
    if orig is None or orig["status"] != "festgeschrieben" or orig["typ"] != "rechnung":
        raise EingabeFehler("Nur festgeschriebene, nicht stornierte Rechnungen können storniert werden.")
    texte = standard_texte(con, "storno")
    heute = date.today().isoformat()
    with dbm.Transaktion(con):
        cur = con.execute(
            "INSERT INTO dokumente (typ, kunde_id, datum, leistungsdatum, leistungsdatum_bis, betreff, einleitung, "
            "schlusstext, hinweise, steuer_modus, bezug_id, erstellt_am, geaendert_am) "
            "VALUES ('storno',?,?,?,?,?,?,?,?,?,?,?,?)",
            (orig["kunde_id"], heute, orig["leistungsdatum"], orig["leistungsdatum_bis"],
             f"Storno zu Rechnung {orig['nummer']}" + (f" – {grund}" if grund else ""),
             texte.get("einleitung", ""), texte.get("schluss", ""), "", orig["steuer_modus"], orig["id"],
             dbm.jetzt(), dbm.jetzt()),
        )
        neu_id = cur.lastrowid
        for p in con.execute("SELECT * FROM positionen WHERE dokument_id=? ORDER BY pos", (dok_id,)).fetchall():
            con.execute(
                "INSERT INTO positionen (dokument_id, pos, artikel_id, bezeichnung, beschreibung, menge, einheit, "
                "einzelpreis, teilekosten, steuersatz, leistungsart) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (neu_id, p["pos"], p["artikel_id"], p["bezeichnung"], p["beschreibung"], p["menge"], p["einheit"],
                 -p["einzelpreis"], -p["teilekosten"], p["steuersatz"], p["leistungsart"]),
            )
        summen_speichern(con, neu_id)
        dbm.protokollieren("storno_angelegt", "dokument", neu_id, {"zu": orig["nummer"], "grund": grund}, con=con)
    try:
        nummer = festschreiben(con, neu_id, daten_dir)
    except Exception:
        # Entwurf wieder entfernen, damit nichts Halbfertiges liegen bleibt
        with dbm.Transaktion(con):
            con.execute("DELETE FROM positionen WHERE dokument_id=?", (neu_id,))
            con.execute("DELETE FROM dokumente WHERE id=?", (neu_id,))
        raise
    with dbm.Transaktion(con):
        con.execute("UPDATE dokumente SET status='storniert', storniert_durch=?, geaendert_am=? WHERE id=?",
                    (neu_id, dbm.jetzt(), dok_id))
        dbm.protokollieren("storniert", "dokument", dok_id, {"durch": nummer}, con=con)
    return neu_id, nummer


def standard_texte(con, dokumenttyp):
    """Liefert die als Standard markierten Textbausteine je Kategorie für einen Dokumenttyp."""
    texte = {}
    for r in con.execute(
            "SELECT * FROM textbausteine WHERE standard=1 AND dokumenttyp IN (?, 'alle') "
            "ORDER BY CASE dokumenttyp WHEN 'alle' THEN 1 ELSE 0 END, id", (dokumenttyp,)):
        texte.setdefault(r["kategorie"], r["text"])
    return texte


# ---------------------------------------------------------------- Prüfung

def integritaet_pruefen(con, daten_dir):
    """Prüft PDF-Prüfsummen, Lückenlosigkeit der Nummern und die Protokollkette."""
    ergebnisse = {"pdf": [], "nummern": [], "protokoll": dbm.protokoll_pruefen(con), "anzahl_dokumente": 0}
    for d in con.execute("SELECT id, nummer, pdf_pfad, pdf_sha256 FROM dokumente WHERE status<>'entwurf'"):
        ergebnisse["anzahl_dokumente"] += 1
        pfad = Path(daten_dir) / (d["pdf_pfad"] or "")
        if not d["pdf_pfad"] or not pfad.is_file():
            ergebnisse["pdf"].append(f"{d['nummer']}: PDF-Datei fehlt.")
        elif hashlib.sha256(pfad.read_bytes()).hexdigest() != d["pdf_sha256"]:
            ergebnisse["pdf"].append(f"{d['nummer']}: PDF-Datei wurde verändert (Prüfsumme stimmt nicht).")
    vergeben = {r["nummer"] for r in con.execute("SELECT nummer FROM dokumente WHERE nummer IS NOT NULL")}
    for k in con.execute("SELECT * FROM nummernkreise ORDER BY praefix, jahr"):
        for n in range(1, k["letzte_nummer"] + 1):
            nr = nummer_formatieren(k["format"], k["praefix"], k["jahr"], n)
            if nr not in vergeben:
                ergebnisse["nummern"].append(f"Nummer {nr} wurde vergeben, das Dokument fehlt.")
    return ergebnisse
