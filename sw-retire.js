const CACHE_PREFIX = 'thoradar-shell-';

self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    let cleared = false;
    try {
      const names = await caches.keys();
      await Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX)).map(name => caches.delete(name)));
      cleared = true;
    } catch (_) {
      // Cache Storage can be blocked. Still release control of the site.
    }
    const unregistered = await self.registration.unregister().catch(() => false);
    const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clients) {
      client.postMessage({ type: 'thoradar-shell-retired', cleared, unregistered });
    }
  })());
});
