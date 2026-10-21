"""Rechnerabhängige Einstellungen aus der Umgebung bzw. einer `.env`-Datei.

Reihenfolge: bereits gesetzte Umgebungsvariablen gewinnen, dann die erste gefundene `.env`:
  1. Datei aus `RSB_ENV_DATEI`
  2. `.env` neben dem Programm (EXE-Ordner bzw. Projektordner)
  3. `/etc/rsb-buchhaltung/rsb.env` (Linux-Server)

Format: eine Zuweisung je Zeile `NAME=Wert`, `#` leitet Kommentare ein, Anführungszeichen sind erlaubt.
"""
import os
import sys
from pathlib import Path

# Alle bekannten Werte mit Erklärung (für .env.beispiel und die Anleitung)
WERTE = {
    "RSB_MODUS": "desktop (Standard, Windows mit Fenster) oder server (Linux/Docker, nur Browser-Zugriff)",
    "RSB_DATEN": "Datenordner (Server/Docker z. B. /daten)",
    "RSB_HOST": "Netzwerkadresse, auf der das Programm lauscht (Server: 0.0.0.0)",
    "RSB_PORT": "Port (Standard 5000)",
    "RSB_THREADS": "gleichzeitige Anfragen (Standard 8)",
    "RSB_HINTER_PROXY": "1 = läuft hinter einem Reverse-Proxy (Caddy/nginx) – echte Client-Adresse übernehmen",
    "RSB_SICHERE_COOKIES": "1 = Zugriff nur per HTTPS (Cookies mit Secure-Flag)",
    "RSB_ERSTES_PASSWORT": "nur beim ersten Start: Passwort für die Anmeldung setzen (danach entfernen)",
    "RSB_LOG_STUFE": "INFO (Standard), DEBUG, WARNING",
    "RSB_KEIN_BROWSER": "1 = beim Start kein Fenster öffnen",
    "RSB_KEIN_SYMBOL": "1 = kein Symbol neben der Uhr",
    "RSB_KEIN_UPDATE": "1 = keine automatischen Updates (EXE)",
}


def _programm_ordner():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def kandidaten():
    liste = []
    if os.environ.get("RSB_ENV_DATEI"):
        liste.append(Path(os.environ["RSB_ENV_DATEI"]))
    liste.append(_programm_ordner() / ".env")
    if os.name != "nt":
        liste.append(Path("/etc/rsb-buchhaltung/rsb.env"))
    return liste


def lesen(pfad):
    """Zuweisungen einer .env-Datei als dict (ohne die Umgebung zu ändern)."""
    werte = {}
    for zeile in Path(pfad).read_text(encoding="utf-8").splitlines():
        z = zeile.strip()
        if not z or z.startswith("#") or "=" not in z:
            continue
        name, wert = z.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        wert = wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        elif " #" in wert:
            wert = wert.split(" #", 1)[0].rstrip()
        if name:
            werte[name] = wert
    return werte


def laden(pfade=None):
    """Erste vorhandene .env in die Umgebung übernehmen (bestehende Werte bleiben). Gibt den Pfad zurück."""
    for pfad in (pfade if pfade is not None else kandidaten()):
        if Path(pfad).is_file():
            for name, wert in lesen(pfad).items():
                os.environ.setdefault(name, wert)
            return Path(pfad)
    return None


def ja(name):
    return (os.environ.get(name) or "").strip().lower() in ("1", "ja", "true", "yes", "on")


def server_modus():
    return (os.environ.get("RSB_MODUS") or "").strip().lower() == "server"
