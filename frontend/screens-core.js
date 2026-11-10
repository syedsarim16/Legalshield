/* M2 Assistant, M3 Sections, M4 SOS: S-18 .. S-28 */
const secById = id => SECTIONS.find(x => x.id === id);
const secCard = x => card(`<div class="t-cap c-pri" style="font-weight:700">${x.law} ${x.no}</div><div class="t-title3">${t(x.title)}</div><div class="row g8 wrap">${x.kind === 'procedure' ? badge('procedure') : (badge(x.bailable ? 'bailable' : 'nonbailable') + badge(x.cognizable ? 'cognizable' : 'noncognizable'))}</div>`, { go: 'S-20?id=' + x.id });

/* ---------- S-18 chat ---------- */
const CHAT_REPLIES = [
  { re: /police|stopp|arrest|detain|pakr|giraft/i, text: 'You can politely ask why you are being stopped or arrested. Under CrPC section 54 the police may arrest without a warrant only in the listed cases, and under section 61 you must be brought before a Magistrate within twenty-four hours.', cites: ['crpc-54', 'crpc-61'], actions: [['Lawful arrest steps', 'book', 'S-42?id=lawful-arrest-steps'], ['Send an SOS', 'alert', 'S-21']] },
  { re: /bail|zamanat|release/i, text: 'For a bailable offence bail is a matter of right. For a non-bailable offence a court decides after hearing both sides, as explained in CrPC section 497. A lawyer files the application.', cites: ['crpc-497'], actions: [['Bail roadmap', 'book', 'S-42?id=bail-process-overview'], ['Find a lawyer', 'people', 'S-32']] },
  { re: /fir|complain|harass|report/i, text: 'If a cognizable offence is reported, the police must record the information under CrPC section 154. If they refuse, you can send a written application using the FIR template.', cites: ['crpc-154'], actions: [['FIR application', 'doc', 'S-30?id=fir-application'], ['Report an incident', 'alert', 'S-49']] },
];
const REFUSAL = 'I cannot answer this from the available statutes.';
function chatMsgs(s) {
  const u = { from: 'user', text: 'I was stopped by police. What should I do?' };
  const a = { from: 'ai', ...CHAT_REPLIES[0] };
  if (s === 'answer') return [u, a];
  if (s === 'refusal') return [{ from: 'user', text: 'What is the punishment under the narcotics law?' }, { from: 'ai', kind: 'ref', text: REFUSAL, note: 'This topic is outside the current coverage (PPC and CrPC only).' }];
  if (s === 'error') return [u, { from: 'ai', kind: 'error', text: 'The assistant is unavailable right now. Please try again.' }];
  if (s === 'typing') return [u, { from: 'ai', kind: 'typing' }];
  return ST.chat;
}
const bubble = m => m.from === 'user' ? `<div class="msgrow user">${bubbleIn(m)}</div>` : `<div class="msgrow"><span class="aiav">${ic('shield', 18)}</span>${bubbleIn(m)}</div>`;
const bubbleIn = m => {
  if (m.from === 'user') return `<div class="bubble user">${esc(m.text)}</div>`;
  if (m.kind === 'typing') return `<div class="bubble ai typing"><span></span><span></span><span></span></div>`;
  if (m.kind === 'error') return `<div class="bubble error"><div class="row g8 t-label">${ic('warning', 16)}${t('Service unavailable')}</div><div>${t(m.text)}</div><button class="t-label" style="font-weight:700;margin-top:8px" data-act="retry">${t('Retry')}</button></div>`;
  if (m.kind === 'ref') return `<div class="bubble ai ref"><div class="row g8 t-label">${ic('info', 16)}${t('Cannot answer')}</div><div>${t(m.text)}</div>${m.note ? `<div class="t-cap" style="margin-top:6px">${t(m.note)}</div>` : ''}</div>`;
  return `<div class="bubble ai stack g8"><div>${t(m.text)}</div><div class="row g8 wrap">${(m.cites || []).map(id => { const x = secById(id); return chip(x.law + ' ' + x.no, { type: 'cite', icon: 'book', go: 'S-20?id=' + id }); }).join('')}</div>
   <div class="row g8 wrap">${(m.actions || []).map(([l, i, g]) => chip(l, { type: 'sug', icon: i, go: g })).join('')}</div>${disc()}</div>`;
};
ACTS.send = () => {
  const inp = $('#msg'); const v = (inp.value || '').trim(); if (!v) return;
  ST.chat.push({ from: 'user', text: v }); ST.typing = true; render(true);
  setTimeout(() => { const r = CHAT_REPLIES.find(x => x.re.test(v)); ST.chat.push(r ? { from: 'ai', ...r } : { from: 'ai', kind: 'ref', text: REFUSAL, note: 'This topic is outside the current coverage (PPC and CrPC only).' }); ST.typing = false; if (cur().id === 'S-18') { render(false); const b = $('.body'); if (b) b.scrollTop = b.scrollHeight; } }, 1100);
};
ACTS.starter = el => { ST.starter = el.dataset.v; setTimeout(() => { const i = $('#msg'); if (i) { i.value = ST.starter; ACTS.send(); } }, 0); };
ACTS.retry = () => setVS('answer');
reg('S-18', { name: 'Assistant chat', module: 'M2 Assistant', api: 'E-13', roles: 'C', frame: 'phone', states: ['live', 'answer', 'refusal', 'error', 'typing'],
  render: ({ s }) => { const msgs = chatMsgs(s); const live = s === 'live';
    const empty = live && !msgs.length && !ST.typing;
    return page({ bar: appbar({ title: 'Legal assistant', right: `<span class="badge b-info" style="margin-inline-end:8px">${t('Auto language')}</span>` }),
      body: empty ? `<div class="stack center g12" style="padding:24px 8px"><div class="iconbig">${ic('chat', 48)}</div><div class="t-title3">${t('Ask about your rights')}</div><div class="t-body c-2">${t('Ask in Urdu, Roman Urdu or English. I answer only from the PPC and CrPC text and show the sections.')}</div></div>
       <div class="stack g8">${['I was stopped by police', 'What is bail?', 'Is my arrest legal?', 'Write a complaint'].map(x => chip(x, { type: 'sug', act: 'starter', data: x })).join('')}</div>${disc()}`
        : `<div class="chatlist">${msgs.map(bubble).join('')}${live && ST.typing ? bubble({ from: 'ai', kind: 'typing' }) : ''}</div>`,
      foot: `<div class="composer"><input id="msg" placeholder="${esc(t('Type your question'))}" aria-label="Message" onkeydown="if(event.key==='Enter')ACTS.send()"><button class="send" data-act="send" aria-label="Send">${ic('send', 24, M)}</button></div>${nav('assistant')}` }); } });

/* ---------- S-19 / S-20 sections ---------- */
const resultsHTML = (q, law) => {
  const ql = (q || '').toLowerCase().trim();
  const r = SECTIONS.filter(x => (law === 'All' || x.law === law) && (!ql || (x.no + ' ' + x.title + ' ' + x.law + ' ' + x.text).toLowerCase().includes(ql)));
  if (!r.length) return `<div class="card center" style="align-items:center;text-align:center"><div class="iconbig" style="width:64px;height:64px">${ic('info', 32)}</div><div class="t-title3">${t('Not covered by LegalShield yet')}</div><div class="t-body c-2">${t('This first release covers the PPC and CrPC only. Special laws such as narcotics, arms, anti-terrorism and PECA are not included.')}</div>${btn('Ask a lawyer', { type: 'secondary', go: 'S-32', icon: 'people' })}</div>`;
  return `<div class="stack g8">${r.map(secCard).join('')}</div>`;
};
ACTS.lawf = el => { ST.law = el.dataset.v; render(true); };
reg('S-19', { name: 'Section search', module: 'M3 Sections', api: 'E-14', roles: 'C, L', frame: 'phone', states: ['default', 'no results', 'loading'],
  render: ({ s }) => { const law = ST.law || 'All'; const q = s === 'no results' ? 'narcotics' : (ST.q || '');
    return page({ bar: appbar({ title: 'Check a section', back: true }), body: `${field({ id: 'q', ph: 'Section number or keyword, e.g. 302 or bail', value: q, icon: 'search' })}${seg(['All', 'PPC', 'CrPC'], law, 'lawf')}
     <div id="res" class="stack g8">${s === 'loading' ? Array.from({ length: 3 }, () => `<div class="card" style="height:96px;opacity:.5"></div>`).join('') : resultsHTML(q, law)}</div>${disc()}`, foot: nav(ST.role === 'lawyer' ? 'sections' : 'home') }); },
  mount: () => { const i = $('#q'); if (i) i.addEventListener('input', () => { ST.q = i.value; $('#res').innerHTML = resultsHTML(i.value, ST.law || 'All'); }); } });

reg('S-20', { name: 'Section detail', module: 'M3 Sections', api: 'E-15', roles: 'C, L', frame: 'phone', states: ['auto', 'not covered'],
  render: ({ q, s }) => { const x = s === 'not covered' ? null : secById(q.id || 'ppc-302');
    if (!x) return page({ bar: appbar({ title: 'Section', back: true }), body: `${empty('info', 'Not covered by LegalShield yet', 'This section is not in the dataset. The first release covers the PPC and CrPC only.', btn('Ask a lawyer', { type: 'secondary', full: false, go: 'S-32', icon: 'people' }))}${disc()}`, foot: nav(ST.role === 'lawyer' ? 'sections' : 'home') });
    const comp = { yes: 'compoundable', court: 'compcourt', no: 'noncompoundable' }[x.comp];
    return page({ bar: appbar({ title: x.law + ' ' + x.no, back: true }), body: `<div class="stack g8"><div class="t-cap c-pri" style="font-weight:700">${x.law} ${x.no}</div><div class="t-title1">${t(x.title)}</div></div>
     <div class="row g8 wrap">${x.kind === 'procedure' ? badge('procedure') : badge(x.bailable ? 'bailable' : 'nonbailable') + badge(x.cognizable ? 'cognizable' : 'noncognizable') + badge(comp)}</div>
     ${x.kind === 'offence' ? card(`<div class="t-label">${t('Punishment')}</div><div class="t-bodyl">${t(x.punishment)}</div><div class="divider"></div><div class="t-label">${t('Triable by')}</div><div class="t-bodyl">${t(x.triable)}</div>`) : ''}
     ${card(`<div class="t-label">${t('What the section says')}</div><div class="t-bodyl">${t(x.text)}</div>`)}
     ${x.law === 'CrPC' && ['crpc-54', 'crpc-61'].includes(x.id) ? btn('Lawful arrest steps', { type: 'secondary', go: 'S-42?id=lawful-arrest-steps', icon: 'book' }) : ''}
     ${disc()}<div class="t-cap c-3">${t('Prototype sample data. Real values come from the advisor-reviewed dataset.')} | Source: Pakistan Code | v2026.09</div>`, foot: nav(ST.role === 'lawyer' ? 'sections' : 'home') }); } });

/* ---------- M4 SOS ---------- */
const SOS_BLOCK = { 'no contacts': 'Add an emergency contact first', 'no network': 'Connection required', 'no permission': 'Location permission needed' };
ACTS.sosgo = () => { delete VS['S-24']; if (!ST.sosNoticeSeen) { HIST.push(location.hash); go('S-22'); } else if (ST.discreet) { go('S-25'); } else go('S-23'); };
ACTS.sosnotice = () => { ST.sosNoticeSeen = true; go('S-23'); };
function sosMain(s, overlay) {
  const blocked = s !== 'ready'; const R = 100, C = 2 * Math.PI * R;
  return page({ bar: appbar({ title: 'Emergency SOS', large: true }), body: `${s === 'no network' ? banner('danger', 'Connection required. SOS and evidence upload need mobile data.') : ''}${s === 'no contacts' ? banner('warning', 'Add at least one emergency contact so SOS can reach someone.', { action: 'Add', go: 'S-13' }) : ''}${s === 'no permission' ? banner('warning', 'Allow location so your contacts can see where you are.', { action: 'Allow', go: 'S-26' }) : ''}
    <div class="statuscard"><div class="avstack">${(s === 'no contacts' ? [] : ST.contacts.slice(0, 3)).map((c, i) => `<span class="avatar">C${i + 1}</span>`).join('') || `<span class="itile e">${ic('people', 24)}</span>`}</div><div class="grow stack g4"><span class="t-label">${ST.contacts.length && s !== 'no contacts' ? ST.contacts.length + ' ' + t('contacts will be alerted') : t('No contacts will be alerted')}</span><span class="t-cap c-2">${t('Lawyers and NGOs in your district too')}</span></div>${badge(blocked ? 'pending' : 'verified', blocked ? 'Not ready' : 'Ready')}</div>
    <div class="stack center g8"><div class="sosstage${blocked ? ' blocked' : ''}"><span class="r r1"></span><span class="r r2"></span><span class="r r3"></span><div class="sosbtn${blocked ? ' blocked' : ''}" id="sos" data-blocked="${blocked ? s : ''}"><svg class="ring" width="212" height="212"><circle id="ringc" cx="106" cy="106" r="${R}" fill="none" stroke="#fff" stroke-opacity=".95" stroke-width="8" stroke-dasharray="${C}" stroke-dashoffset="${C}" stroke-linecap="round"/></svg><div class="core">SOS</div></div></div>
    <div class="t-body c-2 center" style="max-width:270px">${t('Hold the button for 1 second to send your live location.')}</div>
    <button class="btn btn-tertiary btn-M" data-act="sosgo" ${blocked ? 'disabled' : ''}>${t('Prototype shortcut: tap to send')}</button></div>
    <div class="callrow"><a href="tel:15"><span class="ph">${ic('phone', 16)}</span>${t('Police')} 15</a><a href="tel:1122"><span class="ph">${ic('phone', 16)}</span>${t('Rescue')} 1122</a></div>`, foot: nav('sos'), overlay });
}
const sosHold = () => { const b = $('#sos'); if (!b) return; const c = $('#ringc'); const C = parseFloat(c.getAttribute('stroke-dasharray')); let raf, t0;
  const stop = early => { cancelAnimationFrame(raf); c.setAttribute('stroke-dashoffset', C); if (early) toast('Hold for 1 second'); };
  b.addEventListener('pointerdown', () => { if (b.dataset.blocked) { toast(SOS_BLOCK[b.dataset.blocked]); return; } t0 = performance.now(); const step = now => { const p = Math.min((now - t0) / 1000, 1); c.setAttribute('stroke-dashoffset', C * (1 - p)); if (p >= 1) { ACTS.sosgo(); } else raf = requestAnimationFrame(step); }; raf = requestAnimationFrame(step); });
  ['pointerup', 'pointerleave', 'pointercancel'].forEach(ev => b.addEventListener(ev, () => { if (t0) { const done = performance.now() - t0 >= 1000; t0 = 0; if (!done) stop(true); } }));
};
reg('S-21', { name: 'SOS', module: 'M4 SOS', api: 'E-09, E-47', roles: 'C', frame: 'phone', states: ['ready', 'no contacts', 'no network', 'no permission'], render: ({ s }) => sosMain(s), mount: sosHold });
reg('S-22', { name: 'First SOS notice', module: 'M4 SOS', roles: 'C', frame: 'phone',
  render: () => sosMain('ready', sheet(`<div class="iconbig red">${ic('alert', 48)}</div><div class="t-title2 center">${t('Who will see your SOS')}</div>
   <div class="stack g12">${[['people', 'Your emergency contacts get an SMS with a live location link.'], ['gavel', 'Verified lawyers and NGO monitors in your district get an alert.'], ['person', 'They can see your name, phone number and live location until you end the SOS.']].map(([i, x]) => `<div class="row g12" style="align-items:flex-start">${ic(i, 24, 'c-pri')}<span class="t-body">${t(x)}</span></div>`).join('')}</div>${btn('I understand, continue', { act: 'sosnotice' })}${btn('Not now', { type: 'tertiary', go: 'S-21' })}`)) });

reg('S-23', { name: 'SOS countdown', module: 'M4 SOS', roles: 'C', frame: 'phone', lightStatus: true, full: true, states: ['running', '5', '3', '1'],
  render: ({ s }) => { const n = s === 'running' ? 5 : +s; return page({ flush: true, body: '', overlay: `<div class="countdown"><div class="t-title2">${t('Sending SOS in')}</div><div class="num" id="cd">${n}</div><div class="t-bodyl" style="text-align:center;opacity:.9">${t('Your contacts, lawyers and NGOs will get your live location.')}</div><button class="btn btn-L full" data-go="S-21">${t('Cancel')}</button></div>` }); },
  mount: ({ s }) => { if (s !== 'running') return; let n = 5; setTick(() => { n--; if (n <= 0) { delete VS['S-24']; go('S-24'); } else { const e = $('#cd'); if (e) e.textContent = n; } }, 1000); } });

const REACH = (c, l, n) => `<div class="row g8 wrap">${badge('verified', c + ' contacts')}${badge('verified', l + ' lawyers')}${badge('verified', n + ' NGO')}</div>`;
reg('S-24', { name: 'SOS active', module: 'M4 SOS', api: 'E-16, E-17, E-18, E-19', roles: 'C', frame: 'phone', states: ['auto', 'sending', 'reached', 'no recipients', 'offline', 'acknowledged', 'ended'],
  render: ({ s }) => { const st = s === 'auto' ? 'sending' : s;
    const ended = st === 'ended';
    return page({ bar: appbar({ title: ended ? 'SOS ended' : 'SOS is active' }), body: `${st === 'offline' ? banner('danger', 'No connection. Retrying every few seconds. Do not rely on this until it says sent.') : ''}
     <div class="row g12">${st === 'sending' ? `<span class="badge b-info">${ic('cloud', 16)}${t('Sending...')}</span>` : ended ? badge('ended') : `<span class="badge b-success">${ic('checkc', 16)}${t('Sent')}</span>`}<span class="t-cap c-2">${t('Location shared about every 10 seconds')}</span></div>
     ${mapcard(ended ? 'Stopped' : 'Updated 12 s ago', ended)}
     ${['reached', 'acknowledged', 'ended'].includes(st) ? `<div class="stack g8"><div class="t-title3">${t('Who was reached')}</div>${REACH(ST.contacts.length, 2, 1)}</div>` : ''}
     ${st === 'no recipients' ? `<div class="stack g8"><div class="t-title3">${t('Who was reached')}</div>${REACH(ST.contacts.length, 0, 0)}${banner('warning', 'No lawyer or NGO is available in your district right now. Your contacts have been alerted.')}</div>` : ''}
     ${st === 'acknowledged' ? `<div class="li" style="border-color:var(--success)">${avatar('S1')}<span class="grow stack g4"><span class="tt">Adv. Sample One</span><span class="st">${t('has seen your alert and is responding')}</span></span>${badge('ack')}</div>` : ''}
     <button class="btn btn-tertiary btn-M" data-go="W-01">${t('Prototype: open the page your contacts see')}</button><div class="grow"></div>${ended ? btn('Back to SOS', { go: 'S-21' }) : `${btn('End SOS', { type: 'danger', data: 'ended', act: 'sosend' })}${btn('False alarm', { type: 'secondary', data: 'false', act: 'sosend' })}`}` }); },
  mount: ({ s }) => { if (s === 'auto') { setTimer(() => { if (cur().id === 'S-24' && !VS['S-24']) { VS['S-24'] = 'reached'; render(true); } }, 1600); setTimer(() => { if (cur().id === 'S-24' && VS['S-24'] === 'reached') { VS['S-24'] = 'acknowledged'; render(true); toast('Adv. Sample One is responding'); } }, 6500); } } });
ACTS.sosend = el => { if (el.dataset.v === 'false') toast('Contacts and responders were told it was a false alarm'); else toast('SOS ended'); delete VS['S-24']; setTimeout(() => go('S-21'), 700); };

reg('S-25', { name: 'SOS discreet screen', module: 'M4 SOS', api: 'E-17', roles: 'C', frame: 'phone', lightStatus: true, full: true,
  render: () => page({ flush: true, body: `<button data-go="S-21" ondblclick="" style="flex:1;background:#0B0F12;color:#5E6C77;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px">${ic('refresh', 32)}<div class="t-body">${t('Syncing...')}</div><div class="t-cap" style="opacity:.35;margin-top:220px">${t('Prototype: tap anywhere to end the discreet SOS')}</div></button>` }) });

const PERMS = { 'location': ['pin', 'Allow location', 'So your contacts can see where you are during an SOS.'], 'background location': ['pin', 'Allow location all the time', 'SOS keeps sharing your position when the screen is off.'], 'battery': ['refresh', 'Do not put the app to sleep', 'Some phones stop background apps. Allow LegalShield to keep sending your location.'], 'camera': ['cam', 'Allow camera', 'To record photos and video as evidence.'], 'microphone': ['mic', 'Allow microphone', 'To record audio and video evidence.'], 'notifications': ['bell', 'Allow notifications', 'For SOS alerts, verification results and report decisions.'] };
reg('S-26', { name: 'Permission sheets', module: 'M4 SOS', roles: 'C, L, N', frame: 'phone', states: Object.keys(PERMS),
  render: ({ s }) => { const [i, ti, tx] = PERMS[s]; return page({ flush: true, body: `<div style="flex:1;background:var(--bg)"></div>`, overlay: sheet(`<div class="iconbig">${ic(i, 48)}</div><div class="t-title2 center">${t(ti)}</div><div class="t-body c-2 center">${t(tx)}</div>${btn('Continue', { act: 'toast', data: 'The system permission dialog appears here' })}${btn('Not now', { type: 'tertiary', act: 'back' })}`) }); } });

reg('S-27', { name: 'Alerts list', module: 'M4 SOS', api: 'E-21', roles: 'L, N', frame: 'phone', states: ['with alerts', 'empty', 'unverified'],
  render: ({ s }) => { const ver = ST.verified[ST.role] || s === 'with alerts' || s === 'empty'; const list = (s === 'empty' || s === 'unverified') ? [] : ALERTS;
    return page({ bar: appbar({ title: 'SOS alerts', large: true }), body: `${s === 'unverified' ? banner('warning', 'Your account is pending verification. You will get alerts once an admin verifies it.') : ''}
     ${list.length ? `<div class="stack g8">${list.map(a => card(`<div class="row g8"><span class="grow t-title3">${t('SOS alert')}</span>${badge(a.live ? 'newalert' : 'ack')}</div><div class="t-cap c-2">${a.district} | ${t(a.ago)}</div><div class="t-body">${t('Citizen')}: ${a.person}</div>`, { go: 'S-28?id=' + a.id, cls: '' })).join('')}</div>` : empty('bell', 'No active alerts', 'When someone in your district sends an SOS, it appears here.')}`, foot: nav('alerts') }); } });

ACTS.respond = () => { VS['S-28'] = 'acknowledged'; render(true); toast('The citizen can now see that you are responding'); };
reg('S-28', { name: 'Alert detail', module: 'M4 SOS', api: 'E-19, E-54', roles: 'L, N', frame: 'phone', states: ['new', 'acknowledged', 'cancelled', 'ended'],
  render: ({ q, s }) => { const a = ALERTS.find(x => x.id === q.id) || ALERTS[0];
    return page({ bar: appbar({ title: 'SOS alert', back: true }), body: `${s === 'cancelled' ? banner('info', 'The sender marked this as a false alarm.') : ''}
     <div class="row g8">${badge(s === 'new' ? 'newalert' : s === 'acknowledged' ? 'ack' : s === 'cancelled' ? 'cancelled' : 'ended')}<span class="t-cap c-2">${a.district}</span></div>
     ${mapcard(s === 'new' || s === 'acknowledged' ? 'Updated 12 s ago' : 'Stopped', s === 'cancelled' || s === 'ended')}
     ${card(`<div class="row g12">${avatar(a.person.split(' ').map(x => x[0]).join(''))}<div class="grow stack g4"><div class="t-title3">${a.person}</div><div class="t-body c-2">${a.phone}</div></div><a href="tel:${a.phone.replace(/\s/g, '')}" class="ib" style="background:var(--primary);color:var(--on-primary)">${ic('phone', 24)}</a></div>`)}
     <div class="grow"></div>${s === 'new' ? btn('I am responding', { act: 'respond', icon: 'checkc' }) : s === 'acknowledged' ? banner('success', 'You are marked as responding. The citizen can see your name.') : ''}` }); } });
