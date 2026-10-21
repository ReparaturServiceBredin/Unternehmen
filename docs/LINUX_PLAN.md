# Plan: Betrieb auf Linux-Server / in der Cloud

Ziel: Das Programm läuft unverändert weiter als Windows-EXE **und** zusätzlich als Server (Docker auf einem
Linux-Rechner bzw. in der Cloud). Alle Geräte greifen per Browser zu. Diese Datei ist die Übergabe für die nächsten
Arbeitssitzungen: Stand, offene Punkte, Entscheidungen.

> Neue Sitzung: „Lies `docs/LINUX_PLAN.md` und `docs/ENTWICKLUNG.md` und mach beim nächsten offenen Punkt weiter.“

## Bereits erledigt

| Punkt | Version | Was |
|---|---|---|
| Fester Datenordner | 0.23.0 | `rsb/datenort.py`, unabhängig vom Startort, `RSB_DATEN` überschreibt |
| Entwickler-Regeln | 0.23.1 | `docs/ENTWICKLUNG.md`, geprüft durch `tests/test_regeln.py` (Pfade, Encoding, Windows-APIs, Zeitzone-Sperrklinke) |
| Feste Abhängigkeiten | 0.23.1 | `requirements.txt` mit Versionen, Windows-Pakete per `sys_platform` |
| Logging in Datei | 0.31.0 | `rsb/logbuch.py`: `Daten/logs/rsb.log`, rotierend (5 × 2 MB), zusätzlich Konsole |
| Konfiguration `.env` | 0.31.0 | `rsb/konfig.py`: `RSB_…`-Werte aus Umgebung oder `.env` (siehe `docs/BETRIEB_SERVER.md`) |
| Sperre Hintergrundjobs | 0.31.0 | `rsb/sperre.py`: nur ein Prozess führt Anfragen-Abruf, Vertragsläufe, Raten, Löschläufe aus |
| Server-Modus | 0.31.0 | `RSB_MODUS=server`: kein Fenster/Symbol/EXE-Update, lauscht im Netz, sauberes Beenden bei SIGTERM |
| Absicherung | 0.31.0 | Anmeldung immer Pflicht im Server-Modus, erstes Passwort per `RSB_ERSTES_PASSWORT`, Sicherheits-Header, `RSB_HINTER_PROXY` (echte Client-IP), sichere Cookies bei HTTPS |
| Docker | 0.31.0 | `Dockerfile`, `docker-compose.yml`, `.env.beispiel`, Anleitung `docs/BETRIEB_SERVER.md` |

## Offen

1. **Zeitzone vollständig auf Europe/Berlin** – ca. 97 Stellen mit `date.today()`/`datetime.now()` auf
   `hilfen.heute_datum()` bzw. eine Berlin-Zeit-Funktion umstellen; `ZEITZONE_HOECHSTENS` in `tests/test_regeln.py`
   schrittweise auf 0 senken. Im Docker-Container ist zusätzlich `TZ=Europe/Berlin` gesetzt (Übergangslösung).
2. **SharePoint (Microsoft 365) anbinden** – über Microsoft Graph, App-Registrierung in Entra ID durch den Inhaber:
   - a) tägliche Sicherung (ZIP) zusätzlich in eine SharePoint-Dokumentbibliothek hochladen (Sicherung außer Haus),
   - b) festgeschriebene Belege (Rechnungen, KVA, Angebote, AB, Annahmescheine) als PDF in `Belege/<Jahr>/<Art>/`
     ablegen (nur Kopie, Original bleibt im Programm),
   - c) Eingangsrechnungen aus einem SharePoint-Ordner abholen,
   - d) optional Anmeldung mit Microsoft-365-Konto (OIDC).
   Die Datenbank selbst bleibt lokal auf dem Server – nie in SharePoint/OneDrive (Beschädigungsgefahr).
   Zugangsdaten (Client-Secret) verschlüsselt in der Datenbank, Eingabe nur durch den Inhaber in den Einstellungen.
3. **Mehrbenutzer** – eigene Benutzer statt nur „inhaber“ (Protokoll nennt dann die Person), Rechte optional.
4. **Umzug der bestehenden Daten** – Ablauf: in der Windows-Version Sicherung (ZIP inkl. Schlüssel) erstellen,
   auf dem Server in `/daten` entpacken bzw. über „Sicherung wiederherstellen“ einspielen, Prüfung mit
   *Einstellungen → Datenprüfung*. Danach Windows-Version nur noch als Notfall.
5. **Offene Fragen an den Inhaber**
   - Zeitstempel: sollen alte, in Rechnerzeit gespeicherte Zeitpunkte umgerechnet oder nur neue in Berlin-Zeit
     gespeichert werden? (Vorschlag: nur neue; alte stammen von einem Rechner in Deutschland und stimmen schon.)
   - Schlüssel im Backup: Sicherungen enthalten `geheim/` (zum Entschlüsseln gespeicherter Zugangsdaten). Für
     Sicherungen außer Haus (SharePoint) Schlüssel weglassen oder die ZIP mit Passwort verschlüsseln?
   - Hosting: eigener Linux-Rechner im Haus, gemieteter Server (z. B. Hetzner, Standort Deutschland) oder Azure?
     Für die Cloud zwingend HTTPS (Caddy/Traefik davor) und Auftragsverarbeitungsvertrag mit dem Anbieter.

## Entscheidungen

- Eine Codebasis für Windows und Linux; Windows-Teile nur in `rsb/fenster.py` und `rsb/update.py`.
- SQLite bleibt (ein Server, wenige Nutzer). Im Server-Modus läuft genau **ein** Prozess (Waitress mit Threads).
- Updates im Server-Betrieb über ein neues Docker-Image (`docker compose pull && docker compose up -d`); vorher
  sichert das Programm beim Start automatisch (Migrationen legen wie bisher eine Sicherung an).
