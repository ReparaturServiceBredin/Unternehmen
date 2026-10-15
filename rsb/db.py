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
    "abo_modus": "entwurf",          # entwurf = Rechnungsentwürfe anlegen / automatisch = festschreiben + per E-Mail senden
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
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    _migrieren(con)
    vorhanden = {r["schluessel"] for r in con.execute("SELECT schluessel FROM einstellungen")}
    for k, v in STANDARD_EINSTELLUNGEN.items():
        if k not in vorhanden:
            con.execute("INSERT INTO einstellungen VALUES (?, ?)", (k, json.dumps(v)))
    if not con.execute("SELECT 1 FROM vertragsarten LIMIT 1").fetchone():
        for va in STANDARD_VERTRAGSARTEN:
            con.execute("INSERT INTO vertragsarten (name, kategorie, beschreibung, abrechnung, laufzeit_monate, "
                        "mindestlaufzeit_monate, preis, einkauf, auto_verlaengern, erstellt_am) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)", (*va, jetzt()))
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


def _migrieren(con):
    """Ergänzt neue Spalten in bestehenden Datenbanken (Updates ohne Datenverlust)."""
    spalten = {r["name"] for r in con.execute("PRAGMA table_info(kunden)")}
    if "interessent" not in spalten:
        con.execute("ALTER TABLE kunden ADD COLUMN interessent INTEGER NOT NULL DEFAULT 0")
    if "quelle" not in spalten:
        con.execute("ALTER TABLE kunden ADD COLUMN quelle TEXT")
    vspalten = {r["name"] for r in con.execute("PRAGMA table_info(vertraege)")}
    if vspalten and "abgerechnet_bis" not in vspalten:
        con.execute("ALTER TABLE vertraege ADD COLUMN abgerechnet_bis TEXT")


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
    benutzer = session.get("benutzer", "system") if has_request_context() else "system"
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
