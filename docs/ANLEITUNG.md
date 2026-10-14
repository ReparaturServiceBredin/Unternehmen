# Bedienungsanleitung

## 1. Erste Schritte

1. `RSB-Buchhaltung.exe` starten. Die Buchhaltung öffnet sich als eigenes Fenster; das Programmsymbol neben der
   Uhr zeigt, dass sie läuft (Rechtsklick → Beenden). Ein Passwort ist standardmäßig aus
   (einschaltbar unter *Einstellungen → Passwortschutz*).
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
1. `RSB-Buchhaltung.exe` in einen Ordner legen, aber noch **nicht** starten (bzw. das schwarze Fenster schließen).
2. Die Backup-ZIP in den Ordner `Daten` entpacken und vorhandene Dateien ersetzen.
3. Die EXE starten (falls der Passwortschutz eingeschaltet war: mit dem bisherigen Passwort anmelden).
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

## 10. Anfragen aus dem Kontaktformular

Wer auf www.reparatur-bredin.de das Kontaktformular ausfüllt, erzeugt eine E-Mail an kontakt@reparatur-bredin.de.
Das Tool holt diese E-Mails selbst ab und wertet sie aus:

1. Es liest die Felder **Name, Telefon, Email, Geraet und Nachricht**.
   Vor- und Nachname werden automatisch getrennt, auch bei „Kochendörfer Kai“, also Nachname zuerst.
2. Es vergibt **Punkte** nach festen Regeln. Für Spam sprechen zum Beispiel Links, Werbewörter wie SEO oder Krypto,
   Zeichensalat, fremde Schriftzeichen, ungültige Kontaktdaten und englische Werbetexte. Für eine echte Anfrage sprechen
   Wörter wie Display, Akku, Jura, Laptop, defekt oder eine deutsche Telefonnummer.
   Unter jeder Anfrage steht, wie die Punkte zustande kamen.
3. Das Ergebnis:
   - **Echte Anfrage:** Der Kunde wird automatisch als **Interessent** angelegt, die Anfrage steht in seinen Notizen.
     Gibt es die E-Mail-Adresse oder Telefonnummer schon, wird die Anfrage dem **vorhandenen** Kunden zugeordnet.
   - **Unsicher:** Die Anfrage erscheint unter *Anfragen → Zu prüfen*. Sie können den Namen korrigieren und mit
     einem Klick den Kunden anlegen. Alternativ verwerfen oder als Spam markieren.
   - **Spam:** Es wird kein Kunde angelegt. Spam wird nach 30 Tagen automatisch gelöscht.
4. Schreiben Sie dem Interessenten eine Rechnung, wird er automatisch zum normalen Kunden.
5. Interessenten ohne Auftrag schlägt das Tool nach 6 Monaten (einstellbar) zum Löschen vor (Datenschutz).

Neue Anfragen sehen Sie in der Navigation an der roten Zahl neben **Anfragen** und auf der Übersicht.

### Einrichtung (Einstellungen → Anfragen)

| Feld | Eintrag |
|---|---|
| IMAP-Server | `imap.ionos.de`, Port `993` |
| Benutzername / Passwort | leer lassen, dann werden die Zugangsdaten vom E-Mail-Versand verwendet |
| Ordner | `INBOX` (Posteingang) |
| Erledigte verschieben nach | `Anfragen erledigt` (der Ordner wird automatisch angelegt) |
| Formular-E-Mails erkennen am Text | `A new form has been submitted` |

Dann den Haken **„Postfach automatisch prüfen“** setzen und einmal **„Postfach jetzt prüfen“** klicken.
Andere E-Mails im Postfach werden **nicht** angefasst.

**Wichtig – Weiterleitung an Gmail:** Das Tool liest bei IONOS nur E-Mails, die dort auch **gespeichert**
bleiben. Prüfen Sie im IONOS-Webmail bzw. Kundenkonto bei der Weiterleitung von kontakt@ an Gmail, dass
**„Kopie im Postfach behalten“** (oder ähnlich) eingeschaltet ist. Ist kontakt@ nur eine reine Weiterleitung
ohne eigenes Postfach, tragen Sie stattdessen Gmail ein: `imap.gmail.com`, Port 993, Benutzer
reparatur-bredin@gmail.com. Als Passwort dient dort ein **App-Passwort**
(Google-Konto → Sicherheit → 2-Faktor-Bestätigung → App-Passwörter).

**Ohne Postfach-Zugang oder zum Testen:** Über *Anfragen → Anfrage einfügen* den Text einer Formular-E-Mail
hineinkopieren. Die Anfrage wird genauso geprüft.

Die Anfragen werden nur abgeholt, **solange das Programm läuft**. Beim nächsten Start holt das Tool alles nach,
was in den letzten 60 Tagen eingegangen ist.

## 11. Reparaturaufträge (Tafel) und Kostenvoranschläge

Unter **Verkauf → Reparaturaufträge** sehen Sie alle Aufträge auf einer Tafel mit drei Spalten:
**Offen → In Arbeit → Erledigt**. Die Übersicht zeigt die Anzahl je Spalte.

**Auftrag anlegen** – drei Wege:
- auf der Tafel über **„+ Neuer Auftrag“** (Kunde, Gerät, Seriennummer/IMEI, Zubehör, Fehler),
- aus einer **Anfrage** über „Reparaturauftrag anlegen“. Gerät und Fehlerbeschreibung werden übernommen.
- beim **Kunden** über „+ Reparaturauftrag“.

**Kostenvoranschlag (KVA):** Im Auftrag auf **„KVA erstellen“** klicken. Positionen einfügen wie bei einer Rechnung.
Danach **festschreiben**, dann bekommt er eine Nummer (`KV-2026-0001`), und **per E-Mail senden**.
Die Gültigkeit beträgt standardmäßig 30 Tage (*Einstellungen → Rechnung & Steuer*).

**Verschieben:** Ziehen Sie eine Karte mit der Maus in eine andere Spalte.
Ohne Maus, zum Beispiel auf dem Tablet, nutzen Sie die Knöpfe auf der Karte („Starten →“, „Erledigt ✓“, „←“).
Innerhalb einer Spalte können Sie die Reihenfolge ebenfalls per Ziehen ändern.

**Erledigt → Rechnung:** Ziehen Sie einen Auftrag auf **Erledigt**, dann passiert Folgendes:
1. Es entsteht automatisch ein **Rechnungsentwurf**, mit allen Positionen aus dem KVA, dem Kunden, dem Gerät
   und der Seriennummer im Betreff und dem heutigen Tag als Leistungsdatum.
2. Der Entwurf öffnet sich sofort. Sie prüfen ihn (z. B. ob noch ein Teil dazukam) und klicken auf
   **„Festschreiben & Nummer vergeben“**.

Die Rechnung wird bewusst **nicht ungefragt festgeschrieben**. Eine festgeschriebene Rechnung lässt sich nur noch
stornieren. Ein versehentlicher Zug auf „Erledigt“ soll keine Rechnungsnummer verbrauchen.
Wird ein Auftrag zurück- und wieder auf „Erledigt“ gezogen, entsteht **keine** zweite Rechnung.

Die Spalte „Erledigt“ zeigt die letzten 30 Tage, ältere Aufträge über „alle anzeigen“.
