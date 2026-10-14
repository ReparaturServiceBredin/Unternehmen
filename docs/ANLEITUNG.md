# Bedienungsanleitung

## 1. Erste Schritte

1. `start.bat` starten und beim ersten Mal ein Passwort festlegen (mindestens 8 Zeichen).
2. **Einstellungen → Firmendaten:** Anschrift, Telefon, Steuernummer, Bank und IBAN eintragen.
   Diese Angaben erscheinen in der Fußzeile jeder Rechnung.
3. **Einstellungen → E-Mail:** Den Zugang zu Ihrem Postfach eintragen und mit „Test-E-Mail senden“ prüfen.
4. **Leistungen & Artikel:** Ihre Festpreise anlegen, z. B. „Kaffeemaschinen-Wartung“ für 89 €.

## 2. Eine Rechnung schreiben

1. **Rechnungen → + Neue Rechnung** (oder beim Kunden „+ Rechnung für diesen Kunden“).
2. Den Kunden wählen. Das Zahlungsziel wird automatisch gesetzt: 14 Tage für Privat- und 30 Tage für Firmenkunden.
3. Das **Leistungsdatum** eintragen, also den Tag der Reparatur.
4. Positionen hinzufügen:
   - über **„Leistung/Artikel aus Liste einfügen“** oder
   - über **„+ Freie Position“** für Einzelfälle.

   Zu jeder Position sehen Sie Teilekosten und Marge. Diese Werte erscheinen **nicht** auf der Rechnung.
5. **Speichern & Vorschau** zeigt das PDF mit dem Aufdruck „ENTWURF“.
6. **Festschreiben & Nummer vergeben** gibt der Rechnung die nächste Nummer (z. B. `RE-2026-0001`) und archiviert das PDF.
   **Ab diesem Moment ist die Rechnung nicht mehr änderbar.**
7. Danach stehen diese Knöpfe zur Verfügung:
   - **Per E-Mail senden:** Die Rechnung geht als PDF-Anhang an den Kunden, mit dem Standardtext aus den Textbausteinen.
   - **Drucken:** Das PDF öffnet sich mit dem Druckdialog.
   - **PDF herunterladen**

### Fehler in einer festgeschriebenen Rechnung?

Löschen oder Ändern ist absichtlich nicht möglich (siehe GoBD). So gehen Sie stattdessen vor:

1. Die Rechnung öffnen und auf **Stornieren** klicken. Es entsteht eine **Stornorechnung** mit eigener Nummer und negativem Betrag.
2. **Als neue Rechnung kopieren** übernimmt alle Positionen in einen neuen Entwurf. Dort korrigieren Sie den Fehler und schreiben die neue Rechnung fest.
3. Schicken Sie dem Kunden beides: die Stornorechnung und die neue Rechnung.

## 3. Layout ändern (ohne Programmierung)

Unter **Einstellungen → Layout** zeigt rechts eine Musterrechnung, wie das Ergebnis aussieht.

| Einstellung | Wirkung |
|---|---|
| Hauptfarbe | Titel, Tabellenkopf, Linien (Standard: Blau aus Ihrem Logo `#1C54A3`) |
| Zweitfarbe | Grautöne für kleine Texte |
| Schrift | Montserrat (wie im Logo), Open Sans, Lato, Helvetica, Times |
| Schriftgröße | Grundgröße in Punkt (Standard 9,5) |
| Logo, Logobreite, Position | Eigenes Logo hochladen (PNG mit transparentem Hintergrund ist ideal), Breite in mm, links/mitte/rechts |
| Kopfzeile / zusätzliche Fußzeile | Freier Text, z. B. Öffnungszeiten |
| Falzmarken | Kleine Striche am linken Rand zum Falten für Fensterumschläge |
| GiroCode | QR-Code, den der Kunde mit seiner Banking-App scannt (IBAN, Betrag und Rechnungsnummer sind dann schon ausgefüllt) |

Nach **Speichern** auf **Vorschau aktualisieren** klicken.

> Layout-Änderungen gelten nur für **neue** Rechnungen. Bereits festgeschriebene Rechnungen bleiben unverändert,
> denn ihr Original-PDF ist archiviert.

Die Fußzeile wird automatisch aus den Firmendaten gebaut (Anschrift, Kontakt, Bank, Steuernummer).

## 4. Textbausteine

Unter **Textbausteine** verwalten Sie diese Texte:

- **Einleitung** (über den Positionen), **Schlusstext** (unter der Rechnung), **Hinweise** (klein gedruckt)
- **E-Mail-Betreff** und **E-Mail-Text** für den Versand

Ein Baustein mit Haken bei **Standard** wird automatisch in jede neue Rechnung bzw. E-Mail übernommen.
Alle anderen fügen Sie beim Schreiben einer Rechnung über das Auswahlfeld „Textbaustein einfügen …“ ein.

**Platzhalter** werden automatisch ersetzt. Die vollständige Liste steht beim Bearbeiten eines Bausteins. Die wichtigsten:

| Platzhalter | Beispiel |
|---|---|
| `{anrede_brief}` | Sehr geehrte Frau Müller, |
| `{nummer}` | RE-2026-0001 |
| `{datum}` / `{faellig_am}` | 14.10.2026 / 28.10.2026 |
| `{betrag}` | 307,80 € |
| `{inhaber}` / `{firma_name}` | Dennis Bredin / Reparatur Service Bredin |

Die mitgelieferten Bausteine „Datensicherung“ und „Gewährleistung“ sind **Beispieltexte**.
Bitte ersetzen Sie sie durch Ihre eigenen Texte und lassen Sie rechtliche Formulierungen im Zweifel prüfen.

## 5. E-Mail-Einstellungen

| Anbieter | SMTP-Server | Port | Verschlüsselung |
|---|---|---|---|
| IONOS (1&1) | smtp.ionos.de | 587 | STARTTLS |
| Strato | smtp.strato.de | 465 | SSL |
| GMX | mail.gmx.net | 587 | STARTTLS |
| web.de | smtp.web.de | 587 | STARTTLS |
| Gmail | smtp.gmail.com | 587 | STARTTLS (nur mit „App-Passwort“) |

Bitte prüfen Sie die Werte bei Ihrem Anbieter. Benutzername ist meist die vollständige E-Mail-Adresse.
Das Passwort wird verschlüsselt gespeichert.
„Kopie an mich (BCC)“ legt jede versendete Rechnung zusätzlich in Ihrem Postfach ab.
Jeder Versand und jeder Fehlversuch steht unter **Protokoll**.

## 6. Backup und Wiederherstellung

**Automatisch:** Beim Programmstart entsteht einmal täglich eine ZIP-Datei unter `Daten\backups`.
Die letzten 30 Backups bleiben erhalten (einstellbar).

**NAS:** Unter *Einstellungen → Backup* tragen Sie einen zweiten Ordner ein, z. B. `\\NAS\Backup\Buchhaltung`
oder ein Netzlaufwerk wie `Z:\Backup\Buchhaltung`. Jedes Backup wird dorthin kopiert.
**Empfehlung:** Zusätzlich gelegentlich auf einen USB-Stick kopieren, der nicht dauerhaft am PC steckt (Schutz vor Verschlüsselungstrojanern).

**Manuell:** *Einstellungen → Backup → Backup jetzt erstellen*.

**Wiederherstellen** (z. B. auf einem neuen PC):
1. Das Programm wie oben installieren, aber noch **nicht** starten (bzw. das schwarze Fenster schließen).
2. Die Backup-ZIP in den Ordner `Daten` entpacken und vorhandene Dateien ersetzen.
3. `start.bat` starten und mit dem bisherigen Passwort anmelden.
4. Unter *Einstellungen → E-Mail* das E-Mail-Passwort **neu eingeben**. Der Schlüssel dafür ist aus Sicherheitsgründen nicht im Backup enthalten.
5. Unter **Datenprüfung** kontrollieren, ob alles „In Ordnung“ ist.

Eine Wiederherstellung per Knopfdruck kommt in Etappe 5.

## 7. Datenprüfung

Die Seite **Datenprüfung** prüft drei Dinge:
- Sind alle archivierten PDFs unverändert? Das wird über eine Prüfsumme kontrolliert.
- Sind alle vergebenen Rechnungsnummern lückenlos vorhanden?
- Ist das Änderungsprotokoll vollständig und unverändert?

Rufen Sie sie z. B. einmal im Monat und vor jeder Weitergabe an das Finanzamt auf.

## 8. Umstellung auf Umsatzsteuer (später)

Unter *Einstellungen → Rechnung & Steuer → Besteuerung* auf **Regelbesteuerung** umstellen. Die Folgen:
- Preise in Leistungen und Artikeln gelten dann als **Nettopreise**. Jede Leistung hat einen Steuersatz (Standard 19 %).
- Neue Rechnungen zeigen Netto, USt je Steuersatz und Brutto. Der § 19-Hinweis entfällt.
- Bereits festgeschriebene Rechnungen bleiben unverändert.

Den Zeitpunkt der Umstellung bitte mit dem Finanzamt bzw. einem Steuerberater abstimmen.
Prüfen Sie dann auch Ihre Preise, denn bisher sind es Endpreise.

## 9. Kunden löschen (Datenschutz)

- Kunden **ohne** festgeschriebene Rechnungen können Sie vollständig löschen.
- Kunden **mit** Rechnungen müssen wegen der Aufbewahrungspflicht erhalten bleiben. Sie lassen sich **archivieren** und verschwinden dann aus den Listen.
- Das vollständige Löschkonzept steht in [RECHT_UND_GOBD.md](RECHT_UND_GOBD.md#datenschutz-und-löschkonzept).
