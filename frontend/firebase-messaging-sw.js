/* Firebase Cloud Messaging worker. The public client config is fetched from
   the same endpoint as the app so it never contains server credentials. */
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

fetch('/api/v1/firebase/config')
  .then(response => response.json())
  .then(config => {
    if (!config.enabled) return;
    firebase.initializeApp(config);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage(payload => {
      const notification = payload.notification || {};
      return self.registration.showNotification(notification.title || 'LegalShield', {
        body: notification.body || 'You have a new LegalShield update.',
        data: payload.data || {},
      });
    });
  })
  .catch(() => {});
