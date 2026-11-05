// Anpassen der Oberfläche: freie Einträge in Auswahllisten, Bausteine ein-/ausblenden und anordnen, Tabellenspalten.
// Alles wird je Benutzer gespeichert (POST /oberflaeche) und gilt auf allen Geräten.
(function () {
  'use strict';
  const $ = (s, w) => (w || document).querySelector(s);
  const $$ = (s, w) => [...(w || document).querySelectorAll(s)];
  const csrf = () => ($('meta[name=csrf]') || {}).content || '';
  const UI = window.UI_ZUSTAND || {};
  const FREI = '__frei__';

  // Speichern nacheinander (nie parallel), damit eine ältere Anfrage keine neuere überschreibt
  let warteschlange = Promise.resolve();
  function merken(daten) {
    warteschlange = warteschlange.then(() => fetch('/oberflaeche', { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF': csrf() }, body: JSON.stringify(daten) }).catch(() => {}));
    return warteschlange;
  }
  function knopf(text, titel, klasse) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'zweit klein ' + (klasse || ''); b.textContent = text;
    if (titel) { b.title = titel; b.setAttribute('aria-label', titel); }
    return b;
  }

  // ================================================================ 1. Auswahllisten mit eigenem Eintrag
  // <select data-frei data-wert="aktueller Wert" data-vorgabe="leistungsarten"> – Vorschläge aus der Liste oder
  // „✎ Eigener Eintrag …“. Mit data-vorgabe wird der neue Eintrag beim Speichern in die Vorgabenliste übernommen.
  function freiAuswahl(sel) {
    if (sel.dataset.freiBereit) return;
    sel.dataset.freiBereit = '1';
    const optWert = o => (o.value !== '' || o.hasAttribute('value')) ? o.value : o.text;
    const wert = sel.dataset.wert;
    if (wert && !$$('option', sel).some(o => optWert(o) === wert)) {
      sel.add(new Option(wert, wert, true, true));
    }
    sel.add(new Option('✎ Eigener Eintrag …', FREI));
    const name = sel.name;
    const box = document.createElement('span');
    box.className = 'frei-eingabe';
    box.hidden = true;
    const feld = document.createElement('input');
    feld.type = 'text'; feld.placeholder = 'Eigenen Eintrag eingeben'; feld.maxLength = 120; feld.disabled = true;
    const zurueck = knopf('☰', 'Aus der Liste wählen');
    const merker = document.createElement('input');
    merker.type = 'hidden'; merker.name = '_neue_vorgabe'; merker.disabled = true;
    box.append(feld, zurueck, merker);
    sel.after(box);
    let vorher = sel.value === FREI ? '' : sel.value;

    function eigen(an) {
      sel.hidden = an; sel.disabled = an;
      box.hidden = !an; feld.disabled = !an;
      if (an) { feld.name = name; sel.removeAttribute('name'); feld.required = sel.required; feld.focus(); }
      else { sel.name = name; feld.removeAttribute('name'); merker.disabled = true; }
    }
    sel.addEventListener('change', () => {
      if (sel.value === FREI) { eigen(true); sel.value = vorher; }
      else vorher = sel.value;
    });
    feld.addEventListener('input', () => {
      const v = feld.value.trim();
      merker.disabled = !(sel.dataset.vorgabe && v);
      merker.value = sel.dataset.vorgabe ? sel.dataset.vorgabe + '|' + v : '';
    });
    feld.addEventListener('change', () => {
      const v = feld.value.trim();
      const treffer = $$('option', sel).find(o => o.value !== FREI && optWert(o).toLowerCase() === v.toLowerCase());
      if (treffer && v) { sel.value = optWert(treffer); vorher = sel.value; eigen(false); sel.dispatchEvent(new Event('change')); }
    });
    feld.addEventListener('keydown', e => {
      if (e.key === 'Escape') { eigen(false); sel.value = vorher; sel.focus(); }
    });
    zurueck.addEventListener('click', () => { eigen(false); sel.value = vorher; sel.focus(); });
  }
  function freiAlle(wurzel) { $$('select[data-frei]', wurzel).forEach(freiAuswahl); }
  freiAlle(document);
  new MutationObserver(liste => liste.forEach(m => m.addedNodes.forEach(n => {
    if (n.nodeType !== 1) return;
    if (n.matches && n.matches('select[data-frei]')) freiAuswahl(n); else freiAlle(n);
  }))).observe(document.body, { childList: true, subtree: true });

  // ================================================================ 2. Bausteine ein-/ausblenden und anordnen
  // <div class="anpassbar" data-anpassbar="start"> mit Kindern <section class="baustein" data-kachel="id"
  //   data-titel="…" data-breite="3|4|6|12" [data-standard="aus"]>
  const BREITEN = [['3', '¼'], ['4', '⅓'], ['6', '½'], ['8', '⅔'], ['12', 'ganz']];
  const layouts = UI.layouts || {};

  function layoutLesen(rahmen) {
    const l = layouts[rahmen.dataset.anpassbar] || {};
    return { reihe: l.reihe || [], aus: l.aus || null, breite: l.breite || {} };
  }
  function anwenden(rahmen) {
    const l = layoutLesen(rahmen);
    const teile = $$(':scope > [data-kachel]', rahmen);
    const nach = new Map(teile.map(t => [t.dataset.kachel, t]));
    l.reihe.forEach(id => { if (nach.has(id)) rahmen.append(nach.get(id)); });
    teile.forEach(t => {
      const id = t.dataset.kachel;
      const aus = l.aus ? l.aus.includes(id) : t.dataset.standard === 'aus';
      t.classList.toggle('baustein-aus', aus);
      const b = l.breite[id] || t.dataset.breite || '12';
      t.style.setProperty('--spalten', b);
      t.dataset.aktBreite = b;
    });
  }
  function layoutAusDom(rahmen) {
    const teile = $$(':scope > [data-kachel]', rahmen);
    const breite = {};
    teile.forEach(t => { if (t.dataset.aktBreite !== (t.dataset.breite || '12')) breite[t.dataset.kachel] = t.dataset.aktBreite; });
    return { reihe: teile.map(t => t.dataset.kachel), aus: teile.filter(t => t.classList.contains('baustein-aus')).map(t => t.dataset.kachel),
             breite };
  }
  function jetztSpeichern(rahmen, beimVerlassen) {
    clearTimeout(rahmen._speichern); rahmen._speichern = null;
    const l = layoutAusDom(rahmen);
    layouts[rahmen.dataset.anpassbar] = l;
    const daten = { layout: { seite: rahmen.dataset.anpassbar, ...l } };
    if (beimVerlassen) {  // Seite wird verlassen: Anfrage überlebt das Schließen (keepalive)
      fetch('/oberflaeche', { method: 'POST', keepalive: true,
        headers: { 'Content-Type': 'application/json', 'X-CSRF': csrf() }, body: JSON.stringify(daten) }).catch(() => {});
    } else merken(daten);
  }
  function speichern(rahmen) {
    clearTimeout(rahmen._speichern);
    rahmen._speichern = setTimeout(() => jetztSpeichern(rahmen), 200);
  }
  addEventListener('pagehide', () => $$('[data-anpassbar]').forEach(r => { if (r._speichern) jetztSpeichern(r, true); }));

  function werkzeug(rahmen, t) {
    const leiste = document.createElement('div');
    leiste.className = 'baustein-werkzeug';
    const griff = document.createElement('span');
    griff.className = 'baustein-griff'; griff.textContent = '⠿'; griff.title = 'Ziehen zum Verschieben';
    const titel = document.createElement('span'); titel.className = 'baustein-name'; titel.textContent = t.dataset.titel || t.dataset.kachel;
    const hoch = knopf('↑', 'nach vorne'), runter = knopf('↓', 'nach hinten');
    const breite = document.createElement('select');
    breite.className = 'klein-select'; breite.title = 'Breite';
    BREITEN.forEach(([w, n]) => breite.add(new Option(n, w, false, w === t.dataset.aktBreite)));
    const auge = knopf('', '', 'baustein-auge');
    const augeText = () => {
      const aus = t.classList.contains('baustein-aus');
      auge.textContent = aus ? 'Einblenden' : 'Ausblenden';
      auge.title = aus ? 'Baustein wieder anzeigen' : 'Baustein ausblenden';
    };
    augeText();
    hoch.onclick = () => { const v = t.previousElementSibling; if (v) { rahmen.insertBefore(t, v); speichern(rahmen); } };
    runter.onclick = () => { const n = t.nextElementSibling; if (n) { rahmen.insertBefore(n, t); speichern(rahmen); } };
    breite.onchange = () => { t.dataset.aktBreite = breite.value; t.style.setProperty('--spalten', breite.value); speichern(rahmen); };
    auge.onclick = () => { t.classList.toggle('baustein-aus'); augeText(); speichern(rahmen); };
    leiste.append(griff, titel, hoch, runter, breite, auge);
    t.prepend(leiste);
    t.draggable = true;
  }

  function bearbeiten(rahmen, an, schalter) {
    rahmen.classList.toggle('anpassen-an', an);
    schalter.textContent = an ? 'Fertig' : 'Anpassen';
    schalter.setAttribute('aria-pressed', an ? 'true' : 'false');
    const teile = $$(':scope > [data-kachel]', rahmen);
    // Links in Kacheln sind beim Anpassen abgeschaltet, sonst öffnet jeder Klick auf ein Werkzeug die verlinkte Seite
    if (an) {
      $$('a[href]', rahmen).concat(teile.filter(t => t.matches('a[href]'))).forEach(a => {
        a.dataset.hrefAnpassen = a.getAttribute('href'); a.removeAttribute('href');
      });
      teile.forEach(t => werkzeug(rahmen, t));
    } else {
      $$('[data-href-anpassen]', rahmen).concat(teile.filter(t => t.dataset.hrefAnpassen)).forEach(a => {
        a.setAttribute('href', a.dataset.hrefAnpassen); delete a.dataset.hrefAnpassen;
      });
      teile.forEach(t => { $$(':scope > .baustein-werkzeug', t).forEach(w => w.remove()); t.draggable = false; });
    }
    const zurueck = rahmen._zurueck;
    if (zurueck) zurueck.hidden = !an;
  }

  $$('[data-anpassbar]').forEach(rahmen => {
    anwenden(rahmen);
    const kopf = $('.kopf .leiste') || $('.kopf');
    const schalter = knopf('Anpassen', 'Bausteine ein-/ausblenden, verschieben und Breite ändern', 'anpassen-knopf');
    schalter.classList.remove('klein');
    const zurueck = knopf('Standard', 'Anordnung auf den Standard zurücksetzen');
    zurueck.classList.remove('klein'); zurueck.hidden = true;
    rahmen._zurueck = zurueck;
    if (kopf) kopf.append(schalter, zurueck); else rahmen.before(schalter, zurueck);
    let an = false;
    schalter.onclick = () => { an = !an; bearbeiten(rahmen, an, schalter); };
    zurueck.onclick = () => {
      delete layouts[rahmen.dataset.anpassbar];
      merken({ layout: { seite: rahmen.dataset.anpassbar, zuruecksetzen: true } }).then(() => location.reload());
    };
    // Ziehen und Ablegen (Maus); am Handy die Pfeil-Knöpfe
    let gezogen = null;
    rahmen.addEventListener('dragstart', e => {
      const t = e.target.closest('[data-kachel]');
      if (!an || !t || t.parentElement !== rahmen) return;
      gezogen = t; t.classList.add('wird-gezogen'); e.dataTransfer.effectAllowed = 'move';
      try { e.dataTransfer.setData('text/plain', t.dataset.kachel); } catch (_) { /* ältere Browser */ }
    });
    rahmen.addEventListener('dragover', e => {
      if (!gezogen) return;
      e.preventDefault();
      const ziel = e.target.closest('[data-kachel]');
      if (!ziel || ziel === gezogen || ziel.parentElement !== rahmen) return;
      const r = ziel.getBoundingClientRect();
      const danach = (e.clientY - r.top) > r.height / 2 || (e.clientX - r.left) > r.width / 2 && (e.clientY - r.top) > r.height / 4;
      rahmen.insertBefore(gezogen, danach ? ziel.nextElementSibling : ziel);
    });
    rahmen.addEventListener('dragend', () => {
      if (!gezogen) return;
      gezogen.classList.remove('wird-gezogen'); gezogen = null; speichern(rahmen);
    });
  });

  // ================================================================ 3. Tabellenspalten ein-/ausblenden
  // Jede Tabelle class="liste" mit Kopfzeile und mindestens 4 Spalten bekommt „Spalten“. Ausnahme: data-spalten="fest".
  const spaltenZustand = UI.spalten || {};
  const seite = location.pathname.replace(/\/\d+(?=\/|$)/g, '/#');
  const tabellen = $$('table.liste').filter(t => t.dataset.spalten !== 'fest' && !t.closest('[data-spalten="fest"]'));
  tabellen.forEach((tab, nr) => {
    const kopfzeile = tab.tHead ? tab.tHead.rows[0] : tab.rows[0];
    if (!kopfzeile || !kopfzeile.cells.length || [...kopfzeile.cells].some(c => c.tagName !== 'TH')) return;
    // Sortierpfeile gehören nicht zum Namen (sie wechseln beim Umsortieren)
    const namen = [...kopfzeile.cells].map((c, i) =>
      (c.textContent.replace(/[↕▲▼↑↓⇅⬍]/g, '').replace(/\s+/g, ' ').trim() || `Spalte ${i + 1}`).slice(0, 40));
    if (namen.length < 4 || [...kopfzeile.cells].some(c => c.colSpan > 1)) return;
    const schluessel = (seite + '#' + nr).slice(0, 100);
    let aus = new Set(spaltenZustand[schluessel] || []);
    function zeigen() {
      [...tab.rows].forEach(z => {
        if ([...z.cells].some(c => c.colSpan > 1)) return;     // Summen-/Leerzeilen nicht zerlegen
        [...z.cells].forEach((c, i) => { c.classList.toggle('spalte-aus', aus.has(namen[i])); });
      });
    }
    zeigen();
    const box = document.createElement('details');
    box.className = 'spalten-wahl';
    box.innerHTML = '<summary class="klein" title="Spalten ein- oder ausblenden">Spalten</summary><div class="spalten-liste"></div>';
    const liste = $('.spalten-liste', box);
    namen.forEach((n, i) => {
      if (i === 0) return;  // erste Spalte (meist Nummer/Name) bleibt immer sichtbar
      const l = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = !aus.has(n);
      cb.onchange = () => {
        if (cb.checked) aus.delete(n); else aus.add(n);
        zeigen();
        spaltenZustand[schluessel] = [...aus];
        merken({ spalten: { tabelle: schluessel, aus: [...aus] } });
      };
      l.append(cb, ' ' + n);
      liste.append(l);
    });
    const huelle = tab.parentElement.style.overflowX === 'auto' ? tab.parentElement : tab;
    huelle.before(box);
  });
})();
