const CACHE_PREFIX = 'thoradar-shell-';
const CACHE_NAME = `${CACHE_PREFIX}v1`;
const SHELL_URL = new URL('/index.html', self.location.origin).href;
const DATA_START = '/*__THORADAR_DATA_START__*/';
const DATA_END = '/*__THORADAR_DATA_END__*/';
const statuses = new Map();
let refreshTail = Promise.resolve();

async function fetchShell(url) {
  const response = await fetch(url, {
    cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(8000)
  });
  const mime = response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase();
  if (response.status !== 200 || response.type !== 'basic' || mime !== 'text/html') return null;

  const html = await response.clone().text();
  const start = html.indexOf(DATA_START);
  const dataStart = start + DATA_START.length;
  const end = html.indexOf(DATA_END, dataStart);
  if (start === -1 || end === -1 ||
      !html.trimEnd().toLowerCase().endsWith('</html>')) return null;

  const block = html.slice(dataStart, end).trim();
  const declaration = /^const\s+SITE_DATA\s*=\s*(\{[\s\S]*\})\s*;?$/.exec(block);
  if (!declaration) return null;
  try {
    const data = JSON.parse(declaration[1]);
    if (typeof data.briefing_date !== 'string' || !Array.isArray(data.papers)) return null;
  } catch (_) {
    return null;
  }
  return { response, html };
}

async function checkForUpdate(cache, url, displayed) {
  try {
    const fresh = await fetchShell(url);
    if (!fresh) return 'unavailable';
    const stored = await cache.match(SHELL_URL);
    if (!stored || await stored.text() !== fresh.html) await cache.put(SHELL_URL, fresh.response);
    return displayed && await displayed.text() !== fresh.html ? 'updated' : 'current';
  } catch (_) {
    return 'unavailable';
  }
}

function remember(clientId, status) {
  if (!clientId) return;
  statuses.delete(clientId);
  statuses.set(clientId, status);
  if (statuses.size > 64) statuses.delete(statuses.keys().next().value);
}

function sendStatus(client, status) {
  client?.postMessage({ type: 'thoradar-shell-state', status });
}

self.addEventListener('message', event => {
  if (event.data?.type !== 'thoradar-shell-status' || event.source?.type !== 'window') return;
  sendStatus(event.source, statuses.get(event.source.id) || 'unavailable');
});

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await checkForUpdate(cache, SHELL_URL);
  })().catch(() => {}));
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
      .map(name => caches.delete(name)));
  })().catch(() => {}));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || request.mode !== 'navigate') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || (url.pathname !== '/' && url.pathname !== '/index.html')) return;
  // A single test opt-in is cacheable. Other query variants retain native navigation.
  if (url.search && !(url.searchParams.size === 1 && url.searchParams.get('sw') === '1')) return;

  const clientId = event.resultingClientId || event.clientId;
  const lookup = (async () => {
    const cache = await caches.open(CACHE_NAME);
    const page = await cache.match(SHELL_URL);
    return { cache, page, displayed: page?.clone() };
  })().catch(() => null);

  event.respondWith(lookup.then(entry => {
    remember(clientId, entry?.page ? 'checking' : entry ? 'network' : 'fallback');
    if (entry?.page) return entry.page;
    return fetch(request);
  }));

  // Keep writes ordered when multiple tabs ask for a check. Cache hits never wait for this queue.
  const refresh = refreshTail.then(async () => {
    const entry = await lookup;
    if (!entry) return;
    let status = await checkForUpdate(entry.cache, request.url, entry.displayed);
    if (!clientId) return;
    if (!entry.displayed) {
      if (status !== 'unavailable') return;
      status = 'fallback';
    }
    remember(clientId, status);
    sendStatus(await self.clients.get(clientId), status);
  });
  refreshTail = refresh.catch(() => {});
  event.waitUntil(refreshTail);
});
