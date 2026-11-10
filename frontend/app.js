/* App core: registry, router, shell, toolbar, sidebar, delegated events. */
const SCREENS = {}; const ACTS = {}; let TIMERS = [];
const reg = (id, m) => { SCREENS[id] = m; };
const VS = {}; // per-screen view state
const MODULES = ['M1 Account', 'Home', 'M2 Assistant', 'M3 Sections', 'M4 SOS', 'M5 Documents', 'M6 Directory', 'M7 Vault', 'M8 Guides', 'M9 Admin', 'M10 Incidents', 'Web pages'];
const ROLE_HOME = { citizen: 'S-17', lawyer: 'S-27', ngo: 'S-27', admin: 'S-43' };
const HIST = [];

function parseHash() { const h = location.hash.replace(/^#\/?/, ''); const [id, qs] = h.split('?'); return { id: id || 'S-01', q: Object.fromEntries(new URLSearchParams(qs || '')) }; }
const go = tgt => { location.hash = '#/' + tgt; };
const cur = () => parseHash();
const setTimer = (fn, ms) => { const id = setTimeout(fn, ms); TIMERS.push(id); return id; };
const setTick = (fn, ms) => { const id = setInterval(fn, ms); TIMERS.push(id); return id; };
const frameEl = () => document.querySelector('.frame');
function toast(msg) { const f = frameEl(); if (!f) return; const old = f.querySelector('.toast'); if (old) old.remove(); const d = document.createElement('div'); d.className = 'toast'; d.setAttribute('role', 'status'); d.textContent = t(msg); (f.querySelector('.ph-in') || f).appendChild(d); setTimeout(() => d.remove(), 2400); }
const vs = id => VS[id || cur().id];
function setVS(v, id) { VS[id || cur().id] = v; render(true); }

function render(keepScroll) {
  TIMERS.forEach(x => { clearTimeout(x); clearInterval(x); }); TIMERS = [];
  const { id, q } = parseHash(); const m = SCREENS[id];
  const stage = document.getElementById('stage');
  if (!m) { stage.innerHTML = `<div class="hint">Unknown screen ${esc(id)}</div>`; return; }
  const s = VS[id] || (m.states ? m.states[0] : 'default'); const fr = typeof m.frame === 'function' ? m.frame() : m.frame;
  const old = stage.querySelector('.body'); const scroll = keepScroll && old ? old.scrollTop : 0;
  const isUr = ST.lang === 'ur';
  let html = m.render({ q, s, id });
  const attrs = `class="frame ${fr === 'wide' ? 'wide' : fr === 'web' ? 'browser' : 'phone'}${m.lightStatus ? ' lightbar' : ''}" data-theme="${ST.theme}" data-lang="${isUr ? 'ur' : 'latin'}" lang="${isUr ? 'ur' : 'en'}" dir="${isUr ? 'rtl' : 'ltr'}"`;
  if (fr === 'wide') stage.innerHTML = `<div ${attrs}>${html}</div>`;
  else if (fr === 'web') stage.innerHTML = `<div ${attrs}><div class="url">${ic('lock', 14)} ${esc(m.url || 'legalshield.pk')}</div>${html}</div>`;
  else stage.innerHTML = `<div ${attrs}><div class="ph-wrap">${status()}<div class="ph-in${m.full ? ' full' : ''}">${html}</div></div></div>`;
  const nb = stage.querySelector('.body'); if (nb && scroll) nb.scrollTop = scroll;
  if (m.mount) m.mount({ q, s, id, el: stage });
  updateChrome(id, m, s);
}

function updateChrome(id, m, s) {
  document.querySelectorAll('.side a').forEach(a => a.classList.toggle('on', a.dataset.id === id));
  const meta = document.getElementById('meta');
  meta.innerHTML = `<b>${id}</b> ${esc(m.name)} <span style="color:#8493A0">|</span> ${esc(m.module)}${m.api ? ` <span style="color:#8493A0">|</span> API ${esc(m.api)}` : ''}`;
  const pills = document.getElementById('states');
  pills.innerHTML = (m.states || []).length > 1 ? `<span style="color:#5E6C77">States:</span>` + m.states.map(x => `<button class="pill${x === s ? ' on' : ''}" data-state="${x}">${x}</button>`).join('') : '';
  const sel = document.getElementById('role'); if (sel) sel.value = ST.role;
  document.getElementById('lang').value = ST.lang; document.getElementById('theme').value = ST.theme;
}

function buildSide() {
  const box = document.getElementById('sidelist'); const q = (document.getElementById('find').value || '').toLowerCase();
  const groups = {}; Object.entries(SCREENS).forEach(([id, m]) => { if (q && !(id + ' ' + m.name + ' ' + m.module).toLowerCase().includes(q)) return; (groups[m.module] = groups[m.module] || []).push([id, m]); });
  box.innerHTML = MODULES.filter(g => groups[g]).map(g => `<details ${q || g === 'M1 Account' || g === 'M4 SOS' ? 'open' : ''}><summary>${g} (${groups[g].length})</summary>${groups[g].map(([id, m]) => `<a href="#/${id}" data-id="${id}"><b>${id}</b>${esc(m.name)}<i>${m.roles || ''}</i></a>`).join('')}</details>`).join('');
}

function saveState() {
  const firebase = window.LegalShieldFirebase;
  if (!firebase) return;
  firebase.savePreferences({ lang: ST.lang, theme: ST.theme, discreet: ST.discreet })
    .catch(error => { console.error('Could not save account preferences to Firestore.', error); toast('Settings could not sync. Check your connection and try again.'); });
}
function loadState() {
  const q = new URLSearchParams(location.search);
  ['theme', 'lang', 'role'].forEach(k => { if (q.get(k)) ST[k] = q.get(k); });
}

document.addEventListener('click', e => {
  const st = e.target.closest('[data-state]'); if (st) { setVS(st.dataset.state); return; }
  const target = e.target.closest('[data-go],[data-act]');
  if (!target || !e.target.closest('.frame')) return;
  if (target.hasAttribute('disabled')) return;
  if (target.dataset.act) { const fn = ACTS[target.dataset.act]; if (fn) { fn(target, e); } }
  else if (target.dataset.go) { HIST.push(location.hash); go(target.dataset.go); }
});
document.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('a[data-go]')) { e.preventDefault(); e.target.click(); } });
ACTS.back = () => { const p = HIST.pop(); if (p) { location.hash = p; } else go(ROLE_HOME[ST.role]); };
ACTS.copy = () => toast('Copied to clipboard');
ACTS.toast = el => toast(el.dataset.v || 'Done');
ACTS.togglePassword = el => {
  const input = document.getElementById(el.dataset.v);
  if (!(input instanceof HTMLInputElement)) {
    console.error('Password visibility control has no matching input.');
    return;
  }
  const visible = input.type === 'password';
  input.type = visible ? 'text' : 'password';
  el.innerHTML = ic(visible ? 'hidden' : 'visible', 24, 'c-3');
  el.setAttribute('aria-label', t(visible ? 'Hide password' : 'Show password'));
  el.setAttribute('aria-pressed', String(visible));
};

window.addEventListener('hashchange', () => render(false));
window.addEventListener('DOMContentLoaded', () => {
  loadState();
  document.getElementById('role').addEventListener('change', e => { ST.role = e.target.value; saveState(); go(ROLE_HOME[ST.role]); });
  document.getElementById('lang').addEventListener('change', e => { ST.lang = e.target.value; saveState(); buildSide(); render(true); });
  document.getElementById('theme').addEventListener('change', e => { ST.theme = e.target.value; saveState(); render(true); });
  document.getElementById('find').addEventListener('input', buildSide);
  document.getElementById('reset').addEventListener('click', () => {
    ST.role = 'citizen'; ST.lang = 'en'; ST.theme = 'light'; ST.discreet = false;
    saveState(); location.hash = '#/S-01'; render(false);
  });
  buildSide(); if (!location.hash) location.hash = '#/S-01'; render(false);
});
