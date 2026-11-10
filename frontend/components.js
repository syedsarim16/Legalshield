/* Component helpers. Each returns an HTML string. Matches DESIGN_SYSTEM.md section 6. */
const ST = { role: 'citizen', lang: 'en', theme: 'light', discreet: false, sosNoticeSeen: false, verified: { lawyer: false, ngo: false },
  regRole: 'citizen', contacts: [{ id: 1, name: 'Contact One (sister)', phone: '0300 1234567' }, { id: 2, name: 'Contact Two (friend)', phone: '0312 7654321' }, { id: 3, name: 'Contact Three (uncle)', phone: '0333 5551122' }],
  chat: [], evidence: [], incidents: [], shareLinks: {}, sosCount: 3 };

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const t = s => { const d = (typeof I18N !== 'undefined') && I18N[ST.lang]; return (d && d[s]) || s; };

const IC = {
  check: 'M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
  checkc: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
  close: 'M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
  chev: 'M10 6 8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z',
  back: 'M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z',
  add: 'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
  search: 'M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z',
  home: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
  chat: 'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z',
  alert: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z',
  warning: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z',
  info: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z',
  folder: 'M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z',
  menu: 'M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z',
  people: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
  doc: 'M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z',
  book: 'M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z',
  person: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
  bars: 'M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z',
  phone: 'M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z',
  pin: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
  lock: 'M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zM9 8V6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9z',
  trash: 'M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z',
  send: 'M2.01 21 23 12 2.01 3 2 10l15 2-15 2z',
  shield: 'M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z',
  clock: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z',
  block: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9C4.63 15.55 4 13.85 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1C19.37 8.45 20 10.15 20 12c0 4.42-3.58 8-8 8z',
  remove: 'M19 13H5v-2h14v2z',
  cloud: 'M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z',
  copy: 'M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z',
  share: 'M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z',
  play: 'M8 5v14l11-7z',
  mic: 'M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z',
  cam: 'M9 2 7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z',
  video: 'M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z',
  upload: 'M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z',
  gavel: 'M1 21h12v2H1zM5.245 8.07l2.83-2.827 14.14 14.142-2.828 2.828zM12.317 1l5.657 5.656-2.83 2.83-5.654-5.66zM3.825 9.485l5.657 5.657-2.828 2.828-5.657-5.657z',
  bell: 'M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z',
  edit: 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z',
  globe: 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm6.93 6h-2.95a15.65 15.65 0 0 0-1.38-3.56A8.03 8.03 0 0 1 18.92 8zM12 4.04c.83 1.2 1.48 2.53 1.91 3.96h-3.82c.43-1.43 1.08-2.76 1.91-3.96zM4.26 14C4.1 13.36 4 12.69 4 12s.1-1.36.26-2h3.38c-.08.66-.14 1.32-.14 2s.06 1.34.14 2H4.26zm.82 2h2.95c.32 1.25.78 2.45 1.38 3.56A7.987 7.987 0 0 1 5.08 16zm2.95-8H5.08a7.987 7.987 0 0 1 4.33-3.56A15.65 15.65 0 0 0 8.03 8zM12 19.96c-.83-1.2-1.48-2.53-1.91-3.96h3.82c-.43 1.43-1.08 2.76-1.91 3.96zM14.34 14H9.66c-.09-.66-.16-1.32-.16-2s.07-1.35.16-2h4.68c.09.65.16 1.32.16 2s-.07 1.34-.16 2zm.25 5.56c.6-1.11 1.06-2.31 1.38-3.56h2.95a8.03 8.03 0 0 1-4.33 3.56zM16.36 14c.08-.66.14-1.32.14-2s-.06-1.34-.14-2h3.38c.16.64.26 1.31.26 2s-.1 1.36-.26 2h-3.38z',
  logout: 'M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z',
  visible: 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z',
  hidden: 'M2 4.27 3.28 3 21 20.72 19.73 22l-3.15-3.15A11.8 11.8 0 0 1 12 20C7 20 2.73 16.89 1 12c.69-1.75 1.78-3.26 3.14-4.43L2 4.27zM12 4c5 0 9.27 3.11 11 8a12.3 12.3 0 0 1-3.02 4.36l-3.1-3.1A5 5 0 0 0 9.75 6.1L7.8 4.15A12.6 12.6 0 0 1 12 4zm0 3a5 5 0 0 1 5 5c0 .56-.09 1.09-.26 1.59l-6.33-6.33A4.9 4.9 0 0 1 12 7z',
  map: 'M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z',
  stop: 'M6 6h12v12H6z',
  fiber: 'M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2z',
  scale: 'M12 3 2 8v2h20V8L12 3zM4 12v6h2v-6H4zm4 0v6h2v-6H8zm4 0v6h2v-6h-2zm4 0v6h2v-6h-2zM2 20v2h20v-2H2z',
  refresh: 'M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z',
};
const ic = (n, s = 24, cls = '') => `<svg class="ico ${cls}" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true"><path d="${IC[n] || IC.info}"/></svg>`;
const M = 'mirror';

const btn = (label, o = {}) => {
  const type = o.type || 'primary', size = o.size || 'L';
  const full = o.full === false ? '' : ' full';
  const attrs = (o.go ? ` data-go="${o.go}"` : '') + (o.act ? ` data-act="${o.act}"` : '') + (o.data ? ` data-v="${esc(o.data)}"` : '') + (o.id ? ` id="${o.id}"` : '') + (o.dis ? ' disabled' : '');
  return `<button class="btn btn-${type} btn-${size}${full}"${attrs}>${o.icon ? ic(o.icon, 20) : ''}${t(label)}</button>`;
};
const BADGES = {
  bailable: ['success', 'checkc', 'Bailable'], nonbailable: ['danger', 'block', 'Non-bailable'], cognizable: ['warning', 'warning', 'Cognizable'],
  noncognizable: ['neutral', 'remove', 'Non-cognizable'], compoundable: ['info', 'scale', 'Compoundable'], compcourt: ['info', 'scale', 'Compoundable with court permission'], noncompoundable: ['neutral', 'remove', 'Non-compoundable'],
  procedure: ['neutral', 'doc', 'Procedural section'], pending: ['warning', 'clock', 'Pending'], verified: ['success', 'checkc', 'Verified'], rejected: ['danger', 'close', 'Rejected'],
  uploading: ['info', 'cloud', 'Uploading'], complete: ['success', 'lock', 'Complete'], failed: ['danger', 'alert', 'Integrity failed'], role: ['primary', 'person', 'Citizen'],
  approved: ['success', 'checkc', 'Approved'], ack: ['success', 'checkc', 'Responding'], newalert: ['danger', 'alert', 'New'], ended: ['neutral', 'remove', 'Ended'], cancelled: ['neutral', 'close', 'False alarm']
};
const badge = (kind, label) => { const b = BADGES[kind]; return `<span class="badge b-${b[0]}">${ic(b[1], 16)}${t(label || b[2])}</span>`; };
const chip = (label, o = {}) => `<button class="chip${o.sel ? ' sel' : ''}${o.type ? ' ' + o.type : ''}"${o.act ? ` data-act="${o.act}"` : ''}${o.go ? ` data-go="${o.go}"` : ''}${o.data ? ` data-v="${esc(o.data)}"` : ''}>${o.sel && !o.type ? ic('check', 16) : ''}${o.icon ? ic(o.icon, 16) : ''}${t(label)}</button>`;
const banner = (type, text, o = {}) => {
  const map = { info: ['info', 'info'], warning: ['warning', 'warning'], danger: ['danger', 'alert'], success: ['success', 'checkc'] };
  const [k, i] = map[type];
  return `<div class="banner b-${k}" role="status">${ic(i, 24)}<span>${t(text)}</span>${o.action ? `<a class="act"${o.go ? ` data-go="${o.go}"` : ''}${o.act ? ` data-act="${o.act}"` : ''}>${t(o.action)}</a>` : ''}</div>`;
};
const disc = () => `<div class="disc">${ic('info', 16)}<span>${t('Legal information, not legal advice.')}</span></div>`;
const avatar = (i, lg) => `<span class="avatar${lg ? ' lg' : ''}">${esc(i)}</span>`;
const li = o => `<${o.go || o.act ? 'button' : 'div'} class="li${o.go || o.act ? ' tap' : ''}"${o.go ? ` data-go="${o.go}"` : ''}${o.act ? ` data-act="${o.act}"` : ''}${o.data ? ` data-v="${esc(o.data)}"` : ''}>
  ${o.lead ? `<span class="lead${o.red ? ' red' : ''}">${o.lead.startsWith('<') ? o.lead : ic(o.lead, 24)}</span>` : ''}
  <span class="grow stack g4"><span class="tt">${o.raw ? o.title : t(o.title)}</span>${o.sub ? `<span class="st">${o.raw ? o.sub : t(o.sub)}</span>` : ''}${o.extra || ''}</span>
  ${o.trail !== undefined ? o.trail : (o.go || o.act ? `<span class="chev">${ic('chev', 18, M)}</span>` : '')}</${o.go || o.act ? 'button' : 'div'}>`;
const card = (inner, o = {}) => o.go || o.act
  ? `<button class="card tap ${o.cls || ''}"${o.go ? ` data-go="${o.go}"` : ''}${o.act ? ` data-act="${o.act}"` : ''}${o.data ? ` data-v="${esc(o.data)}"` : ''}>${inner}</button>`
  : `<div class="card ${o.cls || ''}">${inner}</div>`;
const field = o => `<div class="field${o.error ? ' err' : ''}${o.dis ? ' dis' : ''}">
  ${o.label ? `<label for="${o.id || ''}">${t(o.label)}</label>` : ''}
  <div class="in${o.ta ? ' ta' : ''}${o.ltr ? ' ltr-in' : ''}">${o.pre ? `<span class="pre">${o.pre}</span>` : ''}
   ${o.ta ? `<textarea id="${o.id || ''}" rows="3" placeholder="${esc(t(o.ph || ''))}">${esc(o.value || '')}</textarea>`
    : o.select ? `<select id="${o.id || ''}">${o.select.map(x => `<option${x === o.value ? ' selected' : ''}>${esc(t(x))}</option>`).join('')}</select>`
      : `<input id="${o.id || ''}" type="${o.type || 'text'}" value="${esc(o.value || '')}" placeholder="${esc(t(o.ph || ''))}"${o.dis ? ' disabled' : ''}${o.inputmode ? ` inputmode="${o.inputmode}"` : ''}${o.maxlength ? ` maxlength="${o.maxlength}"` : ''}>`}
   ${o.type === 'password' ? `<button type="button" class="field-password-toggle" data-act="togglePassword" data-v="${esc(o.id || '')}" aria-label="${t('Show password')}" aria-pressed="false">${ic('visible', 24, 'c-3')}</button>` : o.icon ? ic(o.icon, 24, 'c-3') : ''}</div>
  ${o.error ? `<div class="help">${ic('alert', 16)}${t(o.error)}</div>` : o.help ? `<div class="help">${t(o.help)}</div>` : ''}</div>`;
const appbar = o => `<div class="appbar${o.large ? ' large' : ''}">${o.back ? `<button class="ib" data-act="back" aria-label="${t('Back')}">${ic('back', 24, M)}</button>` : ''}<div class="ttl">${o.raw ? o.title : t(o.title)}</div>${o.modal ? `<button class="ib" data-act="back" aria-label="${t('Close')}">${ic('close', 24)}</button>` : ''}${o.right || ''}</div>`;
const NAVS = {
  citizen: [['home', 'Home', 'S-17', 'home'], ['assistant', 'Assistant', 'S-18', 'chat'], ['sos', 'SOS', 'S-21', 'alert'], ['vault', 'Vault', 'S-36', 'folder'], ['more', 'More', 'S-12', 'menu']],
  lawyer: [['alerts', 'Alerts', 'S-27', 'alert'], ['directory', 'Directory', 'S-32', 'people'], ['sections', 'Sections', 'S-19', 'doc'], ['guides', 'Guides', 'S-41', 'book'], ['profile', 'Profile', 'S-12', 'person']],
  ngo: [['alerts', 'Alerts', 'S-27', 'alert'], ['analytics', 'Analytics', 'S-53', 'bars'], ['profile', 'Profile', 'S-12', 'person']]
};
const nav = active => `<nav class="bnav" aria-label="Main">${(NAVS[ST.role] || NAVS.citizen).map(([k, l, go, i]) => `<a data-go="${go}" class="${k === 'sos' ? 'sos' : ''}${k === active ? ' on' : ''}" role="link" tabindex="0"><span class="pill">${ic(i, k === 'sos' ? 28 : 24)}</span>${t(l)}</a>`).join('')}</nav><div class="homebar"><i></i></div>`;
const seg = (items, sel, act) => `<div class="seg" role="tablist">${items.map(i => `<button class="${i === sel ? 'sel' : ''}" data-act="${act}" data-v="${esc(i)}">${t(i)}</button>`).join('')}</div>`;
const radio = (title, help, sel, act, v) => `<button class="radio${sel ? ' sel' : ''}" data-act="${act}" data-v="${esc(v)}" role="radio" aria-checked="${!!sel}"><span class="grow stack g4"><span class="t-title3">${title}</span>${help ? `<span class="t-cap c-2">${t(help)}</span>` : ''}</span><span class="dot"></span></button>`;
const sw = (on, act, v) => `<button class="switch${on ? ' on' : ''}" data-act="${act}"${v ? ` data-v="${v}"` : ''} role="switch" aria-checked="${!!on}"></button>`;
const mapcard = (cap, ended) => `<div class="mapcard${ended ? ' ended' : ''}"><div class="grid"></div><div class="road"></div><div class="pin"></div><div class="cap">${t(cap)}</div></div>`;
const hashblock = h => `<div class="row g12" style="background:var(--surface-2);border-radius:12px;padding:12px 12px 12px 16px"><span class="mono grow">${h}</span><button class="ib" data-act="copy" style="color:var(--primary)" aria-label="Copy">${ic('copy', 24)}</button></div>`;
const empty = (icon, title, body, action) => `<div class="stack center g12" style="padding:32px 16px"><div class="iconbig">${ic(icon, 48)}</div><div class="t-title3">${t(title)}</div><div class="t-body c-2">${t(body)}</div>${action || ''}</div>`;
const stepper = (n, cur) => `<div class="stepper">${Array.from({ length: n }, (_, i) => `<span class="s${i < cur ? ' on' : ''}"></span>`).join('')}</div>`;
const check = (on, label, act) => `<button class="check${on ? ' on' : ''}" data-act="${act}"><span class="bx">${ic('check', 18)}</span><span class="t-body">${t(label)}</span></button>`;
const filepick = (done, empt, name, act) => `<button class="filepick${done ? ' done' : ''}" data-act="${act}">${ic(done ? 'doc' : 'upload', 24)}<span class="grow t-body">${done ? name : t(empt)}</span>${done ? ic('close', 24) : ''}</button>`;
const sheet = (inner) => `<div class="scrim"><div class="sheet"><span class="grab"></span>${inner}</div></div>`;
const dialog = inner => `<div class="scrim mid"><div class="dialog">${inner}</div></div>`;
const tabbar = (items, sel, act) => `<div class="tabs">${items.map(i => `<button class="${i === sel ? 'sel' : ''}" data-act="${act}" data-v="${esc(i)}">${t(i)}</button>`).join('')}</div>`;
const status = () => `<div class="ph-status"><span>9:41</span><span class="sig"><svg width="18" height="12" viewBox="0 0 18 12"><rect x="0" y="8" width="3" height="4" rx="1" fill="currentColor"/><rect x="5" y="5" width="3" height="7" rx="1" fill="currentColor"/><rect x="10" y="2" width="3" height="10" rx="1" fill="currentColor"/><rect x="15" y="0" width="3" height="12" rx="1" fill="currentColor"/></svg><svg width="16" height="12" viewBox="0 0 24 18"><path d="M12 3C7.6 3 3.6 4.8.6 7.7L2.6 10C5.1 7.6 8.4 6.2 12 6.2s6.9 1.4 9.4 3.8l2-2.3C20.4 4.8 16.4 3 12 3zm0 6.4c-2.6 0-5 1-6.8 2.7l2 2.3c1.3-1.2 3-1.9 4.8-1.9s3.5.7 4.8 1.9l2-2.3c-1.8-1.7-4.2-2.7-6.8-2.7zm0 6.3-2.6 2.6L12 18l2.6-.7z" fill="currentColor"/></svg><svg width="26" height="12" viewBox="0 0 26 12"><rect x=".5" y=".5" width="21" height="11" rx="3.5" stroke="currentColor" fill="none" opacity=".5"/><rect x="2" y="2" width="16" height="8" rx="2" fill="currentColor"/><rect x="23" y="4" width="2" height="4" rx="1" fill="currentColor" opacity=".5"/></svg></span></div>`;
const shieldArt = (w = 132) => `<svg class="art" width="${w}" height="${Math.round(w * 1.15)}" viewBox="0 0 140 161" fill="none" aria-hidden="true"><defs><linearGradient id="sgA" x1="20" y1="10" x2="120" y2="150" gradientUnits="userSpaceOnUse"><stop stop-color="#FFFFFF"/><stop offset="1" stop-color="#BFE6EE"/></linearGradient></defs><path d="M70 6 128 28v50c0 36-24 64-58 77-34-13-58-41-58-77V28z" fill="url(#sgA)"/><path d="M70 6 128 28v50c0 36-24 64-58 77z" fill="#0F4C5C" opacity=".08"/><path d="m44 82 18 18 36-42" stroke="#0F4C5C" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
/* screen layout: bar (fixed top), body (scroll), foot (fixed bottom: nav or composer) */
const page = (o) => `${o.bar || ''}<div class="body${o.flush ? ' flush' : ''}">${o.body}</div>${o.foot || ''}${o.overlay || ''}`;
const table = (heads, rows, o = {}) => `<table class="tbl"><thead><tr>${heads.map(h => `<th>${t(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr class="${r.go || r.act ? 'click' : ''}"${r.go ? ` data-go="${r.go}"` : ''}${r.act ? ` data-act="${r.act}" data-v="${esc(r.v || '')}"` : ''}>${r.cells.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const rail = active => `<aside class="rail"><div class="brand">${ic('shield', 28)} LegalShield</div>${[['verify', 'Verifications', 'S-44', 'checkc'], ['content', 'Content', 'S-46', 'doc'], ['statutes', 'Statutes', 'S-48', 'gavel'], ['incidents', 'Incidents', 'S-51', 'alert'], ['metrics', 'Metrics', 'S-43', 'bars'], ['analytics', 'Analytics', 'S-53', 'map']].map(([k, l, go, i]) => `<a data-go="${go}" class="${k === active ? 'on' : ''}">${ic(i, 24)}${t(l)}</a>`).join('')}<div class="grow"></div><a data-go="S-04">${ic('logout', 24)}${t('Log out')}</a></aside>`;
const dpage = (active, body) => `${rail(active)}<main class="dmain">${body}</main>`;
