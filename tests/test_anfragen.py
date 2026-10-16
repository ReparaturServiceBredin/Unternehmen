import email
import json
from email.message import EmailMessage

import pytest

from rsb import anfragen as anf
from rsb import db as dbm
from rsb.sicherheit import verschluesseln

from conftest import kunde_anlegen, post, rechnung_anlegen

IONOS_HTML = """<html><head><style>p{{color:#333}}</style></head><body><div class="card">
<p>Hello,</p><p>A new form has been submitted on your website. Details below.</p>
<p><strong>Name</strong></p><p>{name}</p>
<p><strong>Telefon</strong></p><p><a href="tel:{tel}">{tel}</a></p>
<p><strong>Email</strong></p><p><a href="mailto:{mail}">{mail}</a></p>
<p><strong>Geraet</strong></p><p>{geraet}</p>
<p><strong>Nachricht</strong></p><p>{nachricht}</p></div></body></html>"""


def formular_mail(name="Kochendörfer Kai", tel="+491719879253", mail="kai.kochendoerfer@t-online.de",
                  geraet="Smartphone / Tablet", nachricht="Display gesprungen<br>Xiaomi 14T Pro", msgid="<a1@ionos>"):
    m = EmailMessage()
    m["From"] = "IONOS <noreply@website.ionos.example>"
    m["To"] = "kontakt@reparatur-bredin.de"
    m["Subject"] = "Neue Formularanfrage"
    m["Message-ID"] = msgid
    m["Date"] = "Wed, 14 Oct 2026 10:15:00 +0200"
    m.set_content("Bitte HTML-Ansicht verwenden")
    m.add_alternative(IONOS_HTML.format(name=name, tel=tel, mail=mail, geraet=geraet, nachricht=nachricht),
                      subtype="html")
    return m


def text_aus(m):
    return anf.mail_text(email.message_from_bytes(m.as_bytes(), policy=email.policy.default))


def test_ionos_formular_wird_gelesen():
    felder = anf.felder_auslesen(text_aus(formular_mail()))
    assert felder == {"name": "Kochendörfer Kai", "telefon": "+491719879253",
                      "email": "kai.kochendoerfer@t-online.de", "geraet": "Smartphone / Tablet",
                      "nachricht": "Display gesprungen\nXiaomi 14T Pro"}


def test_doppelpunkt_variante():
    felder = anf.felder_auslesen("Name: Max Muster\nE-Mail: max@example.com\nNachricht: Akku leer\nbitte melden")
    assert felder["name"] == "Max Muster" and felder["email"] == "max@example.com"
    assert felder["nachricht"] == "Akku leer\nbitte melden"


@pytest.mark.parametrize("name,erwartet", [
    ("Kochendörfer Kai", ("Kai", "Kochendörfer")),
    ("Kai Kochendörfer", ("Kai", "Kochendörfer")),
    ("Müller, Anna", ("Anna", "Müller")),
    ("Anna Maria Schmidt", ("Anna Maria", "Schmidt")),
    ("Schmidt", ("", "Schmidt")),
])
def test_namen(name, erwartet):
    assert anf.name_aufteilen(name) == erwartet


def bew(**f):
    return anf.bewerten(f)[2]


def test_bewertung():
    assert bew(name="Kochendörfer Kai", telefon="+491719879253", email="kai@t-online.de", geraet="Smartphone / Tablet",
               nachricht="Display gesprungen Xiaomi 14T Pro") == "echt"
    assert bew(name="Erika", email="erika@web.de", geraet="Kaffeemaschine",
               nachricht="Meine Jura E8 zieht kein Wasser mehr, was kostet eine Reparatur?") == "echt"
    # SEO-Spam auf Englisch mit Link
    assert bew(name="John Smith", email="john@seo-agency.com", telefon="12345",
               nachricht="Hello, we can bring your website to the first page of Google. Our SEO services and "
                         "backlinks are the best. Visit https://best-seo.example.com for a free trial.") == "spam"
    # Zeichensalat
    assert bew(name="asdf", email="asdf@asdf", telefon="123", nachricht="sdfghjk qwertz") == "spam"
    # Kyrillisch
    assert bew(name="Иван", email="ivan@mail.ru", nachricht="Здравствуйте, предлагаем услуги продвижения сайта") == "spam"
    # knapp, aber plausibel -> nicht automatisch, sondern prüfen
    assert bew(name="Tom", email="tom@gmx.de", nachricht="Hallo") == "unsicher"


def test_verarbeitung_legt_interessent_an_und_keine_dubletten(app, con):
    einst = dbm.einstellungen(con)
    aid = anf.verarbeiten(con, text_aus(formular_mail()), einst, message_id="<a1>")
    a = con.execute("SELECT * FROM anfragen WHERE id=?", (aid,)).fetchone()
    assert a["einstufung"] == "echt" and a["status"] == "kunde_angelegt"
    k = con.execute("SELECT * FROM kunden WHERE id=?", (a["kunde_id"],)).fetchone()
    assert (k["vorname"], k["nachname"], k["interessent"], k["quelle"]) == ("Kai", "Kochendörfer", 1, "Kontaktformular")
    assert "Display gesprungen" in k["notizen"]
    # gleiche E-Mail nochmal -> nichts doppelt
    assert anf.verarbeiten(con, text_aus(formular_mail()), einst, message_id="<a1>") is None
    # neue Anfrage desselben Kunden (andere Schreibweise der Nummer) -> zugeordnet, kein neuer Kunde
    aid2 = anf.verarbeiten(con, text_aus(formular_mail(tel="0171 9879253", mail="anders@example.com",
                                                       nachricht="Akku hält nicht mehr")), einst, message_id="<a2>")
    assert con.execute("SELECT status FROM anfragen WHERE id=?", (aid2,)).fetchone()[0] == "zugeordnet"
    assert con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0] == 1


def test_spam_legt_keinen_kunden_an(app, con):
    text = text_aus(formular_mail(name="Best SEO", mail="x@mailinator.com", tel="1",
                                  nachricht="We offer SEO and backlinks, visit www.seo.example.com"))
    aid = anf.verarbeiten(con, text, dbm.einstellungen(con), message_id="<s1>")
    a = con.execute("SELECT * FROM anfragen WHERE id=?", (aid,)).fetchone()
    assert a["einstufung"] == "spam" and a["kunde_id"] is None
    assert con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0] == 0


def test_rechnung_macht_aus_interessent_kunden(client, con, app):
    aid = anf.verarbeiten(con, text_aus(formular_mail()), dbm.einstellungen(con), message_id="<a1>")
    kid = con.execute("SELECT kunde_id FROM anfragen WHERE id=?", (aid,)).fetchone()[0]
    rechnung_anlegen(client, kid, festschreiben=True)
    assert con.execute("SELECT interessent FROM kunden WHERE id=?", (kid,)).fetchone()[0] == 0


class FalschesImap:
    postfach = {}
    verschoben = []
    angemeldet = None

    def __init__(self, host, port, ssl_context=None, timeout=None):
        self.host = host

    def login(self, user, pw):
        FalschesImap.angemeldet = (user, pw)

    def select(self, ordner):
        return "OK", [b"1"]

    def uid(self, befehl, *args):
        if befehl == "SEARCH":
            return "OK", [b" ".join(self.postfach)]
        if befehl == "FETCH":
            return "OK", [(b"1 (BODY[] {123}", self.postfach[args[0]]), b")"]
        if befehl == "COPY":
            FalschesImap.verschoben.append((args[0], args[1]))
            return "OK", []
        return "OK", []

    def create(self, ordner):
        return "NO", []

    def expunge(self):
        pass

    def logout(self):
        pass


def test_imap_abruf(app, con):
    andere = EmailMessage()
    andere["Subject"] = "Newsletter"
    andere["Message-ID"] = "<n1>"
    andere.set_content("Ganz normale E-Mail")
    FalschesImap.postfach = {b"1": formular_mail().as_bytes(), b"2": andere.as_bytes(),
                             b"3": formular_mail(name="qwertz", mail="a@b", tel="1", nachricht="asdfgh",
                                                 msgid="<x9>").as_bytes()}
    FalschesImap.verschoben = []
    with app.app_context():
        with dbm.Transaktion(con):
            dbm.einstellungen_speichern({"imap_benutzer": "kontakt@reparatur-bredin.de",
                                         "imap_passwort_enc": verschluesseln("geheim")}, con)
        ergebnis = anf.abrufen(con, dbm.einstellungen(con), imap_klasse=FalschesImap)
        assert ergebnis["neu"] == 2 and ergebnis["echt"] == 1 and ergebnis["spam"] == 1
        assert [u for u, _ in FalschesImap.verschoben] == [b"1", b"3"]  # Newsletter bleibt unberührt
        assert FalschesImap.angemeldet == ("kontakt@reparatur-bredin.de", "geheim")
        # zweiter Abruf: nichts doppelt
        assert anf.abrufen(con, dbm.einstellungen(con), imap_klasse=FalschesImap)["neu"] == 0


def test_imap_ohne_zugangsdaten(app, con):
    with app.app_context(), pytest.raises(anf.AbrufFehler):
        anf.abrufen(con, dbm.einstellungen(con))


def test_oberflaeche(client, con):
    r = post(client, "/anfragen/einfuegen", text="Name\nMüller Anna\nTelefon\n0171 1234567\nEmail\nanna@web.de\n"
                                                  "Geraet\nKaffeemaschine\nNachricht\nJura entkalken bitte")
    assert r.status_code == 302
    aid = int(r.headers["Location"].rsplit("/", 1)[1])
    a = con.execute("SELECT * FROM anfragen WHERE id=?", (aid,)).fetchone()
    assert a["einstufung"] == "echt" and a["kunde_id"]
    for url in ["/anfragen", "/anfragen?filter=spam", f"/anfragen/{aid}", "/anfragen/einfuegen",
                "/einstellungen/anfragen", f"/kunden/{a['kunde_id']}", "/kunden?interessenten=1", "/"]:
        assert client.get(url).status_code == 200, url
    # unsichere Anfrage manuell übernehmen mit korrigiertem Namen
    r = post(client, "/anfragen/einfuegen", text="Name\nTom\nEmail\ntom@gmx.de\nNachricht\nHallo")
    aid2 = int(r.headers["Location"].rsplit("/", 1)[1])
    assert con.execute("SELECT einstufung FROM anfragen WHERE id=?", (aid2,)).fetchone()[0] == "unsicher"
    post(client, f"/anfragen/{aid2}/aktion", aktion="kunde", vorname="Tom", nachname="Becker")
    k = con.execute("SELECT k.* FROM kunden k JOIN anfragen a ON a.kunde_id=k.id WHERE a.id=?", (aid2,)).fetchone()
    assert (k["vorname"], k["nachname"]) == ("Tom", "Becker")
    # Speichern in Einstellungen
    r = post(client, "/einstellungen/anfragen", anfragen_aktiv="on", anfragen_intervall_min="5",
             imap_host="imap.ionos.de", imap_port="993", imap_benutzer="", imap_ordner="INBOX",
             imap_zielordner="Anfragen erledigt", imap_verschieben="on", anfrage_erkennung="A new form",
             anfrage_auto_kunde="on", anfrage_schwelle_unsicher="2", anfrage_schwelle_spam="5",
             anfrage_namensreihenfolge="auto", interessent_loeschen_monate="6", imap_passwort="pw")
    assert dbm.einstellungen(con)["anfragen_aktiv"] is True
    assert dbm.einstellungen(con)["imap_passwort_enc"]


class OrdnerImap(FalschesImap):
    """Postfach mit mehreren Ordnern; merkt sich Suche und ob nur lesend geöffnet wurde."""
    ordner = {}
    aufrufe = []

    def select(self, ordner, readonly=False):
        name = ordner.strip('"')
        if name not in OrdnerImap.ordner:
            return "NO", [b"nicht vorhanden"]
        self.aktuell = name
        OrdnerImap.aufrufe.append(("select", name, readonly))
        return "OK", [b"1"]

    def uid(self, befehl, *args):
        inhalt = OrdnerImap.ordner[self.aktuell]
        if befehl == "SEARCH":
            OrdnerImap.aufrufe.append(("search", args[1]))
            return "OK", [b" ".join(inhalt)]
        if befehl == "FETCH":
            return "OK", [(b"1 (BODY[] {123}", inhalt[args[0]]), b")"]
        OrdnerImap.aufrufe.append((befehl,))
        return "OK", []

    def list(self):
        return "OK", [(b'(\\HasNoChildren \\All) "/" "' if "Gmail" in n else b'(\\HasNoChildren) "/" "')
                      + n.encode() + b'"' for n in OrdnerImap.ordner]


def _imap_einrichten(con):
    with dbm.Transaktion(con):
        dbm.einstellungen_speichern({"imap_benutzer": "kontakt@reparatur-bredin.de",
                                     "imap_passwort_enc": verschluesseln("geheim")}, con)


def test_nachholen_aelterer_anfragen_ohne_auto_kunde(app, con):
    with app.app_context():
        _imap_einrichten(con)
        einst = dbm.einstellungen(con)
        # schon bekannt
        anf.verarbeiten(con, text_aus(formular_mail(msgid="<bekannt>")), einst, message_id="<bekannt>")
        # früher gelöscht (z. B. Datenschutz) -> darf nicht zurückkommen
        weg = anf.verarbeiten(con, text_aus(formular_mail(name="Weg Anna", mail="anna@web.de", tel="0170 1111111",
                                                          msgid="<weg>")), einst, message_id="<weg>")
        with dbm.Transaktion(con):
            con.execute("DELETE FROM anfragen WHERE id=?", (weg,))
        assert con.execute("SELECT 1 FROM anfragen_entfernt WHERE message_id='<weg>'").fetchone()
        kunden_vorher = con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0]
        OrdnerImap.ordner = {
            "INBOX": {b"1": formular_mail(name="Alt Max", mail="max@gmx.de", tel="0171 2222222",
                                          msgid="<alt1>").as_bytes(),
                      b"2": formular_mail(msgid="<bekannt>").as_bytes()},
            "Anfragen erledigt": {b"1": formular_mail(name="Erledigt Eva", mail="eva@web.de", tel="0172 3333333",
                                                      msgid="<alt2>").as_bytes(),
                                  b"2": formular_mail(msgid="<weg>").as_bytes()},
            "[Gmail]/Alle Nachrichten": {b"7": formular_mail(name="Archiv Jan", mail="jan@web.de", tel="0173 4444444",
                                                             msgid="<archiv>").as_bytes(),
                                         b"8": formular_mail(name="Alt Max", mail="max@gmx.de", tel="0171 2222222",
                                                             msgid="<alt1>").as_bytes()},
        }
        OrdnerImap.aufrufe = []
        e = anf.nachholen(con, dbm.einstellungen(con), 0, imap_klasse=OrdnerImap)
    assert (e["neu"], e["echt"], e["bekannt"]) == (3, 3, 3)
    assert e["ordner"] == ["INBOX", "Anfragen erledigt", "[Gmail]/Alle Nachrichten"]
    neu = con.execute("SELECT * FROM anfragen WHERE message_id IN ('<alt1>','<alt2>','<archiv>')").fetchall()
    assert len(neu) == 3
    assert all(a["status"] == "neu" and a["kunde_id"] is None for a in neu)  # erst nach Bestätigung
    assert con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0] == kunden_vorher
    assert not con.execute("SELECT 1 FROM anfragen WHERE message_id='<weg>'").fetchone()
    # nur lesend, nichts verschoben/gelöscht, Suche über alle E-Mails
    assert all(a[2] for a in OrdnerImap.aufrufe if a[0] == "select")
    assert not [a for a in OrdnerImap.aufrufe if a[0] in ("COPY", "STORE")]
    assert ("search", "ALL") in OrdnerImap.aufrufe
    # Zeitraum begrenzt die Suche
    OrdnerImap.aufrufe = []
    with app.app_context():
        anf.nachholen(con, dbm.einstellungen(con), 180, imap_klasse=OrdnerImap)
    assert all(a[1].startswith("SINCE ") for a in OrdnerImap.aufrufe if a[0] == "search")


def test_geloeschte_anfrage_kommt_beim_abruf_nicht_zurueck(app, con):
    einst = dbm.einstellungen(con)
    aid = anf.verarbeiten(con, text_aus(formular_mail()), einst, message_id="<a1>")
    with dbm.Transaktion(con):
        con.execute("DELETE FROM anfragen WHERE id=?", (aid,))
    assert anf.verarbeiten(con, text_aus(formular_mail()), einst, message_id="<a1>") is None


def test_anfrage_ohne_kunde_wird_wieder_zu_pruefen(app, con):
    aid = anf.verarbeiten(con, text_aus(formular_mail()), dbm.einstellungen(con), message_id="<a1>")
    kid = con.execute("SELECT kunde_id FROM anfragen WHERE id=?", (aid,)).fetchone()[0]
    with dbm.Transaktion(con):
        con.execute("DELETE FROM kunden WHERE id=?", (kid,))  # Kunde fehlt, Anfrage bleibt
    a = con.execute("SELECT * FROM anfragen WHERE id=?", (aid,)).fetchone()
    assert a["status"] == "kunde_angelegt" and a["kunde_id"] is None
    assert anf.ohne_kunde_zuruecksetzen(con) == 1
    assert con.execute("SELECT status FROM anfragen WHERE id=?", (aid,)).fetchone()[0] == "neu"
    assert anf.ohne_kunde_zuruecksetzen(con) == 0


def test_sammelbestaetigung_und_nachholen_oberflaeche(client, con):
    with client.application.app_context():
        einst = {**dbm.einstellungen(con), "anfrage_auto_kunde": False}
    a1 = anf.verarbeiten(con, text_aus(formular_mail(msgid="<b1>")), einst, message_id="<b1>")
    a2 = anf.verarbeiten(con, text_aus(formular_mail(tel="0171 9879253", mail="anders@example.com",
                                                     nachricht="Akku hält nicht mehr")), einst, message_id="<b2>")
    spam = anf.verarbeiten(con, text_aus(formular_mail(name="Best SEO", mail="x@mailinator.com", tel="1",
                                                       nachricht="We offer SEO, visit www.seo.example.com")),
                           einst, message_id="<b3>")
    seite = client.get("/anfragen").get_data(as_text=True)
    assert "Ältere Anfragen prüfen und nachholen" in seite and f'name="anfrage_id" value="{a1}"' in seite
    r = post(client, "/anfragen/bestaetigen", anfrage_id=[str(a1), str(a2), str(spam)])
    assert r.status_code == 302
    status = {r["id"]: (r["status"], r["kunde_id"]) for r in con.execute("SELECT * FROM anfragen")}
    assert status[a1][0] == "kunde_angelegt" and status[a2] == ("zugeordnet", status[a1][1])
    assert status[spam] == ("neu", None)
    assert con.execute("SELECT COUNT(*) FROM kunden").fetchone()[0] == 1
    # Nachholen ohne eingerichtetes Postfach: verständliche Meldung, kein Absturz
    r = post(client, "/anfragen/nachholen", zeitraum="365")
    assert r.status_code == 302
    assert "Postfach konnte nicht durchsucht werden" in client.get("/anfragen").get_data(as_text=True)
