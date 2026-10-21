"""Protokolldatei des Programms (technisches Log, nicht das GoBD-Änderungsprotokoll).

`Daten/logs/rsb.log`, rotierend (5 Dateien à 2 MB), UTF-8. Zusätzlich Ausgabe auf der Konsole bzw. im
Docker-Log. Die Logs gehören nicht in die Datensicherung.
"""
import logging
import logging.handlers
import os
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_eingerichtet = False


def einrichten(daten_dir, stufe=None):
    """Logging einmalig einrichten. Gibt den Pfad der Protokolldatei zurück."""
    global _eingerichtet
    ordner = Path(daten_dir) / "logs"
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / "rsb.log"
    if _eingerichtet:
        return datei
    stufe = (stufe or os.environ.get("RSB_LOG_STUFE") or "INFO").upper()
    wurzel = logging.getLogger()
    wurzel.setLevel(getattr(logging, stufe, logging.INFO))
    datei_h = logging.handlers.RotatingFileHandler(datei, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8")
    datei_h.setFormatter(logging.Formatter(FORMAT))
    wurzel.addHandler(datei_h)
    konsole = logging.StreamHandler()
    konsole.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M"))
    wurzel.addHandler(konsole)
    logging.getLogger("waitress.queue").setLevel(logging.ERROR)  # „Task queue depth“ ist kein Fehler
    _eingerichtet = True
    return datei


log = logging.getLogger("rsb")
