// Hilfsfunktionen für Beträge im deutschen Format
function zahl(text) {
  if (text === undefined || text === null) return 0;
  let t = String(text).replace(/[€\s]/g, '');
  if (t.includes(',')) t = t.replace(/\./g, '').replace(',', '.');
  const n = parseFloat(t);
  return isNaN(n) ? 0 : n;
}
function euroText(n) {
  return n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function euro(n) { return euroText(n) + ' €'; }

// ---------------------------------------------------------------- Fotos hochladen (Auftrag)
function csrfWert() { const f = document.querySelector('input[name=csrf]'); return f ? f.value : ''; }

document.querySelectorAll('.foto-upload').forEach(box => {
  const zone = box.querySelector('.foto-zone'), info = box.querySelector('.foto-fortschritt');
  async function hochladen(dateien) {
    dateien = [...dateien];
    if (!dateien.length) return;
    const kategorie = box.querySelector('.foto-kategorie').value;
    let fehler = [];
    for (let i = 0; i < dateien.length; i++) {
      info.textContent = `Lade Foto ${i + 1} von ${dateien.length} hoch …`;
      const daten = new FormData();
      daten.append('csrf', csrfWert());
      daten.append('kategorie', kategorie);
      daten.append('upload_token', box.dataset.token || '');
      daten.append('foto', dateien[i], dateien[i].name);
      try {
        const r = await fetch(box.dataset.url, { method: 'POST', body: daten, headers: { 'X-Requested-With': 'fetch' } });
        const j = await r.json().catch(() => ({ ok: false, meldung: r.status === 413 ? 'Datei zu groß' : `Fehler ${r.status}` }));
        (j.dateien || [j]).forEach(e => {
          if (!e.ok) { fehler.push(`${e.datei || dateien[i].name}: ${e.meldung}`); return; }
          const galerie = document.getElementById('galerie-neu');
          if (galerie) galerie.insertAdjacentHTML('beforeend',
            `<div class="foto"><a href="/fotos/${e.id}" target="_blank"><img src="/fotos/${e.id}/vorschau" alt=""></a><div class="info"><b>${kategorie}</b><br>${e.datei}</div></div>`);
        });
      } catch (err) { fehler.push(`${dateien[i].name}: Verbindung fehlgeschlagen`); }
    }
    info.textContent = fehler.length ? 'Nicht gespeichert: ' + fehler.join(' · ') : `${dateien.length} Foto(s) gespeichert.`;
    info.style.color = fehler.length ? 'var(--rot)' : 'var(--gruen)';
    if (box.dataset.neuLaden === '1' && fehler.length < dateien.length) {
      setTimeout(() => { window.location.hash = 'fotos'; window.location.reload(); }, fehler.length ? 2500 : 300);
    }
  }
  box.querySelectorAll('.foto-datei').forEach(inp => inp.addEventListener('change', () => { hochladen(inp.files); inp.value = ''; }));
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('ueber'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('ueber'));
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('ueber'); hochladen(e.dataTransfer.files); });
});

// ---------------------------------------------------------------- KVA-Auswahl (Auftrag verknüpfen)
document.querySelectorAll('.kva-auswahl').forEach(box => {
  const suche = box.querySelector('.kva-suche'), alle = box.querySelector('.kva-alle');
  const tbody = box.querySelector('tbody');
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let timer = null;
  async function laden() {
    const kunde = box.dataset.kunde || '';
    const p = new URLSearchParams({ kunde_id: kunde, alle: (alle.checked || !kunde) ? '1' : '0', q: suche.value });
    const r = await fetch('/auftraege/kva-auswahl?' + p);
    const liste = r.ok ? await r.json() : [];
    if (!liste.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="klein">Keine freien Kostenvoranschläge gefunden${(kunde && !alle.checked) ? ' (nur dieser Kunde – „alle Kunden anzeigen“ probieren)' : ''}.</td></tr>`;
      return;
    }
    tbody.innerHTML = liste.map(d => `<tr data-id="${d.id}" data-text="${esc(d.nummer + ' · ' + d.datum + ' · ' + d.betrag)}">
      <td><a href="/dokumente/${d.id}" target="_blank">${esc(d.nummer)}</a><div class="klein">${esc(d.betreff)}</div></td>
      <td>${esc(d.datum)}</td><td>${esc(d.kunde)}${(kunde && String(d.kunde_id) !== String(kunde)) ? ' <span class="marke-status st-warnung">anderer Kunde</span>' : ''}</td>
      <td class="zahl">${esc(d.betrag)}</td><td class="zahl"><button type="button" class="zweit klein kva-waehlen">Verknüpfen</button></td></tr>`).join('');
  }
  box.laden = laden;
  suche.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(laden, 250); });
  alle.addEventListener('change', laden);
  tbody.addEventListener('click', e => {
    const knopf = e.target.closest('.kva-waehlen');
    if (!knopf) return;
    const zeile = knopf.closest('tr');
    if (box.dataset.modus === 'verknuepfen') {
      const f = document.createElement('form');
      f.method = 'post'; f.action = box.dataset.ziel;
      f.innerHTML = `<input type="hidden" name="csrf" value="${esc(csrfWert())}"><input type="hidden" name="kva_id" value="${zeile.dataset.id}">`;
      document.body.appendChild(f); f.submit();
    } else {
      document.getElementById('f_kva_id').value = zeile.dataset.id;
      document.getElementById('kva-gewaehlt-text').textContent = zeile.dataset.text;
      document.getElementById('kva-gewaehlt').hidden = false;
      tbody.querySelectorAll('tr').forEach(t => t.classList.toggle('gewaehlt', t === zeile));
    }
  });
  laden();
});
