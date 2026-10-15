# Versionsprotokoll

Alle Versionen der Buchhaltung von Reparatur Service Bredin mit Neuerungen, Änderungen, Fehlerbehebungen und
technischen Hinweisen. Die neueste Version steht oben.

**So funktionieren Versionen**
- Die Versionsnummer steht unten links im Programm und unter *Einstellungen → Programm & Updates*.
- Aufbau: `Haupt.Funktion.Korrektur`. Die mittlere Zahl steigt bei neuen Funktionen, die letzte Zahl bei
  reinen Fehlerbehebungen.
- Ab Version 0.4.0 gibt es jede Version als `RSB-Buchhaltung.exe` unter
  [GitHub → Releases](https://github.com/ReparaturServiceBredin/Unternehmen/releases).
  Das Programm installiert neue Versionen selbst und erstellt vorher ein Backup.
- Ihre Daten im Ordner `Daten` bleiben bei jedem Update erhalten. Neue Datenbankfelder ergänzt das Programm beim
  Start selbst.
- Der Abschnitt einer Version erscheint im Programm als Hinweistext, wenn diese Version zum Update bereitsteht.

| Version | Datum | Schwerpunkt |
|---|---|---|
| 0.11.0 | 15.10.2026 | GoBD-Grundlagen: Gutschrift, Pflichtangaben, Änderungsprotokoll, Aufbewahrung |
| 0.10.0 | 15.10.2026 | Automatische E-Mail-Historie je Kunde |
| 0.9.1 | 15.10.2026 | IMAP-Abruf auch mit STARTTLS (Port 143), Verbindungstest |
| 0.9.0 | 15.10.2026 | Leihgeräte: Ausgabe, Rückgabe, Schadensfall, Abrechnung |
| 0.8.0 | 15.10.2026 | Auftrags-Detailansicht: KVA verknüpfen, Fotodokumentation, Verlauf |
| 0.7.0 | 15.10.2026 | Gesendet-Ordner per IMAP, Katalog-Übernahme, ausführliche Beschreibungen |
| 0.6.1 | 15.10.2026 | Vertragsrechnungen vollautomatisch |
| 0.6.0 | 15.10.2026 | Verträge & Lizenzen (Wertgarantie, ESET, MSP) mit wiederkehrenden Rechnungen |
| 0.5.1 | 15.10.2026 | Versionsprotokoll im Programm |
| 0.5.0 | 14.10.2026 | Kein Konsolenfenster, kein Passwortzwang |
| 0.4.0 | 14.10.2026 | EXE-Datei mit automatischen Updates |
| 0.3.0 | 14.10.2026 | Reparaturaufträge (Tafel) und Kostenvoranschlag |
| 0.2.0 | 14.10.2026 | Anfragen aus dem Kontaktformular |
| 0.1.0 | 14.10.2026 | Grundversion: Kunden, Leistungen, Rechnungen, E-Mail |

---

## 0.11.0 – 15.10.2026
GoBD-Grundlagen für Rechnungen und Belege (Ausbaustufe 1 von 10).

### Neu
- **Gutschrift mit eigenem Nummernkreis** (Standard „GS-2026-0001“): bei einer festgeschriebenen Rechnung über
  „Gutschrift erstellen“. Positionen sind vorbelegt, Beträge werden positiv eingegeben und als Minderung gebucht.
  Mit Bezug auf die Rechnung und eigenen Textbausteinen.
- **Pflichtangaben-Prüfung vor dem Festschreiben** (§ 14 Abs. 4 UStG):
  - Ihr vollständiger Name und Ihre Anschrift, Steuernummer oder USt-IdNr.
  - Name und Anschrift des Kunden (bei Kleinbetragsrechnungen bis 250 € nur Hinweis)
  - Rechnungsdatum, Leistungsdatum, Bezeichnung und Menge je Position
  - Steuersatz bzw. Hinweis nach § 19 UStG
  - Was fehlt, steht schon im Entwurf oben mit Link zu den Firmendaten.
- **Feldgenaues Änderungsprotokoll** für Rechnungen und KVA (Entwürfe), Kunden und Artikel: wer, wann (mit
  Sekunden), welches Feld, alter und neuer Wert, dazu Festschreiben und Storno als Ereignis. Nicht änderbar,
  aufklappbar auf den jeweiligen Seiten.
- **Archiv der Rechnungsdaten:** Beim Festschreiben werden neben dem PDF auch alle Rechnungsdaten als JSON-Datei mit
  eigener SHA-256-Prüfsumme archiviert.
- **Prüfsummenkontrolle beim Öffnen:** Angezeigt wird immer das archivierte Original-PDF. Wurde es verändert oder
  fehlt es, erscheint ein deutlicher Hinweis statt eines neu erzeugten PDFs.
- **Aufbewahrungsfristen** unter *Einstellungen → Rechnung & Steuer*: Belege 8 Jahre, Geschäftsbriefe 6 Jahre. Die
  gesetzlichen Mindestfristen können nicht unterschritten werden. Jede festgeschriebene Rechnung zeigt
  „Aufbewahren bis“.
- **Kunden löschen mit Fristprüfung:** Vorschau, was gelöscht und was bis wann aufbewahrt wird.
  - Bei Aufbewahrungspflicht werden die Stammdaten anonymisiert; Name und Anschrift bleiben nur in den
    archivierten Belegen.
  - Sonst wird der Kunde vollständig gelöscht.
- **Verfahrensdokumentation** (Menü *Verwaltung*): aus den tatsächlichen Einstellungen erzeugte Vorlage für den
  Steuerberater, als Seite und PDF.

### Geändert
- Festschreiben ist erst möglich, wenn alle Pflichtangaben vorhanden sind. **Bitte unter Einstellungen →
  Firmendaten Straße, PLZ und Steuernummer (oder USt-IdNr.) prüfen.**
- Datenbank-Schutz erweitert: Auch Zahlungsziel und Daten-Prüfsumme festgeschriebener Belege sind gesperrt.
- Datenprüfung kontrolliert zusätzlich die archivierten Rechnungsdaten.
- Zeitpunkt des Festschreibens in deutscher Zeit mit Sekunden.

### Technik
- Neue Tabelle `feldaenderungen` (nur anhängen, Trigger gegen Ändern und Löschen), neue Felder
  `dokumente.snapshot_sha256` und `kunden.anonymisiert_am`. Vorher automatische Sicherung `vor_update_….db`.
- Neue Module `rsb/aufbewahrung.py` und `rsb/verfahrensdoku.py`. 119 automatische Tests.

---

## 0.10.0 – 15.10.2026
Alle E-Mails mit Kunden erscheinen automatisch beim Kunden, egal ob aus dem Programm, aus Outlook oder vom Handy
gesendet.

### Neu
- **E-Mail-Verlauf beim Kunden:** gesendete (↗) und empfangene (↙) Mails mit Datum, Betreff, Absender/Empfänger,
  Anhangsnamen und Text zum Aufklappen. Verweise auf das versendete Dokument bzw. die Kontaktformular-Anfrage.
- **Einstellungen → Anfragen → „E-Mail-Historie bei Kunden“:**
  - einschalten
  - Ordner für empfangene Mails (mehrere, auch Unterordner) und für gesendete Mails (bei IONOS meist „Gesendete
    Objekte“); „Ordner abrufen“ zeigt alle Ordner zum Ankreuzen, Umlaute in IMAP-UTF-7 werden richtig dargestellt
  - erster Import: 30 Tage, 6 Monate, 1 Jahr oder alles
  - weitere eigene Adressen
  - Es wird der vorhandene IMAP-Zugang verwendet, ohne doppelte Felder. Abgerufen wird im Intervall der Anfragen.
  - Dazu die Knöpfe „Jetzt abgleichen“ und „Alle Ordner neu abgleichen“ mit Anzeige des letzten Abgleichs und
    eventueller Hinweise.
- **Kunden:** neues Feld „Weitere E-Mail-Adressen / Ansprechpartner“ (eine je Zeile).
- **Nachträglicher Abgleich:** Neuer Kunde oder neue Adresse beim Kunden → das Postfach wird im Hintergrund gezielt
  nach Mails von/an/cc dieser Adresse im Importzeitraum durchsucht.

### So arbeitet der Abgleich
- From, To, Cc und Reply-To werden mit allen Kunden-Adressen verglichen. Groß-/Kleinschreibung, Leerzeichen und
  Anzeigenamen werden ignoriert, eigene Adressen zählen nie.
- **Ohne Kundentreffer wird nichts gespeichert,** auch nicht im Protokoll. Das Protokoll enthält nur Anzahlen.
- Trifft eine Mail mehrere Kunden, steht sie bei jedem.
- Richtung: „gesendet“ aus dem Gesendet-Ordner oder bei eigener Absenderadresse, sonst „empfangen“.
- Kontaktformular-Mails werden mit der vorhandenen Anfrage verknüpft und nicht doppelt angelegt.
- **Nur lesen:** Ordner werden mit EXAMINE geöffnet und Inhalte mit BODY.PEEK[] geholt. Nichts wird als gelesen
  markiert, verschoben oder gelöscht.
- **Inkrementell:** je Ordner UIDVALIDITY und letzte UID. Ändert sich die UIDVALIDITY, wird der Ordner im
  Importzeitraum neu abgeglichen.
- Zuerst werden nur die Kopfzeilen geladen, der vollständige Inhalt nur bei einem Kundentreffer.
- Keine Duplikate dank Message-ID. Mails, die das Programm selbst verschickt (KVA, Rechnung, Leihvertrag …), werden
  direkt beim Versand gespeichert und später mit dem Fund im Postfach zusammengeführt.
- Der Abruf läuft im Hintergrund mit Zeitlimit. Fehler erscheinen als Hinweis; ein fehlender Ordner hält die übrigen
  nicht auf.

### Datenschutz
- Beim Löschen eines Kunden wird auch sein E-Mail-Verlauf im Programm gelöscht (Mails, die zusätzlich bei anderen
  Kunden stehen, bleiben dort). Das Postfach selbst bleibt unverändert.
- Anhänge werden nicht kopiert, nur ihre Namen und Größen. Die Dateien bleiben im Postfach.

### Technik
- Neue Tabellen `email_nachrichten`, `email_kunden` und `imap_ordner_status`, neues Feld `kunden.email_weitere`.
  Vor der Erweiterung wird automatisch `Daten\backups\vor_update_….db` angelegt.
- Neues Modul `rsb/email_historie.py`. 111 automatische Tests.

---

## 0.9.1 – 15.10.2026
Anfragen-Abruf funktioniert jetzt auch, wenn Port 993 gesperrt ist.

### Neu
- **Verschlüsselung für den Anfragen-Abruf (IMAP):** In *Einstellungen → Anfragen* wählen Sie jetzt
  „SSL/TLS (meist Port 993)“ oder „STARTTLS (meist Port 143)“, wie beim E-Mail-Versand. Beim Wechsel wird der
  passende Port vorgeschlagen, solange noch der Standardport eingetragen ist.
- **„Verbindung testen“** im IMAP-Bereich der Anfragen: prüft Verbindung, Anmeldung und ob die Ordner „INBOX“ und
  „Anfragen erledigt“ existieren, auch vor dem Speichern.

### Geändert
- Kontaktformular-Abruf und Ablage im Gesendet-Ordner nutzen denselben, gemeinsamen Verbindungsaufbau.
- STARTTLS: Anmeldung erst nach erfolgreicher Verschlüsselung. Bietet der Server kein STARTTLS an oder schlägt es
  fehl, bricht das Programm mit klarer Meldung ab – **nie Anmeldung ohne Verschlüsselung**.
- Verständliche deutsche Fehlermeldungen, z. B. bei „WRONG_VERSION_NUMBER“: *„Port und Verschlüsselung passen nicht
  zusammen (993 = SSL, 143 = STARTTLS).“*, außerdem bei unbekanntem Server, gesperrtem Port, Zeitüberschreitung,
  Zertifikatsproblemen und falschem Passwort.
- Ordnernamen mit Umlauten werden beim Abruf korrekt kodiert.

### Fehlerbehebung
- Port 143 führte zu „[SSL: WRONG_VERSION_NUMBER] wrong version number“, weil der Abruf immer direkt SSL verwendete.

### Technik
- Bestehende Einstellungen werden beim Start einmalig umgestellt: Port 993 → SSL/TLS, sonst STARTTLS.
- Neues Modul `rsb/imap_verbindung.py`. 102 automatische Tests, darunter echte Verbindungstests gegen einen lokalen
  Test-Server (SSL auf einem Klartext-Port, Server ohne STARTTLS: es wird kein Passwort gesendet).

---

## 0.9.0 – 15.10.2026
Leihgeräte für Kunden während der Reparatur, mit Leihvertrag, Rückgabeprotokoll, Schadensfällen und Abrechnung.

### Neu
- **Menüpunkt „Leihgeräte“:**
  - Übersicht mit Status (Verfügbar, Verliehen, Defekt / in Reparatur, Ausgemustert), Filter und Suche
  - verliehene Geräte zeigen Kunde, Auftrag, Ausgabe und Rückgabedatum; überfällige Rückgaben sind rot markiert
  - im Menü ein Zähler für überfällige Rückgaben
- **Je Leihgerät:**
  - Bezeichnung, Typ, Hersteller, Modell, Seriennummer, Inventarnummer
  - Standard-Zubehör als Checkliste, Zustand, Anschaffungsdatum, Anschaffungs- und Zeitwert
  - Leihgebühr kostenlos / pauschal / pro Tag mit kostenlosen Tagen, optionale Kaution
  - Fotos und eine Historie aller Leihen, Schäden und Statuswechsel
  - Geräte werden nicht gelöscht, sondern ausgemustert
- **Reiter „Leihgerät“ im Reparaturauftrag:**
  - **Ausgeben:** nur verfügbare Geräte. Erfasst werden Zeitpunkt (Server-Zeit, vorbelegt), voraussichtliche Rückgabe,
    Zubehör zum Abhaken, Leihgebühr (vorbelegt, änderbar, auch „kostenlos (Kulanz)“), Kaution mit Zahlungsart sowie
    Zustand mit Notiz und Fotos („Leihgerät Ausgabe“).
  - **Leihvertrag / Übergabeprotokoll als PDF:** Kunde, Gerät mit Seriennummer, Zubehör, Zustand mit Fotos,
    Leihgebühr, Kaution, Rückgabedatum, Leihbedingungen und Unterschriftsfelder. Auf Wunsch direkt per E-Mail an
    den Kunden.
  - Die Leihbedingungen sind unter *Einstellungen → Leihgeräte* frei bearbeitbar.
- **Rücknahme:**
  - Zeitpunkt, Zubehör-Checkliste (was fehlt?), Zustand „einwandfrei“ oder „Schaden festgestellt“, Notiz und
    Fotos („Leihgerät Rückgabe“). Die Fotos von Ausgabe und Rückgabe stehen nebeneinander zum Vergleich.
  - Die Leihgebühr wird automatisch berechnet (Kalendertage minus kostenlose Tage, bzw. Pauschale) und kann vor der
    Übernahme geändert werden.
  - Ohne Schaden ist das Gerät wieder verfügbar und die Kaution steht auf „zurückzuzahlen“.
  - Rückgabeprotokoll als PDF.
- **Schadensfall** (bei Schaden oder fehlendem Zubehör):
  - Beschreibung, Fotos und Kostenart (Reparatur, Zubehör-Ersatz, Totalschaden/Verlust mit dem Zeitwert vorbelegt)
  - transparente Verrechnung mit der Kaution: noch zu zahlen bzw. Erstattung
  - das Gerät wird automatisch auf „Defekt“ bzw. „Ausgemustert“ gesetzt
  - per Klick ein interner Reparaturauftrag für das Leihgerät (ohne Rechnung; nach dem Erledigen ist das Gerät
    wieder verfügbar)
  - Schadensfall-Dokumentation als PDF mit Fotos und Verlauf
- **Abrechnung:**
  - Beim Ziehen auf „Erledigt“ kommen Leihgebühr und Schäden als eigene Positionen in den Rechnungsentwurf, z. B.
    „Leihgerät Lenovo ThinkPad T14 #1, 2 Tage à 5,00 €“ und „Schaden Leihgerät: Netzteil fehlt“.
  - Die Kautionsverrechnung steht als Hinweis auf der Rechnung.
  - Ist das Gerät noch nicht zurück, fragt das Programm: „Leihgerät jetzt zurücknehmen oder später separat
    abrechnen?“
- **Katalog:** neue Positionen „Leihgebühr pauschal“, „Leihgebühr pro Tag“ und „Schadenersatz Leihgerät“ unter
  *Leistungen & Artikel*.
- **Tafel:** Auftragskarten zeigen „🔁 Leihgerät“, bei überfälliger Rückgabe rot.
- **Kunde:** Hinweis, wenn der Kunde gerade ein Leihgerät hat, sowie eine Liste früherer Leihen mit Schadensfällen.

### Geändert
- Aufträge mit Leihgerät und Kunden mit Leihvorgängen lassen sich nicht mehr löschen (Archivieren ist möglich).
- Interne Aufträge (Reparatur eigener Leihgeräte) erzeugen beim Erledigen keine Rechnung und fragen nicht nach
  einem KVA.

### Technik
- Neue Tabellen `leihgeraete`, `leihen`, `schadensfaelle` und `leihgeraet_verlauf`, neue Foto-Felder
  `leihgeraet_id`, `leihe_id` und `schadensfall_id`. Datenbank-Trigger verhindern das Ändern von Ausgabe- und
  Rückgabeprotokollen und das Löschen von Leihvorgängen, Schadensfällen, Historie und Geräten. Korrekturen gehen nur
  als Stornierung mit Begründung.
- Zeitstempel serverseitig in Europe/Berlin mit Sekunden.
- Vor der Datenbank-Erweiterung wird automatisch `Daten\backups\vor_update_….db` angelegt.
- 94 automatische Tests.

---

## 0.8.0 – 15.10.2026
Reparaturaufträge mit Detailansicht: Kostenvoranschlag verknüpfen, Fotos dokumentieren, lückenloser Verlauf.

### Neu
- **Detailansicht je Auftrag:** Ein Klick auf eine Karte öffnet den Auftrag. Ziehen & Ablegen und die Pfeil-Knöpfe
  funktionieren wie bisher. Kopf mit Auftragsnummer, Status und Eingangsdatum, Reiter **Auftragsdaten**,
  **Kostenvoranschlag**, **Fotos** und **Verlauf**. Alle Felder sind bearbeitbar, auch Kunde und Status.
- **KVA verknüpfen:**
  - **„Bestehenden KVA verknüpfen“** zeigt freie Kostenvoranschläge des Kunden. Suche nach Nummer, Datum oder
    Betrag, optional „alle Kunden anzeigen“.
  - **„Neuen KVA aus diesem Auftrag erstellen“** füllt den KVA vor und verknüpft ihn automatisch.
  - Ist ein KVA verknüpft: Nummer, Datum, Betrag und Status (offen / angenommen / abgelehnt) sowie die Knöpfe
    Öffnen, PDF, Per E-Mail senden und **Verknüpfung lösen** (mit Rückfrage; der KVA bleibt erhalten).
  - Warnung, wenn KVA und Auftrag zu unterschiedlichen Kunden gehören.
  - Die KVA-Seite zeigt den zugehörigen Auftrag mit Link und den KVA-Status.
- **Erledigt ohne KVA:** Statt stillschweigend eine leere Rechnung anzulegen, fragt das Programm:
  „Kein KVA verknüpft – leeren Rechnungsentwurf erstellen oder KVA jetzt verknüpfen?“ (Tafel, Knopf und
  Detailansicht).
- **Fotodokumentation:**
  - mehrere Fotos auf einmal, Ziehen & Ablegen, am Handy direkt die Kamera
  - Kategorien: Geräteeingang, Vorschaden, Während der Reparatur, Nach der Reparatur, Geräteausgabe
  - Gespeichert werden: Server-Zeit (deutsche Zeit, mit Sekunden), Aufnahmezeit aus der Kamera (EXIF), Benutzer
    und SHA-256-Prüfsumme. Das Original bleibt unverändert.
  - Löschen nur als Markierung mit Pflicht-Begründung; das Foto bleibt erhalten.
  - Fotodokumentation als PDF mit Änderungsprotokoll
- **Karten auf der Tafel** zeigen 📷 Anzahl Fotos und „KVA ✓“ bzw. „kein KVA“.
- **„+ Neuer Auftrag“** ist jetzt eine eigene Seite mit denselben Feldern wie die Detailansicht. Dort können Sie
  gleich einen KVA verknüpfen und Fotos hochladen. Die Fotos werden sofort gespeichert und bleiben erhalten, auch
  wenn das Speichern des Auftrags einmal fehlschlägt (z. B. Kunde vergessen). Ihre Eingaben bleiben dann ebenfalls
  stehen.
- **Verlauf** je Auftrag mit Zeitpunkt und Benutzer:
  - angelegt, Daten geändert, Statuswechsel
  - KVA verknüpft, gelöst, festgeschrieben, angenommen/abgelehnt, per E-Mail versendet
  - Fotos hochgeladen oder als gelöscht markiert
  - Rechnung erstellt

### Geändert
- Beim Löschen eines Auftrags bleibt ein verknüpfter KVA jetzt erhalten (bisher wurde ein KVA-Entwurf
  mitgelöscht). Aufträge mit Fotos oder festgeschriebener Rechnung lassen sich nicht löschen. Kunden, zu deren
  Aufträgen es Fotos gibt, ebenfalls nicht; sie können archiviert werden.
- Größere Uploads möglich (bis 60 MB je Foto).

### Technik
- Neue Tabellen `auftrag_fotos` und `auftrag_verlauf`, beide durch Datenbank-Trigger gegen Ändern und Löschen
  geschützt. Neues Feld `dokumente.kva_status`. Fotos liegen in `Daten\fotos\JJJJ\MM\` (Vorschaubilder in
  `Daten\fotos\vorschau\`) und sind Teil des Backups.
- Vor der Datenbank-Erweiterung wird automatisch `Daten\backups\vor_update_….db` angelegt. Für bestehende
  Aufträge wird der Verlauf einmalig aus dem Änderungsprotokoll nachgetragen.
- 82 automatische Tests.

---

## 0.7.0 – 15.10.2026
Versendete Mails im Postfach, manuelle Positionen automatisch im Katalog, ausführliche Artikelbeschreibungen.

### Neu
- **Kopie im Gesendet-Ordner (IMAP):** *Einstellungen → E-Mail → IMAP*. Jede versendete Mail wird nach dem
  erfolgreichen SMTP-Versand mit Anhängen, Datum und Message-ID per IMAP im gewählten Ordner abgelegt
  (als gelesen markiert).
  - IMAP-Server, Port (993), Verschlüsselung (SSL/TLS oder STARTTLS/143), gleiche Zugangsdaten wie SMTP oder eigene
    (Passwort verschlüsselt gespeichert)
  - **„Ordner abrufen“** listet die Ordner des Postfachs (Umlaute/IMAP-UTF-7 werden richtig angezeigt),
    der Gesendet-Ordner wird vorausgewählt
  - **„Verbindung testen“** mit verständlicher Meldung: Erfolg, falsches Passwort, Server nicht erreichbar,
    Ordner fehlt
  - Schlägt die Ablage fehl, gilt die Mail trotzdem als gesendet – gelber Hinweis, Eintrag im Protokoll,
    **kein erneuter Versand**. Das Versandprotokoll vermerkt, ob die Kopie abgelegt wurde.
- **Manuelle Positionen → „Leistungen und Artikel“:** Von Hand eingegebene Positionen in KVA und Rechnungen werden
  beim Speichern automatisch in den Katalog übernommen (Bezeichnung, Beschreibung, Einheit, Einkauf, Preis, Marge,
  Steuersatz, Typ) und mit der Position verknüpft.
  - pro Position Haken **„In Leistungen und Artikel speichern“** (für einmalige Sonderpositionen abwählen) und Typ
    Leistung/Artikel (mit Einkaufspreis automatisch „Artikel“)
  - keine Duplikate (Groß-/Kleinschreibung und Leerzeichen werden ignoriert); weichen die Preise ab, kommt die
    Rückfrage **„Preise im Katalog aktualisieren?“** (Ja/Nein)
  - fehlt der Einkaufspreis, bleibt die Marge leer (statt 0 % oder 100 %)
- **„Aus bisherigen Dokumenten übernehmen“** (in *Leistungen & Artikel*): sammelt alle manuellen Positionen aus
  früheren KVA und Rechnungen, fasst Duplikate zusammen und zeigt eine Vorschau mit Preisen, früheren Preisen und
  Margen zum Abhaken.
- **Ausführliche Beschreibung** für Leistungen und Artikel (großes mehrzeiliges Feld, keine Längenbegrenzung):
  wird beim Einfügen in KVA/Rechnung übernommen und kann dort für den Einzelfall angepasst werden, ohne den
  Katalog zu ändern. Im PDF steht sie kleiner unter der Bezeichnung, Zeilenumbrüche bleiben erhalten, lange Texte
  brechen sauber auf die nächste Seite um.
- Artikelsuche durchsucht auch die Beschreibung (z. B. „USB-C“, „HDMI“); die Liste zeigt nur die erste Zeile.

### Geändert
- E-Mail-Versand liest die Zugangsdaten immer frisch aus den gespeicherten Einstellungen. Fehlen sie oder sind sie
  ungültig (z. B. leer oder „localhost“), kommt eine klare Meldung statt eines Verbindungsversuchs.
- Zeitlimit 20 Sekunden für SMTP und IMAP (auch beim Abholen der Anfragen).
- Bei „Verbindung abgelehnt“ (z. B. WinError 10061) ein zweiter Verbindungsversuch nach 2 Sekunden – nur beim
  Verbindungsaufbau, es wird nie doppelt gesendet; die Fehlermeldung nennt Server und Port.
- Einkaufspreis bei Leistungen/Artikeln darf leer bleiben (= unbekannt, keine Marge).

### Technik
- Neue Felder `artikel.ek_unbekannt`, `versandprotokoll.ablage`. Vor jeder Datenbank-Erweiterung wird automatisch
  eine Sicherung `Daten\backups\vor_update_….db` angelegt.
- 73 automatische Tests.

---

## 0.6.1 – 15.10.2026
Vertragsrechnungen gehen ab jetzt vollautomatisch raus.

### Geändert
- **Wiederkehrende Rechnungen vollautomatisch:** Fällige Vertragsrechnungen werden automatisch festgeschrieben und
  per E-Mail an den Kunden gesendet. Die Umstellung erfolgt bei diesem Update einmalig. Wer lieber erst prüfen will,
  stellt unter *Einstellungen → Verträge* auf „als Entwurf anlegen“ zurück – diese Wahl bleibt dann erhalten.
- Warnhinweis auf der Übersicht und bei den Verträgen, solange der E-Mail-Zugang fehlt (dann werden Rechnungen nur
  festgeschrieben, aber nicht versendet).

---

## 0.6.0 – 15.10.2026
Verträge, Lizenzen und Garantien beim Kunden – mit automatischen wiederkehrenden Rechnungen.

### Neu
- **Verträge & Lizenzen** (*Verkauf → Verträge & Lizenzen*) und beim Kunden unter „Verträge, Lizenzen & Garantien“:
  - Bezeichnung, Kategorie (Garantie/Versicherung, Lizenz, MSP, Wartung, Sonstiges), Vertrags-/Policen-/Lizenznummer,
    Gerät/Seriennummer, Beginn, Laufzeit, Mindestlaufzeit, Preis, Einkauf (Marge), Anzahl (z. B. Geräte), Notizen
- **Abrechnungsarten:**
  - *nur Dokumentation* – z. B. Wertgarantie (Kunde zahlt direkt an den Versicherer)
  - *monatlich, vierteljährlich, halbjährlich, jährlich* – z. B. MSP-Pakete, im Voraus bis zur Kündigung
  - *einmal je Laufzeit* – z. B. ESET 1, 2 oder 3 Jahre; optional „verlängert sich automatisch“
- **Vertragsarten** als Vorlagen, jederzeit erweiterbar (*Verträge & Lizenzen → Vertragsarten*). Mitgeliefert:
  Wertgarantie, ESET 1/2/3 Jahre, MSP Basis (Preise bitte eintragen).
- **Wiederkehrende Rechnungen:** täglich automatisch (und per Knopf „Jetzt abrechnen“) eine Rechnung je Kunde mit
  allen fälligen Verträgen, Zeitraum und Lizenznummer stehen auf der Rechnung. Wahlweise als **Entwurf** oder
  **automatisch festschreiben und per E-Mail senden** (*Einstellungen → Verträge*).
- **Kündigen:** Vertrag als gekündigt hinterlegen (Eingang, Ende zum, Grund). Bis zum Kündigungsdatum wird noch
  berechnet, danach **keine Rechnung mehr**. Kündigung kann zurückgenommen werden. Vorschlag für das Enddatum:
  Ende der laufenden Periode bzw. Mindestlaufzeit.
- **Lizenz verlängern** per Knopf: neue Laufzeit + Rechnungsentwurf.
- **Erinnerung:** Lizenzen/Garantien, die in den nächsten 60 Tagen (einstellbar) ablaufen, erscheinen unter
  „Laufen bald ab“ und auf der Übersicht.
- **Kennzahlen:** aktive Verträge, regelmäßige Einnahmen pro Monat, fällige Abrechnungen.
- **Bestehende Verträge übernehmen:** Feld „Bereits berechnet bis“ – frühere Zeiträume (z. B. aus Lexware)
  werden nicht noch einmal berechnet.

### Behoben
- In leeren Feldern der Kunden-, Artikel- und Textbaustein-Formulare stand „None“.

### Hinweise
- Keine doppelten Rechnungen: Jeder berechnete Zeitraum wird gespeichert. Wird ein Rechnungsentwurf gelöscht,
  gilt der Zeitraum wieder als offen.
- Verträge mit festgeschriebenen Rechnungen können nicht gelöscht, nur gekündigt werden.

---

## 0.5.1 – 15.10.2026
Versionsprotokoll direkt im Programm.

### Neu
- **Versionsprotokoll im Programm:** *Einstellungen → Programm & Updates → Versionsprotokoll anzeigen*.
  Ein Klick auf die Versionsnummer unten links öffnet es ebenfalls.
- Ausführliches Versionsprotokoll mit allen bisherigen Versionen (auch unter `docs/AENDERUNGEN.md`).

---

## 0.5.0 – 14.10.2026
Das Programm verhält sich jetzt wie eine normale Windows-Anwendung.

### Neu
- **Eigenes Programmfenster** ohne Adressleiste und Tabs (Microsoft Edge im App-Modus, bei Windows 11 vorhanden).
  Gibt es Edge nicht, öffnet sich der Standardbrowser.
- **Symbol im Infobereich** (unten rechts neben der Uhr):
  - Klick: Buchhaltung öffnen
  - Rechtsklick: „Buchhaltung öffnen“, „Daten-Ordner öffnen“, „Beenden“
- Einstellung **Programmfenster**: eigenes Fenster oder Tab im normalen Browser
  (*Einstellungen → Programm & Updates*).
- Programmmeldungen stehen in `Daten\programm.log`. Ab 1 MB wird die Datei automatisch gewechselt.

### Geändert
- **Kein schwarzes Konsolenfenster** mehr beim Start.
- **Keine Passwortabfrage** mehr. Bei Bedarf unter *Einstellungen → Passwortschutz* einschalten (mind. 8 Zeichen)
  und dort auch wieder ausschalten.
- Der Knopf „Abmelden“ erscheint nur noch bei eingeschaltetem Passwortschutz.

### Hinweise
- Ohne Passwort schützt die Windows-Anmeldung (PIN/Passwort) und die Bildschirmsperre (`Win + L`).
  Von anderen Geräten ist das Programm nicht erreichbar.

### Technik
- Webserver im Hintergrund, Infobereichssymbol über `pystray`, EXE ohne Konsole (`console=False`).
- Neue Einstellungen: `login_aktiv` (Standard: aus), `fenster_modus` (Standard: eigenes Fenster).
- 48 automatische Tests, Windows-Start-Test bei GitHub bestanden.

---

## 0.4.0 – 14.10.2026
Erste Version als EXE-Datei – keine Python-Installation und kein Installer mehr nötig.

### Neu
- **RSB-Buchhaltung.exe** – eine einzige Datei. Ordner anlegen (z. B. `C:\RSB-Buchhaltung`), Datei hineinlegen,
  starten. Der Ordner `Daten` entsteht direkt daneben.
- **Automatische Updates:**
  - Prüfung beim Start und alle 6 Stunden bei GitHub (kostenlos, ohne Login, es werden keine Daten übertragen)
  - neue Version wird beim nächsten Start installiert: Download → Prüfsummen-Kontrolle (SHA-256) → Backup →
    Austausch der EXE → Neustart
  - Hinweisleiste „Neue Programmversion verfügbar“ mit Knopf **„Jetzt aktualisieren“**
  - abschaltbar unter *Einstellungen → Programm & Updates*
- Ein zweiter Doppelklick auf die EXE, während das Programm schon läuft, öffnet nur die Oberfläche
  und startet das Programm kein zweites Mal.
- Dateieigenschaften der EXE (Firma, Produkt, Version) und eigenes Programmsymbol.

### Behoben
- Veröffentlichung bei GitHub scheiterte an Sonderzeichen (→) in den Hinweistexten (UTF-8 erzwungen).

### Technik
- Bau mit PyInstaller. GitHub Actions baut die Windows-EXE bei jeder neuen Versionsnummer, testet sie
  (Programmstart und Versionsabfrage unter Windows) und veröffentlicht sie mit Prüfsumme als Release.
- Update-Ablauf lokal geprüft: Version 0.4.0 → 0.4.1 automatisch beim Start und über den Knopf, jeweils mit Backup
  und Aufräumen der alten Datei.

### Umstieg von start.bat
- Den Ordner `Daten` aus der alten Installation neben die EXE kopieren. Alles bleibt erhalten, auch das
  gespeicherte E-Mail-Passwort.

---

## 0.3.0 – 14.10.2026
Reparaturaufträge und Kostenvoranschläge. *(Nur als Quellcode, noch keine EXE.)*

### Neu
- **Reparaturaufträge als Tafel** (*Verkauf → Reparaturaufträge*) mit den Spalten **Offen → In Arbeit → Erledigt**:
  - Karten per **Ziehen & Ablegen** verschieben, auch innerhalb einer Spalte (Reihenfolge)
  - alternativ Knöpfe auf jeder Karte („Starten →“, „Erledigt ✓“, „←“), z. B. für Tablets
  - Karte zeigt Auftragsnummer (`RA-2026-0001`), Kunde, Gerät, Fehler, Tage seit Eingang, KVA und Rechnung
  - Spalte „Erledigt“ zeigt die letzten 30 Tage, ältere über „alle anzeigen“
- **Auftragsdetails:** Gerät, Seriennummer/IMEI, mitgegebenes Zubehör, Fehlerbeschreibung, interne Notizen,
  Zeitpunkte für Eingang, Beginn und Erledigung.
- Auftrag anlegen auf der Tafel, **aus einer Anfrage** (übernimmt Gerät und Fehler) oder beim Kunden.
- **Kostenvoranschlag (KVA)** als neue Dokumentart:
  - eigene Nummern `KV-2026-0001`, „Gültig bis“ (Standard 30 Tage, einstellbar)
  - eigene Textbausteine (Einleitung, Schluss, E-Mail), PDF, Druck, E-Mail-Versand
  - „In Rechnung übernehmen“ übernimmt alle Positionen
- **Auftrag auf „Erledigt“ ziehen → Rechnungsentwurf** mit den KVA-Positionen, Gerät und IMEI im Betreff und
  dem heutigen Datum als Leistungsdatum. Der Entwurf öffnet sich direkt zum Prüfen und Festschreiben.
  Wird ein Auftrag zurück und erneut auf „Erledigt“ gezogen, entsteht keine zweite Rechnung.
- Übersicht: Kacheln mit der Anzahl offener, laufender und erledigter Aufträge.
- Rechnungsliste mit Filter nach Art (Rechnungen / Kostenvoranschläge).

### Behoben
- Bestätigungsdialog beim Festschreiben wurde wegen Anführungszeichen nicht angezeigt.

### Hinweise
- Rechnungen werden bewusst **nicht automatisch festgeschrieben**, damit ein versehentliches Ziehen keine
  Rechnungsnummer verbraucht.

---

## 0.2.0 – 14.10.2026
Anfragen aus dem Kontaktformular der Website. *(Nur als Quellcode, noch keine EXE.)*

### Neu
- **Automatischer Abruf** der Formular-E-Mails aus dem Postfach (IMAP, z. B. IONOS oder Gmail), alle 5 Minuten
  (einstellbar). Nur E-Mails mit dem Text „A new form has been submitted“ werden verarbeitet.
  Erledigte E-Mails kommen in den Ordner „Anfragen erledigt“.
- **Auslesen** der Felder Name, Telefon, Email, Gerät und Nachricht. Vor- und Nachname werden automatisch
  getrennt, auch bei „Nachname Vorname“.
- **Spam-/Unsinn-Erkennung** mit Punkten und Begründung: Links, Werbewörter, Zeichensalat, fremde Schrift,
  ungültige Kontaktdaten, englische Werbetexte – dagegen zählen Themenwörter (Display, Akku, Jura, Laptop …).
  - **Echte Anfrage:** Kunde wird automatisch als **Interessent** angelegt
  - **Unsicher:** Liste „Zu prüfen“, Kunde mit einem Klick anlegen (Name korrigierbar)
  - **Spam:** kein Kunde, automatische Löschung nach 30 Tagen
- **Keine Dubletten:** gleiche E-Mail oder Telefonnummer → Anfrage wird dem vorhandenen Kunden zugeordnet.
- Interessent wird mit der ersten Rechnung automatisch zum Kunden.
- **Datenschutz:** Interessenten ohne Auftrag werden nach 6 Monaten (einstellbar) zum Löschen vorgeschlagen.
- „Anfrage einfügen“ zum Testen oder ohne Postfachzugang.
- Hinweis auf neue Anfragen in der Navigation (rote Zahl) und auf der Übersicht.

---

## 0.1.0 – 14.10.2026
Grundversion (Etappe 1). *(Nur als Quellcode, Start über `installieren.bat` / `start.bat`.)*

### Neu
- **Kundenstamm:** Privat- und Firmenkunden, Kundennummern `K-0001`, Suche, Notizen, eigenes Zahlungsziel,
  Archivieren und Löschen (nur ohne Rechnungen).
- **Leistungen & Artikel:** Festpreise, Teilekosten, Aufschlag, **Marge in € und %**, Leistungsarten für
  Auswertungen (Smartphone, Kaffeemaschine, PC/Laptop, Sonstiges).
- **Rechnungen:**
  - Entwurf mit Vorschau, danach **Festschreiben** mit fortlaufender, lückenloser Nummer `RE-2026-0001`
  - festgeschriebene Rechnungen sind unveränderbar (Schutz direkt in der Datenbank). Korrektur nur über
    **Stornorechnung** und „Als neue Rechnung kopieren“
  - Zahlungsziel 14 Tage (privat) bzw. 30 Tage (Firma)
- **PDF** nach DIN 5008 mit Logo, Farben, Schrift (Montserrat), Falzmarken, Fußzeile mit Firmen-, Bank- und
  Steuerdaten und **QR-Code zum Bezahlen (GiroCode)**. Druck direkt aus dem Programm.
- **Kleinunternehmer-Modus** (§ 19 UStG) mit Pflichthinweis, umschaltbar auf Regelbesteuerung (19 %/7 %).
- **E-Mail-Versand** über das eigene Postfach (SMTP), Textvorlagen, Kopie an sich selbst, **Versandprotokoll**.
  Das Passwort wird verschlüsselt gespeichert.
- **Layout ohne Programmierung:** Farben, Schrift, Logo, Kopf- und Fußzeile, Live-Vorschau.
- **Textbausteine** mit Platzhaltern wie `{nummer}`, `{betrag}`, `{faellig_am}`.
- **Änderungsprotokoll** mit Prüfsummenkette und Seite **Datenprüfung** (PDF-Prüfsummen, lückenlose Nummern,
  Protokoll).
- **Backup:** täglich automatisch als ZIP, zusätzliche Kopie auf ein NAS, Backup per Knopf.
- Übersicht mit Umsatz und Anzeige der Kleinunternehmergrenze.
- Dokumentation: Installation, Bedienung, Recht/GoBD/Datenschutz.

---

## Geplant
- SEPA-Lastschrift für Vertragsrechnungen (Mandatsverwaltung)
- Bankabgleich: N26-Umsätze (CSV) importieren und Zahlungen per Rechnungsnummer zuordnen (wartet auf
  Beispieldatei)
- Anzahlungsrechnung (50 %) und Schlussrechnung mit Abzug, Auftragsbestätigung, Gutschrift
- Zahlungsstatus (offen, teilweise, bezahlt, überfällig), Zahlungserinnerung und 2 Mahnstufen à 3,95 €
- Einnahmen/Ausgaben mit Belegen, EÜR nach Anlage EÜR, Monats- und Jahresübersicht
- Export für Steuer/Finanzamt, Kunden-Import aus CSV, Wiederherstellung per Knopfdruck, Vorlage
  Verfahrensdokumentation
