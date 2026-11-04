// Sichtschutz: Schalter in der Kopfleiste; ist er an, werden Namen, Kontaktdaten und Beträge unscharf.
(function () {
  const html = document.documentElement;
  const cookie = (name, wert) => { document.cookie = name + '=' + wert + ';path=/;max-age=' + (wert ? 31536000 : 0) + ';SameSite=Lax'; };
  document.addEventListener('click', e => {
    const k = e.target.closest('[data-sichtschutz]');
    if (!k) return;
    e.preventDefault();
    const aktion = k.dataset.sichtschutz;
    if (aktion === 'umschalten') { cookie('rsb_sichtschutz', html.classList.contains('sichtschutz') ? '' : '1'); cookie('rsb_sichtschutz_kunde', ''); }
    else if (aktion === 'kunde') cookie('rsb_sichtschutz_kunde', k.dataset.kunde);
    else if (aktion === 'kunde-aus') cookie('rsb_sichtschutz_kunde', '');
    location.reload();
  });
  if (!html.classList.contains('sichtschutz')) return;

  const daten = JSON.parse(document.getElementById('sv-begriffe')?.textContent || '{"begriffe":[]}');
  const ausgenommen = String(daten.kunde || '');
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const teile = [
    '-?(?:\\d{1,3}(?:\\.\\d{3})+|\\d+),\\d{2}(?:\\s?€)?',            // Beträge 1.234,56 (€)
    '€\\s?-?\\d[\\d.]*(?:,\\d{2})?',
    '[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+',                                // E-Mail
    '(?:\\+\\d{2}|\\b0)\\d[\\d /()-]{5,}\\d',                          // Telefon
    '\\bDE\\d{2}(?:\\s?\\d{4}){4}\\s?\\d{2}\\b',                       // IBAN
  ];
  if (daten.begriffe.length) teile.push('(?<![\\p{L}\\d])(?:' + daten.begriffe.map(esc).join('|') + ')(?![\\p{L}\\d])');
  const muster = new RegExp(teile.join('|'), 'giu');

  function textknoten(wurzel) {
    const walker = document.createTreeWalker(wurzel, NodeFilter.SHOW_TEXT, {
      acceptNode: n => (!n.nodeValue.trim() || !n.parentElement || n.parentElement.closest('.sv, .sv-frei, script, style, noscript, textarea, option')
        || (ausgenommen && n.parentElement.closest('[data-sv-kunde="' + ausgenommen + '"]'))) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const liste = [];
    while (walker.nextNode()) liste.push(walker.currentNode);
    for (const n of liste) {
      const text = n.nodeValue;
      muster.lastIndex = 0;
      if (!muster.test(text)) continue;
      muster.lastIndex = 0;
      const frag = document.createDocumentFragment();
      let pos = 0, m;
      while ((m = muster.exec(text))) {
        if (!m[0]) { muster.lastIndex++; continue; }
        frag.append(text.slice(pos, m.index));
        const s = document.createElement('span'); s.className = 'sv'; s.textContent = m[0]; frag.append(s);
        pos = m.index + m[0].length;
      }
      frag.append(text.slice(pos));
      n.replaceWith(frag);
    }
  }
  function felder(wurzel) {
    wurzel.querySelectorAll?.('input, textarea, select').forEach(f => {
      if (f.closest('.sv-frei') || (ausgenommen && f.closest('[data-sv-kunde="' + ausgenommen + '"]'))) return;
      const typ = (f.type || '').toLowerCase();
      if (['hidden', 'date', 'time', 'datetime-local', 'checkbox', 'radio', 'submit', 'button', 'file', 'search', 'color', 'range'].includes(typ)) return;
      if (f.tagName === 'SELECT') {
        muster.lastIndex = 0;
        if (![...f.options].some(o => { muster.lastIndex = 0; return muster.test(o.textContent); })) return;
      }
      f.classList.add('sv-feld'); f.tabIndex = -1;
    });
    wurzel.querySelectorAll?.('[title]').forEach(el => { muster.lastIndex = 0; if (muster.test(el.title)) el.removeAttribute('title'); });
  }
  function los(wurzel) { textknoten(wurzel); felder(wurzel); }
  muster.lastIndex = 0;
  if (muster.test(document.title)) document.title = 'Sichtschutz aktiv';
  los(document.body);
  html.classList.add('sv-fertig');
  new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => {
    if (n.nodeType === 1 && !n.closest('.sv')) los(n);
    else if (n.nodeType === 3 && n.parentElement) los(n.parentElement);
  }))).observe(document.body, { childList: true, subtree: true });
})();
