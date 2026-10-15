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

**Kopie im Ordner „Gesendet“ (IMAP):** Darunter im Abschnitt *IMAP* den Haken „Gesendete Mails im Postfach
ablegen“ setzen, `imap.ionos.de`, Port 993, SSL/TLS. „Gleiche Zugangsdaten wie SMTP“ angehakt lassen. Dann
**„Ordner abrufen“** (wählt „Gesendete Objekte“ vor) → **„Verbindung testen“** → Speichern. Danach liegt jede
versendete Rechnung auch im Postfach unter „Gesendet“. Klappt die Ablage einmal nicht, ist die Mail trotzdem
verschickt – Sie sehen dann einen gelben Hinweis.

**Fehler „Zielcomputer verweigerte die Verbindung“ (WinError 10061):** Das Programm versucht es automatisch ein
zweites Mal. Bleibt der Fehler, blockiert meist ein Virenschutz den Versand aus Programmen (z. B. ESET
„E-Mail-Client-Schutz“ bzw. Firewall-Regel). Dann `RSB-Buchhaltung.exe` dort als vertrauenswürdig freigeben.
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
| IMAP-Server | `imap.ionos.de` |
| Port / Verschlüsselung | `993` mit **SSL/TLS** – oder, falls Port 993 in Ihrem Netz gesperrt ist, `143` mit **STARTTLS** |
| Benutzername / Passwort | leer lassen, dann werden die Zugangsdaten vom E-Mail-Versand verwendet |
| Ordner | `INBOX` (Posteingang) |
| Erledigte verschieben nach | `Anfragen erledigt` (der Ordner wird automatisch angelegt) |
| Formular-E-Mails erkennen am Text | `A new form has been submitted` |

Mit **„Verbindung testen“** prüfen Sie sofort (auch vor dem Speichern) Verbindung, Anmeldung und ob die Ordner
„INBOX“ und „Anfragen erledigt“ vorhanden sind. Beim Wechsel der Verschlüsselung schlägt das Programm den passenden Port
vor. Beide Varianten sind verschlüsselt: Bei STARTTLS meldet sich das Programm erst an, nachdem die Verbindung
verschlüsselt ist. Klappt das nicht, bricht es ab und sendet das Passwort nie unverschlüsselt.

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
- auf der Tafel über **„+ Neuer Auftrag“**. Sie geben Kunde, Status, Gerät, Seriennummer/IMEI, Zubehör, Fehler und
  Notizen ein. Optional verknüpfen Sie gleich einen KVA und laden Fotos hoch. Fotos werden sofort gespeichert. Klappt
  das Anlegen einmal nicht (z. B. Kunde vergessen), bleiben Fotos und Eingaben erhalten.
- aus einer **Anfrage** über „Reparaturauftrag anlegen“. Gerät und Fehlerbeschreibung werden übernommen.
- beim **Kunden** über „+ Reparaturauftrag“ (der Kunde ist dann schon ausgewählt).

**Auftrag öffnen:** Klicken Sie auf eine Karte. Kopf mit Nummer, Status und Eingang, darunter vier Reiter:
- **Auftragsdaten** – alles bearbeitbar, auch Kunde und Status, mit „Speichern“.
- **Kostenvoranschlag** – siehe unten.
- **Fotos** – Kategorie wählen, dann Fotos hineinziehen, „Dateien auswählen“ oder am Handy „Kamera“. Zu jedem Foto
  sehen Sie Upload-Zeit (mit Sekunden), Aufnahmezeit der Kamera, Benutzer und Prüfsumme. **Löschen** geht nur
  mit Begründung: das Foto wird grau markiert, bleibt aber gespeichert. **„Fotodokumentation als PDF“** erzeugt
  ein PDF aller Fotos mit diesen Angaben, z. B. für Versicherung oder Reklamation.
- **Verlauf** – wer wann was gemacht hat (angelegt, Status, KVA, Fotos, Rechnung). Nicht änderbar.

**Kostenvoranschlag (KVA):**
- Noch keiner verknüpft:
  - **„Neuen KVA aus diesem Auftrag erstellen“** – Kunde, Gerät und Fehler sind schon eingetragen.
  - oder unter **„Bestehenden KVA verknüpfen“** einen vorhandenen auswählen. Angezeigt werden freie KVAs des Kunden.
    Sie können nach Nummer, Datum oder Betrag suchen oder „alle Kunden anzeigen“ wählen.
- Verknüpft: Nummer, Datum, Betrag und Status (offen / angenommen / abgelehnt – nach Rückmeldung des Kunden
  einstellen), dazu Öffnen, PDF, Per E-Mail senden und **Verknüpfung lösen**. Der KVA selbst bleibt dabei erhalten.
- Gehört der KVA zu einem anderen Kunden als der Auftrag, erscheint ein gelber Warnhinweis.
- Positionen fügen Sie ein wie bei einer Rechnung. Danach **festschreiben**, dann bekommt er eine Nummer
  (`KV-2026-0001`), und **per E-Mail senden**. Die Gültigkeit beträgt standardmäßig 30 Tage
  (*Einstellungen → Rechnung & Steuer*).
- Die Karten auf der Tafel zeigen **📷 Anzahl** und **„KVA ✓“** bzw. **„kein KVA“**.

**Verschieben:** Ziehen Sie eine Karte mit der Maus in eine andere Spalte.
Ohne Maus, zum Beispiel auf dem Tablet, nutzen Sie die Knöpfe auf der Karte („Starten →“, „Erledigt ✓“, „←“).
Innerhalb einer Spalte können Sie die Reihenfolge ebenfalls per Ziehen ändern.

**Erledigt → Rechnung:** Ziehen Sie einen Auftrag auf **Erledigt**, dann passiert Folgendes:
1. Es entsteht automatisch ein **Rechnungsentwurf**, mit allen Positionen aus dem KVA, dem Kunden, dem Gerät
   und der Seriennummer im Betreff und dem heutigen Tag als Leistungsdatum.
2. Der Entwurf öffnet sich sofort. Sie prüfen ihn (z. B. ob noch ein Teil dazukam) und klicken auf
   **„Festschreiben & Nummer vergeben“**.

Ist **kein KVA verknüpft**, fragt das Programm vorher: *„Kein KVA verknüpft – leeren Rechnungsentwurf erstellen
oder KVA jetzt verknüpfen?“*. „KVA jetzt verknüpfen“ öffnet den Reiter Kostenvoranschlag des Auftrags.

Die Rechnung wird bewusst **nicht ungefragt festgeschrieben**. Eine festgeschriebene Rechnung lässt sich nur noch
stornieren. Ein versehentlicher Zug auf „Erledigt“ soll keine Rechnungsnummer verbrauchen.
Wird ein Auftrag zurück- und wieder auf „Erledigt“ gezogen, entsteht **keine** zweite Rechnung.

Die Spalte „Erledigt“ zeigt die letzten 30 Tage, ältere Aufträge über „alle anzeigen“.

## 12. Verträge, Lizenzen & Garantien (MSP, ESET, Wertgarantie)

Unter **Verkauf → Verträge & Lizenzen** und beim jeweiligen **Kunden** (Abschnitt „Verträge, Lizenzen & Garantien“).

**Neuer Vertrag:** Beim Kunden auf „+ Vertrag / Lizenz“ klicken, eine **Vorlage** wählen (füllt alles vor),
Lizenzschlüssel bzw. Policennummer und ggf. Gerät eintragen, speichern.

| Beispiel | Abrechnung | Ergebnis |
|---|---|---|
| Wertgarantie | nur Dokumentation | keine Rechnung; Ablauf wird überwacht |
| ESET 1/2/3 Jahre | einmal je Laufzeit (12/24/36 Monate) | eine Rechnung zum Beginn; vor Ablauf Erinnerung, Verlängern per Knopf (oder automatisch) |
| MSP-Paket | monatlich | jeden Monat im Voraus, bis zur Kündigung |

**Vertragsarten erweitern:** *Verträge & Lizenzen → Vertragsarten → + Neue Vertragsart* – z. B.
„ESET Internet Security 3 Geräte, 1 Jahr“ mit Preis und Einkauf. Steht danach sofort als Vorlage bereit.

**Abrechnung:** Das Programm prüft täglich, was fällig ist, und erstellt **je Kunde eine Rechnung** mit allen
fälligen Positionen (inkl. Zeitraum und Lizenznummer). Unter *Einstellungen → Verträge* wählen Sie:
- **Automatisch** (eingestellt): festschreiben und per E-Mail an den Kunden (E-Mail-Zugang und Kunden-E-Mail
  nötig; fehlt die Kunden-E-Mail, wird die Rechnung nur festgeschrieben und im Protokoll vermerkt).
- **Entwurf:** Sie prüfen unter *Rechnungen & KVA → Entwürfe* und schreiben selbst fest.

**Kündigen:** Vertrag öffnen → „Kündigen“: Eingangsdatum, **Vertrag endet zum** (Vorschlag: Ende der laufenden
Periode bzw. Mindestlaufzeit), Grund. Bis zu diesem Datum wird noch berechnet, danach nicht mehr.
„Kündigung zurücknehmen“ macht das rückgängig.

**Bestehende Verträge übernehmen:** Beginn wie im Original eintragen und **„Bereits berechnet bis“** setzen
(z. B. Ende des letzten in Lexware berechneten Monats) – sonst würden vergangene Monate nachberechnet.

## 13. Leistungen und Artikel automatisch füllen

- Positionen, die Sie in einem KVA oder einer Rechnung **von Hand** eingeben, landen beim Speichern automatisch in
  *Leistungen & Artikel* – inklusive Beschreibung, Einkaufspreis und Marge. Beim nächsten Mal einfach aus der Liste
  einfügen.
- Für einmalige Sonderpositionen den Haken **„In Leistungen und Artikel speichern“** unter der Position entfernen.
- Gibt es die Bezeichnung schon mit anderem Preis, fragt das Programm: **„Preise im Katalog aktualisieren?“**
- Alte Dokumente: *Leistungen & Artikel → „Aus bisherigen Dokumenten übernehmen“* – Vorschau prüfen, abhaken,
  übernehmen.
- **Beschreibung:** Im Artikel beliebig lang und mehrzeilig (z. B. Anschlüsse, Maße, Kompatibilität). Beim Einfügen
  in ein Dokument wird sie übernommen und kann dort gekürzt werden – der Katalog bleibt unverändert.

## 14. Leihgeräte

Unter **Verkauf → Leihgeräte** verwalten Sie Geräte, die Kunden während einer Reparatur bekommen.

**Gerät anlegen:** „+ Neues Leihgerät“. Tragen Sie Bezeichnung (z. B. „Lenovo ThinkPad T14 #1“), Seriennummer,
Inventarnummer und das Zubehör ein (eins je Zeile, z. B. Netzteil, Tasche, Maus). Dazu kommt der **Zeitwert**, der
bei Verlust oder Totalschaden angesetzt wird, und die Standard-Leihgebühr: kostenlos, pauschal oder pro Tag. Bei „pro
Tag“ können die ersten Tage kostenlos sein. Optional geben Sie eine Kaution an. Fotos des Geräts laden Sie im Reiter
„Fotos“ hoch.

**Ausgeben:** im Reparaturauftrag Reiter **„Leihgerät“** → **„Leihgerät ausgeben“**.
1. Ein verfügbares Gerät wählen. Leihgebühr, Kaution und Zubehör werden vom Gerät übernommen und lassen sich für
   diesen Fall ändern, auch auf „kostenlos (Kulanz)“.
2. Voraussichtliche Rückgabe eintragen und das mitgegebene Zubehör abhaken.
3. Zustand notieren und Fotos machen (am Handy über „Kamera“).
4. „Leihgerät ausgeben“. Danach **„Leihvertrag / Übergabeprotokoll (PDF)“** drucken und vom Kunden unterschreiben
   lassen, oder per E-Mail senden.

Die Leihbedingungen im Vertrag ändern Sie unter *Einstellungen → Leihgeräte*. Lassen Sie diesen Text im Zweifel
einmal rechtlich prüfen.

**Zurücknehmen:** im Auftrag oder in der Leihgeräte-Übersicht **„Leihgerät zurücknehmen“**.
- Zubehör abhaken: was nicht abgehakt ist, gilt als fehlend.
- Zustand wählen und Fotos machen. Die Ausgabe-Fotos stehen zum Vergleich daneben.
- Die Leihgebühr wird berechnet. Beispiel: 5 Tage, 3 frei, 5 € pro Tag = 2 × 5 € = 10 €. Sie können den Betrag vor
  dem Speichern ändern.
- Bei Schaden oder fehlendem Zubehör erscheint der Bereich **Schadensfall**: Beschreibung, Kostenart, Betrag (bei
  Totalschaden mit dem Zeitwert vorbelegt) und Schadensfotos. Mit dem Haken „internen Reparaturauftrag anlegen“
  erscheint die Reparatur des Leihgeräts auf der Tafel. Für interne Aufträge gibt es keine Rechnung; nach „Erledigt“
  ist das Gerät wieder verfügbar.

**Kaution:** Ohne Schaden steht sie auf „zurückzuzahlen“. Klicken Sie nach der Auszahlung auf „… zurückgezahlt“.
Bei einem Schaden wird sie verrechnet. Der Leihvorgang zeigt, was der Kunde noch zahlen muss bzw. was Sie erstatten.

**Abrechnung:** Ziehen Sie den Auftrag auf **Erledigt**, stehen Leihgebühr und Schadenersatz als eigene Positionen im
Rechnungsentwurf. Die Kautionsverrechnung steht als Hinweis darunter. Ist das Gerät dann noch beim Kunden, fragt das
Programm: *„Leihgerät jetzt zurücknehmen oder später separat abrechnen?“*. Bei „später“ erstellen Sie nach der
Rücknahme eine eigene Rechnung über „Abrechnung“ im Leihvorgang.

**Nichts geht verloren:** Ausgabe- und Rückgabeprotokolle, Schadensfälle und die Historie lassen sich nicht ändern
oder löschen. Eine irrtümliche Ausgabe oder ein falscher Schadensfall wird mit Begründung **storniert** und bleibt
markiert sichtbar.

## 15. E-Mail-Historie bei Kunden

Alle E-Mails, die Sie mit einem Kunden austauschen, erscheinen automatisch beim Kunden unter **„E-Mail-Verlauf“**.
Das gilt für Mails aus dem Programm, aus Outlook und vom Handy.

**Einrichten:** *Einstellungen → Anfragen*. Der IMAP-Zugang oben muss funktionieren (z. B. `imap.ionos.de`, Port 143,
STARTTLS, „Verbindung testen“). Darunter im Abschnitt **„E-Mail-Historie bei Kunden“**:
1. „E-Mail-Historie aktivieren“ ankreuzen.
2. **„Ordner abrufen“** und die Ordner ankreuzen: empfangene Mails (meist `INBOX`, ggf. Unterordner) und gesendete
   Mails (bei IONOS meist „Gesendete Objekte“).
3. Festlegen, wie weit der erste Import zurückgehen soll (z. B. 6 Monate).
4. Speichern und unten auf **„Jetzt abgleichen“** klicken. Danach läuft der Abgleich automatisch im Intervall der
   Anfragen, solange das Programm geöffnet ist.

**Was gespeichert wird:** nur Mails, an denen mindestens ein Kunde beteiligt ist (Absender, Empfänger, Cc oder
Antwortadresse). Alles andere wird übersprungen und nicht gespeichert. Hat ein Kunde mehrere Adressen oder
Ansprechpartner, tragen Sie diese beim Kunden unter **„Weitere E-Mail-Adressen“** ein. Das Programm sucht dann sofort im
Postfach nach früheren Mails dieser Adressen. Das passiert auch beim Anlegen eines neuen Kunden.

**Ihr Postfach bleibt unverändert:** Das Programm liest nur. Nichts wird als gelesen markiert, verschoben oder
gelöscht. Anhänge bleiben im Postfach; beim Kunden stehen nur ihre Namen.

**Neu abgleichen:** Wenn Sie den Importzeitraum vergrößern, klicken Sie auf „Alle Ordner neu abgleichen“. Doppelte
Einträge entstehen dabei nicht.
