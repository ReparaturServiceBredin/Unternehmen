"""Datenbankzugriff, Einstellungen und Änderungsprotokoll."""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, g, has_request_context, session

SCHEMA = Path(__file__).with_name("schema.sql")

# Standardwerte für alle Einstellungen. Alles hier ist später in der Oberfläche änderbar.
STANDARD_EINSTELLUNGEN = {
    # Firma
    "firma_name": "Reparatur Service Bredin",
    "firma_zusatz": "Einfach & zuverlässig",
    "inhaber": "Dennis Bredin",
    "strasse": "",
    "plz": "",
    "ort": "Möckmühl",
    "land": "Deutschland",
    "telefon": "",
    "email": "kontakt@reparatur-bredin.de",
    "web": "www.reparatur-bredin.de",
    "steuernummer": "",
    "ust_idnr": "",
    "bank_name": "",
    "kontoinhaber": "Dennis Bredin",
    "iban": "",
    "bic": "",
    # Steuer
    "steuer_modus": "kleinunternehmer",  # oder "regel"
    "regel_steuersatz": 19,
    "kleinunternehmer_hinweis": "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet (Kleinunternehmerregelung).",
    # Zahlung
    "zahlungsziel_privat": 14,
    "zahlungsziel_firma": 30,
    "zahlungsarten_text": "Zahlbar per Überweisung oder in bar bei Abholung.",
    "anzahlung_prozent": 50,
    "mahngebuehr_cent": 395,
    "mahnstufen": 2,
    "kva_gueltig_tage": 30,
    # Verträge & Lizenzen
    "abo_modus": "automatisch",      # automatisch = festschreiben + per E-Mail senden / entwurf = nur Entwürfe anlegen
    "abo_letzter_lauf": "",
    "vertrag_erinnerung_tage": 60,   # so viele Tage vor Ablauf einer Lizenz/Garantie erinnern
    # Layout
    "farbe_primaer": "#1C54A3",
    "farbe_sekundaer": "#5D6670",
    "schrift": "Montserrat",
    "schriftgroesse": 9.5,
    "logo_datei": "",            # leer = mitgeliefertes Logo
    "logo_breite_mm": 62,
    "logo_position": "rechts",   # links / mitte / rechts
    "kopfzeile_text": "",
    "fusszeile_text": "",
    "faltmarken": True,
    "girocode": True,
    # Nummern
    "nummern_format": "{praefix}-{jahr}-{nummer:04d}",
    "praefix_rechnung": "RE",
    "praefix_angebot": "KV",
    "praefix_auftrag": "AB",
    "praefix_gutschrift": "GS",
    "praefix_mahnung": "MA",
    "praefix_kunde": "K",
    "leistungsarten": "Smartphone, Kaffeemaschine, PC/Laptop, Sonstiges",
    # E-Mail
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_sicherheit": "starttls",  # starttls / ssl / keine
    "smtp_benutzer": "",
    "smtp_passwort_enc": "",
    "absender_name": "Reparatur Service Bredin",
    "absender_email": "kontakt@reparatur-bredin.de",
    "bcc_an_mich": True,
    # Kopie gesendeter Mails per IMAP im Postfach ablegen
    "gesendet_aktiv": False,
    "gesendet_imap_host": "imap.ionos.de",
    "gesendet_imap_port": 993,
    "gesendet_imap_sicherheit": "ssl",      # ssl (Port 993) / starttls (Port 143)
    "gesendet_gleiche_zugangsdaten": True,
    "gesendet_imap_benutzer": "",
    "gesendet_imap_passwort_enc": "",
    "gesendet_ordner": "",
    # Backup
    "backup_auto": True,
    "backup_ziel": "",
    "backup_behalten": 30,
    "letztes_backup": "",
    # Anfragen aus dem Kontaktformular
    "anfragen_aktiv": False,
    "anfragen_intervall_min": 5,
    "imap_host": "imap.ionos.de",
    "imap_port": 993,
    "imap_benutzer": "",
    "imap_passwort_enc": "",
    "imap_ordner": "INBOX",
    "imap_zielordner": "Anfragen erledigt",
    "imap_verschieben": True,
    "anfrage_erkennung": "A new form has been submitted",
    "anfrage_auto_kunde": True,
    "anfrage_schwelle_unsicher": 2,
    "anfrage_schwelle_spam": 5,
    "anfrage_namensreihenfolge": "auto",   # auto / vorname_nachname / nachname_vorname
    "interessent_loeschen_monate": 6,
    "anfragen_letzter_abruf": "",
    "anfragen_letzter_fehler": "",
    # Programm-Updates
    "update_auto": True,
    "update_letzte_pruefung": "",
    "update_verfuegbar": "",
    "update_hinweise": "",
    "update_fehler": "",
    # Sicherheit
    "login_aktiv": False,        # Passwortabfrage beim Öffnen (in den Einstellungen einschaltbar)
    "passwort_hash": "",
    # Programmfenster
    "fenster_modus": "app",      # app = eigenes Fenster (Edge-App-Modus) / browser = normaler Browser-Tab
}


# Mitgelieferte Vertragsarten (Preise bitte anpassen; alles unter Verträge & Lizenzen → Vertragsarten änderbar)
# (name, kategorie, beschreibung, abrechnung, laufzeit, mindestlaufzeit, preis_cent, einkauf_cent, auto_verlaengern)
STANDARD_VERTRAGSARTEN = [
    ("Wertgarantie Geräteschutz", "Garantie/Versicherung",
     "Nur zur Dokumentation – der Kunde zahlt direkt an Wertgarantie.", "keine", None, None, 0, 0, 0),
    ("ESET Antivirus – 1 Jahr", "Lizenz", "Lizenz für 1 Gerät, Laufzeit 1 Jahr", "laufzeit", 12, None, 0, 0, 0),
    ("ESET Antivirus – 2 Jahre", "Lizenz", "Lizenz für 1 Gerät, Laufzeit 2 Jahre", "laufzeit", 24, None, 0, 0, 0),
    ("ESET Antivirus – 3 Jahre", "Lizenz", "Lizenz für 1 Gerät, Laufzeit 3 Jahre", "laufzeit", 36, None, 0, 0, 0),
    ("MSP Basis (monatlich)", "MSP", "IT-Betreuung: Überwachung, Updates, Virenschutz", "monatlich", None, 12, 0, 0, 0),
]


def jetzt():
    return datetime.now().isoformat(timespec="seconds")


def jetzt_berlin():
    """Server-Zeitstempel in deutscher Zeit (Europe/Berlin) mit Sekunden und Zeitzonen-Angabe."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Berlin")).isoformat(timespec="seconds")
    except Exception:  # z. B. fehlende Zeitzonendaten – dann lokale Zeit mit Abstand zu UTC
        return datetime.now().astimezone().isoformat(timespec="seconds")


def aktueller_benutzer():
    return session.get("benutzer", "system") if has_request_context() else "system"


def verbinden(pfad):
    con = sqlite3.connect(pfad, timeout=15, isolation_level=None)  # Autocommit, Transaktionen explizit
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def get_db():
    if "db" not in g:
        g.db = verbinden(current_app.config["DB_PFAD"])
    return g.db


def schliessen(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def initialisieren(pfad):
    con = verbinden(pfad)
    _migrieren(con, pfad)  # zuerst: Indizes/Trigger im Schema dürfen sich auf neue Spalten beziehen
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    _migrieren(con, pfad)
    vorhanden = {r["schluessel"] for r in con.execute("SELECT schluessel FROM einstellungen")}
    for k, v in STANDARD_EINSTELLUNGEN.items():
        if k not in vorhanden:
            con.execute("INSERT INTO einstellungen VALUES (?, ?)", (k, json.dumps(v)))
    # Einmalige Umstellung (Version 0.6.1, Wunsch des Inhabers): Vertragsrechnungen vollautomatisch
    if not con.execute("SELECT 1 FROM einstellungen WHERE schluessel='umstellung_abo_automatisch'").fetchone():
        con.execute("UPDATE einstellungen SET wert=? WHERE schluessel='abo_modus'", (json.dumps("automatisch"),))
        con.execute("INSERT INTO einstellungen VALUES ('umstellung_abo_automatisch', ?)", (json.dumps(jetzt()),))
    if not con.execute("SELECT 1 FROM vertragsarten LIMIT 1").fetchone():
        for va in STANDARD_VERTRAGSARTEN:
            con.execute("INSERT INTO vertragsarten (name, kategorie, beschreibung, abrechnung, laufzeit_monate, "
                        "mindestlaufzeit_monate, preis, einkauf, auto_verlaengern, erstellt_am) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)", (*va, jetzt()))
    _verlauf_nachtragen(con)
    from .textbausteine_standard import STANDARD_TEXTBAUSTEINE
    vorhandene_typen = {r[0] for r in con.execute("SELECT DISTINCT dokumenttyp FROM textbausteine")}
    leer = not vorhandene_typen
    for tb in STANDARD_TEXTBAUSTEINE:
        # beim ersten Start alle; bei Updates nur Bausteine für neu hinzugekommene Dokumenttypen
        if leer or tb["dokumenttyp"] not in vorhandene_typen:
            con.execute(
                "INSERT INTO textbausteine (kategorie, dokumenttyp, name, text, standard) VALUES (?,?,?,?,?)",
                (tb["kategorie"], tb["dokumenttyp"], tb["name"], tb["text"], tb["standard"]),
            )
    con.close()


# Spalten, die in neueren Versionen dazugekommen sind: (Tabelle, Spalte, Definition)
MIGRATIONEN = [
    ("kunden", "interessent", "INTEGER NOT NULL DEFAULT 0"),
    ("kunden", "quelle", "TEXT"),
    ("vertraege", "abgerechnet_bis", "TEXT"),
    ("versandprotokoll", "ablage", "TEXT"),
    ("artikel", "ek_unbekannt", "INTEGER NOT NULL DEFAULT 0"),
    ("dokumente", "kva_status", "TEXT"),
]


def _migrieren(con, pfad=None):
    """Ergänzt neue Spalten in bestehenden Datenbanken (Updates ohne Datenverlust).

    Vor jeder Änderung wird eine Sicherungskopie der Datenbank im Ordner backups angelegt.
    """
    fehlend = []
    for tabelle, spalte, definition in MIGRATIONEN:
        spalten = {r["name"] for r in con.execute(f"PRAGMA table_info({tabelle})")}
        if spalten and spalte not in spalten:
            fehlend.append((tabelle, spalte, definition))
    if not fehlend:
        return []
    if pfad:
        _sicherung_vor_migration(con, pfad)
    for tabelle, spalte, definition in fehlend:
        con.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {definition}")
    return fehlend


def _verlauf_nachtragen(con):
    """Einmalig: Für Aufträge aus älteren Versionen den Verlauf aus dem Änderungsprotokoll übernehmen."""
    if con.execute("SELECT 1 FROM einstellungen WHERE schluessel='verlauf_nachgetragen'").fetchone():
        return
    texte = {"auftrag_angelegt": "Auftrag angelegt", "auftrag_geaendert": "Auftragsdaten geändert"}
    for a in con.execute("SELECT id, eingang_am FROM auftraege").fetchall():
        eintraege = con.execute("SELECT * FROM protokoll WHERE objekt='auftrag' AND objekt_id=? ORDER BY id",
                                (a["id"],)).fetchall()
        if not eintraege:
            con.execute("INSERT INTO auftrag_verlauf (auftrag_id, zeitpunkt, benutzer, ereignis, details) "
                        "VALUES (?,?,?,?,?)", (a["id"], a["eingang_am"], "system", "Auftrag angelegt", None))
        for e in eintraege:
            if e["aktion"] == "auftrag_status":
                d = json.loads(e["details"] or "{}")
                text, details = "Status geändert", f"{d.get('von')} → {d.get('nach')}"
            else:
                text, details = texte.get(e["aktion"], e["aktion"]), None
            con.execute("INSERT INTO auftrag_verlauf (auftrag_id, zeitpunkt, benutzer, ereignis, details) "
                        "VALUES (?,?,?,?,?)", (a["id"], e["zeitpunkt"], e["benutzer"], text, details))
    con.execute("INSERT INTO einstellungen VALUES ('verlauf_nachgetragen', ?)", (json.dumps(jetzt()),))


def _sicherung_vor_migration(con, pfad):
    ziel_ordner = Path(pfad).parent / "backups"
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    ziel = ziel_ordner / f"vor_update_{datetime.now():%Y-%m-%d_%H%M%S}.db"
    if ziel.exists():  # nie eine ältere Sicherung überschreiben
        ziel = ziel.with_name(f"{ziel.stem}_{datetime.now():%f}.db")
    kopie = sqlite3.connect(ziel)
    with kopie:
        con.backup(kopie)
    kopie.close()


# ---------------------------------------------------------------- Einstellungen

def einstellungen(con=None):
    con = con or get_db()
    werte = dict(STANDARD_EINSTELLUNGEN)
    for r in con.execute("SELECT schluessel, wert FROM einstellungen"):
        try:
            werte[r["schluessel"]] = json.loads(r["wert"])
        except (TypeError, ValueError):
            werte[r["schluessel"]] = r["wert"]
    return werte


def einstellung(name, con=None):
    return einstellungen(con).get(name)


def einstellungen_speichern(werte: dict, con=None):
    con = con or get_db()
    for k, v in werte.items():
        con.execute(
            "INSERT INTO einstellungen (schluessel, wert) VALUES (?, ?) "
            "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
            (k, json.dumps(v)),
        )


# ---------------------------------------------------------------- Protokoll

def _hash(vorher, zeitpunkt, benutzer, aktion, objekt, objekt_id, details):
    roh = json.dumps([vorher, zeitpunkt, benutzer, aktion, objekt, objekt_id, details], ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()


def protokollieren(aktion, objekt=None, objekt_id=None, details=None, con=None):
    """Schreibt einen Eintrag ins Änderungsprotokoll. Jeder Eintrag enthält den Hash des vorherigen."""
    con = con or get_db()
    benutzer = aktueller_benutzer()
    if details is not None and not isinstance(details, str):
        details = json.dumps(details, ensure_ascii=False, default=str)
    letzte = con.execute("SELECT hash FROM protokoll ORDER BY id DESC LIMIT 1").fetchone()
    vorher = letzte["hash"] if letzte else "0" * 64
    zeit = jetzt()
    h = _hash(vorher, zeit, benutzer, aktion, objekt, objekt_id, details)
    con.execute(
        "INSERT INTO protokoll (zeitpunkt, benutzer, aktion, objekt, objekt_id, details, hash_vorher, hash) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (zeit, benutzer, aktion, objekt, objekt_id, details, vorher, h),
    )


def protokoll_pruefen(con=None):
    """Prüft die Hash-Kette. Gibt eine Liste mit Fehlern zurück (leer = in Ordnung)."""
    con = con or get_db()
    fehler = []
    vorher = "0" * 64
    for r in con.execute("SELECT * FROM protokoll ORDER BY id"):
        if r["hash_vorher"] != vorher:
            fehler.append(f"Eintrag {r['id']}: Verkettung unterbrochen (Eintrag davor fehlt oder wurde verändert).")
        erwartet = _hash(r["hash_vorher"], r["zeitpunkt"], r["benutzer"], r["aktion"], r["objekt"],
                         r["objekt_id"], r["details"])
        if erwartet != r["hash"]:
            fehler.append(f"Eintrag {r['id']}: Inhalt wurde nachträglich verändert.")
        vorher = r["hash"]
    return fehler


class Transaktion:
    """Kontextmanager für eine schreibende Transaktion (BEGIN IMMEDIATE sperrt sofort)."""

    def __init__(self, con):
        self.con = con

    def __enter__(self):
        self.con.execute("BEGIN IMMEDIATE")
        return self.con

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.con.execute("COMMIT")
        else:
            self.con.execute("ROLLBACK")
        return False
