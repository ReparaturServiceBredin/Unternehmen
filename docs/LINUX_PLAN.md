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
| Zeitzone | 0.32.0 | Alle Zeitpunkte über `hilfen.jetzt_dt()`/`heute_datum()` in Europe/Berlin, auch auf UTC-Servern; Regeltest erlaubt 0 Ausnahmen |
| Mehrbenutzer | 0.33.0 | `rsb/benutzer.py`: weitere Benutzer (Rollen Inhaber/Mitarbeiter), Protokoll mit Namen, Sitzungsende bei Deaktivieren/neuem Passwort; Anmeldesperre nach 5 Fehlversuchen |
| Datenumzug | 0.33.0 | Schlüssel in jeder Sicherung, Sicherung im Browser hochladen und einspielen, Server startet selbst neu, Server-Passwort bleibt erhalten |
| Server-Feinschliff | 0.33.0 | keine Anmeldeschleife, Passwortschutz auf dem Server nicht abschaltbar, QR-Codes mit Server-Adresse, Uploads bis 4 GB |
| Docker | 0.31.0 | `Dockerfile`, `docker-compose.yml`, `.env.beispiel`, Anleitung `docs/BETRIEB_SERVER.md` |

## Offen

1. **SharePoint (Microsoft 365) anbinden** – zurückgestellt (Inhaber, 21.10.2026). Über Microsoft Graph, App-Registrierung in Entra ID durch den Inhaber:
   - a) tägliche Sicherung (ZIP) zusätzlich in eine SharePoint-Dokumentbibliothek hochladen (Sicherung außer Haus),
   - b) festgeschriebene Belege (Rechnungen, KVA, Angebote, AB, Annahmescheine) als PDF in `Belege/<Jahr>/<Art>/`
     ablegen (nur Kopie, Original bleibt im Programm),
   - c) Eingangsrechnungen aus einem SharePoint-Ordner abholen,
   - d) optional Anmeldung mit Microsoft-365-Konto (OIDC).
   Die Datenbank selbst bleibt lokal auf dem Server – nie in SharePoint/OneDrive (Beschädigungsgefahr).
   Zugangsdaten (Client-Secret) verschlüsselt in der Datenbank, Eingabe nur durch den Inhaber in den Einstellungen.
2. **IONOS-Server einrichten** – Schritte in `docs/BETRIEB_SERVER.md`, Abschnitt „IONOS“.

## Entscheidungen

- **Uhrzeiten (21.10.2026):** Alle Zeitpunkte sind deutsche Zeit. Bestehende Einträge bleiben unverändert (stammen
  von einem Rechner in Deutschland), neue werden unabhängig vom Server in Europe/Berlin gespeichert.
- **Schlüssel im Backup (21.10.2026):** Der Schlüssel (`geheim/schluessel.key`) gehört in jede Sicherung (seit 0.33.0;
  vorher nur in `vor_wiederherstellung_*.zip`), damit eine
  Wiederherstellung alle gespeicherten Zugangsdaten mitbringt. Folge: Sicherungen sind so schützenswert wie die
  Zugangsdaten selbst – Ablage außer Haus nur an zugriffsgeschützten Orten (eigene SharePoint-Bibliothek, NAS).
- **Hosting (21.10.2026):** IONOS (VPS, Rechenzentrum Deutschland, Auftragsverarbeitungsvertrag im IONOS-Kundenkonto
  abschließen). Später ist ein eigener Rechner im Haus möglich – der Umzug ist derselbe Ablauf (Sicherung einspielen).
- Eine Codebasis für Windows und Linux; Windows-Teile nur in `rsb/fenster.py` und `rsb/update.py`.
- SQLite bleibt (ein Server, wenige Nutzer). Im Server-Modus läuft genau **ein** Prozess (Waitress mit Threads).
- Updates im Server-Betrieb über ein neues Docker-Image (`docker compose pull && docker compose up -d`); vorher
  sichert das Programm beim Start automatisch (Migrationen legen wie bisher eine Sicherung an).
