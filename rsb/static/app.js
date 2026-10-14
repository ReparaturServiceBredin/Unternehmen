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
