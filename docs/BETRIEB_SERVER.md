# Betrieb auf einem Linux-Server (Docker)

Das Programm läuft hier als Server: kein Fenster, kein Symbol neben der Uhr. Alle Geräte (PC, Tablet, Handy) öffnen
es im Browser. Die Windows-EXE bleibt unverändert nutzbar.

## Voraussetzungen

- Linux-Rechner oder gemieteter Server mit **Docker** und **Docker Compose**
  (Debian/Ubuntu: `sudo apt install docker.io docker-compose-v2`)
- Für Zugriff aus dem Internet: eine Domain (z. B. `buchhaltung.reparatur-bredin.de`) und HTTPS über einen
  Reverse-Proxy (unten: Caddy, holt das Zertifikat automatisch)
- Bei gemieteten Servern: Standort Deutschland/EU und **Auftragsverarbeitungsvertrag** mit dem Anbieter (DSGVO)

## IONOS (gewählter Anbieter)

1. Im IONOS-Kundenkonto einen **VPS Linux** bestellen: Ubuntu 24.04, Rechenzentrum **Deutschland**. Für das
   Programm genügen 2 vCores, 2–4 GB RAM und 80 GB Speicher (Belege und Fotos wachsen mit).
2. Im Kundenkonto unter *Datenschutz* den **Auftragsverarbeitungsvertrag (AVV)** abschließen.
3. In der **Firewall** des Servers (IONOS Cloud Panel → Netzwerk → Firewall-Richtlinien) nur 22 (SSH), 80 und 443
   freigeben – **nicht 5000**.
4. Für die Domain beim DNS einen **A-Eintrag** anlegen, z. B. `buchhaltung` → öffentliche IP des Servers.
5. Per SSH anmelden (`ssh root@<IP>`), System aktualisieren und Docker sowie Caddy installieren:

   ```bash
   apt update && apt -y upgrade
   apt -y install docker.io docker-compose-v2 caddy git
   ```

   Am besten einen eigenen Benutzer mit SSH-Schlüssel anlegen und die Passwort-Anmeldung für SSH abschalten.
6. Weiter mit „Einrichten“ und „HTTPS mit Caddy“ unten. Die Caddy-Konfiguration liegt in `/etc/caddy/Caddyfile`,
   danach `systemctl reload caddy`.

Später auf einen eigenen Rechner im Haus umziehen: dort dieselben Schritte, dann Sicherung einspielen (siehe
„Bestehende Daten übernehmen“). Für Zugriff von außen braucht es dann eine Portfreigabe im Router oder einen
Tunnel – das klären wir, wenn es soweit ist.

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

## Bestehende Daten übernehmen (Umzug vom PC)

1. In der Windows-Version (ab 0.33.0): *Einstellungen → Backup → Backup jetzt erstellen*. Die ZIP enthält Datenbank,
   Belege, Fotos und den Schlüssel für gespeicherte Zugangsdaten (E-Mail- und Bank-Passwörter funktionieren danach
   weiter). Die Datei über die Liste darunter herunterladen.
2. Auf dem Server im Browser anmelden: *Einstellungen → Backup → Sicherung hochladen*, Datei wählen.
3. In der Liste prüfen (Kunden, Aufträge, Firmendaten) und **Wiederherstellen** klicken. Der Server sichert vorher den
   aktuellen Stand, spielt die Sicherung ein und startet von selbst neu (etwa 10 Sekunden).
4. Neu anmelden – das Server-Passwort bleibt erhalten, auch wenn die Sicherung vom PC keins hatte.
   *Einstellungen → Datenprüfung* ausführen. Danach die Windows-Version nicht mehr parallel benutzen.

Von Hand geht es auch: `docker compose down`, ZIP in `daten/` entpacken, `sudo chown -R 1000:1000 daten`,
`docker compose up -d`.

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

Im Server-Modus ist die **Anmeldung immer Pflicht**, auch wenn sie in den Einstellungen ausgeschaltet ist. Nach fünf
falschen Passwörtern von derselben Adresse ist die Anmeldung dort 15 Minuten gesperrt.

## Benutzer

*Einstellungen → Anmeldung & Benutzer → Weitere Benutzer*: eigene Zugänge für Mitarbeiter. Der Inhaber meldet sich
weiter nur mit dem Passwort an (Benutzername leer). Rolle **Mitarbeiter**: alles außer Einstellungen, Backup und
Protokoll; **Inhaber**: alle Rechte. Das Protokoll zeigt, wer was geändert hat. Deaktivieren oder ein neues Passwort
beendet die Sitzungen des Benutzers sofort.

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
- **Neustart nach „Wiederherstellen“** übernimmt Docker (`restart: unless-stopped` in `docker-compose.yml`). Ohne
  Docker (systemd) braucht der Dienst `Restart=always`.
- **Uhrzeit:** Alle Zeitpunkte rechnet das Programm selbst in deutscher Zeit – auch wenn der Server auf UTC läuft.
- **Sicherungen enthalten den Schlüssel** für gespeicherte Zugangsdaten (E-Mail, Bank-API usw.). Sicherungen
  deshalb nur an zugriffsgeschützten Orten ablegen.
