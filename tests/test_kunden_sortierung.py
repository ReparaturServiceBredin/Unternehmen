"""Kundenliste: Sortierung per Klick auf die Spaltenköpfe, gemerkt in der Sitzung."""
import re

from conftest import kunde_anlegen


def namen(client, url):
    html = client.get(url).get_data(as_text=True)
    return re.findall(r'/kunden/\d+"><b>([^<]+)</b>', html)


def test_sortieren_nach_spalten(client):
    kunde_anlegen(client, vorname="Birgit", nachname="Schmitt", ort="Möckmühl", plz="74219")
    kunde_anlegen(client, typ="firma", firma="Ölwerk GmbH", nachname="", ort="Adelsheim", plz="74740")
    kunde_anlegen(client, vorname="Jochen", nachname="schilling", ort="", plz="")
    # Standard: Name/Firma, Umlaute wie A/O, Groß/klein egal
    assert namen(client, "/kunden") == ["Ölwerk GmbH", "Jochen schilling", "Birgit Schmitt"]
    assert namen(client, "/kunden?sort=name&ab=1") == ["Birgit Schmitt", "Jochen schilling", "Ölwerk GmbH"]
    assert namen(client, "/kunden?sort=nr") == ["Birgit Schmitt", "Ölwerk GmbH", "Jochen schilling"]
    assert namen(client, "/kunden?sort=neu&ab=1") == ["Jochen schilling", "Ölwerk GmbH", "Birgit Schmitt"]
    # Ort: ohne Ort immer am Ende
    assert namen(client, "/kunden?sort=ort") == ["Ölwerk GmbH", "Birgit Schmitt", "Jochen schilling"]
    assert namen(client, "/kunden?sort=ort&ab=1")[-1] == "Jochen schilling"
    # gemerkt
    html = client.get("/kunden").get_data(as_text=True)
    assert 'aria-sort="descending"' in html and "sort=ort" in html
    # unbekannte Sortierung → Standard bleibt bestehen
    assert client.get("/kunden?sort=quatsch").status_code == 200
