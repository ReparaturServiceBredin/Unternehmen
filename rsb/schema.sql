-- Datenbankschema Reparatur Service Bredin
-- Beträge werden immer in CENT (ganze Zahlen) gespeichert, damit keine Rundungsfehler entstehen.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT
);

CREATE TABLE IF NOT EXISTS kunden (
    id               INTEGER PRIMARY KEY,
    kundennr         TEXT UNIQUE NOT NULL,
    typ              TEXT NOT NULL DEFAULT 'privat' CHECK (typ IN ('privat', 'firma')),
    firma            TEXT,
    anrede           TEXT,
    vorname          TEXT,
    nachname         TEXT,
    strasse          TEXT,
    plz              TEXT,
    ort              TEXT,
    land             TEXT DEFAULT 'Deutschland',
    email            TEXT,
    telefon          TEXT,
    ust_idnr         TEXT,
    zahlungsziel_tage INTEGER,
    notizen          TEXT,
    interessent      INTEGER NOT NULL DEFAULT 0,
    quelle           TEXT,
    archiviert       INTEGER NOT NULL DEFAULT 0,
    erstellt_am      TEXT NOT NULL,
    geaendert_am     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artikel (
    id                INTEGER PRIMARY KEY,
    artikelnr         TEXT,
    name              TEXT NOT NULL,
    beschreibung      TEXT,
    leistungsart      TEXT,
    typ               TEXT NOT NULL DEFAULT 'leistung' CHECK (typ IN ('leistung', 'material')),
    einheit           TEXT DEFAULT 'Stk.',
    preis             INTEGER NOT NULL DEFAULT 0,   -- Verkaufspreis (netto) in Cent
    teilekosten       INTEGER NOT NULL DEFAULT 0,   -- Einkauf/Teilekosten in Cent
    aufschlag_prozent REAL,
    steuersatz        REAL NOT NULL DEFAULT 19,
    ek_unbekannt      INTEGER NOT NULL DEFAULT 0,   -- 1 = Einkaufspreis nicht bekannt -> keine Marge anzeigen
    aktiv             INTEGER NOT NULL DEFAULT 1,
    erstellt_am       TEXT NOT NULL,
    geaendert_am      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS textbausteine (
    id          INTEGER PRIMARY KEY,
    kategorie   TEXT NOT NULL,       -- einleitung, schluss, hinweis, email_betreff, email_text
    dokumenttyp TEXT NOT NULL DEFAULT 'alle',
    name        TEXT NOT NULL,
    text        TEXT NOT NULL,
    standard    INTEGER NOT NULL DEFAULT 0
);

-- Fortlaufende Nummernkreise (je Präfix und Jahr)
CREATE TABLE IF NOT EXISTS nummernkreise (
    praefix       TEXT NOT NULL,
    jahr          INTEGER NOT NULL,
    letzte_nummer INTEGER NOT NULL DEFAULT 0,
    format        TEXT NOT NULL DEFAULT '{praefix}-{jahr}-{nummer:04d}',
    PRIMARY KEY (praefix, jahr)
);

CREATE TABLE IF NOT EXISTS dokumente (
    id               INTEGER PRIMARY KEY,
    typ              TEXT NOT NULL,   -- rechnung, storno (weitere Typen folgen in Etappe 2)
    status           TEXT NOT NULL DEFAULT 'entwurf' CHECK (status IN ('entwurf', 'festgeschrieben', 'storniert')),
    nummer           TEXT UNIQUE,
    kunde_id         INTEGER REFERENCES kunden(id),
    datum            TEXT NOT NULL,
    leistungsdatum   TEXT,
    leistungsdatum_bis TEXT,
    zahlungsziel_tage INTEGER,
    faellig_am       TEXT,
    betreff          TEXT,
    einleitung       TEXT,
    schlusstext      TEXT,
    hinweise         TEXT,
    steuer_modus     TEXT NOT NULL DEFAULT 'kleinunternehmer',
    bezug_id         INTEGER REFERENCES dokumente(id),
    summe_netto      INTEGER NOT NULL DEFAULT 0,
    summe_steuer     INTEGER NOT NULL DEFAULT 0,
    summe_brutto     INTEGER NOT NULL DEFAULT 0,
    snapshot_json    TEXT,
    pdf_pfad         TEXT,
    pdf_sha256       TEXT,
    festgeschrieben_am TEXT,
    storniert_durch  INTEGER REFERENCES dokumente(id),
    versendet_am     TEXT,
    bezahlt_betrag   INTEGER NOT NULL DEFAULT 0,
    erstellt_am      TEXT NOT NULL,
    geaendert_am     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positionen (
    id            INTEGER PRIMARY KEY,
    dokument_id   INTEGER NOT NULL REFERENCES dokumente(id),
    pos           INTEGER NOT NULL,
    artikel_id    INTEGER REFERENCES artikel(id),
    bezeichnung   TEXT NOT NULL,
    beschreibung  TEXT,
    menge         REAL NOT NULL DEFAULT 1,
    einheit       TEXT,
    einzelpreis   INTEGER NOT NULL DEFAULT 0,   -- Cent, netto
    teilekosten   INTEGER NOT NULL DEFAULT 0,   -- Cent je Einheit (für Margenauswertung)
    steuersatz    REAL NOT NULL DEFAULT 0,
    leistungsart  TEXT
);

-- Versandprotokoll für E-Mails
CREATE TABLE IF NOT EXISTS versandprotokoll (
    id             INTEGER PRIMARY KEY,
    dokument_id    INTEGER REFERENCES dokumente(id),
    zeitpunkt      TEXT NOT NULL,
    empfaenger     TEXT NOT NULL,
    bcc            TEXT,
    betreff        TEXT,
    text           TEXT,
    anhang_name    TEXT,
    anhang_sha256  TEXT,
    status         TEXT NOT NULL,   -- gesendet / fehler
    fehlermeldung  TEXT,
    ablage         TEXT             -- Kopie im IMAP-Gesendet-Ordner: abgelegt / fehler: … / leer = nicht aktiv
);

-- Änderungsprotokoll (nur anhängen, mit Hash-Kette gegen unbemerkte Manipulation)
CREATE TABLE IF NOT EXISTS protokoll (
    id          INTEGER PRIMARY KEY,
    zeitpunkt   TEXT NOT NULL,
    benutzer    TEXT,
    aktion      TEXT NOT NULL,
    objekt      TEXT,
    objekt_id   INTEGER,
    details     TEXT,
    hash_vorher TEXT NOT NULL,
    hash        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_dok_kunde ON dokumente(kunde_id);
CREATE INDEX IF NOT EXISTS ix_pos_dok ON positionen(dokument_id);

-- ------------------------------------------------------------------
-- Schutzregeln (Trigger): festgeschriebene Dokumente sind unveränderbar
-- ------------------------------------------------------------------

CREATE TRIGGER IF NOT EXISTS dok_schutz_update
BEFORE UPDATE ON dokumente
WHEN OLD.status <> 'entwurf' AND (
       NEW.status = 'entwurf'
    OR NEW.typ IS NOT OLD.typ
    OR NEW.nummer IS NOT OLD.nummer
    OR NEW.kunde_id IS NOT OLD.kunde_id
    OR NEW.datum IS NOT OLD.datum
    OR NEW.leistungsdatum IS NOT OLD.leistungsdatum
    OR NEW.leistungsdatum_bis IS NOT OLD.leistungsdatum_bis
    OR NEW.faellig_am IS NOT OLD.faellig_am
    OR NEW.betreff IS NOT OLD.betreff
    OR NEW.einleitung IS NOT OLD.einleitung
    OR NEW.schlusstext IS NOT OLD.schlusstext
    OR NEW.hinweise IS NOT OLD.hinweise
    OR NEW.steuer_modus IS NOT OLD.steuer_modus
    OR NEW.bezug_id IS NOT OLD.bezug_id
    OR NEW.summe_netto IS NOT OLD.summe_netto
    OR NEW.summe_steuer IS NOT OLD.summe_steuer
    OR NEW.summe_brutto IS NOT OLD.summe_brutto
    OR NEW.snapshot_json IS NOT OLD.snapshot_json
    OR NEW.pdf_pfad IS NOT OLD.pdf_pfad
    OR NEW.pdf_sha256 IS NOT OLD.pdf_sha256
    OR NEW.festgeschrieben_am IS NOT OLD.festgeschrieben_am
    OR (OLD.storniert_durch IS NOT NULL AND NEW.storniert_durch IS NOT OLD.storniert_durch)
)
BEGIN
    SELECT RAISE(ABORT, 'Festgeschriebene Dokumente können nicht geändert werden. Bitte Storno oder Gutschrift verwenden.');
END;

CREATE TRIGGER IF NOT EXISTS dok_schutz_delete
BEFORE DELETE ON dokumente
WHEN OLD.status <> 'entwurf' OR OLD.nummer IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Festgeschriebene Dokumente können nicht gelöscht werden.');
END;

CREATE TRIGGER IF NOT EXISTS pos_schutz_insert
BEFORE INSERT ON positionen
WHEN (SELECT status FROM dokumente WHERE id = NEW.dokument_id) <> 'entwurf'
BEGIN
    SELECT RAISE(ABORT, 'Positionen festgeschriebener Dokumente können nicht geändert werden.');
END;

CREATE TRIGGER IF NOT EXISTS pos_schutz_update
BEFORE UPDATE ON positionen
WHEN (SELECT status FROM dokumente WHERE id = OLD.dokument_id) <> 'entwurf'
BEGIN
    SELECT RAISE(ABORT, 'Positionen festgeschriebener Dokumente können nicht geändert werden.');
END;

CREATE TRIGGER IF NOT EXISTS pos_schutz_delete
BEFORE DELETE ON positionen
WHEN (SELECT status FROM dokumente WHERE id = OLD.dokument_id) <> 'entwurf'
BEGIN
    SELECT RAISE(ABORT, 'Positionen festgeschriebener Dokumente können nicht gelöscht werden.');
END;

CREATE TRIGGER IF NOT EXISTS nummernkreis_schutz
BEFORE UPDATE ON nummernkreise
WHEN NEW.letzte_nummer < OLD.letzte_nummer
BEGIN
    SELECT RAISE(ABORT, 'Nummernkreise können nicht zurückgesetzt werden.');
END;

CREATE TRIGGER IF NOT EXISTS nummernkreis_schutz_delete
BEFORE DELETE ON nummernkreise
BEGIN
    SELECT RAISE(ABORT, 'Nummernkreise können nicht gelöscht werden.');
END;

CREATE TRIGGER IF NOT EXISTS protokoll_schutz_update
BEFORE UPDATE ON protokoll
BEGIN
    SELECT RAISE(ABORT, 'Das Protokoll kann nicht geändert werden.');
END;

CREATE TRIGGER IF NOT EXISTS protokoll_schutz_delete
BEFORE DELETE ON protokoll
BEGIN
    SELECT RAISE(ABORT, 'Das Protokoll kann nicht gelöscht werden.');
END;

CREATE TRIGGER IF NOT EXISTS versand_schutz_update
BEFORE UPDATE ON versandprotokoll
BEGIN
    SELECT RAISE(ABORT, 'Das Versandprotokoll kann nicht geändert werden.');
END;

CREATE TRIGGER IF NOT EXISTS versand_schutz_delete
BEFORE DELETE ON versandprotokoll
BEGIN
    SELECT RAISE(ABORT, 'Das Versandprotokoll kann nicht gelöscht werden.');
END;

-- Anfragen aus dem Kontaktformular (per E-Mail abgeholt oder manuell eingefügt)
CREATE TABLE IF NOT EXISTS anfragen (
    id           INTEGER PRIMARY KEY,
    eingang_am   TEXT NOT NULL,
    quelle       TEXT NOT NULL DEFAULT 'email',   -- email / manuell
    message_id   TEXT UNIQUE,
    absender     TEXT,
    betreff      TEXT,
    name         TEXT,
    vorname      TEXT,
    nachname     TEXT,
    telefon      TEXT,
    email        TEXT,
    geraet       TEXT,
    nachricht    TEXT,
    felder_json  TEXT,
    rohtext      TEXT,
    spam_punkte  INTEGER NOT NULL DEFAULT 0,
    gruende_json TEXT,
    einstufung   TEXT NOT NULL,                   -- echt / unsicher / spam
    status       TEXT NOT NULL DEFAULT 'neu',     -- neu / kunde_angelegt / zugeordnet / verworfen
    kunde_id     INTEGER REFERENCES kunden(id) ON DELETE SET NULL,
    bearbeitet_am TEXT
);
CREATE INDEX IF NOT EXISTS ix_anfragen_status ON anfragen(status, einstufung);

-- Reparaturaufträge (Tafel: offen -> in Arbeit -> erledigt)
CREATE TABLE IF NOT EXISTS auftraege (
    id              INTEGER PRIMARY KEY,
    auftragsnr      TEXT UNIQUE NOT NULL,
    kunde_id        INTEGER NOT NULL REFERENCES kunden(id),
    anfrage_id      INTEGER REFERENCES anfragen(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'offen' CHECK (status IN ('offen', 'in_arbeit', 'erledigt')),
    geraet          TEXT,
    leistungsart    TEXT,
    seriennummer    TEXT,
    zubehoer        TEXT,
    fehler          TEXT,
    notizen         TEXT,
    kva_id          INTEGER REFERENCES dokumente(id),
    rechnung_id     INTEGER REFERENCES dokumente(id),
    reihenfolge     REAL NOT NULL DEFAULT 0,
    eingang_am      TEXT NOT NULL,
    begonnen_am     TEXT,
    erledigt_am     TEXT,
    erstellt_am     TEXT NOT NULL,
    geaendert_am    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_auftraege_status ON auftraege(status);

-- Vertragsarten (frei erweiterbar): z. B. Wertgarantie, ESET-Lizenz, MSP-Paket
CREATE TABLE IF NOT EXISTS vertragsarten (
    id                    INTEGER PRIMARY KEY,
    name                  TEXT NOT NULL,
    kategorie             TEXT NOT NULL DEFAULT 'Sonstiges',
    beschreibung          TEXT,
    abrechnung            TEXT NOT NULL DEFAULT 'monatlich',   -- keine / monatlich / vierteljaehrlich / halbjaehrlich / jaehrlich / laufzeit
    laufzeit_monate       INTEGER,                             -- leer = unbefristet
    mindestlaufzeit_monate INTEGER,
    preis                 INTEGER NOT NULL DEFAULT 0,          -- Cent je Abrechnung (bei "laufzeit": für die ganze Laufzeit)
    einkauf               INTEGER NOT NULL DEFAULT 0,          -- Cent Einkauf je Abrechnung (für die Marge)
    auto_verlaengern      INTEGER NOT NULL DEFAULT 0,
    aktiv                 INTEGER NOT NULL DEFAULT 1,
    erstellt_am           TEXT NOT NULL
);

-- Verträge / Lizenzen / Garantien beim Kunden
CREATE TABLE IF NOT EXISTS vertraege (
    id                    INTEGER PRIMARY KEY,
    kunde_id              INTEGER NOT NULL REFERENCES kunden(id),
    vertragsart_id        INTEGER REFERENCES vertragsarten(id) ON DELETE SET NULL,
    bezeichnung           TEXT NOT NULL,
    kategorie             TEXT NOT NULL DEFAULT 'Sonstiges',
    abrechnung            TEXT NOT NULL DEFAULT 'monatlich',
    beginn                TEXT NOT NULL,
    laufzeit_monate       INTEGER,
    mindestlaufzeit_monate INTEGER,
    ende                  TEXT,                                -- Ende der aktuellen Laufzeit (bei befristeten Lizenzen)
    auto_verlaengern      INTEGER NOT NULL DEFAULT 0,
    preis                 INTEGER NOT NULL DEFAULT 0,
    einkauf               INTEGER NOT NULL DEFAULT 0,
    anzahl                REAL NOT NULL DEFAULT 1,
    vertragsnummer        TEXT,                                -- Vertrags-/Policen-/Lizenznummer, Lizenzschlüssel
    geraet                TEXT,                                -- Gerät / Seriennummer (z. B. bei Wertgarantie)
    notizen               TEXT,
    status                TEXT NOT NULL DEFAULT 'aktiv' CHECK (status IN ('aktiv', 'gekuendigt')),
    gekuendigt_am         TEXT,
    kuendigung_zum        TEXT,
    kuendigungsgrund      TEXT,
    abgerechnet_bis       TEXT,                                -- bis hier schon anderweitig berechnet (z. B. Lexware)
    erstellt_am           TEXT NOT NULL,
    geaendert_am          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_vertraege_kunde ON vertraege(kunde_id);

-- Welche Zeiträume eines Vertrags schon abgerechnet sind (verhindert doppelte Rechnungen)
CREATE TABLE IF NOT EXISTS vertrag_abrechnungen (
    id           INTEGER PRIMARY KEY,
    vertrag_id   INTEGER NOT NULL REFERENCES vertraege(id) ON DELETE CASCADE,
    dokument_id  INTEGER NOT NULL REFERENCES dokumente(id) ON DELETE CASCADE,
    von          TEXT NOT NULL,
    bis          TEXT NOT NULL,
    betrag       INTEGER NOT NULL,
    UNIQUE (vertrag_id, von)
);
