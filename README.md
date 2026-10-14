# Reparatur Service Bredin – Buchhaltung & Rechnungen

Eigenes Rechnungs- und Buchhaltungsprogramm für **Reparatur Service Bredin** (Inhaber Dennis Bredin, Möckmühl).
Es läuft lokal auf Ihrem Windows-PC, die Bedienung erfolgt im Browser, und es entstehen **keine laufenden Kosten**.

**Stand: Etappe 1** – Kunden, Leistungen/Artikel mit Marge, Rechnungen als PDF mit Logo und GiroCode, Druck,
E-Mail-Versand mit Protokoll, Storno, unveränderbare fortlaufende Nummern, Passwortschutz, tägliches Backup.

| Dokument | Inhalt |
|---|---|
| [docs/ANLEITUNG.md](docs/ANLEITUNG.md) | Bedienung: Rechnung schreiben, Layout & Textbausteine ändern, Backup & Wiederherstellung |
| [docs/RECHT_UND_GOBD.md](docs/RECHT_UND_GOBD.md) | Pflichtangaben, E-Rechnung, Aufbewahrung, GoBD – und ehrlich: wo die Grenzen liegen |
| [docs/ETAPPEN.md](docs/ETAPPEN.md) | Ihre Vorgaben, Technik-Entscheidung und Fahrplan der Etappen |

---

## Installation unter Windows 11 (einmalig, ca. 10 Minuten)

1. **Programm herunterladen:** Auf GitHub im Repository oben auf **Code → Download ZIP** klicken.
2. **Entpacken** nach z. B. `C:\RSB-Buchhaltung` (Rechtsklick auf die ZIP-Datei → *Alle extrahieren*).
   Bitte **nicht** in einen OneDrive-Ordner – die Datenbank verträgt keine gleichzeitige Synchronisation.
3. Im Ordner doppelt auf **`installieren.bat`** klicken.
   - Fehlt Python, wird es automatisch installiert (über *winget*). Danach `installieren.bat` **noch einmal** starten.
   - Falls Windows „Der Computer wurde durch Windows geschützt“ meldet: *Weitere Informationen → Trotzdem ausführen*.
4. Fertig. Die Installation braucht nur dieses eine Mal Internet.

## Starten

- Doppelklick auf **`start.bat`**. Es öffnet sich ein schwarzes Fenster (bitte **offen lassen**) und
  der Browser mit `http://localhost:5000`.
- Beim **ersten Start** legen Sie ein Passwort fest und tragen unter *Einstellungen → Firmendaten* Anschrift,
  Steuernummer und Bankverbindung ein.
- Beenden: das schwarze Fenster schließen.

Tipp: Rechtsklick auf `start.bat` → *Weitere Optionen → Verknüpfung erstellen* und die Verknüpfung auf den Desktop legen.

## Ihre Daten – ein einziger Ordner

Alles liegt im Ordner **`Daten`** neben dem Programm:

```
Daten\
  buchhaltung.db      Datenbank (Kunden, Artikel, Rechnungen, Protokoll)
  dokumente\2026\     archivierte Original-PDFs aller festgeschriebenen Rechnungen
  belege\             (ab Etappe 4) Belege zu Ausgaben
  bilder\             Ihr hochgeladenes Logo
  backups\            automatische Backups (ZIP)
  geheim\             Schlüssel für das verschlüsselte E-Mail-Passwort – nicht weitergeben
```

Backups, Wiederherstellung und NAS-Kopie: siehe [docs/ANLEITUNG.md](docs/ANLEITUNG.md#backup-und-wiederherstellung).

## Technik (kurz)

Python 3 · Flask (Weboberfläche) · Waitress (lokaler Webserver) · SQLite (Datenbank in einer Datei) ·
ReportLab (PDF) · cryptography (Verschlüsselung) – alles Open Source und kostenlos.
Das Programm ist nur vom eigenen PC aus erreichbar (`127.0.0.1`).

## Für Entwickler

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest              # automatische Tests
RSB_DATEN=Testdaten .venv/bin/python -m rsb.beispieldaten   # Beispieldaten in separatem Ordner
RSB_DATEN=Testdaten .venv/bin/python -m rsb                 # starten
```
Umgebungsvariablen: `RSB_DATEN` (Datenordner), `RSB_HOST`, `RSB_PORT`, `RSB_KEIN_BROWSER=1`.

## So sieht es aus

| Rechnung schreiben (mit Marge je Position) | Fertige Rechnung (PDF) |
|---|---|
| ![Rechnung bearbeiten](docs/bilder/rechnung_bearbeiten.png) | ![Beispielrechnung](docs/bilder/beispielrechnung.png) |
| **Layout-Einstellungen mit Vorschau** | **Festgeschrieben & versendet** |
| ![Layout](docs/bilder/layout.png) | ![Versendet](docs/bilder/rechnung_versendet.png) |

Beispiel-PDF: [docs/Beispielrechnung_RE-2026-0001.pdf](docs/Beispielrechnung_RE-2026-0001.pdf) (mit Beispieldaten).
