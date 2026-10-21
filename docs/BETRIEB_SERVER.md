# Betrieb auf einem Linux-Server (Docker)

Das Programm läuft hier als Server: kein Fenster, kein Symbol neben der Uhr. Alle Geräte (PC, Tablet, Handy) öffnen
es im Browser. Die Windows-EXE bleibt unverändert nutzbar.

## Voraussetzungen

- Linux-Rechner oder gemieteter Server mit **Docker** und **Docker Compose**
  (Debian/Ubuntu: `sudo apt install docker.io docker-compose-plugin`)
- Für Zugriff aus dem Internet: eine Domain (z. B. `buchhaltung.reparatur-bredin.de`) und HTTPS über einen
  Reverse-Proxy (unten: Caddy, holt das Zertifikat automatisch)
- Bei gemieteten Servern: Standort Deutschland/EU und **Auftragsverarbeitungsvertrag** mit dem Anbieter (DSGVO)

## Einrichten (einmalig)

```bash
git clone https://github.com/ReparaturServiceBredin/Unternehmen.git rsb
cd rsb
cp .env.beispiel .env
nano .env          # RSB_ERSTES_PASSWORT setzen (mindestens 8 Zeichen)
docker compose up -d --build
docker compose logs -f     # beenden mit Strg+C
```

Danach im Browser `http://<server>:5000` (nur lokal, siehe Port-Freigabe in `docker-compose.yml`) bzw. über den
Reverse-Proxy öffnen und mit dem Passwort anmelden. **Dann `RSB_ERSTES_PASSWORT` aus der `.env` löschen** und
`docker compose up -d` ausführen. Das Passwort lässt sich jederzeit unter *Einstellungen → Passwortschutz* ändern.

## Bestehende Daten übernehmen

1. In der Windows-Version: *Einstellungen → Backup → Jetzt sichern* (ZIP enthält Datenbank, Belege, Fotos und den
   Schlüssel für gespeicherte Zugangsdaten).
2. Auf dem Server den Container stoppen (`docker compose down`), die ZIP in den Ordner `daten/` entpacken
   (vorhandene Dateien überschreiben), Rechte setzen: `sudo chown -R 1000:1000 daten`.
3. `docker compose up -d`, anmelden, *Einstellungen → Datenprüfung* ausführen.

## Einstellungen (`.env`)

| Name | Bedeutung |
|---|---|
| `RSB_MODUS` | `server` (im Docker-Image bereits gesetzt) |
| `RSB_DATEN` | Datenordner im Container, `/daten` |
| `RSB_PORT` | Port im Container, `5000` |
| `RSB_THREADS` | gleichzeitige Anfragen, Standard 8 |
| `RSB_HINTER_PROXY` | `1`, wenn ein Reverse-Proxy davor sitzt (echte Client-Adresse, HTTPS-Erkennung) |
| `RSB_SICHERE_COOKIES` | `1` bei HTTPS – Anmelde-Cookie nur verschlüsselt |
| `RSB_ERSTES_PASSWORT` | nur für den allerersten Start |
| `RSB_LOG_STUFE` | `INFO` (Standard), `DEBUG` zur Fehlersuche |

Im Server-Modus ist die **Anmeldung immer Pflicht**, auch wenn sie in den Einstellungen ausgeschaltet ist.

## HTTPS mit Caddy (Zugriff aus dem Internet)

`Caddyfile`:

```
buchhaltung.reparatur-bredin.de {
    reverse_proxy 127.0.0.1:5000
}
```

Caddy holt und erneuert das Zertifikat selbst. In der `.env` dann `RSB_HINTER_PROXY=1` und
`RSB_SICHERE_COOKIES=1` setzen. Port 5000 nie direkt ins Internet freigeben – nur 80/443 für Caddy.

## Updates

```bash
cd rsb
git pull
docker compose up -d --build
```

Beim Start ergänzt das Programm neue Datenbankfelder selbst und legt vorher automatisch eine Sicherung an.

## Sicherung, Protokoll, Wartung

- **Daten:** alles liegt im Ordner `daten/` (Datenbank, Belege, Fotos, `backups/` mit den täglichen Sicherungen).
  Diesen Ordner zusätzlich außer Haus sichern (z. B. per `rsync` auf ein NAS; später automatisch nach SharePoint).
- **Technisches Protokoll:** `daten/logs/rsb.log` (rotierend) bzw. `docker compose logs`.
- **Hintergrundaufgaben** (Anfragen abrufen, Verträge abrechnen, Raten-Erinnerungen, Löschfristen) laufen nur in
  einem Prozess je Datenordner (`daten/hintergrund.sperre`).
- **Stoppen:** `docker compose down` – das Programm schließt die Datenbank sauber.
- **Uhrzeit:** Der Container läuft in deutscher Zeit (`TZ=Europe/Berlin`).
