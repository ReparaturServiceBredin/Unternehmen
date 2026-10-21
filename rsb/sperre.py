"""Sperre für Hintergrundaufgaben: nur ein Prozess je Datenordner ruft Anfragen ab, rechnet Verträge ab, verschickt
Raten-Erinnerungen und führt Löschläufe aus – auch wenn versehentlich zwei Instanzen laufen.

Plattformunabhängig über eine Sperrdatei mit Lebenszeichen: Der Besitzer aktualisiert sie regelmäßig. Ist sie älter
als ABGELAUFEN_SEK (Prozess abgestürzt, Rechner aus), darf ein anderer Prozess sie übernehmen.
"""
import json
import os
import threading
import time
from pathlib import Path

LEBENSZEICHEN_SEK = 60
ABGELAUFEN_SEK = 5 * 60


class Sperre:
    def __init__(self, daten_dir, name="hintergrund"):
        self.pfad = Path(daten_dir) / f"{name}.sperre"
        self._halten = False

    def _schreiben(self, fd):
        os.write(fd, json.dumps({"pid": os.getpid(), "seit": time.time()}).encode("utf-8"))
        os.close(fd)

    def erwerben(self):
        for _ in range(2):
            try:
                fd = os.open(self.pfad, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    alter = time.time() - self.pfad.stat().st_mtime
                except FileNotFoundError:
                    continue
                if alter <= ABGELAUFEN_SEK:
                    return False
                try:
                    self.pfad.unlink()  # verwaiste Sperre übernehmen
                except FileNotFoundError:
                    pass
                continue
            self._schreiben(fd)
            self._halten = True
            threading.Thread(target=self._lebenszeichen, daemon=True).start()
            return True
        return False

    def _lebenszeichen(self):
        while self._halten:
            time.sleep(LEBENSZEICHEN_SEK)
            if self._halten:
                try:
                    os.utime(self.pfad)
                except FileNotFoundError:  # von außen entfernt: neu anlegen
                    try:
                        self._schreiben(os.open(self.pfad, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                    except OSError:
                        pass

    def freigeben(self):
        self._halten = False
        try:
            self.pfad.unlink()
        except FileNotFoundError:
            pass
