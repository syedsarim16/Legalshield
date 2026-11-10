/* LegalShield: connects the prototype UI to the FastAPI backend (Modules 1-3).
   Loaded last, so it overrides the prototype's demo ACTS and wraps screen renders.
   Screens of Modules 4-10 have no backend yet and stay as demo screens (marked with a ribbon). */
(() => {
  const API = '/api/v1';
  const PROTO = new URLSearchParams(location.search).has('proto');
  if (PROTO) document.body.classList.remove('appmode');
  const PUBLIC = new Set(['S-01', 'S-02', 'S-03', 'S-04', 'S-05', 'S-06', 'S-07', 'S-08', 'S-09', 'S-10', 'S-11', 'W-01', 'W-02']);
  const REAL = new Set(['S-01', 'S-02', 'S-03', 'S-04', 'S-05', 'S-06', 'S-07', 'S-08', 'S-09', 'S-10', 'S-11', 'S-12', 'S-13', 'S-14', 'S-15', 'S-16', 'S-17', 'S-18', 'S-19', 'S-20']);
  const LANG = { en: 'en', rn: 'ur-Latn', ur: 'ur' };
  const roleUi = r => (r === 'ngo_monitor' ? 'ngo' : r);
  const roleApi = r => (r === 'ngo' ? 'ngo_monitor' : r);
  const OTP_LIFETIME_MS = 60 * 1000;
  const fb = () => window.LegalShieldFirebase;
  ST.form = {}; ST.files = {}; ST.me = null; ST.pending = null; ST.secResults = null; ST.secLoading = false;
  let firebaseUser = null;
  let refreshToken = null;

  function startResendCountdown(buttonId, countdownId, resendAt) {
    const button = document.getElementById(buttonId);
    const countdown = document.getElementById(countdownId);
    if (!button || !countdown) return;
    const update = () => {
      const seconds = Math.max(0, Math.ceil((resendAt - Date.now()) / 1000));
      button.disabled = seconds > 0;
      countdown.textContent = seconds ? `(${seconds}s)` : '';
      return seconds > 0;
    };
    if (update()) {
      const timer = setTick(() => { if (!update()) clearInterval(timer); }, 1000);
    }
  }

  /* ---------------- HTTP client ---------------- */
  class ApiErr extends Error { constructor(status, code, message) { super(message); this.status = status; this.code = code; } }
  async function api(method, path, body, { auth = true, form = false } = {}) {
    const headers = {}; let payload;
    if (body !== undefined) { if (form) payload = body; else { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); } }
    let token = null;
    if (auth) {
      token = await fb()?.token?.();
      if (!token) throw new ApiErr(401, 'UNAUTHENTICATED', 'Sign in required.');
      headers.Authorization = 'Bearer ' + token;
    }
    const request = async () => {
      try { return await fetch(API + path, { method, headers, body: payload }); }
      catch (e) { throw new ApiErr(0, 'NETWORK', 'Cannot reach the server. Check your connection.'); }
    };
    let res = await request();
    if (res.status === 401 && auth) {
      const errorBody = await res.clone().json().catch(() => ({}));
      if (errorBody.error?.code === 'FIREBASE_TOKEN_INVALID') {
        let refreshedToken;
        try { refreshedToken = await fb()?.token?.(true); }
        catch (refreshError) {
          const code = String(refreshError?.code || '').toLowerCase();
          if (['auth/user-token-expired', 'auth/invalid-user-token', 'auth/user-disabled', 'auth/user-not-found'].includes(code)) {
            endSession(true);
            throw new ApiErr(401, 'FIREBASE_TOKEN_REVOKED', 'Your Firebase session expired or was revoked. Please sign in again.');
          }
          throw refreshError;
        }
        if (refreshedToken) {
          token = refreshedToken;
          headers.Authorization = 'Bearer ' + token;
          res = await request();
        }
      }
    }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const e = data.error || {};
      if (res.status === 401 && auth && ['TOKEN_EXPIRED', 'TOKEN_INVALID', 'UNAUTHENTICATED', 'FIREBASE_TOKEN_INVALID', 'FIREBASE_TOKEN_EXPIRED', 'FIREBASE_TOKEN_REVOKED'].includes(e.code)) endSession(true);
      throw new ApiErr(res.status, e.code || 'HTTP_ERROR', e.message || 'Something went wrong.');
    }
    return data;
  }

  /* ---------------- session ---------------- */
  function endSession(redirect) {
    firebaseUser = null; refreshToken = null; ST.me = null; ST.contacts = []; ST.chat = []; ST.pending = null;
    const signOut = fb()?.signOut?.(); if (signOut) signOut.catch(error => console.error('Firebase sign-out failed.', error));
    if (redirect) { HIST.length = 0; location.hash = '#/S-10'; }
  }
  async function loadMe() {
    ST.me = await api('GET', '/users/me');
    ST.role = roleUi(ST.me.role);
    ST.verified[ST.role] = ST.me.verification_status === 'verified';
    const preferences = await fb().loadPreferences();
    if (preferences) {
      if (['en', 'rn', 'ur'].includes(preferences.lang)) ST.lang = preferences.lang;
      if (['light', 'dark'].includes(preferences.theme)) ST.theme = preferences.theme;
      if (typeof preferences.discreet === 'boolean') ST.discreet = preferences.discreet;
      saveState(); buildSide();
    }
    saveState();
    if (ST.me.role === 'citizen') await loadContacts();
    return ST.me;
  }
  async function loadContacts() {
    ST.contacts = (await api('GET', '/users/me/contacts')).contacts;
  }
  const home = () => ROLE_HOME[ST.role] || 'S-17';
  async function signIn(phone, password) {
    const j = await api('POST', '/auth/login', { phone, password }, { auth: false });
    await useSession(j);
  }

  async function useSession(j) {
    refreshToken = j.refresh_token || null;
    if (j.firebase_custom_token) await fb().signInWithCustomToken(j.firebase_custom_token);
    firebaseUser = await fb().currentUser();
    if (!firebaseUser) throw new ApiErr(401, 'FIREBASE_TOKEN_INVALID', 'Firebase sign-in could not be established.');
    ST.pending = null;
    await loadMe();
    await registerMessagingDevice();
    HIST.length = 0; go(home());
  }

  async function registerMessagingDevice() {
    try {
      const token = await fb()?.requestMessagingToken?.();
      if (token) await api('POST', '/users/me/devices', { fcm_token: token });
    } catch (e) { /* Notifications are optional and must not block sign-in. */ }
  }

  /* ---------------- UI helpers ---------------- */
  const val = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
  const otpValue = () => [...document.querySelectorAll('#otp input')].map(i => i.value).join('');
  const matchesDisplayedOtp = (entered, expected) => {
    if (typeof expected !== 'string' || !/^\d{6}$/.test(expected)) {
      showErr('The test verification code is unavailable. Request a new code.');
      return false;
    }
    if (entered !== expected) {
      showErr('The code does not match the displayed verification code.');
      return false;
    }
    return true;
  };
  function showErr(msg) {
    const old = document.querySelector('.form-err'); if (old) old.remove();
    const body = document.querySelector('.frame .body'); if (!body) { toast(msg); return; }
    body.insertAdjacentHTML('afterbegin', `<div class="form-err">${banner('danger', msg)}</div>`);
    body.scrollTop = 0;
  }
  function friendlyError(error) {
    if (error instanceof ApiErr) return error.message;
    const code = String(error?.code || '').toLowerCase();
    const messages = {
      'auth/invalid-custom-token': 'Firebase could not establish your account session. Check the Firebase project configuration.',
    };
    return messages[code] || (error?.message ? `Firebase sign-in error: ${error.message}` : 'Something went wrong. Please try again.');
  }
  async function guard(fn, btnEl) {
    if (btnEl) btnEl.disabled = true;
    try { await fn(); }
    catch (e) { showErr(friendlyError(e)); if (!(e instanceof ApiErr)) console.error(e); }
    finally { if (btnEl && btnEl.isConnected) btnEl.disabled = false; }
  }
  // keep typed values when the prototype re-renders a screen
  document.addEventListener('input', e => {
    const id = e.target && e.target.id; if (!id || id === 'msg' || !e.target.closest('.frame')) return;
    (ST.form[cur().id] = ST.form[cur().id] || {})[id] = e.target.value;
  });
  function restoreForm() {
    const f = ST.form[cur().id]; if (!f) return;
    Object.entries(f).forEach(([id, v]) => { const el = document.getElementById(id); if (el && !el.value) el.value = v; });
  }
  const F = (screen, id) => (ST.form[screen] || {})[id] || '';
  const initials = n => (n || '?').split(/\s+/).filter(Boolean).map(x => x[0]).slice(0, 2).join('').toUpperCase();
  const maskPhone = p => (p ? p.replace(/^\+92(\d{3})\d{3}(\d{4})$/, '+92 $1 ••• $2') : '');

  /* ---------------- render wrapper: guard, patches, demo ribbon ---------------- */
  const baseRender = window.render;
  window.render = function (keepScroll) {
    const id = cur().id;
    if (!PROTO && !PUBLIC.has(id) && !firebaseUser) { location.hash = '#/S-04'; return; }
    if (!PROTO && ST.me && ST.me.role !== 'admin' && /^S-(4[3-9]|5\d)$/.test(id)) { location.hash = '#/' + home(); return; }
    baseRender(keepScroll);
    restoreForm();
    if (!PROTO) {
      const dashed = document.querySelector('#stage .card[style*="dashed"]'); if (dashed && id === 'S-10') dashed.remove();
      if (!REAL.has(id)) {
        const f = document.querySelector('#stage .ph-in, #stage .frame');
        if (f) f.insertAdjacentHTML('afterbegin', '<div class="demo-ribbon">Demo screen: the backend for this module is not built yet.</div>');
      }
    }
  };

  /* ---------------- boot ---------------- */
  const s01 = SCREENS['S-01'], s01mount = s01.mount;
  s01.mount = ctx => {
    if (PROTO) return s01mount(ctx);
    if (firebaseUser) { loadMe().then(() => go(home())).catch(error => { console.error('Could not load the signed-in account.', error); endSession(true); }); return; }
    s01mount(ctx);
  };
  if (!PROTO) {
    fb().initialAuthState().then(user => {
      firebaseUser = user;
      if (!user) return;
      return loadMe().then(() => {
        if (PUBLIC.has(cur().id)) go(home());
        else render(true);
      });
    }).catch(error => {
      console.error('Firebase session could not be restored.', error);
      toast('Firebase could not restore your session. Check the Firebase configuration and connection.');
    });
  }

  /* ---------------- M1: register ---------------- */
  ACTS.pickfile = el => {
    const key = el.dataset.v || 'lic';
    if (ST.files[key]) { delete ST.files[key]; render(true); return; }
    const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/jpeg,image/png,application/pdf';
    inp.onchange = () => { if (inp.files[0]) { ST.files[key] = inp.files[0]; render(true); } };
    inp.click();
  };
  const fileLabel = k => { const f = ST.files[k]; return f ? `${f.name}  |  ${(f.size / 1048576).toFixed(1)} MB` : ''; };
  ['S-06', 'S-07', 'S-08'].forEach(id => {
    const m = SCREENS[id], orig = m.render;
    m.render = ctx => {
      let h = orig(ctx);
      h = h.replace('data-go="S-09"', 'data-act="doregister"');
      h = h.replace(/(<button class="filepick[^"]*" data-act="pickfile"[^>]*>[\s\S]*?<span class="grow t-body">)[^<]*(<\/span>)/, (m0, a, b) => a + (fileLabel(id === 'S-07' ? 'lic' : 'org') || t(id === 'S-07' ? 'Upload licence (photo or PDF)' : 'Upload proof document')) + b);
      h = h.replace(/filepick(?! done)([^"]*)" data-act="pickfile"/, (m0, x) => `filepick${ST.files[id === 'S-07' ? 'lic' : 'org'] ? ' done' : ''}${x}" data-act="pickfile"`);
      return h;
    };
  });
  ACTS.doregister = el => guard(async () => {
    const screen = cur().id, role = { 'S-06': 'citizen', 'S-07': 'lawyer', 'S-08': 'ngo_monitor' }[screen];
    const file = role === 'lawyer' ? ST.files.lic : ST.files.org;
    const fd = new FormData();
    fd.append('role', role); fd.append('full_name', val('fn')); fd.append('phone', val('ph')); fd.append('password', val('pw'));
    if (val('cn')) fd.append('cnic', val('cn'));
    if (role === 'lawyer') { fd.append('bar_council_no', val('bar')); if (ST.files.lic) fd.append('verification_document', ST.files.lic); }
    if (role === 'ngo_monitor') { fd.append('organisation_name', val('org')); fd.append('districts', val('dist')); if (ST.files.org) fd.append('verification_document', ST.files.org); }
    const r = await api('POST', '/auth/register', fd, { auth: false, form: true });
    ST.pending = { phone: val('ph'), password: val('pw'), role, devOtp: r.dev_otp || null, purpose: 'register', resendAt: Date.now() + OTP_LIFETIME_MS };
    ST.files = {}; ST.form = {};
    HIST.push(location.hash); go('S-09');
  }, el);

  /* ---------------- M1: OTP (register) ---------------- */
  const s09 = SCREENS['S-09'], s09render = s09.render;
  s09.render = ctx => {
    let h = s09render(ctx);
    const p = ST.pending;
    if (p) h = h.replace(/\+92 300 ••• 4567/, '+92 ' + p.phone.replace(/\D/g, '').replace(/^(0|92)/, '').replace(/^(\d{3})\d{3}(\d{4})$/, '$1 ••• $2'));
    return h.replace('<div id="otp-dev-code" class="t-cap c-2 center" aria-live="polite"></div>',
      p && p.devOtp ? `<div id="otp-dev-code" class="t-cap c-2 center" aria-live="polite">Test verification code: <b>${p.devOtp}</b></div>` : '');
  };
  ACTS.verifyotp = el => guard(async () => {
    const p = ST.pending; if (!p) { go('S-10'); return; }
    const code = otpValue(); if (code.length !== 6) { showErr('Enter the 6-digit code.'); return; }
    if (!matchesDisplayedOtp(code, p.devOtp)) return;
    await api('POST', '/auth/otp/verify', { purpose: 'register', phone: p.phone, code }, { auth: false });
    const { phone, password } = p; ST.pending = null;
    await signIn(phone, password);
    if (ST.role !== 'citizen') setTimeout(() => toast('Phone verified. Your account is pending admin verification.'), 200);
    else setTimeout(() => toast('Phone verified. Welcome to LegalShield.'), 200);
  }, el);
  s09.mount = ((orig) => ctx => {
    orig(ctx);
    if (ST.pending) startResendCountdown('register-resend', 'register-resend-countdown', ST.pending.resendAt || Date.now());
  })(s09.mount);
  ACTS.resendotp = el => guard(async () => {
    const p = ST.pending; if (!p) return;
    if (Date.now() < p.resendAt) return;
    const r = await api('POST', '/auth/otp/request', { purpose: 'register', phone: p.phone }, { auth: false });
    p.devOtp = r.dev_otp || null; p.resendAt = Date.now() + OTP_LIFETIME_MS; render(true); toast('New code sent');
  }, el);

  /* ---------------- M1: login ---------------- */
  ACTS.login = el => guard(async () => {
    const phone = val('ph'), password = val('pw');
    if (!phone || !password) { showErr('Enter your mobile number and password.'); return; }
    try { await signIn(phone, password); }
    catch (e) {
      if (e.code === 'PHONE_NOT_VERIFIED') {
        const r = await api('POST', '/auth/otp/request', { purpose: 'register', phone }, { auth: false });
        ST.pending = { phone, password, devOtp: r.dev_otp || null, purpose: 'register', resendAt: Date.now() + OTP_LIFETIME_MS }; HIST.push(location.hash); go('S-09'); return;
      }
      throw e;
    }
  }, el);

  /* ---------------- M1: forgot password ---------------- */
  ACTS.fpnext = el => guard(async () => {
    const step = vs('S-11') || 'phone';
    if (step === 'phone') {
      const phone = val('ph'); if (!phone) { showErr('Enter your mobile number.'); return; }
      const r = await api('POST', '/auth/otp/request', { purpose: 'reset', phone }, { auth: false });
      ST.reset = { phone, devOtp: r.dev_otp || null, resendAt: Date.now() + OTP_LIFETIME_MS }; setVS('otp', 'S-11');
    } else if (step === 'otp') {
      const code = otpValue(); if (code.length !== 6) { showErr('Enter the 6-digit code.'); return; }
      if (!matchesDisplayedOtp(code, ST.reset?.devOtp)) return;
      const r = await api('POST', '/auth/otp/verify', { purpose: 'reset', phone: ST.reset.phone, code }, { auth: false });
      ST.reset.resetToken = r.reset_token; setVS('password', 'S-11');
    } else {
      const np = val('np');
      await api('POST', '/auth/password/reset', { reset_token: ST.reset.resetToken, new_password: np }, { auth: false });
      ST.reset = null; toast('Password changed. Please log in.'); setTimeout(() => go('S-10'), 700);
    }
  }, el);
  const s11 = SCREENS['S-11'], s11render = s11.render;
  s11.render = ctx => {
    const h = s11render(ctx);
    return h.replace('<div id="reset-otp-dev-code" class="t-cap c-2 center" aria-live="polite"></div>',
      ST.reset && ST.reset.devOtp && ctx.s === 'otp'
        ? `<div id="reset-otp-dev-code" class="t-cap c-2 center" aria-live="polite">Test verification code: <b>${ST.reset.devOtp}</b></div>`
        : '');
  };
  s11.mount = ((orig) => ctx => {
    if (orig) orig(ctx);
    if (ctx.s === 'otp' && ST.reset) startResendCountdown('reset-resend', 'reset-resend-countdown', ST.reset.resendAt || Date.now());
  })(s11.mount);
  ACTS.resendresetotp = el => guard(async () => {
    const reset = ST.reset; if (!reset || Date.now() < reset.resendAt) return;
    const r = await api('POST', '/auth/otp/request', { purpose: 'reset', phone: reset.phone }, { auth: false });
    reset.devOtp = r.dev_otp || null; reset.resendAt = Date.now() + OTP_LIFETIME_MS; render(true); toast('New code sent');
  }, el);

  /* ---------------- M1: profile ---------------- */
  const s12 = SCREENS['S-12'], s12render = s12.render;
  s12.render = ctx => {
    const me = ST.me; let s = ctx.s;
    if (me && s === 'default' && me.verification_status === 'rejected') s = 'rejected';
    let h = s12render({ ...ctx, s });
    if (!me) return h;
    h = h.replace(/(Sample Citizen|Adv\. Sample One|Sample NGO Monitor|Sample Admin)/g, esc(me.full_name))
      .replace(/\+92 300 ••• 4567/, maskPhone(me.phone))
      .replace(/(<span class="avatar lg">)[^<]*(<\/span>)/, `$1${esc(initials(me.full_name))}$2`)
      .replace('data-go="S-04"', 'data-act="logout"');
    if (me.verification_note && s === 'rejected') h = h.replace(/(Verification was rejected[^<]*)/, `$1 ${esc(me.verification_note)}`);
    return h;
  };
  ACTS.logout = el => guard(async () => {
    await api('POST', '/auth/logout', refreshToken ? { refresh_token: refreshToken } : {});
    endSession(false); HIST.length = 0; go('S-04');
  }, el);

  /* ---------------- M1: emergency contacts ---------------- */
  const s13 = SCREENS['S-13'], s13mount = s13.mount;
  s13.mount = ctx => { if (s13mount) s13mount(ctx); if (!PROTO && !ST.contactsLoaded) { ST.contactsLoaded = true; loadContacts().then(() => cur().id === 'S-13' && render(true)); } };
  ACTS.addcontact = el => guard(async () => {
    const name = val('cn'), phone = val('cp'); if (!name || !phone) { showErr('Enter a name and a mobile number.'); return; }
    await api('POST', '/users/me/contacts', { name, phone });
    await loadContacts(); ST.form['S-13'] = {}; VS['S-13'] = 'list'; render(true); toast('Contact added');
  }, el);
  ACTS.delcontact = el => guard(async () => {
    await api('DELETE', '/users/me/contacts/' + el.dataset.v); await loadContacts(); render(true); toast('Contact removed');
  });

  /* ---------------- M1: change phone ---------------- */
  ACTS.cpnext = el => guard(async () => {
    if ((vs('S-14') || 'password') === 'otp') {
      const code = otpValue(); if (code.length !== 6) { showErr('Enter the 6-digit code.'); return; }
      if (!matchesDisplayedOtp(code, ST.cp?.devOtp)) return;
      await api('POST', '/auth/otp/verify', { purpose: 'change_phone', phone: ST.cp.newPhone, code }, { auth: false });
      ST.cp = null; endSession(false); toast('Phone number changed. Please log in again.'); setTimeout(() => go('S-10'), 900);
    } else {
      const newPhone = val('np'), pw = val('pw'); if (!newPhone || !pw) { showErr('Enter your password and the new number.'); return; }
      const r = await api('POST', '/auth/otp/request', { purpose: 'change_phone', new_phone: newPhone, current_password: pw });
      ST.cp = { newPhone, currentPassword: pw, devOtp: r.dev_otp || null, resendAt: Date.now() + OTP_LIFETIME_MS }; setVS('otp', 'S-14');
    }
  }, el);
  const s14 = SCREENS['S-14'], s14render = s14.render;
  s14.render = ctx => {
    const h = s14render(ctx);
    return h.replace('<div id="change-phone-otp-dev-code" class="t-cap c-2 center" aria-live="polite"></div>',
      ST.cp && ST.cp.devOtp && ctx.s === 'otp'
        ? `<div id="change-phone-otp-dev-code" class="t-cap c-2 center" aria-live="polite">Test verification code: <b>${ST.cp.devOtp}</b></div>`
        : '');
  };
  s14.mount = ((orig) => ctx => {
    if (orig) orig(ctx);
    if (ctx.s === 'otp' && ST.cp) startResendCountdown('change-phone-resend', 'change-phone-resend-countdown', ST.cp.resendAt || Date.now());
  })(s14.mount);
  ACTS.resendchangeotp = el => guard(async () => {
    const pending = ST.cp; if (!pending || Date.now() < pending.resendAt) return;
    const r = await api('POST', '/auth/otp/request', { purpose: 'change_phone', new_phone: pending.newPhone, current_password: pending.currentPassword });
    pending.devOtp = r.dev_otp || null; pending.resendAt = Date.now() + OTP_LIFETIME_MS; render(true); toast('New code sent');
  }, el);

  /* ---------------- M1: delete account ---------------- */
  ACTS.delgo = async () => {
    try {
      await api('DELETE', '/users/me', { password: val('pw') });
      endSession(false); toast('Account and data deleted'); setTimeout(() => go('S-04'), 800);
    } catch (e) { VS['S-15'] = 'default'; render(true); showErr(e.message); }
  };

  /* ---------------- M1: home ---------------- */
  const s17 = SCREENS['S-17'], s17render = s17.render;
  s17.render = ctx => { const h = s17render(ctx); return ST.me ? h.replace(/(<span class="avatar">)[^<]*(<\/span>)/, `$1${esc(initials(ST.me.full_name))}$2`) : h; };

  /* ---------------- sections cache (M3) ---------------- */
  const compUi = { yes: 'yes', with_court_permission: 'court', no: 'no' };
  function cacheSection(r, full) {
    const id = (r.law + '-' + r.section_number).toLowerCase();
    const x = {
      id, law: r.law, no: r.section_number, title: r.title, kind: r.kind, bailable: r.bailable, cognizable: r.cognizable,
      comp: compUi[r.compoundable] || 'no', punishment: r.punishment || '', triable: r.triable_by || '', text: r.text_en || '',
      source: r.source_ref || '', version: r.version || '', reviewed: r.reviewed_by_advisor, full: !!full,
    };
    const i = SECTIONS.findIndex(s => s.id === id);
    if (i >= 0) { if (full || !SECTIONS[i].full) SECTIONS[i] = x; } else SECTIONS.push(x);
    return id;
  }
  const notCovered = () => `<div class="card center" style="align-items:center;text-align:center"><div class="iconbig" style="width:64px;height:64px">${ic('info', 32)}</div><div class="t-title3">${t('Not covered by LegalShield yet')}</div><div class="t-body c-2">${t('This first release covers the PPC and CrPC only. Special laws such as narcotics, arms, anti-terrorism and PECA are not included.')}</div>${btn('Ask a lawyer', { type: 'secondary', go: 'S-32', icon: 'people' })}</div>`;
  const skeleton = () => Array.from({ length: 3 }, () => '<div class="card" style="height:96px;opacity:.5"></div>').join('');

  /* ---------------- M3: section search ---------------- */
  const paintResults = () => {
    const box = document.getElementById('res'); if (!box) return;
    if (ST.secLoading) { box.innerHTML = skeleton(); return; }
    if (ST.secResults === null) { box.innerHTML = `<div class="t-body c-2 center" style="padding:16px">${t('Type a section number or keyword to start.')}</div>`; return; }
    box.innerHTML = ST.secResults.length ? `<div class="stack g8">${ST.secResults.map(secCard).join('')}</div>` : notCovered();
  };
  let searchTimer, searchSeq = 0;
  const runSearch = () => {
    clearTimeout(searchTimer);
    const q = (ST.q || '').trim();
    if (!q) { ST.secResults = null; ST.secLoading = false; paintResults(); return; }
    ST.secLoading = true; paintResults();
    const seq = ++searchSeq;
    searchTimer = setTimeout(async () => {
      try {
        const law = ST.law && ST.law !== 'All' ? '&law=' + ST.law : '';
        const j = await api('GET', `/sections/search?q=${encodeURIComponent(q)}${law}&lang=${LANG[ST.lang]}&limit=25`);
        if (seq !== searchSeq) return;
        ST.secResults = j.results.map(r => { const id = cacheSection(r, false); return SECTIONS.find(s => s.id === id); });
      } catch (e) { if (seq !== searchSeq) return; ST.secResults = []; toast(e.message); }
      ST.secLoading = false; paintResults();
    }, 250);
  };
  const s19 = SCREENS['S-19'];
  s19.mount = () => {
    const i = document.getElementById('q'); if (!i) return;
    i.addEventListener('input', () => { ST.q = i.value; runSearch(); });
    paintResults();
  };
  ACTS.lawf = el => { ST.law = el.dataset.v; render(true); runSearch(); };

  /* ---------------- M3: section detail ---------------- */
  const s20 = SCREENS['S-20'], s20render = s20.render;
  s20.render = ctx => {
    const id = (ctx.q.id || '').toLowerCase(); const x = SECTIONS.find(s => s.id === id);
    if (!x || !x.full) {
      if (ctx.s === 'not covered' || ST.missing === id) return s20render({ ...ctx, s: 'not covered' });
      const [law, ...rest] = id.split('-'); const no = rest.join('-');
      api('GET', `/sections/${encodeURIComponent(law)}/${encodeURIComponent(no)}?lang=${LANG[ST.lang]}`).then(j => {
        if (j.covered) cacheSection(j.section, true); else ST.missing = id;
        if (cur().id === 'S-20' && (cur().q.id || '').toLowerCase() === id) render(true);
      }).catch(e => { toast(e.message); ST.missing = id; if (cur().id === 'S-20') render(true); });
      return page({ bar: appbar({ title: 'Section', back: true }), body: skeleton() });
    }
    let h = s20render({ ...ctx, s: 'auto' });
    const src = `${t('Source')}: ${esc(x.source || 'n/a')} | v${esc(x.version || '')}`;
    h = h.replace(/<div class="t-cap c-3">[^<]*Prototype sample data[^<]*<\/div>/, `<div class="t-cap c-3">${src}</div>`);
    if (x.reviewed === false) h = h.replace(/(<div class="body[^"]*">)/, `$1${banner('warning', 'Development data: this record has not been reviewed by a legal advisor.')}`);
    return h;
  };

  /* ---------------- M2: assistant ---------------- */
  const ACTION_LABELS = { guide: ['Know your rights', 'book'], template: ['Make a document', 'doc'], sos: ['Send an SOS', 'alert'], directory: ['Find a lawyer', 'people'], section: ['View section', 'search'] };
  const actionTarget = a => ({
    guide: 'S-42?id=' + a.target, template: 'S-30?id=' + a.target, sos: 'S-21', directory: 'S-32',
    section: 'S-20?id=' + String(a.target).toLowerCase().replace(/\s+/g, '-'),
  }[a.type]);
  const ACTION_NAMES = { 'lawful-arrest-steps': 'Lawful arrest steps', 'bail-process-overview': 'Bail roadmap', 'fir-application': 'FIR application', 'harassment-complaint': 'Harassment complaint', 'illegal-detention-notice': 'Illegal detention notice', 'habeas-corpus-draft': 'Habeas corpus draft' };
  function toAiMsg(r) {
    if (r.refused) return { from: 'ai', kind: 'ref', text: r.answer };
    const cites = (r.citations || []).map(c => cacheSection({ law: c.law, section_number: c.section_number, title: c.title, kind: 'offence' }, false));
    const actions = (r.suggested_actions || []).filter(a => actionTarget(a)).map(a => {
      const [label, icon] = ACTION_LABELS[a.type]; return [ACTION_NAMES[a.target] || label, icon, actionTarget(a)];
    });
    return { from: 'ai', text: r.answer, cites, actions, raw: true };
  }
  async function ask() {
    const messages = ST.chat.filter(m => (m.from === 'user' || (m.from === 'ai' && m.kind !== 'error' && m.kind !== 'ref'))).slice(-10)
      .map(m => ({ role: m.from === 'user' ? 'user' : 'assistant', content: String(m.text).slice(0, 1000) }));
    while (messages.length && messages[0].role !== 'user') messages.shift();
    ST.typing = true; render(true);
    try {
      const r = await api('POST', '/chat/messages', { messages });
      ST.chat.push(toAiMsg(r));
    } catch (e) {
      ST.chat.push(e.code === 'CHAT_RATE_LIMITED' ? { from: 'ai', kind: 'ref', text: e.message } : { from: 'ai', kind: 'error', text: e.code === 'LLM_UNAVAILABLE' || e.code === 'NETWORK' ? e.message : 'The assistant is unavailable right now. Please try again.' });
    }
    ST.typing = false;
    if (cur().id === 'S-18') { render(false); const b = document.querySelector('.body'); if (b) b.scrollTop = b.scrollHeight; }
  }
  ACTS.send = () => {
    if (ST.typing) return;
    const inp = document.getElementById('msg'); const v = ((inp && inp.value) || '').trim(); if (!v) return;
    if (v.length > 1000) { toast('Please keep your question under 1000 characters.'); return; }
    ST.chat.push({ from: 'user', text: v }); ask();
  };
  ACTS.retry = () => { if (ST.chat.length && ST.chat[ST.chat.length - 1].kind === 'error') ST.chat.pop(); ask(); };
  // the live chat view never shows the prototype's canned states in app mode
  const s18 = SCREENS['S-18'];
  if (!PROTO) s18.states = ['live'];
})();
