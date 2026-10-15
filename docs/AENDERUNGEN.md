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
| 0.6.1 | 15.10.2026 | Vertragsrechnungen vollautomatisch |
| 0.6.0 | 15.10.2026 | Verträge & Lizenzen (Wertgarantie, ESET, MSP) mit wiederkehrenden Rechnungen |
| 0.5.1 | 15.10.2026 | Versionsprotokoll im Programm |
| 0.5.0 | 14.10.2026 | Kein Konsolenfenster, kein Passwortzwang |
| 0.4.0 | 14.10.2026 | EXE-Datei mit automatischen Updates |
| 0.3.0 | 14.10.2026 | Reparaturaufträge (Tafel) und Kostenvoranschlag |
| 0.2.0 | 14.10.2026 | Anfragen aus dem Kontaktformular |
| 0.1.0 | 14.10.2026 | Grundversion: Kunden, Leistungen, Rechnungen, E-Mail |

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
