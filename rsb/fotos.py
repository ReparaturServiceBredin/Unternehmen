"""Fotodokumentation zu Reparaturaufträgen.

Grundsätze:
- Originale werden unverändert gespeichert (Prüfsumme SHA-256); Vorschaubilder sind nur abgeleitete Kopien.
- Server-Zeitstempel in deutscher Zeit mit Sekunden, dazu – falls vorhanden – die EXIF-Aufnahmezeit der Kamera.
- Löschen nur als Markierung mit Begründung; Datensätze lassen sich nicht ändern oder entfernen (Datenbank-Trigger).
- Jeder Vorgang steht im Verlauf des Auftrags und im Änderungsprotokoll.
"""
import hashlib
import io
from datetime import datetime
from pathlib import Path

from . import db as dbm
from .hilfen import EingabeFehler

KATEGORIEN = ["Geräteeingang", "Vorschaden", "Während der Reparatur", "Nach der Reparatur", "Geräteausgabe"]
ENDUNGEN = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
            "heic": "image/heic", "heif": "image/heif", "gif": "image/gif"}
VORSCHAU_PX = 480


def _bild_oeffnen(daten):
    try:
        from PIL import Image
        bild = Image.open(io.BytesIO(daten))
        bild.load()
        return bild
    except Exception:
        return None


def exif_zeit(daten):
    """Aufnahmezeit aus den EXIF-Daten (DateTimeOriginal, sonst DateTime) als ISO-Text, sonst None."""
    bild = _bild_oeffnen(daten)
    if bild is None:
        return None
    try:
        exif = bild.getexif()
        wert = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal / DateTime
        if not wert:
            return None
        return datetime.strptime(str(wert).strip()[:19], "%Y:%m:%d %H:%M:%S").isoformat()
    except (ValueError, TypeError, AttributeError, KeyError):
        return None


def vorschau_pfad(daten_dir, sha):
    return Path(daten_dir) / "fotos" / "vorschau" / f"{sha}.jpg"


def vorschau_erzeugen(daten_dir, sha, daten):
    """Kleines, richtig gedrehtes JPEG für Galerie und PDF. Das Original bleibt unangetastet."""
    ziel = vorschau_pfad(daten_dir, sha)
    if ziel.exists():
        return ziel
    bild = _bild_oeffnen(daten)
    if bild is None:
        return None
    from PIL import ImageOps
    bild = ImageOps.exif_transpose(bild).convert("RGB")
    bild.thumbnail((VORSCHAU_PX * 2, VORSCHAU_PX * 2))
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "JPEG", quality=85)
    return ziel


def speichern(con, daten_dir, daten, dateiname, kategorie, auftrag_id=None, upload_token=None):
    """Speichert ein hochgeladenes Foto. Muss in einer Transaktion laufen. Gibt die Foto-ID zurück."""
    if kategorie not in KATEGORIEN:
        raise EingabeFehler("Bitte eine Foto-Kategorie auswählen.")
    if not daten:
        raise EingabeFehler("Die Datei ist leer.")
    endung = (dateiname or "").rsplit(".", 1)[-1].lower() if "." in (dateiname or "") else ""
    bild = _bild_oeffnen(daten)
    if endung not in ENDUNGEN:
        if bild is None:
            raise EingabeFehler(f"„{dateiname}“ ist kein unterstütztes Bild (JPG, PNG, WEBP, HEIC).")
        endung = (bild.format or "jpg").lower().replace("jpeg", "jpg")
    elif bild is None and endung not in ("heic", "heif"):
        raise EingabeFehler(f"„{dateiname}“ konnte nicht als Bild gelesen werden.")
    sha = hashlib.sha256(daten).hexdigest()
    jetzt = dbm.jetzt_berlin()
    rel = Path("fotos") / jetzt[:4] / jetzt[5:7] / f"{sha}.{endung}"
    ziel = Path(daten_dir) / rel
    if not ziel.exists():
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(daten)
    vorschau_erzeugen(daten_dir, sha, daten)
    cur = con.execute(
        "INSERT INTO auftrag_fotos (auftrag_id, upload_token, kategorie, dateiname, pfad, mime, groesse, sha256, "
        "exif_zeit, hochgeladen_am, benutzer) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (auftrag_id, upload_token, kategorie, dateiname or f"foto.{endung}", rel.as_posix(),
         ENDUNGEN.get(endung, "application/octet-stream"), len(daten), sha, exif_zeit(daten), jetzt,
         dbm.aktueller_benutzer()))
    fid = cur.lastrowid
    dbm.protokollieren("foto_hochgeladen", "auftrag" if auftrag_id else "foto", auftrag_id or fid,
                       {"foto": fid, "datei": dateiname, "kategorie": kategorie, "sha256": sha}, con=con)
    if auftrag_id:
        from .auftraege import verlauf
        verlauf(con, auftrag_id, "Foto hochgeladen", f"{kategorie}: {dateiname} (SHA-256 {sha[:12]}…)")
    return fid


def zuordnen(con, upload_token, auftrag_id):
    """Beim Anlegen hochgeladene Fotos dem neuen Auftrag zuordnen. Gibt die Anzahl zurück."""
    if not upload_token:
        return 0
    fotos = con.execute("SELECT * FROM auftrag_fotos WHERE upload_token=? AND auftrag_id IS NULL ORDER BY id",
                        (upload_token,)).fetchall()
    for f in fotos:
        con.execute("UPDATE auftrag_fotos SET auftrag_id=? WHERE id=?", (auftrag_id, f["id"]))
    if fotos:
        from .auftraege import verlauf
        verlauf(con, auftrag_id, "Fotos hochgeladen", f"{len(fotos)} Foto(s) beim Anlegen des Auftrags")
        dbm.protokollieren("fotos_zugeordnet", "auftrag", auftrag_id, {"fotos": [f["id"] for f in fotos]}, con=con)
    return len(fotos)


def als_geloescht_markieren(con, foto_id, grund):
    grund = (grund or "").strip()
    if len(grund) < 3:
        raise EingabeFehler("Bitte einen Grund für das Löschen angeben.")
    f = con.execute("SELECT * FROM auftrag_fotos WHERE id=?", (foto_id,)).fetchone()
    if not f:
        raise EingabeFehler("Foto nicht gefunden.")
    if f["geloescht_am"]:
        raise EingabeFehler("Das Foto ist bereits als gelöscht markiert.")
    con.execute("UPDATE auftrag_fotos SET geloescht_am=?, geloescht_von=?, loeschgrund=? WHERE id=?",
                (dbm.jetzt_berlin(), dbm.aktueller_benutzer(), grund, foto_id))
    dbm.protokollieren("foto_geloescht_markiert", "auftrag", f["auftrag_id"], {"foto": foto_id, "grund": grund},
                       con=con)
    if f["auftrag_id"]:
        from .auftraege import verlauf
        verlauf(con, f["auftrag_id"], "Foto als gelöscht markiert", f"{f['dateiname']} – Grund: {grund}")


def liste(con, auftrag_id=None, upload_token=None, mit_geloeschten=True):
    if auftrag_id:
        sql, arg = "SELECT * FROM auftrag_fotos WHERE auftrag_id=?", auftrag_id
    else:
        sql, arg = "SELECT * FROM auftrag_fotos WHERE upload_token=? AND auftrag_id IS NULL", upload_token
    if not mit_geloeschten:
        sql += " AND geloescht_am IS NULL"
    return con.execute(sql + " ORDER BY hochgeladen_am, id", (arg,)).fetchall()


def zeit_de(iso):
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M:%S")
    except ValueError:
        return iso


def pdf_dokumentation(con, auftrag, daten_dir):
    """PDF der Fotodokumentation: je Foto Vorschau, Kategorie, Zeitstempel, Benutzer, Prüfsumme, Markierungen."""
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    from .hilfen import kunde_name
    from .pdf import _schrift_registrieren

    einst = dbm.einstellungen(con)
    f_norm, f_fett, _ = _schrift_registrieren(einst.get("schrift") or "Montserrat")
    blau = colors.HexColor(einst.get("farbe_primaer") or "#1C54A3")
    grau = colors.HexColor(einst.get("farbe_sekundaer") or "#5D6670")
    st_titel = ParagraphStyle("t", fontName=f_fett, fontSize=16, leading=20, textColor=blau)
    st = ParagraphStyle("n", fontName=f_norm, fontSize=9, leading=12)
    st_klein = ParagraphStyle("k", fontName=f_norm, fontSize=7.5, leading=10, textColor=grau)
    st_h = ParagraphStyle("h", fontName=f_fett, fontSize=11, leading=15, textColor=blau, spaceBefore=6)
    fotos = liste(con, auftrag["id"])
    kunde = con.execute("SELECT * FROM kunden WHERE id=?", (auftrag["kunde_id"],)).fetchone()
    puffer = io.BytesIO()

    def fuss(c, doc):
        c.saveState()
        c.setFont(f_norm, 7)
        c.setFillColor(grau)
        c.drawString(20 * mm, 10 * mm, f"Fotodokumentation {auftrag['auftragsnr']} · {einst.get('firma_name', '')} · "
                                       f"erstellt {zeit_de(dbm.jetzt_berlin())}")
        c.drawRightString(190 * mm, 10 * mm, f"Seite {doc.page}")
        c.restoreState()

    doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Fotodokumentation {auftrag['auftragsnr']}",
                            author=einst.get("firma_name", ""))
    inhalt = [Paragraph(f"Fotodokumentation – Auftrag {escape(auftrag['auftragsnr'])}", st_titel), Spacer(1, 4 * mm)]
    kopf = [["Kunde", f"{kunde['kundennr']} · {kunde_name(kunde)}" if kunde else ""],
            ["Gerät", auftrag["geraet"] or "–"], ["Seriennr./IMEI", auftrag["seriennummer"] or "–"],
            ["Eingang", zeit_de(auftrag["eingang_am"])], ["Fehler", auftrag["fehler"] or "–"],
            ["Fotos", f"{len([f for f in fotos if not f['geloescht_am']])} gültig, "
                      f"{len([f for f in fotos if f['geloescht_am']])} als gelöscht markiert"]]
    t = Table([[Paragraph(f"<b>{escape(a)}</b>", st), Paragraph(escape(str(b)).replace("\n", "<br/>"), st)]
               for a, b in kopf], colWidths=[35 * mm, 135 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D9DE"))]))
    inhalt += [t, Spacer(1, 6 * mm)]
    for kat in KATEGORIEN:
        gruppe = [f for f in fotos if f["kategorie"] == kat]
        if not gruppe:
            continue
        inhalt.append(Paragraph(escape(kat), st_h))
        for f in gruppe:
            vorschau = vorschau_pfad(daten_dir, f["sha256"])
            if not vorschau.exists() and (Path(daten_dir) / f["pfad"]).exists():
                vorschau = vorschau_erzeugen(daten_dir, f["sha256"], (Path(daten_dir) / f["pfad"]).read_bytes()) or vorschau
            if vorschau and vorschau.exists():
                from PIL import Image as PILImage
                with PILImage.open(vorschau) as b:
                    w, h = b.size
                breite = 70 * mm
                hoehe = min(breite * h / w, 90 * mm)
                breite = hoehe * w / h
                bild = Image(str(vorschau), width=breite, height=hoehe)
            else:
                bild = Paragraph("(keine Vorschau – Format wird im PDF nicht angezeigt)", st_klein)
            angaben = [f"<b>{escape(f['dateiname'])}</b>",
                       f"Hochgeladen: {zeit_de(f['hochgeladen_am'])} (Server, Europe/Berlin) von {escape(f['benutzer'] or '')}",
                       f"Aufnahmezeit (EXIF): {zeit_de(f['exif_zeit']) if f['exif_zeit'] else 'nicht vorhanden'}",
                       f"Größe: {f['groesse'] / 1024:.0f} KB · Foto-ID {f['id']}",
                       f"SHA-256: <font size='6.5'>{f['sha256']}</font>"]
            if f["geloescht_am"]:
                angaben.append(f"<font color='#B3261E'><b>ALS GELÖSCHT MARKIERT</b> am {zeit_de(f['geloescht_am'])} "
                               f"von {escape(f['geloescht_von'] or '')} – Grund: {escape(f['loeschgrund'] or '')}</font>")
            zeile = Table([[bild, Paragraph("<br/>".join(angaben), st)]], colWidths=[75 * mm, 95 * mm])
            zeile.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D9DE")),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
            inhalt.append(KeepTogether([zeile]))
    # Änderungsprotokoll der Fotos
    verlauf_fotos = con.execute("SELECT * FROM auftrag_verlauf WHERE auftrag_id=? AND ereignis LIKE 'Foto%' "
                                "ORDER BY zeitpunkt, id", (auftrag["id"],)).fetchall()
    inhalt += [PageBreak(), Paragraph("Änderungsprotokoll der Fotodokumentation", st_h)]
    zeilen = [[Paragraph("<b>Zeitpunkt</b>", st), Paragraph("<b>Benutzer</b>", st), Paragraph("<b>Vorgang</b>", st)]]
    for v in verlauf_fotos:
        zeilen.append([Paragraph(zeit_de(v["zeitpunkt"]), st_klein), Paragraph(escape(v["benutzer"] or ""), st_klein),
                       Paragraph(escape(f"{v['ereignis']}: {v['details'] or ''}"), st_klein)])
    t = Table(zeilen, colWidths=[35 * mm, 25 * mm, 110 * mm], repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D9DE"))]))
    inhalt += [t, Spacer(1, 4 * mm),
               Paragraph("Die Originaldateien werden unverändert gespeichert; die SHA-256-Prüfsumme belegt, dass ein Foto "
                         "nicht nachträglich verändert wurde. Fotos können nicht gelöscht, sondern nur mit Begründung als "
                         "gelöscht markiert werden.", st_klein)]
    doc.build(inhalt, onFirstPage=fuss, onLaterPages=fuss)
    return puffer.getvalue()
