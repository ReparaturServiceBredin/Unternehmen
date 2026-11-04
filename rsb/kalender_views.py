"""Seiten des Arbeitskalenders (eigener Blueprint „kalender“, URL-Präfix /kalender).

Logik und Berechnung: arbeitskalender.py. Bestehende Seiten werden nicht verändert; Reparaturaufträge und KVAs
werden nur gelesen und verlinkt.
"""
import json
import secrets
from calendar import Calendar
from datetime import date, timedelta
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file,
                   session, url_for)

from . import arbeitskalender as ak
from . import db as dbm
from .hilfen import EingabeFehler, cent_aus_text, heute_datum, sicherer_dateiname
from .mail import MailFehler, senden

bp = Blueprint("kalender", __name__, url_prefix="/kalender")

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]
FOTO_ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".pdf"}


def _f(name, standard=""):
    return (request.form.get(name) or standard).strip()


def _datum(text, pflicht=True):
    t = (text or "").strip()
    if not t and not pflicht:
        return None
    try:
        return date.fromisoformat(t).isoformat()
    except ValueError:
        raise EingabeFehler(f"„{text}“ ist kein gültiges Datum.")


def _zahl(text):
    t = (text or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        raise EingabeFehler(f"„{text}“ ist keine Zahl.")


def _nur_inhaber():
    if session.get("rolle") == "mitarbeiter":
        abort(403, "Dieser Bereich ist dem Inhaber vorbehalten.")


def _zurueck(aid, anker=""):
    return redirect(url_for("kalender.arbeit", aid=aid) + anker)


def _farben():
    return {"typ": ak.TYPEN, "status": ak.TERMIN_STATUS}


# ---------------------------------------------------------------------- Kalender

@bp.route("/")
def uebersicht():
    con = dbm.get_db()
    einst = dbm.einstellungen(con)
    ansicht = request.args.get("ansicht") or "woche"
    if ansicht not in ("tag", "woche", "monat"):
        ansicht = "woche"
    try:
        tag = date.fromisoformat(request.args.get("datum") or "")
    except ValueError:
        tag = heute_datum()
    if ansicht == "tag":
        von = bis = tag
        zurueck, weiter = tag - timedelta(days=1), tag + timedelta(days=1)
        titel = f"{ak.WOCHENTAGE[tag.weekday()]}, {tag:%d.%m.%Y}"
        tage = [tag]
    elif ansicht == "woche":
        von = tag - timedelta(days=tag.weekday())
        bis = von + timedelta(days=6)
        zurueck, weiter = von - timedelta(days=7), von + timedelta(days=7)
        titel = f"KW {von.isocalendar()[1]} · {von:%d.%m.} – {bis:%d.%m.%Y}"
        tage = [von + timedelta(days=i) for i in range(7)]
    else:
        wochen = Calendar().monthdatescalendar(tag.year, tag.month)
        von, bis = wochen[0][0], wochen[-1][-1]
        erster = tag.replace(day=1)
        zurueck = (erster - timedelta(days=1)).replace(day=1)
        weiter = (erster + timedelta(days=32)).replace(day=1)
        titel = f"{MONATE[tag.month - 1]} {tag.year}"
        tage = [d for w in wochen for d in w]
    termine = ak.termine_zeitraum(con, von.isoformat(), bis.isoformat())
    je_tag = {}
    for t in termine:
        je_tag.setdefault(t["datum"], []).append(t)
    beginn_h = int(einst.get("ak_tag_beginn") or 7)
    ende_h = max(int(einst.get("ak_tag_ende") or 19), beginn_h + 1)
    for t in termine:  # Stunden außerhalb des Rasters erweitern es
        h = int(t["beginn"][:2])
        beginn_h = min(beginn_h, h)
        ende_h = max(ende_h, min(24, h + 1 + (int(t["beginn"][3:]) + (t["dauer_min"] or 0)) // 60))
    return render_template("ak_kalender.html", ansicht=ansicht, tag=tag, tage=tage, je_tag=je_tag, titel=titel,
                           zurueck=zurueck, weiter=weiter, heute=heute_datum(), monat=tag.month,
                           beginn_h=beginn_h, ende_h=ende_h, ak=ak, offene=ak.liste(con)[:12])


# ---------------------------------------------------------------------- Liste / Auswertung

@bp.route("/offen")
def offen():
    con = dbm.get_db()
    einst = dbm.einstellungen(con)
    f, arbeiten = _gefiltert(con)
    zeilen = [{"a": a, "r": ak.abrechnung(con, a, einst)} for a in arbeiten]
    summe = {k: sum(z["r"][k] for z in zeilen) for k in ("geplant_min", "ist_min", "netto", "mwst", "brutto",
                                                         "intern")}
    gruppe = "woche" if request.args.get("gruppe") == "woche" else "monat"
    auswertung = ak.auswertung(con, arbeiten, gruppe, f["von"] or None, f["bis"] or None, einst)
    auftraege, kvas = ak.kandidaten(con)
    return render_template("ak_offen.html", zeilen=zeilen, summe=summe, f=f, ak=ak, auftraege=auftraege, kvas=kvas,
                           auswertung=auswertung, gruppe=gruppe)


def _gefiltert(con):
    f = {k: (request.args.get(k) or "").strip() for k in ("status", "kunde", "von", "bis", "typ")}
    return f, ak.liste(con, f["status"] or None, f["kunde"] or None, f["von"] or None, f["bis"] or None,
                       f["typ"] or None)


@bp.route("/export.csv")
def export_csv():
    con = dbm.get_db()
    _, arbeiten = _gefiltert(con)
    from flask import Response
    return Response(ak.csv_export(con, arbeiten), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=Arbeiten_{heute_datum().isoformat()}.csv"})


@bp.route("/uebernehmen", methods=["POST"])
def uebernehmen():
    con = dbm.get_db()
    with dbm.Transaktion(con):
        aid = ak.uebernehmen(con, auftrag_id=int(_f("auftrag_id") or 0) or None,
                             dokument_id=int(_f("dokument_id") or 0) or None)
    flash("In den Arbeitskalender übernommen – jetzt Termine planen.", "ok")
    return _zurueck(aid)


# ---------------------------------------------------------------------- Arbeit

def _arbeit_werte(con):
    typ = _f("typ")
    status = _f("status", "offen")
    prio = _f("prioritaet")
    if typ not in ak.TYPEN or status not in ak.STATUS or prio not in ak.PRIORITAETEN:
        raise EingabeFehler("Bitte Typ, Status und Priorität aus der Liste wählen.")
    if not _f("titel"):
        raise EingabeFehler("Bitte einen Titel für die Arbeit angeben.")
    kid = int(_f("kunde_id")) if _f("kunde_id").isdigit() else None
    if kid and not con.execute("SELECT 1 FROM kunden WHERE id=?", (kid,)).fetchone():
        kid = None
    satz = _f("stundensatz")
    return {"typ": typ, "kunde_id": kid, "name": _f("name"), "adresse": _f("adresse"), "telefon": _f("telefon"),
            "email": _f("email"), "titel": _f("titel"), "beschreibung": request.form.get("beschreibung", "").strip(),
            "status": status, "prioritaet": prio or None,
            "stundensatz": cent_aus_text(satz) if satz else None,
            "privat": 1 if typ == "frei" and request.form.get("privat") else 0}


def _kunden(con):
    return con.execute("SELECT * FROM kunden WHERE COALESCE(archiviert, 0)=0 AND anonymisiert_am IS NULL "
                       "ORDER BY COALESCE(NULLIF(firma, ''), nachname), vorname").fetchall()


@bp.route("/neu", methods=["GET", "POST"])
def neu():
    con = dbm.get_db()
    if request.method == "POST":
        with dbm.Transaktion(con):
            aid = ak.anlegen(con, _arbeit_werte(con))
        flash("Arbeit angelegt – jetzt Termine planen.", "ok")
        return _zurueck(aid, "#termine")
    vorlage = {"typ": request.args.get("typ") or "frei", "status": "offen"}
    if (request.args.get("kunde_id") or "").isdigit():
        k = con.execute("SELECT * FROM kunden WHERE id=?", (int(request.args["kunde_id"]),)).fetchone()
        if k:
            vorlage.update(kunde_id=k["id"], **ak.kunde_felder(k))
    return render_template("ak_arbeit.html", a=None, vorlage=vorlage, kunden=_kunden(con), ak=ak,
                           einst_satz=dbm.einstellung("ak_stundensatz"))


@bp.route("/<int:aid>", methods=["GET", "POST"])
def arbeit(aid):
    con = dbm.get_db()
    a = ak.laden(con, aid)
    einst = dbm.einstellungen(con)
    if request.method == "POST":
        werte = _arbeit_werte(con)
        with dbm.Transaktion(con):
            con.execute(f"UPDATE arbeiten SET {', '.join(f'{k}=?' for k in werte)}, geaendert_am=? WHERE id=?",
                        [*werte.values(), dbm.jetzt(), aid])
            dbm.protokollieren("arbeit_geaendert", "arbeit", aid, con=con)
        flash("Gespeichert.", "ok")
        return _zurueck(aid)
    termine = ak.termine_von(con, aid)
    kosten = con.execute("SELECT * FROM arbeit_kosten WHERE arbeit_id=? ORDER BY datum, id", (aid,)).fetchall()
    nachrichten = con.execute("SELECT * FROM arbeit_nachrichten WHERE arbeit_id=? ORDER BY id DESC", (aid,)).fetchall()
    auftrag = con.execute("SELECT id, auftragsnr FROM auftraege WHERE id=?", (a["auftrag_id"],)).fetchone() \
        if a["auftrag_id"] else None
    kva = con.execute("SELECT id, nummer, summe_brutto FROM dokumente WHERE id=?", (a["dokument_id"],)).fetchone() \
        if a["dokument_id"] else None
    satz = ak.stundensatz(a, einst)
    termin_pos = {t["id"]: ak.termin_rechnung(t, satz, einst) for t in termine}
    return render_template("ak_arbeit.html", a=a, vorlage=dict(a), kunden=_kunden(con), ak=ak, termine=termine,
                           kosten=kosten, nachrichten=nachrichten, auftrag=auftrag, kva=kva,
                           r=ak.abrechnung(con, a, einst), termin_pos=termin_pos, heute=heute_datum().isoformat(),
                           einst_satz=einst.get("ak_stundensatz"),
                           standard_dauer=int(einst.get("ak_standard_dauer") or 60),
                           standard_anfahrt=einst.get("ak_anfahrt") or "km",
                           nachrichten_termine={n["id"]: json.loads(n["termin_ids"] or "[]") for n in nachrichten})


@bp.route("/<int:aid>/loeschen", methods=["POST"])
def arbeit_loeschen(aid):
    con = dbm.get_db()
    a = ak.laden(con, aid)
    with dbm.Transaktion(con):
        con.execute("DELETE FROM arbeiten WHERE id=?", (aid,))
        dbm.protokollieren("arbeit_geloescht", "arbeit", aid, {"titel": a["titel"]}, con=con)
    flash("Arbeit gelöscht (verknüpfte Aufträge und KVAs bleiben unverändert).", "ok")
    return redirect(url_for("kalender.offen"))


# ---------------------------------------------------------------------- Schnell anlegen / verschieben

@bp.route("/schnell", methods=["POST"])
def schnell():
    """Schnellformular im Kalender (Doppelklick / langes Drücken): nur Titel und Typ, Rest vorbelegt."""
    con = dbm.get_db()
    dauer = ak.minuten_aus(_f("dauer")) or int(dbm.einstellung("ak_standard_dauer") or 60)
    with dbm.Transaktion(con):
        aid, tid = ak.schnell_anlegen(con, _f("titel"), _f("typ"), _datum(_f("datum")), ak.uhrzeit(_f("beginn")),
                                      dauer, privat=bool(request.form.get("privat")))
    if request.form.get("mehr"):
        return _zurueck(aid)
    flash("Eingetragen.", "ok")
    ziel = request.form.get("weiter") or ""
    return redirect(ziel if ziel.startswith("/kalender") else url_for("kalender.uebersicht"))


@bp.route("/termin/<int:tid>/verschieben", methods=["POST"])
def termin_verschieben(tid):
    """Drag & Drop: neues Datum/Uhrzeit/Dauer (JSON-Antwort für den Kalender)."""
    con = dbm.get_db()
    with dbm.Transaktion(con):
        ak.verschieben(con, tid, _datum(_f("datum")), ak.uhrzeit(_f("beginn")), int(_f("dauer") or 60))
    return jsonify(ok=True)


# ---------------------------------------------------------------------- Termine

def _termin_werte():
    dauer = ak.minuten_aus(_f("dauer"))
    return {"art": _f("art"), "datum": _datum(_f("datum")), "beginn": ak.uhrzeit(_f("beginn")),
            "dauer_min": dauer if dauer is not None else int(dbm.einstellung("ak_standard_dauer") or 60),
            "notiz": _f("notiz")}


@bp.route("/<int:aid>/termin", methods=["POST"])
def termin_neu(aid):
    con = dbm.get_db()
    ak.laden(con, aid)
    w = _termin_werte()
    with dbm.Transaktion(con):
        con.execute("INSERT INTO arbeit_termine (arbeit_id, art, datum, beginn, dauer_min, notiz, anfahrt, "
                    "erstellt_am) VALUES (?,?,?,?,?,?,?,?)",
                    (aid, w["art"], w["datum"], w["beginn"], w["dauer_min"], w["notiz"],
                     dbm.einstellung("ak_anfahrt") or "km", dbm.jetzt()))
        ak.status_nachziehen(con, aid)
        dbm.protokollieren("arbeit_termin", "arbeit", aid, {"datum": w["datum"], "beginn": w["beginn"]}, con=con)
    flash("Termin eingeplant.", "ok")
    return _zurueck(aid, "#termine")


def _termin(con, tid):
    t = con.execute("SELECT * FROM arbeit_termine WHERE id=?", (tid,)).fetchone()
    if not t:
        abort(404)
    return t


@bp.route("/termin/<int:tid>", methods=["POST"])
def termin_speichern(tid):
    """Planung, tatsächliche Zeit und Anfahrt eines Termins speichern."""
    con = dbm.get_db()
    t = _termin(con, tid)
    w = _termin_werte()
    status = _f("status", t["status"])
    if status not in ak.TERMIN_STATUS:
        raise EingabeFehler("Unbekannter Status.")
    anfahrt = _f("anfahrt")
    if anfahrt not in ak.ANFAHRT:
        anfahrt = None
    ist_beginn, ist_ende = ak.uhrzeit(_f("ist_beginn"), False), ak.uhrzeit(_f("ist_ende"), False)
    ist_min = ak.minuten_aus(_f("ist_dauer"))
    if ist_min is None and ist_beginn and ist_ende and not t["timer_start"]:
        ist_min = ak.ist_minuten({"ist_minuten": None, "ist_beginn": ist_beginn, "ist_ende": ist_ende,
                                  "timer_start": None})
    with dbm.Transaktion(con):
        con.execute(
            "UPDATE arbeit_termine SET art=?, datum=?, beginn=?, dauer_min=?, notiz=?, status=?, ist_beginn=?, "
            "ist_ende=?, ist_minuten=?, anfahrt=?, km=?, fahrzeit_min=?, fahrzeit_berechnen=?, anfahrt_weiter=?, "
            "bestaetigt_am=CASE WHEN ?='bestaetigt' THEN COALESCE(bestaetigt_am, ?) ELSE bestaetigt_am END "
            "WHERE id=?",
            (w["art"], w["datum"], w["beginn"], w["dauer_min"], w["notiz"], status, ist_beginn, ist_ende, ist_min,
             anfahrt, _zahl(_f("km")), ak.minuten_aus(_f("fahrzeit")), 1 if request.form.get("fahrzeit_berechnen")
             else 0, 1 if request.form.get("anfahrt_weiter") else 0, status, dbm.jetzt_berlin(), tid))
        ak.status_nachziehen(con, t["arbeit_id"])
        if ist_min and status in ("geplant", "vorschlag", "bestaetigt") and not request.form.get("status"):
            ak.termin_erledigt(con, tid)  # Zeit erfasst → erledigt (wenn der Status nicht von Hand gewählt wurde)
        dbm.protokollieren("arbeit_termin_geaendert", "arbeit", t["arbeit_id"], {"termin": tid}, con=con)
    flash("Termin gespeichert.", "ok")
    return _zurueck(t["arbeit_id"], f"#termin-{tid}")


@bp.route("/termin/<int:tid>/timer", methods=["POST"])
def termin_timer(tid):
    con = dbm.get_db()
    t = _termin(con, tid)
    with dbm.Transaktion(con):
        ak.timer(con, tid, _f("aktion"))
    return _zurueck(t["arbeit_id"], f"#termin-{tid}")


@bp.route("/termin/<int:tid>/bestaetigt", methods=["POST"])
def termin_bestaetigt(tid):
    con = dbm.get_db()
    t = _termin(con, tid)
    with dbm.Transaktion(con):
        if request.form.get("zuruecknehmen"):
            con.execute("UPDATE arbeit_termine SET status=CASE WHEN vorgeschlagen_am IS NOT NULL THEN 'vorschlag' "
                        "ELSE 'geplant' END, bestaetigt_am=NULL WHERE id=?", (tid,))
        else:
            ak.bestaetigen(con, tid, andere_absagen=bool(request.form.get("andere_absagen")))
        dbm.protokollieren("arbeit_termin_bestaetigt", "arbeit", t["arbeit_id"], {"termin": tid}, con=con)
    return _zurueck(t["arbeit_id"], f"#termin-{tid}")


@bp.route("/termin/<int:tid>/loeschen", methods=["POST"])
def termin_loeschen(tid):
    con = dbm.get_db()
    t = _termin(con, tid)
    with dbm.Transaktion(con):
        con.execute("DELETE FROM arbeit_termine WHERE id=?", (tid,))
        dbm.protokollieren("arbeit_termin_geloescht", "arbeit", t["arbeit_id"], {"datum": t["datum"]}, con=con)
    flash("Termin gelöscht.", "ok")
    return _zurueck(t["arbeit_id"], "#termine")


@bp.route("/termin/<int:tid>.ics")
def termin_ics(tid):
    con = dbm.get_db()
    t = _termin(con, tid)
    import io
    daten = ak.ics(t, ak.laden(con, t["arbeit_id"]), dbm.einstellungen(con))
    return send_file(io.BytesIO(daten), mimetype="text/calendar", as_attachment=True, download_name=ak.ics_name(t))


# ---------------------------------------------------------------------- Nebenkosten

def _foto_ordner():
    ordner = Path(current_app.config["DATEN"]) / "belege" / "arbeitskalender"
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


@bp.route("/<int:aid>/kosten", methods=["POST"])
def kosten_neu(aid):
    con = dbm.get_db()
    ak.laden(con, aid)
    einst = dbm.einstellungen(con)
    kat = _f("kategorie")
    if kat not in ak.KATEGORIEN:
        raise EingabeFehler("Bitte eine Kategorie wählen.")
    modus = _f("modus") or "beleg"
    menge = _zahl(_f("abwesenheit") if kat == "verpflegung" else _f("naechte"))
    einzel = cent_aus_text(_f("preis_nacht")) if kat == "uebernachtung" and _f("preis_nacht") else None
    betrag = ak.kosten_betrag(einst, kat, modus, menge, einzel, cent_aus_text(_f("betrag")),
                              anreisetag=bool(request.form.get("anreisetag")))
    if kat == "verpflegung" and modus == "pauschale" and menge is None:
        raise EingabeFehler("Für die Verpflegungspauschale bitte die Abwesenheit in Stunden angeben.")
    if kat == "uebernachtung" and modus == "naechte" and not (menge and einzel):
        raise EingabeFehler("Bitte Anzahl Nächte und Preis je Nacht angeben.")
    if betrag <= 0 and not (kat == "verpflegung" and modus == "pauschale"):
        raise EingabeFehler("Bitte einen Betrag angeben.")
    if kat == "sonstiges" and not _f("bezeichnung"):
        raise EingabeFehler("Bitte bei „Sonstiges“ eine Bezeichnung angeben.")
    tid = int(_f("termin_id")) if _f("termin_id").isdigit() else None
    datei = request.files.get("foto")
    foto = None
    if datei and datei.filename:
        endung = Path(datei.filename).suffix.lower()
        if endung not in FOTO_ENDUNGEN:
            raise EingabeFehler("Belegfoto bitte als JPG, PNG, WEBP, HEIC oder PDF.")
        foto = f"{aid}_{secrets.token_hex(6)}_{sicherer_dateiname(Path(datei.filename).stem)[:40]}{endung}"
        datei.save(_foto_ordner() / foto)
    with dbm.Transaktion(con):
        con.execute(
            "INSERT INTO arbeit_kosten (arbeit_id, termin_id, kategorie, bezeichnung, datum, modus, menge, einzel, "
            "betrag, weiterberechnen, notiz, foto, erstellt_am) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (aid, tid, kat, _f("bezeichnung"), _datum(_f("datum"), False), modus if kat in ("verpflegung",
             "uebernachtung") else "beleg", menge, einzel, betrag, 1 if request.form.get("weiterberechnen") else 0,
             _f("notiz"), foto, dbm.jetzt()))
        dbm.protokollieren("arbeit_kosten", "arbeit", aid, {"kategorie": kat, "betrag": betrag}, con=con)
    flash("Kosten erfasst.", "ok")
    return _zurueck(aid, "#kosten")


@bp.route("/kosten/<int:kid>/loeschen", methods=["POST"])
def kosten_loeschen(kid):
    con = dbm.get_db()
    k = con.execute("SELECT * FROM arbeit_kosten WHERE id=?", (kid,)).fetchone() or abort(404)
    with dbm.Transaktion(con):
        con.execute("DELETE FROM arbeit_kosten WHERE id=?", (kid,))
        dbm.protokollieren("arbeit_kosten_geloescht", "arbeit", k["arbeit_id"], {"betrag": k["betrag"]}, con=con)
    if k["foto"]:
        (_foto_ordner() / k["foto"]).unlink(missing_ok=True)
    return _zurueck(k["arbeit_id"], "#kosten")


@bp.route("/kosten/<int:kid>/foto")
def kosten_foto(kid):
    con = dbm.get_db()
    k = con.execute("SELECT foto FROM arbeit_kosten WHERE id=?", (kid,)).fetchone()
    if not k or not k["foto"] or not (_foto_ordner() / k["foto"]).is_file():
        abort(404)
    return send_file(_foto_ordner() / Path(k["foto"]).name)


# ---------------------------------------------------------------------- Terminvorschlag

@bp.route("/<int:aid>/vorschlag", methods=["GET", "POST"])
def vorschlag(aid):
    con = dbm.get_db()
    a = ak.laden(con, aid)
    einst = dbm.einstellungen(con)
    alle = [t for t in ak.termine_von(con, aid) if t["status"] in ("geplant", "vorschlag", "bestaetigt")]
    if request.method == "POST":
        ids = [int(x) for x in request.form.getlist("termin") if x.isdigit()]
        gewaehlt = [t for t in alle if t["id"] in ids]
        an, betreff, text = _f("an"), _f("betreff"), request.form.get("text", "").strip()
        if not gewaehlt:
            raise EingabeFehler("Bitte mindestens einen Termin auswählen.")
        if not an or "@" not in an or not betreff or not text:
            raise EingabeFehler("Bitte E-Mail-Adresse, Betreff und Text angeben.")
        anhaenge = [(ak.ics(t, a, einst), ak.ics_name(t)) for t in gewaehlt]
        try:
            hinweis = senden(con, None, an, betreff, text, weitere=anhaenge)
        except MailFehler as e:
            flash(f"E-Mail wurde NICHT gesendet: {e}", "fehler")
            return render_template("ak_vorschlag.html", a=a, termine=alle, gewaehlt=ids, an=an, betreff=betreff,
                                   text=text, ak=ak, telefon=ak.telefon_international(a["telefon"]),
                                   smtp_ok=bool(einst.get("smtp_host")))
        with dbm.Transaktion(con):
            ak.nachricht_vermerken(con, aid, "email", an, betreff, text, ids)
        flash(f"Terminvorschlag an {an} gesendet ({len(anhaenge)} Kalenderdatei{'en' if len(anhaenge) > 1 else ''}).",
              "ok")
        if hinweis:
            flash(hinweis, "warnung")
        return _zurueck(aid, "#termine")
    ids = [int(x) for x in request.args.getlist("termin") if x.isdigit()] or \
        [t["id"] for t in alle if t["status"] == "geplant" and t["datum"] >= heute_datum().isoformat()]
    gewaehlt = [t for t in alle if t["id"] in ids]
    betreff, text = ak.vorschlag_texte(con, a, gewaehlt, einst) if gewaehlt else ("", "")
    return render_template("ak_vorschlag.html", a=a, termine=alle, gewaehlt=ids, an=a["email"] or "",
                           betreff=betreff, text=text, ak=ak, telefon=ak.telefon_international(a["telefon"]),
                           smtp_ok=bool(einst.get("smtp_host")))


@bp.route("/<int:aid>/vorschlag/vermerken", methods=["POST"])
def vorschlag_vermerken(aid):
    """WhatsApp/SMS/kopiert: Versand passiert außerhalb des Programms – hier nur vermerken."""
    con = dbm.get_db()
    ak.laden(con, aid)
    kanal = _f("kanal")
    if kanal not in ("whatsapp", "sms", "kopiert"):
        raise EingabeFehler("Unbekannter Weg.")
    ids = [int(x) for x in request.form.getlist("termin") if x.isdigit()]
    with dbm.Transaktion(con):
        ak.nachricht_vermerken(con, aid, kanal, _f("an"), _f("betreff"), request.form.get("text", ""), ids)
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    flash(f"Als gesendet vermerkt ({ak.KANAELE[kanal]}).", "ok")
    return _zurueck(aid, "#termine")


@bp.route("/<int:aid>/vorschlag/text")
def vorschlag_text(aid):
    """Text für die gewählten Termine neu erzeugen (Auswahl im Formular geändert)."""
    con = dbm.get_db()
    a = ak.laden(con, aid)
    ids = [int(x) for x in request.args.getlist("termin") if x.isdigit()]
    gewaehlt = [t for t in ak.termine_von(con, aid) if t["id"] in ids]
    betreff, text = ak.vorschlag_texte(con, a, gewaehlt) if gewaehlt else ("", "")
    return jsonify(betreff=betreff, text=text)


# ---------------------------------------------------------------------- Einstellungen

GELD = ["ak_stundensatz", "ak_km_satz", "ak_anfahrt_pauschale", "ak_fahrzeit_satz", "ak_verpflegung_8h",
        "ak_verpflegung_24h", "ak_verpflegung_anreise"]


@bp.route("/einstellungen", methods=["GET", "POST"])
def einstellungen():
    _nur_inhaber()
    con = dbm.get_db()
    if request.method == "POST":
        werte = {k: cent_aus_text(_f(k)) for k in GELD}
        if any(v < 0 for v in werte.values()):
            raise EingabeFehler("Sätze dürfen nicht negativ sein.")
        anfahrt = _f("ak_anfahrt")
        werte["ak_anfahrt"] = anfahrt if anfahrt in ak.ANFAHRT else "km"
        for k, lo, hi in (("ak_standard_dauer", 5, 24 * 60), ("ak_tag_beginn", 0, 23), ("ak_tag_ende", 1, 24)):
            try:
                werte[k] = max(lo, min(hi, int(_f(k))))
            except ValueError:
                raise EingabeFehler("Bitte ganze Zahlen für Dauer und Kalenderzeiten angeben.")
        if _f("steuer_modus") in ("regel", "kleinunternehmer"):  # gilt fürs ganze Programm (Rechnung & Steuer)
            werte["steuer_modus"] = _f("steuer_modus")
        werte["ak_vorschlag_betreff"] = _f("ak_vorschlag_betreff") or ak.STANDARD_BETREFF
        werte["ak_vorschlag_text"] = request.form.get("ak_vorschlag_text", "").strip() or ak.STANDARD_TEXT
        with dbm.Transaktion(con):
            dbm.einstellungen_speichern(werte, con)
            dbm.protokollieren("einstellungen_gespeichert", "einstellungen", None, {"bereich": "arbeitskalender"},
                               con=con)
        flash("Einstellungen gespeichert.", "ok")
        return redirect(url_for("kalender.einstellungen"))
    return render_template("ak_einstellungen.html", ak=ak, geld=GELD)
