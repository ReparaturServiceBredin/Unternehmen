"""Phase 5: Garantie je Reparatur/Position, Wiedererkennung per SN/IMEI, Garantiefall."""
import json
import re
from datetime import date

from rsb import db as dbm
from rsb import garantie as gar

from conftest import kunde_anlegen, post
from test_annahme import auftrag_mit_annahme, unterschreiben
from test_auftraege import kva_mit_position


def test_plus_monate():
    assert gar.plus_monate(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert gar.plus_monate(date(2026, 10, 15), 12) == date(2027, 10, 15)
    assert gar.sn_normal(" 3567-8901 2345/678 ") == "356789012345678"


def test_garantie_auf_abholschein_und_rechnung(client, con, app):
    kid = kunde_anlegen(client)
    aid = auftrag_mit_annahme(client, kid, geraet="Xiaomi 14T Pro", garantie_monate="6")
    kva_mit_position(client, con, aid)
    post(client, f"/auftraege/{aid}/status", status="erledigt")
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (aid,)).fetchone()
    assert a["garantie_monate"] == 6
    # Rechnung festschreiben → Garantietext im Snapshot
    re_id = a["rechnung_id"]
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (re_id,)).fetchone()
    client.post(f"/dokumente/{re_id}", data={
        "csrf": "test-token", "kunde_id": kid, "datum": "", "leistungsdatum": "2026-10-15", "zahlungsziel_tage": "",
        "betreff": d["betreff"], "einleitung": "x", "schlusstext": "y", "hinweise": "", "aktion": "festschreiben",
        "p_bezeichnung": ["Displaytausch", "Schutzfolie"], "p_beschreibung": ["", ""], "p_menge": ["1", "1"],
        "p_einheit": ["pauschal", "Stk."], "p_preis": ["149,00", "9,90"], "p_teilekosten": ["70,00", "1,00"],
        "p_steuersatz": ["19", "19"], "p_leistungsart": ["Smartphone", "Smartphone"], "p_artikel_id": ["", ""],
        "p_garantie": ["", "0"]})
    d = con.execute("SELECT * FROM dokumente WHERE id=?", (re_id,)).fetchone()
    assert d["status"] == "festgeschrieben"
    snap = json.loads(d["snapshot_json"])
    assert "6 Monate Garantie" in snap["garantie_text"] and "gesetzlichen" in snap["garantie_text"]
    assert [p["garantie_monate"] for p in snap["positionen"]] == [None, 0]
    assert client.get(f"/dokumente/{re_id}/pdf").status_code == 200
    unterschreiben(client, aid, art="abholung")
    b = con.execute("SELECT snapshot FROM auftrag_belege WHERE auftrag_id=? AND art='abholung'", (aid,)).fetchone()
    assert "6 Monate Garantie" in json.loads(b["snapshot"])["garantie"]
    seite = client.get(f"/auftraege/{aid}").get_data(as_text=True)
    assert "6 Monate bis" in seite and "läuft" in seite


def test_wiedererkennung_und_garantiefall(client, con):
    kid = kunde_anlegen(client)
    alt = auftrag_mit_annahme(client, kid, seriennummer="356789012345678")
    post(client, f"/auftraege/{alt}/status", status="erledigt", ohne_kva="1")
    post(client, f"/auftraege/{alt}/abgeholt")
    # Suche ignoriert Leerzeichen/Bindestriche
    liste = client.get("/auftraege/geraet-pruefen?sn=3567 8901-2345 678").get_json()
    assert len(liste) == 1 and liste[0]["laeuft"] and "12 Monate bis" in liste[0]["garantie"]
    assert client.get(f"/auftraege/geraet-pruefen?sn=356789012345678&ohne={alt}").get_json() == []
    # Garantiefall anlegen
    neu = auftrag_mit_annahme(client, kid, seriennummer="356789012345678", auftragsart="garantie",
                              garantie_bezug_id=str(alt), interne_kosten="35,00", interne_kosten_notiz="Akku")
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (neu,)).fetchone()
    assert a["auftragsart"] == "garantie" and a["garantie_bezug_id"] == alt and a["interne_kosten"] == 3500
    seite = client.get(f"/auftraege/{neu}").get_data(as_text=True)
    assert "war schon 1× hier" in seite and "Garantiefall" in seite and "35,00" in seite
    # Erledigt ohne KVA-Rückfrage und ohne Rechnung
    post(client, f"/auftraege/{neu}/status", status="erledigt")
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (neu,)).fetchone()
    assert a["status"] == "erledigt" and a["rechnung_id"] is None
    assert "Garantiefälle zu diesem Auftrag" in client.get(f"/auftraege/{alt}").get_data(as_text=True)


def test_artikel_garantie_und_einstellung(client, con):
    post(client, "/einstellungen?bereich=annahme", garantie_monate="6", annahme_zubehoer="Ladekabel",
         annahme_kva_gebuehr_cent="0", annahme_datenschutz="", annahme_abholbedingungen="", abholschein_text="")
    assert dbm.einstellungen(con)["garantie_monate"] == 6
    r = post(client, "/artikel/neu", name="Akkutausch iPhone", preis="89,00", teilekosten="30,00", einheit="pauschal",
             typ="leistung", steuersatz="19", aktiv="1", garantie_monate="3")
    assert r.status_code == 302
    assert con.execute("SELECT garantie_monate FROM artikel WHERE name='Akkutausch iPhone'").fetchone()[0] == 3
    kid = kunde_anlegen(client)
    aid = auftrag_mit_annahme(client, kid)
    assert "Standard: 6" in client.get(f"/auftraege/{aid}").get_data(as_text=True)
    a = con.execute("SELECT * FROM auftraege WHERE id=?", (aid,)).fetchone()
    assert gar.monate(a, dbm.einstellungen(con)) == 6
