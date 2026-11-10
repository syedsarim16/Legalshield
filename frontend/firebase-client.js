/* Firebase Web SDK adapter. Authentication state is persisted in IndexedDB. */
(() => {
  const SDK = 'https://www.gstatic.com/firebasejs/10.14.1/';
  let config = { enabled: false };
  let app = null;
  let auth = null;
  let firestore = null;
  let sdk = null;

  const ready = (async () => {
    const response = await fetch('/api/v1/firebase/config');
    if (!response.ok) throw new Error('Firebase configuration could not be loaded.');
    config = await response.json();
    if (!config.enabled) throw new Error('Firebase is not configured for this application.');

    const [appSdk, authSdk, storeSdk] = await Promise.all([
      import(SDK + 'firebase-app.js'),
      import(SDK + 'firebase-auth.js'),
      import(SDK + 'firebase-firestore.js'),
    ]);
    sdk = { ...appSdk, ...authSdk, ...storeSdk };
    app = sdk.initializeApp(config);
    auth = sdk.getAuth(app);
    await sdk.setPersistence(auth, sdk.indexedDBLocalPersistence);
    firestore = sdk.getFirestore(app);
    return { ...config, ready: true };
  })();

  async function token(forceRefresh = false) {
    await ready;
    return auth.currentUser ? sdk.getIdToken(auth.currentUser, forceRefresh) : null;
  }

  async function currentUser() {
    await ready;
    return auth.currentUser;
  }

  async function initialAuthState() {
    await ready;
    return new Promise(resolve => {
      const unsubscribe = sdk.onAuthStateChanged(auth, user => {
        unsubscribe();
        resolve(user);
      });
    });
  }

  async function signInWithCustomToken(customToken) {
    await ready;
    const result = await sdk.signInWithCustomToken(auth, customToken);
    await sdk.getIdToken(result.user, true);
    return result;
  }

  async function signInWithEmailAndPassword(email, password) {
    await ready;
    return sdk.signInWithEmailAndPassword(auth, email, password);
  }

  async function signOut() {
    await ready;
    await sdk.signOut(auth);
  }

  async function loadPreferences() {
    await ready;
    if (!auth.currentUser) return null;
    const idToken = await sdk.getIdToken(auth.currentUser);
    const response = await fetch('/api/v1/users/me/preferences', {
      headers: { Authorization: 'Bearer ' + idToken },
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error?.message || 'Account preferences could not be loaded.');
    return result;
  }

  async function savePreferences(preferences) {
    await ready;
    if (!auth.currentUser) return;
    const idToken = await sdk.getIdToken(auth.currentUser);
    const response = await fetch('/api/v1/users/me/preferences', {
      method: 'PUT',
      headers: { Authorization: 'Bearer ' + idToken, 'Content-Type': 'application/json' },
      body: JSON.stringify(preferences),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error?.message || 'Account preferences could not be saved.');
  }

  async function requestMessagingToken() {
    await ready;
    if (!config.vapidKey || !('Notification' in window)) return null;
    const permission = Notification.permission === 'default'
      ? await Notification.requestPermission()
      : Notification.permission;
    if (permission !== 'granted') return null;
    const registration = 'serviceWorker' in navigator
      ? await navigator.serviceWorker.register('/app/firebase-messaging-sw.js', { scope: '/app/' })
      : undefined;
    const messagingSdk = await import(SDK + 'firebase-messaging.js');
    const messaging = messagingSdk.getMessaging(app);
    return messagingSdk.getToken(messaging, {
      vapidKey: config.vapidKey,
      serviceWorkerRegistration: registration,
    });
  }

  window.LegalShieldFirebase = {
    ready,
    token,
    currentUser,
    initialAuthState,
    signInWithCustomToken,
    signInWithEmailAndPassword,
    signOut,
    loadPreferences,
    savePreferences,
    requestMessagingToken,
    onAuthStateChanged(callback) {
      return ready.then(() => sdk.onAuthStateChanged(auth, callback));
    },
    available: () => !!auth,
    firestore: () => firestore,
    app: () => app,
  };
})();
