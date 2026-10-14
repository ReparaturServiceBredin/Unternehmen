"""E-Mail-Versand über den eigenen SMTP-Zugang."""
import hashlib
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from . import db as dbm
from .sicherheit import entschluesseln


class MailFehler(Exception):
    pass


def _verbindung(einst):
    host = (einst.get("smtp_host") or "").strip()
    if not host:
        raise MailFehler("Es ist noch kein E-Mail-Server eingerichtet (Einstellungen → E-Mail).")
    port = int(einst.get("smtp_port") or 587)
    art = einst.get("smtp_sicherheit") or "starttls"
    kontext = ssl.create_default_context()
    try:
        if art == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=30, context=kontext)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            if art == "starttls":
                server.starttls(context=kontext)
        if einst.get("smtp_benutzer"):
            server.login(einst["smtp_benutzer"], entschluesseln(einst.get("smtp_passwort_enc")))
        return server
    except smtplib.SMTPAuthenticationError:
        raise MailFehler("Anmeldung am E-Mail-Server fehlgeschlagen. Bitte Benutzername und Passwort prüfen.")
    except (OSError, smtplib.SMTPException) as e:
        raise MailFehler(f"Verbindung zum E-Mail-Server fehlgeschlagen: {e}")


def nachricht_bauen(einst, an, betreff, text, anhang=None, anhang_name=None, bcc=None):
    msg = EmailMessage()
    absender = einst.get("absender_email") or einst.get("smtp_benutzer")
    msg["From"] = formataddr((einst.get("absender_name") or "", absender))
    msg["To"] = an
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = betreff
    msg["Message-ID"] = make_msgid(domain=(absender or "localhost").split("@")[-1])
    msg.set_content(text)
    if anhang:
        msg.add_attachment(anhang, maintype="application", subtype="pdf", filename=anhang_name)
    return msg


def senden(con, einst, an, betreff, text, anhang=None, anhang_name=None, dokument_id=None):
    """Sendet eine E-Mail und schreibt das Ergebnis ins Versandprotokoll (auch bei Fehlern)."""
    bcc = einst.get("absender_email") if einst.get("bcc_an_mich") else None
    sha = hashlib.sha256(anhang).hexdigest() if anhang else None
    status, fehler = "gesendet", None
    try:
        msg = nachricht_bauen(einst, an, betreff, text, anhang, anhang_name, bcc)
        server = _verbindung(einst)
        try:
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except MailFehler as e:
        status, fehler = "fehler", str(e)
    except (OSError, smtplib.SMTPException, ValueError) as e:
        status, fehler = "fehler", f"Versand fehlgeschlagen: {e}"
    with dbm.Transaktion(con):
        con.execute(
            "INSERT INTO versandprotokoll (dokument_id, zeitpunkt, empfaenger, bcc, betreff, text, anhang_name, "
            "anhang_sha256, status, fehlermeldung) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (dokument_id, dbm.jetzt(), an, bcc, betreff, text, anhang_name, sha, status, fehler),
        )
        if status == "gesendet" and dokument_id:
            con.execute("UPDATE dokumente SET versendet_am=? WHERE id=?", (dbm.jetzt(), dokument_id))
        dbm.protokollieren("email_" + status, "dokument" if dokument_id else "einstellungen", dokument_id,
                           {"an": an, "betreff": betreff, "fehler": fehler}, con=con)
    if fehler:
        raise MailFehler(fehler)
