"""Alle Seiten der Weboberfläche."""
import json
import re
from datetime import date
from pathlib import Path

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, session,
                   url_for)
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

from . import db as dbm
from . import logik
from .backup import backup_erstellen
from .hilfen import (EingabeFehler, cent_aus_text, euro, heute, kunde_name, platzhalter_ersetzen, plus_tage,
                     zahl_aus_text)
from .mail import MailFehler, senden
from .pdf import SCHRIFTEN, pdf_erzeugen
from .sicherheit import verschluesseln
from .textbausteine_standard import PLATZHALTER_HILFE

bp = Blueprint("main", __name__)


def daten_dir():
    return current_app.config["DATEN"]


def _f(name, standard=""):
    return (request.form.get(name) or standard).strip()


# ====================================================================== Anmeldung

@bp.route("/einrichten", methods=["GET", "POST"])
def einrichten():
    if dbm.einstellung("passwort_hash"):
        return redirect(url_for("main.login"))
    if request.method == "POST":
        pw, pw2 = request.form.get("passwort", ""), request.form.get("passwort2", "")
        if len(pw) < 8:
            flash("Das Passwort muss mindestens 8 Zeichen lang sein.", "fehler")
        elif pw != pw2:
            flash("Die beiden Passwörter stimmen nicht überein.", "fehler")
        else:
            con = dbm.get_db()
            with dbm.Transaktion(con):
                dbm.einstellungen_speichern({"passwort_hash": generate_password_hash(pw)}, con)
                dbm.protokollieren("passwort_eingerichtet", "system", con=con)
            session.clear()
            session["angemeldet"] = True
            session["benutzer"] = "inhaber"
            session.permanent = True
            flash("Willkommen! Bitte tragen Sie zuerst Ihre Firmendaten ein.", "ok")
            return redirect(url_for("main.einstellungen"))
    return render_template("einrichten.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if check_password_hash(dbm.einstellung("passwort_hash") or "", request.form.get("passwort", "")):
            session.clear()
            session["angemeldet"] = True
            session["benutzer"] = "inhaber"
            session.permanent = True
            weiter = request.args.get("weiter") or ""
            return redirect(weiter if weiter.startswith("/") and not weiter.startswith("//") else url_for("main.start"))
        con = dbm.get_db()
        with dbm.Transaktion(con):
            dbm.protokollieren("anmeldung_fehlgeschlagen", "system", con=con)
        flash("Das Passwort ist falsch.", "fehler")
    return render_template("login.html")


@bp.route("/abmelden", methods=["POST"])
def abmelden():
    session.clear()
    return redirect(url_for("main.login"))


# ====================================================================== Start

@bp.route("/")
def start():
    con = dbm.get_db()
    jahr = date.today().year

    def umsatz(j):
        return con.execute(
            "SELECT COALESCE(SUM(summe_brutto),0) FROM dokumente WHERE status<>'entwurf' "
            "AND typ IN ('rechnung','storno') AND substr(datum,1,4)=?", (str(j),)).fetchone()[0]

    zahlen = {
        "kunden": con.execute("SELECT COUNT(*) FROM kunden WHERE archiviert=0").fetchone()[0],
        "entwuerfe": con.execute("SELECT COUNT(*) FROM dokumente WHERE status='entwurf'").fetchone()[0],
        "umsatz_jahr": umsatz(jahr),
        "umsatz_vorjahr": umsatz(jahr - 1),
        "offen": con.execute(
            "SELECT COALESCE(SUM(summe_brutto - bezahlt_betrag),0) FROM dokumente "
            "WHERE status='festgeschrieben' AND typ='rechnung'").fetchone()[0],
    }
    zahlen["anfragen"] = con.execute("SELECT COUNT(*) FROM anfragen WHERE status='neu' AND einstufung<>'spam'"
                                     ).fetchone()[0]
    letzte = con.execute(
        "SELECT d.*, k.firma, k.vorname, k.nachname, k.typ AS ktyp FROM dokumente d "
        "LEFT JOIN kunden k ON k.id=d.kunde_id ORDER BY d.geaendert_am DESC LIMIT 8").fetchall()
    return render_template("start.html", zahlen=zahlen, letzte=letzte, jahr=jahr)


# ====================================================================== Kunden

@bp.route("/kunden")
def kunden():
    q = request.args.get("q", "").strip()
    archiv = request.args.get("archiv") == "1"
    nur_interessenten = request.args.get("interessenten") == "1"
    sql = "SELECT * FROM kunden WHERE archiviert=?" + (" AND interessent=1" if nur_interessenten else "")
    args = [1 if archiv else 0]
    if q:
        sql += (" AND (kundennr LIKE ? OR firma LIKE ? OR vorname LIKE ? OR nachname LIKE ? OR email LIKE ? "
                "OR ort LIKE ? OR telefon LIKE ?)")
        args += [f"%{q}%"] * 7
    sql += " ORDER BY COALESCE(NULLIF(firma,''), nachname), vorname"
    return render_template("kunden.html", kunden=dbm.get_db().execute(sql, args).fetchall(), q=q, archiv=archiv,
                           nur_interessenten=nur_interessenten)


@bp.route("/kunden/neu", methods=["GET", "POST"])
@bp.route("/kunden/<int:kid>", methods=["GET", "POST"])
def kunde(kid=None):
    con = dbm.get_db()
    k = con.execute("SELECT * FROM kunden WHERE id=?", (kid,)).fetchone() if kid else None
    if kid and not k:
        abort(404)
    if request.method == "POST":
        felder = {f: _f(f) for f in ("typ", "firma", "anrede", "vorname", "nachname", "strasse", "plz", "ort", "land",
                                     "email", "telefon", "ust_idnr", "notizen")}
        if felder["typ"] not in ("privat", "firma"):
            felder["typ"] = "privat"
        if not (felder["firma"] or felder["nachname"]):
            raise EingabeFehler("Bitte mindestens Nachname oder Firma angeben.")
        ziel = _f("zahlungsziel_tage")
        felder["zahlungsziel_tage"] = int(ziel) if ziel.isdigit() else None
        felder["interessent"] = 1 if request.form.get("interessent") else 0
        with dbm.Transaktion(con):
            if k:
                con.execute(f"UPDATE kunden SET {', '.join(f'{f}=?' for f in felder)}, geaendert_am=? WHERE id=?",
                            [*felder.values(), dbm.jetzt(), kid])
                dbm.protokollieren("kunde_geaendert", "kunde", kid, con=con)
            else:
                nr = logik.naechste_kundennr(con, dbm.einstellungen(con))
                cur = con.execute(
                    f"INSERT INTO kunden (kundennr, {', '.join(felder)}, erstellt_am, geaendert_am) "
                    f"VALUES (?, {', '.join('?' * len(felder))}, ?, ?)",
                    [nr, *felder.values(), dbm.jetzt(), dbm.jetzt()])
                kid = cur.lastrowid
                dbm.protokollieren("kunde_angelegt", "kunde", kid, {"kundennr": nr}, con=con)
        flash("Kunde gespeichert.", "ok")
        if request.form.get("danach") == "rechnung":
            return redirect(url_for("main.dokument_neu", kunde_id=kid))
        return redirect(url_for("main.kunde", kid=kid))
    dokumente = con.execute("SELECT * FROM dokumente WHERE kunde_id=? ORDER BY datum DESC, id DESC",
                            (kid,)).fetchall() if kid else []
    kunden_anfragen = con.execute("SELECT * FROM anfragen WHERE kunde_id=? ORDER BY eingang_am DESC",
                                  (kid,)).fetchall() if kid else []
    return render_template("kunde.html", k=k, dokumente=dokumente, anfragen=kunden_anfragen)


@bp.route("/kunden/<int:kid>/archivieren", methods=["POST"])
def kunde_archivieren(kid):
    con = dbm.get_db()
    wert = 0 if request.form.get("zurueck") else 1
    with dbm.Transaktion(con):
        con.execute("UPDATE kunden SET archiviert=?, geaendert_am=? WHERE id=?", (wert, dbm.jetzt(), kid))
        dbm.protokollieren("kunde_archiviert" if wert else "kunde_reaktiviert", "kunde", kid, con=con)
    flash("Kunde archiviert." if wert else "Kunde wieder aktiv.", "ok")
    return redirect(url_for("main.kunde", kid=kid))


@bp.route("/kunden/<int:kid>/loeschen", methods=["POST"])
def kunde_loeschen(kid):
    con = dbm.get_db()
    if con.execute("SELECT 1 FROM dokumente WHERE kunde_id=? AND status<>'entwurf'", (kid,)).fetchone():
        raise EingabeFehler("Dieser Kunde hat festgeschriebene Dokumente und muss wegen der Aufbewahrungspflicht "
                            "erhalten bleiben. Sie können ihn stattdessen archivieren.")
    with dbm.Transaktion(con):
        for d in con.execute("SELECT id FROM dokumente WHERE kunde_id=?", (kid,)).fetchall():
            con.execute("DELETE FROM positionen WHERE dokument_id=?", (d["id"],))
            con.execute("DELETE FROM dokumente WHERE id=?", (d["id"],))
        con.execute("DELETE FROM anfragen WHERE kunde_id=?", (kid,))
        con.execute("DELETE FROM kunden WHERE id=?", (kid,))
        dbm.protokollieren("kunde_geloescht", "kunde", kid, con=con)
    flash("Kunde gelöscht.", "ok")
    return redirect(url_for("main.kunden"))


# ====================================================================== Leistungen & Artikel

def _leistungsarten():
    return [x.strip() for x in (dbm.einstellung("leistungsarten") or "").split(",") if x.strip()]


@bp.route("/artikel")
def artikel_liste():
    q = request.args.get("q", "").strip()
    sql, args = "SELECT * FROM artikel WHERE 1=1", []
    if q:
        sql += " AND (name LIKE ? OR artikelnr LIKE ? OR leistungsart LIKE ? OR beschreibung LIKE ?)"
        args += [f"%{q}%"] * 4
    sql += " ORDER BY aktiv DESC, leistungsart, name"
    return render_template("artikel_liste.html", artikel=dbm.get_db().execute(sql, args).fetchall(), q=q)


@bp.route("/artikel/neu", methods=["GET", "POST"])
@bp.route("/artikel/<int:aid>", methods=["GET", "POST"])
def artikel(aid=None):
    con = dbm.get_db()
    a = con.execute("SELECT * FROM artikel WHERE id=?", (aid,)).fetchone() if aid else None
    if aid and not a:
        abort(404)
    if request.method == "POST":
        if not _f("name"):
            raise EingabeFehler("Bitte eine Bezeichnung angeben.")
        teile = cent_aus_text(_f("teilekosten"))
        aufschlag = _f("aufschlag_prozent")
        aufschlag = zahl_aus_text(aufschlag) if aufschlag else None
        preis = cent_aus_text(_f("preis"), leer=None)
        if preis is None:
            if aufschlag is None:
                raise EingabeFehler("Bitte einen Verkaufspreis oder Teilekosten mit Aufschlag angeben.")
            preis = int(round(teile * (1 + aufschlag / 100)))
        felder = {
            "artikelnr": _f("artikelnr"), "name": _f("name"), "beschreibung": _f("beschreibung"),
            "leistungsart": _f("leistungsart"), "typ": _f("typ") if _f("typ") in ("leistung", "material") else "leistung",
            "einheit": _f("einheit", "Stk."), "preis": preis, "teilekosten": teile, "aufschlag_prozent": aufschlag,
            "steuersatz": zahl_aus_text(_f("steuersatz"), 19), "aktiv": 1 if request.form.get("aktiv") else 0,
        }
        with dbm.Transaktion(con):
            if a:
                con.execute(f"UPDATE artikel SET {', '.join(f'{f}=?' for f in felder)}, geaendert_am=? WHERE id=?",
                            [*felder.values(), dbm.jetzt(), aid])
                dbm.protokollieren("artikel_geaendert", "artikel", aid, con=con)
            else:
                cur = con.execute(f"INSERT INTO artikel ({', '.join(felder)}, erstellt_am, geaendert_am) "
                                  f"VALUES ({', '.join('?' * len(felder))}, ?, ?)",
                                  [*felder.values(), dbm.jetzt(), dbm.jetzt()])
                aid = cur.lastrowid
                dbm.protokollieren("artikel_angelegt", "artikel", aid, con=con)
        flash("Leistung/Artikel gespeichert.", "ok")
        return redirect(url_for("main.artikel_liste"))
    return render_template("artikel.html", a=a, leistungsarten=_leistungsarten())


@bp.route("/artikel/<int:aid>/loeschen", methods=["POST"])
def artikel_loeschen(aid):
    con = dbm.get_db()
    with dbm.Transaktion(con):
        if con.execute("SELECT 1 FROM positionen WHERE artikel_id=?", (aid,)).fetchone():
            con.execute("UPDATE artikel SET aktiv=0, geaendert_am=? WHERE id=?", (dbm.jetzt(), aid))
            flash("Der Artikel wird in Dokumenten verwendet und wurde deshalb nur deaktiviert.", "info")
        else:
            con.execute("DELETE FROM artikel WHERE id=?", (aid,))
            flash("Artikel gelöscht.", "ok")
        dbm.protokollieren("artikel_geloescht", "artikel", aid, con=con)
    return redirect(url_for("main.artikel_liste"))


# ====================================================================== Dokumente

@bp.route("/dokumente")
def dokumente():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    sql = ("SELECT d.*, k.firma, k.vorname, k.nachname, k.typ AS ktyp FROM dokumente d "
           "LEFT JOIN kunden k ON k.id=d.kunde_id WHERE 1=1")
    args = []
    if status:
        sql += " AND d.status=?"
        args.append(status)
    if q:
        sql += " AND (d.nummer LIKE ? OR d.betreff LIKE ? OR k.firma LIKE ? OR k.nachname LIKE ?)"
        args += [f"%{q}%"] * 4
    sql += " ORDER BY CASE d.status WHEN 'entwurf' THEN 0 ELSE 1 END, d.datum DESC, d.id DESC"
    return render_template("dokumente.html", dokumente=dbm.get_db().execute(sql, args).fetchall(),
                           status=status, q=q)


def _zahlungsziel(einst, kunde):
    if kunde and kunde["zahlungsziel_tage"] is not None:
        return kunde["zahlungsziel_tage"]
    if kunde and kunde["typ"] == "firma":
        return int(einst["zahlungsziel_firma"])
    return int(einst["zahlungsziel_privat"])


@bp.route("/dokumente/neu")
def dokument_neu():
    con = dbm.get_db()
    einst = dbm.einstellungen(con)
    typ = request.args.get("typ", "rechnung")
    if typ not in ("rechnung",):
        abort(400)
    kid = request.args.get("kunde_id", type=int)
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (kid,)).fetchone() if kid else None
    texte = logik.standard_texte(con, typ)
    ziel = _zahlungsziel(einst, kunde)
    with dbm.Transaktion(con):
        cur = con.execute(
            "INSERT INTO dokumente (typ, kunde_id, datum, leistungsdatum, zahlungsziel_tage, faellig_am, einleitung, "
            "schlusstext, hinweise, steuer_modus, erstellt_am, geaendert_am) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (typ, kunde["id"] if kunde else None, heute(), heute(), ziel, plus_tage(heute(), ziel),
             texte.get("einleitung", ""), texte.get("schluss", ""), texte.get("hinweis", ""),
             einst["steuer_modus"], dbm.jetzt(), dbm.jetzt()))
        dbm.protokollieren("entwurf_angelegt", "dokument", cur.lastrowid, {"typ": typ}, con=con)
    return redirect(url_for("main.dokument", did=cur.lastrowid))


def _dokument_laden(did):
    d = dbm.get_db().execute("SELECT * FROM dokumente WHERE id=?", (did,)).fetchone()
    if not d:
        abort(404)
    return d


@bp.route("/dokumente/<int:did>", methods=["GET", "POST"])
def dokument(did):
    con = dbm.get_db()
    d = _dokument_laden(did)
    einst = dbm.einstellungen(con)
    if request.method == "POST":
        if d["status"] != "entwurf":
            raise EingabeFehler("Festgeschriebene Dokumente können nicht mehr bearbeitet werden.")
        _entwurf_speichern(con, d, einst)
        aktion = request.form.get("aktion")
        if aktion == "vorschau":
            return redirect(url_for("main.dokument", did=did, vorschau=1))
        if aktion == "festschreiben":
            nummer = logik.festschreiben(con, did, daten_dir())
            flash(f"Rechnung {nummer} wurde festgeschrieben und archiviert.", "ok")
            return redirect(url_for("main.dokument", did=did))
        flash("Entwurf gespeichert.", "ok")
        return redirect(url_for("main.dokument", did=did))

    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (d["kunde_id"],)).fetchone() if d["kunde_id"] else None
    if d["status"] != "entwurf":
        snap = json.loads(d["snapshot_json"])
        versand = con.execute("SELECT * FROM versandprotokoll WHERE dokument_id=? ORDER BY id DESC", (did,)).fetchall()
        bezug = con.execute("SELECT id, nummer FROM dokumente WHERE id=?", (d["bezug_id"],)).fetchone()
        storno = con.execute("SELECT id, nummer FROM dokumente WHERE id=?", (d["storniert_durch"],)).fetchone()
        return render_template("dokument_ansicht.html", d=d, snap=snap, kunde=kunde, versand=versand,
                               bezug=bezug, storno=storno)
    positionen = con.execute("SELECT * FROM positionen WHERE dokument_id=? ORDER BY pos", (did,)).fetchall()
    kunden_liste = con.execute("SELECT * FROM kunden WHERE archiviert=0 OR id=? "
                               "ORDER BY COALESCE(NULLIF(firma,''), nachname), vorname", (d["kunde_id"],)).fetchall()
    artikel_liste = [dict(a) for a in con.execute("SELECT * FROM artikel WHERE aktiv=1 ORDER BY leistungsart, name")]
    bausteine = [dict(t) for t in con.execute(
        "SELECT * FROM textbausteine WHERE kategorie IN ('einleitung','schluss','hinweis') "
        "AND dokumenttyp IN (?, 'alle') ORDER BY kategorie, name", (d["typ"],))]
    summen = logik.summen_berechnen(positionen, einst["steuer_modus"])
    return render_template("dokument_bearbeiten.html", d=d, kunde=kunde, positionen=positionen,
                           kunden=kunden_liste, artikel=artikel_liste, bausteine=bausteine, summen=summen,
                           leistungsarten=_leistungsarten(), titel=logik.titel(d["typ"]),
                           vorschau=request.args.get("vorschau"))


def _entwurf_speichern(con, d, einst):
    kid = request.form.get("kunde_id", type=int)
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (kid,)).fetchone() if kid else None
    datum = _f("datum") or heute()
    ziel = _f("zahlungsziel_tage")
    ziel = int(ziel) if ziel.isdigit() else _zahlungsziel(einst, kunde)
    try:
        faellig = plus_tage(datum, ziel)
        for feld in ("leistungsdatum", "leistungsdatum_bis"):
            if _f(feld):
                date.fromisoformat(_f(feld))
    except ValueError:
        raise EingabeFehler("Bitte ein gültiges Datum eingeben.")
    f = request.form
    zeilen = zip(f.getlist("p_bezeichnung"), f.getlist("p_beschreibung"), f.getlist("p_menge"),
                 f.getlist("p_einheit"), f.getlist("p_preis"), f.getlist("p_teilekosten"),
                 f.getlist("p_steuersatz"), f.getlist("p_leistungsart"), f.getlist("p_artikel_id"))
    positionen = []
    for bez, beschr, menge, einheit, preis, teile, satz, art, aid in zeilen:
        if not bez.strip():
            continue
        positionen.append((bez.strip(), beschr.strip(), zahl_aus_text(menge, 1), einheit.strip(),
                           cent_aus_text(preis), cent_aus_text(teile), zahl_aus_text(satz, 19), art.strip(),
                           int(aid) if aid.isdigit() else None))
    with dbm.Transaktion(con):
        con.execute(
            "UPDATE dokumente SET kunde_id=?, datum=?, leistungsdatum=?, leistungsdatum_bis=?, zahlungsziel_tage=?, "
            "faellig_am=?, betreff=?, einleitung=?, schlusstext=?, hinweise=?, steuer_modus=?, geaendert_am=? "
            "WHERE id=? AND status='entwurf'",
            (kunde["id"] if kunde else None, datum, _f("leistungsdatum") or None, _f("leistungsdatum_bis") or None,
             ziel, faellig, _f("betreff"), f.get("einleitung", ""), f.get("schlusstext", ""), f.get("hinweise", ""),
             einst["steuer_modus"], dbm.jetzt(), d["id"]))
        con.execute("DELETE FROM positionen WHERE dokument_id=?", (d["id"],))
        for i, p in enumerate(positionen, 1):
            con.execute(
                "INSERT INTO positionen (dokument_id, pos, bezeichnung, beschreibung, menge, einheit, einzelpreis, "
                "teilekosten, steuersatz, leistungsart, artikel_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (d["id"], i, *p))
        logik.summen_speichern(con, d["id"])


@bp.route("/dokumente/<int:did>/pdf")
def dokument_pdf(did):
    d = _dokument_laden(did)
    herunterladen = request.args.get("download") == "1"
    if d["status"] == "entwurf":
        snap = logik.snapshot_bauen(dbm.get_db(), did)
        pdf = pdf_erzeugen(snap, daten_dir=daten_dir(), entwurf=True)
        from io import BytesIO
        return send_file(BytesIO(pdf), mimetype="application/pdf", download_name=f"Entwurf_{did}.pdf",
                         as_attachment=herunterladen)
    return send_file(Path(daten_dir()) / d["pdf_pfad"], mimetype="application/pdf",
                     download_name=f"{d['nummer']}.pdf", as_attachment=herunterladen)


@bp.route("/dokumente/<int:did>/drucken")
def dokument_drucken(did):
    d = _dokument_laden(did)
    return render_template("drucken.html", d=d)


@bp.route("/dokumente/<int:did>/loeschen", methods=["POST"])
def dokument_loeschen(did):
    con = dbm.get_db()
    d = _dokument_laden(did)
    if d["status"] != "entwurf":
        raise EingabeFehler("Festgeschriebene Dokumente können nicht gelöscht werden. Bitte stornieren.")
    with dbm.Transaktion(con):
        con.execute("DELETE FROM positionen WHERE dokument_id=?", (did,))
        con.execute("DELETE FROM dokumente WHERE id=?", (did,))
        dbm.protokollieren("entwurf_geloescht", "dokument", did, con=con)
    flash("Entwurf gelöscht.", "ok")
    return redirect(url_for("main.dokumente"))


@bp.route("/dokumente/<int:did>/stornieren", methods=["POST"])
def dokument_stornieren(did):
    neu_id, nummer = logik.stornieren(dbm.get_db(), did, daten_dir(), _f("grund"))
    flash(f"Stornorechnung {nummer} wurde erstellt.", "ok")
    return redirect(url_for("main.dokument", did=neu_id))


@bp.route("/dokumente/<int:did>/kopieren", methods=["POST"])
def dokument_kopieren(did):
    """Legt einen neuen Entwurf mit denselben Positionen an (z. B. als Korrektur nach Storno)."""
    con = dbm.get_db()
    d = _dokument_laden(did)
    einst = dbm.einstellungen(con)
    typ = "rechnung"
    texte = logik.standard_texte(con, typ)
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (d["kunde_id"],)).fetchone() if d["kunde_id"] else None
    ziel = _zahlungsziel(einst, kunde)
    with dbm.Transaktion(con):
        cur = con.execute(
            "INSERT INTO dokumente (typ, kunde_id, datum, leistungsdatum, leistungsdatum_bis, zahlungsziel_tage, "
            "faellig_am, betreff, einleitung, schlusstext, hinweise, steuer_modus, erstellt_am, geaendert_am) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (typ, d["kunde_id"], heute(), d["leistungsdatum"], d["leistungsdatum_bis"], ziel, plus_tage(heute(), ziel),
             d["betreff"] if d["typ"] == "rechnung" else "", texte.get("einleitung", ""), texte.get("schluss", ""),
             d["hinweise"] if d["typ"] == "rechnung" else "", einst["steuer_modus"], dbm.jetzt(), dbm.jetzt()))
        neu = cur.lastrowid
        for p in con.execute("SELECT * FROM positionen WHERE dokument_id=? ORDER BY pos", (did,)).fetchall():
            con.execute(
                "INSERT INTO positionen (dokument_id, pos, artikel_id, bezeichnung, beschreibung, menge, einheit, "
                "einzelpreis, teilekosten, steuersatz, leistungsart) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (neu, p["pos"], p["artikel_id"], p["bezeichnung"], p["beschreibung"], p["menge"], p["einheit"],
                 abs(p["einzelpreis"]), abs(p["teilekosten"]), p["steuersatz"], p["leistungsart"]))
        logik.summen_speichern(con, neu)
        dbm.protokollieren("entwurf_kopiert", "dokument", neu, {"von": d["nummer"] or did}, con=con)
    flash("Neuer Entwurf als Kopie angelegt.", "ok")
    return redirect(url_for("main.dokument", did=neu))


@bp.route("/dokumente/<int:did>/email", methods=["GET", "POST"])
def dokument_email(did):
    con = dbm.get_db()
    d = _dokument_laden(did)
    if d["status"] == "entwurf":
        raise EingabeFehler("Bitte das Dokument zuerst festschreiben. Entwürfe werden nicht versendet.")
    einst = dbm.einstellungen(con)
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (d["kunde_id"],)).fetchone()
    if request.method == "POST":
        an = _f("an")
        if "@" not in an:
            raise EingabeFehler("Bitte eine gültige E-Mail-Adresse angeben.")
        pdf = (Path(daten_dir()) / d["pdf_pfad"]).read_bytes()
        try:
            senden(con, einst, an, _f("betreff"), request.form.get("text", ""), pdf, f"{d['nummer']}.pdf", did)
        except MailFehler as e:
            flash(f"E-Mail wurde NICHT gesendet: {e}", "fehler")
            return redirect(url_for("main.dokument_email", did=did))
        flash(f"E-Mail an {an} wurde gesendet.", "ok")
        return redirect(url_for("main.dokument", did=did))
    bezug = con.execute("SELECT * FROM dokumente WHERE id=?", (d["bezug_id"],)).fetchone() if d["bezug_id"] else None
    werte = logik.platzhalter_werte(d, kunde, einst, bezug=bezug)
    texte = logik.standard_texte(con, d["typ"])
    return render_template("dokument_email.html", d=d, kunde=kunde,
                           an=(kunde["email"] if kunde else "") or "",
                           betreff=platzhalter_ersetzen(texte.get("email_betreff", "{nummer}"), werte),
                           text=platzhalter_ersetzen(texte.get("email_text", ""), werte),
                           smtp_ok=bool(einst.get("smtp_host")))


# ====================================================================== Einstellungen

EINSTELLUNGS_BEREICHE = {
    "firma": ["firma_name", "firma_zusatz", "inhaber", "strasse", "plz", "ort", "land", "telefon", "email", "web",
              "steuernummer", "ust_idnr", "bank_name", "kontoinhaber", "iban", "bic"],
    "rechnung": ["steuer_modus", "regel_steuersatz", "kleinunternehmer_hinweis", "zahlungsziel_privat",
                 "zahlungsziel_firma", "zahlungsarten_text", "anzahlung_prozent", "mahngebuehr_cent", "mahnstufen",
                 "nummern_format", "praefix_rechnung", "praefix_kunde", "leistungsarten"],
    "layout": ["farbe_primaer", "farbe_sekundaer", "schrift", "schriftgroesse", "logo_breite_mm", "logo_position",
               "kopfzeile_text", "fusszeile_text", "faltmarken", "girocode"],
    "email": ["smtp_host", "smtp_port", "smtp_sicherheit", "smtp_benutzer", "absender_name", "absender_email",
              "bcc_an_mich"],
    "backup": ["backup_auto", "backup_ziel", "backup_behalten"],
    "anfragen": ["anfragen_aktiv", "anfragen_intervall_min", "imap_host", "imap_port", "imap_benutzer",
                 "imap_ordner", "imap_zielordner", "imap_verschieben", "anfrage_erkennung", "anfrage_auto_kunde",
                 "anfrage_schwelle_unsicher", "anfrage_schwelle_spam", "anfrage_namensreihenfolge",
                 "interessent_loeschen_monate"],
}
JA_NEIN = {"faltmarken", "girocode", "bcc_an_mich", "backup_auto", "anfragen_aktiv", "imap_verschieben",
           "anfrage_auto_kunde"}
GANZZAHL = {"zahlungsziel_privat", "zahlungsziel_firma", "anzahlung_prozent", "mahnstufen", "smtp_port",
            "backup_behalten", "regel_steuersatz", "anfragen_intervall_min", "imap_port", "anfrage_schwelle_unsicher",
            "anfrage_schwelle_spam", "interessent_loeschen_monate"}
KOMMAZAHL = {"schriftgroesse", "logo_breite_mm"}


@bp.route("/einstellungen", methods=["GET", "POST"])
def einstellungen():
    bereich = request.args.get("bereich", "firma")
    if bereich not in EINSTELLUNGS_BEREICHE and bereich not in ("sicherheit",):
        bereich = "firma"
    con = dbm.get_db()
    if request.method == "POST" and bereich in EINSTELLUNGS_BEREICHE:
        neu = {}
        for feld in EINSTELLUNGS_BEREICHE[bereich]:
            if feld in JA_NEIN:
                neu[feld] = bool(request.form.get(feld))
            elif feld == "mahngebuehr_cent":
                neu[feld] = cent_aus_text(_f(feld))
            elif feld in GANZZAHL:
                neu[feld] = int(zahl_aus_text(_f(feld), 0))
            elif feld in KOMMAZAHL:
                neu[feld] = zahl_aus_text(_f(feld), 0)
            else:
                neu[feld] = _f(feld)
        if bereich == "firma":
            neu["iban"] = neu["iban"].replace(" ", "").upper()
        if bereich == "email" and request.form.get("smtp_passwort"):
            neu["smtp_passwort_enc"] = verschluesseln(request.form["smtp_passwort"])
        if bereich == "anfragen" and request.form.get("imap_passwort"):
            neu["imap_passwort_enc"] = verschluesseln(request.form["imap_passwort"])
        if bereich == "anfragen" and neu["anfrage_schwelle_spam"] <= neu["anfrage_schwelle_unsicher"]:
            raise EingabeFehler("Die Spam-Schwelle muss größer sein als die Schwelle für „unsicher“.")
        if bereich == "rechnung":
            if neu["steuer_modus"] not in ("kleinunternehmer", "regel"):
                neu["steuer_modus"] = "kleinunternehmer"
            try:
                logik.nummer_formatieren(neu["nummern_format"], "RE", 2026, 1)
                neu["nummern_format"].format(praefix="RE", jahr=2026, nummer=1)
            except (KeyError, ValueError, IndexError):
                raise EingabeFehler("Das Nummernformat ist ungültig. Beispiel: {praefix}-{jahr}-{nummer:04d}")
        with dbm.Transaktion(con):
            alt = dbm.einstellungen(con)
            dbm.einstellungen_speichern(neu, con)
            geheim = ("smtp_passwort_enc", "imap_passwort_enc")
            geaendert = {k: v for k, v in neu.items() if alt.get(k) != v and k not in geheim}
            for k in geheim:
                if k in neu:
                    geaendert[k.replace("_enc", "")] = "(geändert)"
            dbm.protokollieren("einstellungen_geaendert", "einstellungen", None, geaendert, con=con)
        flash("Einstellungen gespeichert.", "ok")
        return redirect(url_for("main.einstellungen", bereich=bereich))
    return render_template("einstellungen.html", bereich=bereich, schriften=list(SCHRIFTEN),
                           smtp_passwort_gesetzt=bool(dbm.einstellung("smtp_passwort_enc")),
                           imap_passwort_gesetzt=bool(dbm.einstellung("imap_passwort_enc")),
                           backups=_backup_liste())


def _backup_liste():
    ordner = Path(daten_dir()) / "backups"
    return sorted(((p.name, p.stat().st_size) for p in ordner.glob("backup_*.zip")), reverse=True)[:10]


@bp.route("/einstellungen/logo", methods=["POST"])
def logo_hochladen():
    datei = request.files.get("logo")
    con = dbm.get_db()
    if request.form.get("entfernen"):
        with dbm.Transaktion(con):
            dbm.einstellungen_speichern({"logo_datei": ""}, con)
            dbm.protokollieren("logo_entfernt", "einstellungen", con=con)
        flash("Eigenes Logo entfernt, das Standardlogo wird verwendet.", "ok")
        return redirect(url_for("main.einstellungen", bereich="layout"))
    if not datei or not datei.filename:
        raise EingabeFehler("Bitte eine Bilddatei auswählen.")
    try:
        bild = Image.open(datei.stream)
        bild.load()
    except Exception:
        raise EingabeFehler("Die Datei konnte nicht als Bild gelesen werden (erlaubt: PNG, JPG).")
    rel = Path("bilder") / f"logo_{date.today():%Y%m%d}_{abs(hash(datei.filename)) % 10000}.png"
    bild.convert("RGBA").save(Path(daten_dir()) / rel)
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"logo_datei": rel.as_posix()}, con)
        dbm.protokollieren("logo_geaendert", "einstellungen", None, {"datei": rel.as_posix()}, con=con)
    flash("Logo gespeichert.", "ok")
    return redirect(url_for("main.einstellungen", bereich="layout"))


@bp.route("/einstellungen/logo.png")
def logo_anzeigen():
    eigen = dbm.einstellung("logo_datei")
    pfad = Path(daten_dir()) / eigen if eigen else None
    if not pfad or not pfad.is_file():
        pfad = Path(__file__).parent / "static" / "bilder" / "logo_standard.png"
    return send_file(pfad, mimetype="image/png")


@bp.route("/einstellungen/musterrechnung.pdf")
def musterrechnung():
    """Zeigt das aktuelle Layout mit Beispieldaten – ohne etwas zu speichern."""
    einst = dbm.einstellungen()
    pos = [
        {"pos": 1, "bezeichnung": "Akkutausch Smartphone", "beschreibung": "inkl. Ersatzakku und Funktionstest",
         "menge": 1, "einheit": "Stk.", "einzelpreis": 7900, "steuersatz": 19, "betrag": 7900},
        {"pos": 2, "bezeichnung": "Kaffeemaschinen-Wartung", "beschreibung": "Entkalken, Brühgruppe reinigen",
         "menge": 1, "einheit": "pauschal", "einzelpreis": 8900, "steuersatz": 19, "betrag": 8900},
    ]
    s = logik.summen_berechnen(pos, einst["steuer_modus"])
    texte = logik.standard_texte(dbm.get_db(), "rechnung")
    werte = {"anrede_brief": "Sehr geehrte Frau Muster,", "nummer": "RE-2026-0000", "betrag": euro(s["brutto"]),
             "faellig_am": "28.10.2026", "datum": "14.10.2026", "inhaber": einst["inhaber"],
             "firma_name": einst["firma_name"]}
    snap = {
        "typ": "rechnung", "titel": "Rechnung", "nummer": "RE-2026-0000", "datum": heute(), "leistungsdatum": heute(),
        "leistungsdatum_bis": None, "faellig_am": plus_tage(heute(), 14), "betreff": "Musterrechnung (Layoutvorschau)",
        "einleitung": platzhalter_ersetzen(texte.get("einleitung", ""), werte),
        "schlusstext": platzhalter_ersetzen(texte.get("schluss", ""), werte), "hinweise": "",
        "steuer_modus": einst["steuer_modus"],
        "kleinunternehmer_hinweis": einst["kleinunternehmer_hinweis"] if einst["steuer_modus"] == "kleinunternehmer" else "",
        "zahlungsarten_text": einst["zahlungsarten_text"], "bezug": None,
        "kunde": {"kundennr": "K-0000", "name": "Erika Muster",
                  "anschrift": ["Frau Erika Muster", "Musterweg 1", "74219 Möckmühl"], "ust_idnr": "", "typ": "privat"},
        "firma": {k: einst.get(k, "") for k in logik.FIRMA_FELDER},
        "layout": {k: einst.get(k) for k in logik.LAYOUT_FELDER},
        "positionen": pos, "summen": s,
    }
    from io import BytesIO
    return send_file(BytesIO(pdf_erzeugen(snap, daten_dir=daten_dir(), entwurf=True)), mimetype="application/pdf",
                     download_name="Musterrechnung.pdf")


@bp.route("/einstellungen/testmail", methods=["POST"])
def testmail():
    con = dbm.get_db()
    einst = dbm.einstellungen(con)
    an = _f("an") or einst.get("absender_email")
    try:
        senden(con, {**einst, "bcc_an_mich": False}, an, "Test-E-Mail aus der Buchhaltung",
               "Diese Test-E-Mail bestätigt, dass der E-Mail-Versand funktioniert.")
        flash(f"Test-E-Mail an {an} gesendet.", "ok")
    except MailFehler as e:
        flash(f"Test fehlgeschlagen: {e}", "fehler")
    return redirect(url_for("main.einstellungen", bereich="email"))


@bp.route("/einstellungen/passwort", methods=["POST"])
def passwort_aendern():
    con = dbm.get_db()
    if not check_password_hash(dbm.einstellung("passwort_hash"), request.form.get("alt", "")):
        raise EingabeFehler("Das bisherige Passwort ist falsch.")
    neu = request.form.get("neu", "")
    if len(neu) < 8 or neu != request.form.get("neu2"):
        raise EingabeFehler("Das neue Passwort muss mindestens 8 Zeichen haben und zweimal gleich eingegeben werden.")
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"passwort_hash": generate_password_hash(neu)}, con)
        dbm.protokollieren("passwort_geaendert", "system", con=con)
    flash("Passwort geändert.", "ok")
    return redirect(url_for("main.einstellungen", bereich="sicherheit"))


@bp.route("/einstellungen/backup", methods=["POST"])
def backup_jetzt():
    con = dbm.get_db()
    einst = dbm.einstellungen(con)
    ziel, extern = backup_erstellen(daten_dir(), current_app.config["DB_PFAD"], einst)
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"letztes_backup": dbm.jetzt()}, con)
        dbm.protokollieren("backup_manuell", "system", None, {"datei": ziel.name, "extern": extern}, con=con)
    meldung = f"Backup {ziel.name} erstellt."
    if extern:
        meldung += f" Kopie: {extern}"
    flash(meldung, "fehler" if extern and extern.startswith("FEHLER") else "ok")
    return redirect(url_for("main.einstellungen", bereich="backup"))


@bp.route("/einstellungen/backup/<name>")
def backup_herunterladen(name):
    pfad = Path(daten_dir()) / "backups" / Path(name).name
    if not pfad.is_file() or not pfad.name.startswith("backup_"):
        abort(404)
    return send_file(pfad, as_attachment=True)


# ====================================================================== Textbausteine

@bp.route("/textbausteine")
def textbausteine():
    liste = dbm.get_db().execute("SELECT * FROM textbausteine ORDER BY dokumenttyp, kategorie, name").fetchall()
    return render_template("textbausteine.html", liste=liste)


TB_KATEGORIEN = {"einleitung": "Einleitung", "schluss": "Schlusstext", "hinweis": "Hinweis",
                 "email_betreff": "E-Mail-Betreff", "email_text": "E-Mail-Text"}
TB_TYPEN = {"alle": "Alle Dokumente", "rechnung": "Rechnung", "storno": "Stornorechnung"}


@bp.route("/textbausteine/neu", methods=["GET", "POST"])
@bp.route("/textbausteine/<int:tid>", methods=["GET", "POST"])
def textbaustein(tid=None):
    con = dbm.get_db()
    t = con.execute("SELECT * FROM textbausteine WHERE id=?", (tid,)).fetchone() if tid else None
    if request.method == "POST":
        if request.form.get("loeschen") and t:
            with dbm.Transaktion(con):
                con.execute("DELETE FROM textbausteine WHERE id=?", (tid,))
                dbm.protokollieren("textbaustein_geloescht", "textbaustein", tid, con=con)
            flash("Textbaustein gelöscht.", "ok")
            return redirect(url_for("main.textbausteine"))
        kat, typ = _f("kategorie"), _f("dokumenttyp")
        if kat not in TB_KATEGORIEN or typ not in TB_TYPEN or not _f("name"):
            raise EingabeFehler("Bitte Name, Kategorie und Dokumenttyp angeben.")
        standard = 1 if request.form.get("standard") else 0
        with dbm.Transaktion(con):
            if standard:
                con.execute("UPDATE textbausteine SET standard=0 WHERE kategorie=? AND dokumenttyp=?", (kat, typ))
            werte = (kat, typ, _f("name"), request.form.get("text", ""), standard)
            if t:
                con.execute("UPDATE textbausteine SET kategorie=?, dokumenttyp=?, name=?, text=?, standard=? "
                            "WHERE id=?", (*werte, tid))
            else:
                tid = con.execute("INSERT INTO textbausteine (kategorie, dokumenttyp, name, text, standard) "
                                  "VALUES (?,?,?,?,?)", werte).lastrowid
            dbm.protokollieren("textbaustein_gespeichert", "textbaustein", tid, con=con)
        flash("Textbaustein gespeichert.", "ok")
        return redirect(url_for("main.textbausteine"))
    return render_template("textbaustein.html", t=t, kategorien=TB_KATEGORIEN, typen=TB_TYPEN,
                           platzhalter=PLATZHALTER_HILFE)


# ====================================================================== Protokoll & Prüfung

@bp.route("/protokoll")
def protokoll():
    con = dbm.get_db()
    eintraege = con.execute("SELECT * FROM protokoll ORDER BY id DESC LIMIT 300").fetchall()
    versand = con.execute("SELECT v.*, d.nummer FROM versandprotokoll v LEFT JOIN dokumente d ON d.id=v.dokument_id "
                          "ORDER BY v.id DESC LIMIT 100").fetchall()
    return render_template("protokoll.html", eintraege=eintraege, versand=versand)


@bp.route("/pruefung")
def pruefung():
    ergebnis = logik.integritaet_pruefen(dbm.get_db(), daten_dir())
    return render_template("pruefung.html", e=ergebnis)


@bp.app_template_filter("kname")
def _kname(row):
    return kunde_name(row)


# ====================================================================== Anfragen (Kontaktformular)

from . import anfragen as anf  # noqa: E402

ANFRAGE_FILTER = {
    "offen": ("Zu prüfen", "status='neu' AND einstufung<>'spam'"),
    "kunden": ("Kunde angelegt/zugeordnet", "status IN ('kunde_angelegt','zugeordnet')"),
    "spam": ("Spam", "status='neu' AND einstufung='spam'"),
    "verworfen": ("Verworfen", "status='verworfen'"),
    "alle": ("Alle", "1=1"),
}


@bp.route("/anfragen")
def anfragen_liste():
    con = dbm.get_db()
    filt = request.args.get("filter", "offen")
    if filt not in ANFRAGE_FILTER:
        filt = "offen"
    liste = con.execute(f"SELECT a.*, k.kundennr FROM anfragen a LEFT JOIN kunden k ON k.id=a.kunde_id "
                        f"WHERE {ANFRAGE_FILTER[filt][1]} ORDER BY a.eingang_am DESC LIMIT 300").fetchall()
    anzahl = {k: con.execute(f"SELECT COUNT(*) FROM anfragen WHERE {w}").fetchone()[0]
              for k, (_, w) in ANFRAGE_FILTER.items()}
    loeschvorschlaege = anf.interessenten_zum_loeschen(con, dbm.einstellungen(con))
    return render_template("anfragen.html", liste=liste, filt=filt, filter=ANFRAGE_FILTER, anzahl=anzahl,
                           loeschvorschlaege=loeschvorschlaege, anzeigename=anf.anfrage_anzeigename)


@bp.route("/anfragen/abrufen", methods=["POST"])
def anfragen_abrufen():
    try:
        e = anf.abruf_mit_protokoll(dbm.get_db())
    except anf.AbrufFehler as fehler:
        flash(str(fehler), "fehler")
        return redirect(url_for("main.anfragen_liste"))
    flash(f"Postfach geprüft: {e['neu']} neue Anfrage(n) – {e['echt']} echt, {e['unsicher']} unsicher, "
          f"{e['spam']} Spam. {e['verschoben']} E-Mail(s) in den Ordner „{dbm.einstellung('imap_zielordner')}“ "
          f"verschoben.", "ok")
    return redirect(url_for("main.anfragen_liste"))


@bp.route("/anfragen/einfuegen", methods=["GET", "POST"])
def anfrage_einfuegen():
    """Formular-E-Mail per Kopieren/Einfügen übernehmen (z. B. zum Testen oder ohne IMAP)."""
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if not text:
            raise EingabeFehler("Bitte den Text der Anfrage einfügen.")
        if "<" in text and ">" in text and re.search(r"</?(p|div|br|td|strong)\b", text, re.I):
            text = anf.html_zu_text(text)
        con = dbm.get_db()
        aid = anf.verarbeiten(con, text, dbm.einstellungen(con), quelle="manuell")
        return redirect(url_for("main.anfrage", aid=aid))
    return render_template("anfrage_einfuegen.html")


def _anfrage_laden(aid):
    a = dbm.get_db().execute("SELECT * FROM anfragen WHERE id=?", (aid,)).fetchone()
    if not a:
        abort(404)
    return a


@bp.route("/anfragen/<int:aid>")
def anfrage(aid):
    con = dbm.get_db()
    a = _anfrage_laden(aid)
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (a["kunde_id"],)).fetchone() if a["kunde_id"] else None
    vorhanden = None if kunde else anf.passender_kunde(con, a["email"], a["telefon"])
    return render_template("anfrage.html", a=a, kunde=kunde, vorhanden=vorhanden,
                           felder=json.loads(a["felder_json"] or "{}"), gruende=json.loads(a["gruende_json"] or "[]"),
                           leistungsart=anf.geraet_zu_leistungsart(a["geraet"]), anzeigename=anf.anfrage_anzeigename)


@bp.route("/anfragen/<int:aid>/aktion", methods=["POST"])
def anfrage_aktion(aid):
    con = dbm.get_db()
    a = _anfrage_laden(aid)
    aktion = request.form.get("aktion")
    with dbm.Transaktion(con):
        if aktion == "kunde":
            if a["kunde_id"]:
                raise EingabeFehler("Zu dieser Anfrage gibt es bereits einen Kunden.")
            con.execute("UPDATE anfragen SET vorname=?, nachname=? WHERE id=?",
                        (_f("vorname"), _f("nachname"), aid))
            kid, neu = anf.kunde_aus_anfrage(con, aid, dbm.einstellungen(con), _f("vorname"), _f("nachname"))
            meldung = "Kunde als Interessent angelegt." if neu else "Anfrage dem vorhandenen Kunden zugeordnet."
        elif aktion == "verwerfen":
            con.execute("UPDATE anfragen SET status='verworfen', bearbeitet_am=? WHERE id=?", (dbm.jetzt(), aid))
            dbm.protokollieren("anfrage_verworfen", "anfrage", aid, con=con)
            meldung, kid = "Anfrage verworfen (wird nach 30 Tagen automatisch gelöscht).", None
        elif aktion == "spam":
            con.execute("UPDATE anfragen SET einstufung='spam', status='neu', bearbeitet_am=? WHERE id=?",
                        (dbm.jetzt(), aid))
            dbm.protokollieren("anfrage_als_spam", "anfrage", aid, con=con)
            meldung, kid = "Als Spam markiert.", None
        elif aktion == "kein_spam":
            con.execute("UPDATE anfragen SET einstufung='unsicher', bearbeitet_am=? WHERE id=?", (dbm.jetzt(), aid))
            dbm.protokollieren("anfrage_kein_spam", "anfrage", aid, con=con)
            meldung, kid = "Anfrage zurück in „Zu prüfen“ verschoben.", None
        else:
            abort(400)
    flash(meldung, "ok")
    if kid and request.form.get("danach") == "kunde":
        return redirect(url_for("main.kunde", kid=kid))
    return redirect(url_for("main.anfrage", aid=aid))


@bp.route("/anfragen/interessenten-loeschen", methods=["POST"])
def interessenten_loeschen():
    con = dbm.get_db()
    ids = [int(i) for i in request.form.getlist("kunde_id") if i.isdigit()]
    erlaubt = {k["id"] for k in anf.interessenten_zum_loeschen(con, dbm.einstellungen(con))}
    with dbm.Transaktion(con):
        for kid in ids:
            if kid in erlaubt:
                con.execute("DELETE FROM anfragen WHERE kunde_id=?", (kid,))
                con.execute("DELETE FROM kunden WHERE id=?", (kid,))
                dbm.protokollieren("interessent_geloescht", "kunde", kid, "Löschfrist abgelaufen, kein Auftrag",
                                   con=con)
    flash(f"{len([i for i in ids if i in erlaubt])} Interessent(en) gelöscht.", "ok")
    return redirect(url_for("main.anfragen_liste"))
