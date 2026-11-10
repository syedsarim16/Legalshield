/* M1 Account + Home: S-01 .. S-17 */
const $ = s => document.querySelector(s);
const roleLabel = r => ({ citizen: 'Citizen', lawyer: 'Lawyer', ngo: 'NGO monitor', admin: 'Admin' }[r]);
const back = (title, body, extra = {}) => page({ bar: appbar({ title, back: true, ...(extra.bar || {}) }), body, foot: extra.foot, overlay: extra.overlay });

ACTS.setlang = el => { ST.lang = el.dataset.v; saveState(); buildSide(); render(true); };
ACTS.acc = () => { ST.accepted = !ST.accepted; render(true); };
ACTS.regrole = el => { ST.regRole = el.dataset.v; render(true); };
ACTS.regnext = () => { HIST.push(location.hash); go({ citizen: 'S-06', lawyer: 'S-07', ngo: 'S-08' }[ST.regRole]); };
ACTS.demorole = el => { ST.role = el.dataset.v === 'ngo_monitor' ? 'ngo' : el.dataset.v.toLowerCase(); saveState(); render(true); };
ACTS.login = () => { HIST.length = 0; go(ROLE_HOME[ST.role]); };
ACTS.pickfile = el => { const k = 'file_' + el.dataset.v; ST[k] = !ST[k]; render(true); };
ACTS.verifyotp = () => { ST.role = ST.regRole || ST.role; saveState(); HIST.length = 0; if (ST.role === 'citizen') { go('S-17'); } else { go('S-12'); } setTimeout(() => toast('Phone verified. Your account is pending admin verification.'), 150); };
ACTS.fpnext = el => { const order = ['phone', 'otp', 'password']; const i = order.indexOf(vs('S-11') || 'phone'); if (i < 2) setVS(order[i + 1]); else { toast('Password changed. Please log in.'); setTimeout(() => go('S-10'), 700); } };
ACTS.delcontact = el => { ST.contacts = ST.contacts.filter(c => String(c.id) !== el.dataset.v); render(true); toast('Contact removed'); };
ACTS.addcontact = () => { const n = $('#cn').value.trim() || 'New contact', p = $('#cp').value.trim() || '0300 0000000'; ST.contacts.push({ id: Date.now(), name: n, phone: p }); VS['S-13'] = 'list'; render(true); toast('Contact added'); };
ACTS.showadd = () => setVS('add', 'S-13');
ACTS.closesheet = () => { VS['S-13'] = 'list'; render(true); };
ACTS.discreet = () => { ST.discreet = !ST.discreet; saveState(); render(true); };
ACTS.notif = () => { ST.notif = !ST.notif; render(true); };
ACTS.cpnext = () => { if ((vs('S-14') || 'password') === 'otp') { toast('Phone number changed. Other devices were signed out.'); setTimeout(() => go('S-12'), 700); } else setVS('otp', 'S-14'); };
ACTS.delacct = () => setVS('confirm', 'S-15');
ACTS.delcancel = () => setVS('default', 'S-15');
ACTS.delgo = () => { toast('Account and data deleted'); setTimeout(() => go('S-04'), 800); };

reg('S-01', { name: 'Splash', module: 'M1 Account', api: 'E-05', roles: 'all', frame: 'phone', lightStatus: true, full: true,
  render: () => `<button class="body flush" data-go="S-02" style="justify-content:center;align-items:center;gap:20px;background:var(--grad-hero);color:#fff;position:relative;overflow:hidden"><span class="welcome-hero" style="position:absolute;inset:0;padding:0;background:none"></span>${shieldArt(124)}<div class="t-display" style="font-size:36px;line-height:42px">LegalShield</div><div class="t-bodyl" style="opacity:.88;padding-inline:44px;text-align:center">${t('Know your rights. Get help fast.')}</div><div class="t-cap" style="opacity:.65;margin-top:64px">${t('Tap to continue')}</div></button>`,
  mount: () => { if (!ST.booted) { ST.booted = true; setTimer(() => { if (cur().id === 'S-01') go('S-02'); }, 2300); } } });

reg('S-02', { name: 'Language', module: 'M1 Account', roles: 'all', frame: 'phone',
  render: () => page({ body: `<div class="stack g8" style="margin-top:12px"><div class="t-title1">${t('Choose your language')}</div><div class="t-body c-2">${t('You can change this later in Settings.')}</div></div>
   <div class="stack g12" role="radiogroup">${radio('اردو', 'Urdu, right-to-left', ST.lang === 'ur', 'setlang', 'ur')}${radio('Roman Urdu', 'Urdu written in English letters', ST.lang === 'rn', 'setlang', 'rn')}${radio('English', 'English', ST.lang === 'en', 'setlang', 'en')}</div>
   <div class="grow"></div>${btn('Continue', { go: 'S-03' })}` }) });

reg('S-03', { name: 'Disclaimer and terms', module: 'M1 Account', roles: 'all', frame: 'phone', states: ['unchecked', 'checked'],
  render: ({ s }) => { const on = s === 'checked' || ST.accepted; return page({ body: `<div class="iconbig">${ic('shield', 48)}</div><div class="t-title1 center">${t('Before you start')}</div>
   <div class="stack g12">${['LegalShield gives legal information, not legal advice.', 'It covers the Pakistan Penal Code (PPC) and Code of Criminal Procedure (CrPC) only.', 'Whether evidence is accepted is decided by the court.', 'Your location, CNIC and evidence are sensitive. We collect the minimum and encrypt it.'].map(x => `<div class="row g12" style="align-items:flex-start">${ic('checkc', 24, 'c-ok')}<span class="t-bodyl">${t(x)}</span></div>`).join('')}</div>
   <div class="row g16 t-body"><a class="c-pri" style="font-weight:600;text-decoration:underline" data-act="toast" data-v="Privacy policy would open here">${t('Privacy policy')}</a><a class="c-pri" style="font-weight:600;text-decoration:underline" data-act="toast" data-v="Terms of use would open here">${t('Terms of use')}</a></div>
   ${check(on, 'I understand and agree', 'acc')}<div class="grow"></div>${btn('Continue', { go: 'S-04', dis: !on })}` }); } });

reg('S-04', { name: 'Welcome', module: 'M1 Account', roles: 'all', frame: 'phone', lightStatus: true, full: true,
  render: () => page({ flush: true, body: `<div class="welcome-hero">${shieldArt(132)}<div class="t-display" style="font-size:34px;line-height:40px">LegalShield</div><div class="t-bodyl" style="opacity:.9;max-width:290px">${t('Verify your rights, call for help and keep evidence safe, in Urdu, Roman Urdu or English.')}</div></div>
   <div class="welcome-sheet">${btn('Log in', { go: 'S-10' })}${btn('Create account', { type: 'secondary', go: 'S-05' })}<div class="t-cap c-3 center" style="padding-top:4px">${t('Legal information, not legal advice.')}</div></div>` }) });

reg('S-05', { name: 'Choose role', module: 'M1 Account', roles: 'all', frame: 'phone',
  render: () => back('Create account', `<div class="auth-head"><div class="auth-kicker">${t('LegalShield')}</div><div class="t-title2">${t('Choose your account')}</div><div class="t-body c-2">${t('Select the role that best matches how you will use LegalShield.')}</div></div><div class="stack g12" role="radiogroup">${radio(t('Citizen'), 'Get help with your rights, SOS and evidence', ST.regRole === 'citizen', 'regrole', 'citizen')}${radio(t('Lawyer'), 'Offer advice. Needs Bar Council verification', ST.regRole === 'lawyer', 'regrole', 'lawyer')}${radio(t('NGO monitor'), 'Receive alerts and see anonymised reports. Needs verification', ST.regRole === 'ngo', 'regrole', 'ngo')}</div><div class="grow"></div>${btn('Continue', { act: 'regnext' })}`) });

const regForm = (extra, s, title) => back(title, `${stepper(3, 1)}
  <div class="auth-head"><div class="auth-kicker">${t('Protected account setup')}</div><div class="t-title2">${t('Tell us about yourself')}</div><div class="t-body c-2">${t('Enter the test verification code shown on the next screen to activate your account.')}</div></div>
  ${field({ id: 'fn', label: 'Full name', ph: 'As on your CNIC', value: s === 'errors' ? 'Sample Citizen' : '' })}
  ${field({ id: 'ph', label: 'Mobile number', pre: '+92', ph: '300 1234567', type: 'tel', ltr: true, value: s === 'errors' ? '300 1234567' : '', error: s === 'errors' ? 'This number is already registered' : '', inputmode: 'numeric' })}
  ${field({ id: 'cn', label: 'CNIC', ph: '12345-1234567-1', ltr: true, value: s === 'errors' ? '35202-12345' : '', error: s === 'errors' ? 'Enter 13 digits like 12345-1234567-1' : '', help: s === 'errors' ? '' : 'Format check only. We do not verify with NADRA.' })}
  ${extra}
  ${field({ id: 'pw', label: 'Password', type: 'password', ph: 'At least 8 characters', icon: 'visible' })}
  <div class="grow"></div>${btn('Continue', { go: 'S-09' })}`);
reg('S-06', { name: 'Register: citizen', module: 'M1 Account', api: 'E-01', roles: 'C', frame: 'phone', states: ['default', 'errors'], render: ({ s }) => regForm('', s, 'Citizen account') });
reg('S-07', { name: 'Register: lawyer', module: 'M1 Account', api: 'E-01', roles: 'L', frame: 'phone', states: ['default', 'errors'],
  render: ({ s }) => regForm(`${field({ id: 'bar', label: 'Bar Council number', ph: 'e.g. ICT-2231' })}<div class="stack g8"><label class="t-label">${t('Licence (photo or PDF)')}</label>${filepick(ST.file_lic, 'Upload licence (photo or PDF)', 'licence_ayesha.pdf  |  1.2 MB', 'pickfile').replace('data-act="pickfile"', 'data-act="pickfile" data-v="lic"')}<div class="t-cap c-2">${t('An admin checks this before you can appear in the directory.')}</div></div>`, s, 'Lawyer account') });
reg('S-08', { name: 'Register: NGO monitor', module: 'M1 Account', api: 'E-01', roles: 'N', frame: 'phone', states: ['default', 'errors'],
  render: ({ s }) => regForm(`${field({ id: 'org', label: 'Organisation name', ph: 'Your organisation' })}${field({ id: 'dist', label: 'Districts you cover', select: DISTRICTS, value: 'Islamabad' })}<div class="stack g8"><label class="t-label">${t('Proof of organisation')}</label>${filepick(ST.file_org, 'Upload proof document', 'registration_letter.pdf  |  0.8 MB', 'pickfile').replace('data-act="pickfile"', 'data-act="pickfile" data-v="org"')}</div>`, s, 'NGO monitor account') });

reg('S-09', { name: 'OTP verification', module: 'M1 Account', api: 'E-03, E-02', roles: 'all', frame: 'phone', states: ['default', 'wrong code', 'expired'],
  render: ({ s }) => back('Verify your number', `<div class="t-bodyl c-2">${t('Enter the 6-digit test code for +92 300 ••• 4567.')}</div>
   <div class="otp${s === 'wrong code' ? ' err' : ''}" id="otp">${Array.from({ length: 6 }, (_, i) => `<input inputmode="numeric" maxlength="1" aria-label="Digit ${i + 1}">`).join('')}</div>
   <div id="otp-dev-code" class="t-cap c-2 center" aria-live="polite"></div>
   ${s === 'wrong code' ? `<div class="help c-dng row g8 center" style="justify-content:center">${ic('alert', 16)}${t('That code is not correct')}</div>` : ''}${s === 'expired' ? banner('warning', 'This code has expired. Request a new one.') : ''}
   <button id="register-resend" class="btn btn-tertiary btn-M" style="align-self:center" data-act="resendotp" disabled><span>${t('Resend code')}</span> <span id="register-resend-countdown" aria-live="polite"></span></button><div class="grow"></div>${btn('Verify', { act: 'verifyotp' })}`),
  mount: () => { const ins = [...document.querySelectorAll('#otp input')]; ins.forEach((el, i) => { el.addEventListener('input', () => { el.value = el.value.replace(/\D/g, ''); if (el.value && ins[i + 1]) ins[i + 1].focus(); }); el.addEventListener('keydown', e => { if (e.key === 'Backspace' && !el.value && ins[i - 1]) ins[i - 1].focus(); }); }); if (ins[0]) ins[0].focus(); } });

reg('S-10', { name: 'Login', module: 'M1 Account', api: 'E-04', roles: 'all', frame: 'phone', states: ['default', 'error', 'locked'],
  render: ({ s }) => back('Log in', `${s === 'error' ? banner('danger', 'Wrong number or password.') : ''}${s === 'locked' ? banner('warning', 'Too many attempts. Try again in 10 minutes.') : ''}
   <div class="login-hero"><div class="auth-brand"><span class="auth-logo">${ic('shield', 20)}</span><span>LegalShield</span><span class="auth-live">${t('Protected')}</span></div><div class="auth-hero-title">${t('Welcome back')}</div><div class="auth-hero-copy">${t('Your rights, contacts and trusted legal tools are ready when you are.')}</div></div>
   <div class="auth-trust"><span class="auth-trust-icon">${ic('shield', 20)}</span><span class="stack g4"><b>${t('Your account is protected')}</b><span>${t('Sign in with your password. Verification codes are generated for testing.')}</span></span></div>
   <div class="login-fields">${field({ id: 'ph', label: 'Mobile number', pre: '+92', ph: '300 1234567', ltr: true, type: 'tel' })}${field({ id: 'pw', label: 'Password', type: 'password', ph: 'Your password', icon: 'visible' })}</div>
   <a class="c-pri t-label" style="text-decoration:underline;cursor:pointer;align-self:flex-start" data-go="S-11">${t('Forgot password?')}</a>
   <div class="card" style="border-style:dashed;gap:8px"><div class="t-cap c-2">${t('Prototype only: log in as')}</div>${seg(['Citizen', 'Lawyer', 'NGO', 'Admin'], roleLabel(ST.role) === 'NGO monitor' ? 'NGO' : roleLabel(ST.role), 'demorole')}</div>
   <div class="grow"></div>${btn('Log in', { act: 'login', dis: s === 'locked' })}<div class="auth-footnote">${t('New to LegalShield?')} <a data-go="S-05">${t('Create an account')}</a></div>`) });

reg('S-11', { name: 'Forgot password', module: 'M1 Account', api: 'E-02, E-03', roles: 'all', frame: 'phone', states: ['phone', 'otp', 'password'],
  render: ({ s }) => back('Reset password', `${stepper(3, ['phone', 'otp', 'password'].indexOf(s) + 1)}
   ${s === 'phone' ? `<div class="t-bodyl c-2">${t('Enter your registered mobile number.')}</div>${field({ id: 'ph', label: 'Mobile number', pre: '+92', ph: '300 1234567', ltr: true })}` : ''}
   ${s === 'otp' ? `<div class="t-bodyl c-2">${t('Enter the 6-digit verification code.')}</div><div class="otp" id="otp">${Array.from({ length: 6 }, () => '<input inputmode="numeric" maxlength="1">').join('')}</div><div id="reset-otp-dev-code" class="t-cap c-2 center" aria-live="polite"></div><button id="reset-resend" class="btn btn-tertiary btn-M" data-act="resendresetotp" disabled><span>${t('Resend code')}</span> <span id="reset-resend-countdown" aria-live="polite"></span></button>` : ''}
   ${s === 'password' ? `${field({ id: 'np', label: 'New password', type: 'password', ph: 'At least 8 characters', icon: 'visible' })}${banner('info', 'You will be signed out on all other devices.')}` : ''}
   <div class="grow"></div>${btn(s === 'password' ? 'Save password' : 'Continue', { act: 'fpnext' })}`) });

reg('S-12', { name: 'Profile', module: 'M1 Account', api: 'E-07, E-08, E-06', roles: 'all', frame: 'phone', states: ['default', 'pending', 'verified', 'rejected'],
  render: ({ s }) => {
    const r = ST.role, needs = r === 'lawyer' || r === 'ngo';
    const status = s === 'default' ? (ST.verified[r] ? 'verified' : 'pending') : s;
    const name = { citizen: 'Sample Citizen', lawyer: 'Adv. Sample One', ngo: 'Sample NGO Monitor', admin: 'Sample Admin' }[r];
    const ban = needs && status !== 'verified' ? (status === 'rejected' ? banner('danger', 'Verification was rejected. Contact support with a clearer document.') : banner('warning', 'Your account is pending verification. Alerts and directory listing start once verified.')) : '';
    return page({ bar: appbar({ title: r === 'citizen' ? 'More' : 'Profile', large: true }), body: `${ban}
     <div class="row g16">${avatar(name.split(' ').map(x => x[0]).slice(-2).join(''), true)}<div class="stack g4"><div class="t-title2">${name}</div><div class="t-body c-2">+92 300 ••• 4567</div><div class="row g8">${badge('role', roleLabel(r))}${needs ? badge(status === 'verified' ? 'verified' : status === 'rejected' ? 'rejected' : 'pending') : ''}</div></div></div>
     <div class="stack g8">${r === 'citizen' ? li({ lead: 'people', title: 'Emergency contacts', sub: ST.contacts.length + ' people will get your SOS', go: 'S-13' }) + li({ lead: 'doc', title: 'Make a document', sub: 'Complaints and legal notices', go: 'S-29' }) + li({ lead: 'people', title: 'Lawyers and legal aid', sub: 'Find help near you', go: 'S-32' }) + li({ lead: 'alert', title: 'Report an incident', sub: 'Help NGOs see where abuse happens', go: 'S-49' }) : ''}
     ${r === 'lawyer' ? li({ lead: 'edit', title: 'Edit my directory profile', sub: 'Cities, specialisations, SOS opt-in', go: 'S-34' }) : ''}
     ${li({ lead: 'phone', title: 'Change phone number', go: 'S-14' })}${li({ lead: 'globe', title: 'Settings', sub: 'Language, discreet SOS, notifications', go: 'S-16' })}${li({ lead: 'shield', title: 'Privacy policy', go: 'S-03' })}
     ${r !== 'admin' ? li({ lead: 'trash', red: true, title: 'Delete account', sub: 'Permanently remove your data', go: 'S-15' }) : ''}${li({ lead: 'logout', title: 'Log out', go: 'S-04', trail: '' })}</div>`, foot: nav(r === 'citizen' ? 'more' : 'profile') });
  } });

reg('S-13', { name: 'Emergency contacts', module: 'M1 Account', api: 'E-09, E-10, E-11', roles: 'C', frame: 'phone', states: ['list', 'add', 'empty'],
  render: ({ s }) => { const list = s === 'empty' ? [] : ST.contacts; return page({ bar: appbar({ title: 'Emergency contacts', back: true }),
    body: `<div class="t-body c-2">${t('These people get an SMS with your live location when you send an SOS.')}</div>
     ${list.length ? `<div class="stack g8">${list.map(c => li({ lead: '<b>' + esc(c.name[0]) + '</b>', title: esc(c.name), raw: true, sub: c.phone, trail: `<button class="ib" data-act="delcontact" data-v="${c.id}" aria-label="Remove">${ic('trash', 24, 'c-dng')}</button>` })).join('')}</div>` : empty('people', 'No emergency contacts yet', 'Add at least one person so SOS can reach them.')}
     <div class="grow"></div>${btn('Add contact', { act: 'showadd', icon: 'add' })}`, overlay: s === 'add' ? sheet(`<div class="t-title2">${t('Add contact')}</div>${field({ id: 'cn', label: 'Name', ph: 'Name' })}${field({ id: 'cp', label: 'Mobile number', ph: '0300 1234567', ltr: true })}${banner('info', 'This person will receive SMS messages with your location during an SOS. Tell them first.')}<div class="row g12">${btn('Cancel', { type: 'secondary', act: 'closesheet' })}${btn('Save', { act: 'addcontact' })}</div>`) : '' }); } });

reg('S-14', { name: 'Change phone number', module: 'M1 Account', api: 'E-02, E-03', roles: 'all', frame: 'phone', states: ['password', 'otp', 'number in use'],
  render: ({ s }) => back('Change phone number', `${stepper(2, s === 'otp' ? 2 : 1)}
   ${s === 'otp' ? `<div class="t-bodyl c-2">${t('Enter the test verification code.')}</div><div class="otp" id="otp">${Array.from({ length: 6 }, () => '<input inputmode="numeric" maxlength="1">').join('')}</div><div id="change-phone-otp-dev-code" class="t-cap c-2 center" aria-live="polite"></div><button id="change-phone-resend" class="btn btn-tertiary btn-M" data-act="resendchangeotp" disabled><span>${t('Resend code')}</span> <span id="change-phone-resend-countdown" aria-live="polite"></span></button>`
     : `${field({ id: 'pw', label: 'Current password', type: 'password', ph: 'Your password' })}${field({ id: 'np', label: 'New mobile number', pre: '+92', ph: '312 7654321', ltr: true, error: s === 'number in use' ? 'This number is already in use' : '' })}`}
   <div class="grow"></div>${btn(s === 'otp' ? 'Confirm change' : 'Send code', { act: 'cpnext' })}`) });

reg('S-15', { name: 'Delete account', module: 'M1 Account', api: 'E-49', roles: 'C, L, N', frame: 'phone', states: ['default', 'confirm', 'wrong password'],
  render: ({ s }) => back('Delete account', `${banner('danger', 'This cannot be undone.')}
   <div class="t-title3">${t('What will be deleted')}</div><div class="stack g8">${['Your evidence files and share links', 'Your emergency contacts and devices', 'Your SOS history', 'Pending and rejected incident reports', 'Your lawyer or NGO profile and documents'].map(x => `<div class="row g12">${ic('trash', 20, 'c-dng')}<span class="t-body">${t(x)}</span></div>`).join('')}</div>
   <div class="t-body c-2">${t('Approved incident reports stay in anonymised form (district, category and month only).')}</div>
   ${field({ id: 'pw', label: 'Enter your password to confirm', type: 'password', ph: 'Your password', error: s === 'wrong password' ? 'Wrong password' : '' })}
   <div class="grow"></div>${btn('Delete my account', { type: 'danger', act: 'delacct' })}`, { overlay: s === 'confirm' ? dialog(`<div class="t-title2">${t('Delete account?')}</div><div class="t-body c-2">${t('All your data will be permanently removed.')}</div><div class="row g12">${btn('Cancel', { type: 'secondary', act: 'delcancel' })}${btn('Delete', { type: 'danger', act: 'delgo' })}</div>`) : '' }) });

reg('S-16', { name: 'Settings', module: 'M1 Account', roles: 'all', frame: 'phone', states: ['default', 'discreet on'],
  render: ({ s }) => { const d = s === 'discreet on' || ST.discreet; return back('Settings', `<div class="stack g8"><div class="t-title3">${t('Language')}</div><div class="stack g8">${radio('اردو', '', ST.lang === 'ur', 'setlang', 'ur')}${radio('Roman Urdu', '', ST.lang === 'rn', 'setlang', 'rn')}${radio('English', '', ST.lang === 'en', 'setlang', 'en')}</div></div>
   ${ST.role === 'citizen' ? `<div class="card"><div class="row g12"><div class="grow stack g4"><div class="t-title3">${t('Discreet SOS')}</div><div class="t-cap c-2">${t('Sends immediately with no sound or vibration. Notification and screen look like a normal sync.')}</div></div>${sw(d, 'discreet')}</div>${d ? banner('info', 'Discreet mode is on. The countdown is skipped, so hold the button carefully.') : ''}</div>` : ''}
   <div class="card"><div class="row g12"><div class="grow stack g4"><div class="t-title3">${t('Notifications')}</div><div class="t-cap c-2">${t('Alerts, verification results and report decisions')}</div></div>${sw(ST.notif !== false, 'notif')}</div></div>
   <div class="t-cap c-3 center">LegalShield 1.0 (prototype)</div>`); } });

reg('S-17', { name: 'Home', module: 'Home', api: 'E-47', roles: 'C', frame: 'phone',
  render: () => page({ body: `<div class="hero"><div class="row g12"><div class="grow stack g4"><span class="hi">${t('Assalam o Alaikum')}</span><div class="t-title1" style="color:#fff">${t('How can we help?')}</div></div><span class="avatar">SC</span></div>
     <div class="status"><span class="shield">${ic('shield', 24)}</span><div class="stack"><b>${t('Protection ready')}</b><span>${ST.contacts.length} ${t('emergency contacts')}</span></div><button class="go" data-go="S-21">${ic('alert', 16)}${t('SOS')}</button></div></div>
   <div class="callrow"><a href="tel:15"><span class="ph">${ic('phone', 16)}</span>${t('Police')} 15</a><a href="tel:1122"><span class="ph">${ic('phone', 16)}</span>${t('Rescue')} 1122</a></div>
   <button class="feature" data-go="S-18"><span class="lead">${ic('chat', 24)}</span><span class="arrow">${ic('chev', 18, M)}</span><span class="t-title2" style="margin-top:6px">${t('Ask the assistant')}</span><span class="t-body" style="opacity:.88;max-width:250px">${t('Plain-language answers with the exact PPC or CrPC section.')}</span></button>
   <div class="grid2">${[['search', 'Check a section', 'S-19', ''], ['book', 'Know your rights', 'S-41', 'b'], ['doc', 'Make a document', 'S-29', 'c'], ['people', 'Find a lawyer', 'S-32', 'd'], ['alert', 'Report an incident', 'S-49', 'e'], ['folder', 'Evidence vault', 'S-36', 'b']].map(([i, l, g, c]) => `<button class="tile" data-go="${g}"><span class="itile ${c}">${ic(i, 26)}</span><span class="t-title3">${t(l)}</span></button>`).join('')}</div>
   ${disc()}`, foot: nav('home') }) });
