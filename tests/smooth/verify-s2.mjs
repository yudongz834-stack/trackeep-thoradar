import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { arch, release, tmpdir, version } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { ROOT, chromeArgs, connect, gitRead, sha256, sleep } from '../aicls/lib.mjs';

const [output, mutation = 'none'] = process.argv.slice(2);
if (!output || !['none', 'no-retire-cleanup'].includes(mutation)) {
  throw new Error('Usage: node tests/smooth/verify-s2.mjs <result.json> [none|no-retire-cleanup]');
}
const result = {
  startedAt: new Date().toISOString(), runs: 1, seed: null, mutation,
  baseline: gitRead(['rev-parse', 'HEAD']).trim(),
  environment: { os: version(), release: release(), arch: arch(), node: process.version },
  checks: [], requests: [], documents: [], errors: []
};
const html = await readFile(join(ROOT, 'index.html'), 'utf8');
const worker = await readFile(join(ROOT, 'sw.js'), 'utf8');
const retire = await readFile(join(ROOT, 'sw-retire.js'), 'utf8');
result.sha256 = {
  'index.html': sha256(html), 'sw.js': sha256(worker), 'sw-retire.js': sha256(retire),
  'tests/smooth/verify-s2.mjs': sha256(await readFile(new URL(import.meta.url)))
};

function replaceOnce(source, anchor, value) {
  const pos = source.indexOf(anchor);
  if (pos < 0 || source.indexOf(anchor, pos + anchor.length) !== -1) throw new Error('Fixture anchor: ' + anchor);
  return source.slice(0, pos) + value + source.slice(pos + anchor.length);
}

const header = /const SITE_DATA = \{"generated_at":"(\d{4}-\d\d-\d\d)([^"]*)","briefing_date":"(\d{4}-\d\d-\d\d)"/.exec(html);
if (!header) throw new Error('Missing official date fixture anchor');
const v1 = { date: header[3], html, hash: sha256(html) };
function edition(offset, padding = 0) {
  const day = new Date(v1.date + 'T00:00:00Z');
  day.setUTCDate(day.getUTCDate() + offset);
  const date = day.toISOString().slice(0, 10);
  let body = replaceOnce(html, header[0], `const SITE_DATA = {"generated_at":"${date}${header[2]}","briefing_date":"${date}"`);
  if (padding) body = body.replace(/<\/html>\s*$/i, '<!--' + 'x'.repeat(padding) + '--></html>');
  return { date, html: body, hash: sha256(body) };
}
const v2 = edition(1);
const v3 = edition(2, 200_000);
result.fixtures = [v1, v2, v3].map(({ date, hash, html }) => ({ date, hash, bytes: Buffer.byteLength(html) }));
const retireSource = mutation === 'no-retire-cleanup'
  ? replaceOnce(retire, "      await Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX)).map(name => caches.delete(name)));", '')
  : retire;
result.retireResponseSha256 = sha256(retireSource);

let scenario = '';
let shell = 'v1';
let script = 'regular';
let archive = 'unavailable';
let staleCanonical = false;
const htmlMime = 'text/html; charset=utf-8';
const endpoints = {
  v1: { body: v1.html }, v2: { body: v2.html }, v3: { body: v3.html },
  '404': { status: 404, body: v3.html },
  '500': { status: 500, body: v3.html },
  'auth-html': { body: '<!doctype html><html><head><title>Sign in</title></head><body>Authentication required</body></html>' },
  'auth-redirect': { status: 302, body: '', location: '/auth-return' },
  truncated: { body: v3.html.replace(/<\/html>\s*$/i, '') },
  'missing-start': { body: replaceOnce(v3.html, '/*__THORADAR_DATA_START__*/', '/* start missing */') },
  'missing-end': { body: replaceOnce(v3.html, '/*__THORADAR_DATA_END__*/', '/* end missing */') },
  'wrong-mime': { body: v3.html, mime: 'text/plain; name=text/html' },
  '203': { status: 203, body: v3.html },
  timeout: { body: v3.html, delay: 9000 }
};
const site = createServer((req, res) => {
  const { pathname, search } = new URL(req.url, 'http://127.0.0.1');
  const row = { scenario, url: req.url, method: req.method, startMs: Date.now(),
    pragma: req.headers.pragma ?? null, cacheControl: req.headers['cache-control'] ?? null };
  result.requests.push(row);
  function reply(status, mime, body, headers = {}) {
    row.status = status;
    row.mime = mime;
    res.once('finish', () => { row.finishedMs = Date.now(); });
    res.once('close', () => { if (!res.writableFinished) row.disconnectedMs = Date.now(); });
    res.writeHead(status, { 'Content-Type': mime, 'Cache-Control': 'no-store', ...headers });
    res.end(body);
  }
  if (pathname === '/sw.js' || pathname === '/sw-retire.js') {
    row.version = pathname === '/sw-retire.js' ? 'retire-file' : script;
    const source = {
      regular: worker,
      update: worker + '\n// Local HTTP fixture forces an update at the existing registration URL.\n',
      retire: retireSource,
      'retire-file': retireSource,
      'blocked-cache': "Object.defineProperty(self, 'caches', { get() { throw new DOMException('Storage blocked by test', 'SecurityError'); } });\n" + worker
    }[row.version];
    return reply(200, 'text/javascript', source);
  }
  if (pathname === '/data/radar_latest.json') {
    row.version = archive;
    return reply(archive === 'available' ? 200 : 503, 'application/json', archive === 'available' ? '{"papers":[]}' : '{}');
  }
  if (pathname === '/auth-return') return reply(200, htmlMime, v3.html);
  if (pathname === '/quota-setup') return reply(200, htmlMime, '<!doctype html><title>CDP quota setup</title>');
  if (pathname !== '/' && pathname !== '/index.html') return reply(404, 'text/plain', 'not found');
  row.version = shell;
  if (shell === 'offline') {
    row.destroyedSocket = true;
    req.socket.destroy();
    return;
  }
  const { body, status = 200, mime = htmlMime, location, delay } = endpoints[shell];
  const headers = location ? { Location: location } : {};
  if (staleCanonical && search === '') headers['Cache-Control'] = 'public, max-age=3600';
  const send = () => reply(status, mime, body, headers);
  if (delay) {
    const timer = setTimeout(send, delay);
    res.once('close', () => {
      clearTimeout(timer);
      if (!res.writableFinished) row.disconnectedMs = Date.now();
    });
  } else send();
});

async function until(label, test, timeout = 14_000) {
  const deadline = Date.now() + timeout;
  do {
    const value = await test();
    if (value) return value;
    await sleep(35);
  } while (Date.now() < deadline);
  throw new Error('Timed out: ' + label);
}

async function check(name, inspect) {
  let evidence;
  try { evidence = await inspect(); }
  catch (error) {
    console.error(name + ' ' + error.stack);
    evidence = { pass: false, error: String(error) };
  }
  const { pass, ...detail } = evidence;
  result.checks.push({ name, pass: !!pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name} ${JSON.stringify(detail)}`);
}

let cdp;
let origin;
const sessions = new Map();

async function withPage(label, run, { mobile = false, beforeDocument } = {}) {
  scenario = label;
  shell = 'v1';
  script = 'regular';
  archive = 'unavailable';
  staleCanonical = false;
  const { browserContextId } = await cdp.send('Target.createBrowserContext');
  let session;
  try {
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank', browserContextId });
    ({ sessionId: session } = await cdp.send('Target.attachToTarget', { targetId, flatten: true }));
    sessions.set(session, label);
    const send = (method, args = {}) => cdp.send(method, args, session);
    for (const domain of ['Page', 'Runtime', 'Network', 'ServiceWorker']) await send(domain + '.enable');
    await send('Emulation.setDeviceMetricsOverride', {
      width: mobile ? 390 : 1440, height: mobile ? 844 : 900, deviceScaleFactor: 1, mobile
    });
    if (beforeDocument) await send('Page.addScriptToEvaluateOnNewDocument', { source: beforeDocument });
    async function evaluate(fn, ...args) {
      const { result: value, exceptionDetails } = await send('Runtime.evaluate', {
        expression: `(${fn})(${args.map(arg => JSON.stringify(arg)).join(',')})`,
        awaitPromise: true, returnByValue: true
      });
      if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
      return value.value;
    }
    const snapshot = () => evaluate(() => {
      const describe = id => {
        const el = document.getElementById(id);
        const box = el?.getBoundingClientRect();
        return { text: el?.textContent ?? null, visible: !!(box && box.height > 0 && box.left >= 0 && box.right <= innerWidth && box.bottom <= innerHeight) };
      };
      return {
        date: SITE_DATA.briefing_date, points: document.querySelectorAll('#blips .blip').length,
        status: describe('shell-status'), warning: describe('window-hint'),
        view: document.body.dataset.protoView, timeOrigin: performance.timeOrigin, viewport: [innerWidth, innerHeight],
        days: state.days, papers: PAPERS.length, selected: state.selected
      };
    });
    const storage = () => evaluate(async () => {
      let registrations = [];
      let controller = null;
      try {
        registrations = await navigator.serviceWorker?.getRegistrations() || [];
        controller = navigator.serviceWorker?.controller?.scriptURL ?? null;
      } catch (_) {}
      const report = { registrations: registrations.length, active: registrations[0]?.active?.state ?? null,
        waiting: registrations[0]?.waiting?.state ?? null, controller };
      try {
        const names = await window.caches?.keys() || [];
        const name = names.find(value => value.startsWith('thoradar-shell-'));
        const cache = name && await caches.open(name);
        const paths = cache ? (await cache.keys()).map(request => new URL(request.url).pathname) : [];
        const page = cache && await cache.match('/index.html');
        const hash = page ? Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await page.arrayBuffer())),
          byte => byte.toString(16).padStart(2, '0')).join('') : null;
        return { ...report, names, paths, hash };
      } catch (error) { return { ...report, storageError: error.name }; }
    });
    async function navigate(path) {
      const url = origin + path;
      const { errorText, loaderId } = await send('Page.navigate', { url });
      if (errorText) throw new Error('Navigate ' + path + ': ' + errorText);
      const doc = await until('document response ' + path, () =>
        result.documents.find(row => row.session === label && row.loaderId === loaderId && row.url === url));
      await until('radar ready ' + path, async () => {
        try {
          return await evaluate(url => location.href === url && document.readyState === 'complete' &&
            document.body.dataset.protoReady === 'true', url);
        } catch (error) {
          if (!/context|navigat/i.test(error.message)) throw error;
          return false;
        }
      });
      return { doc, page: await snapshot() };
    }
    const status = part => until('banner ' + part, async () => {
      const page = await snapshot();
      return page.status.text?.includes(part) && page;
    });
    const warm = async (hash = v1.hash) => {
      const first = await navigate('/index.html?sw=1');
      await until('activated healthy cache', async () => {
        const saved = await storage();
        return saved.active === 'activated' && saved.hash === hash && saved;
      });
      return first;
    };
    await run({ send, evaluate, snapshot, storage, navigate, status, warm });
  } finally {
    if (session) sessions.delete(session);
    await cdp.send('Target.disposeBrowserContext', { browserContextId });
  }
}

const isCached = nav => nav.doc.source === 'cache-storage';
const notShellCache = nav => nav.doc.source !== 'cache-storage' && nav.page.points > 0;
const storageHealthy = (saved, hash) => saved.hash === hash && saved.paths?.join(',') === '/index.html';
const requestsSince = cursor => result.requests.slice(cursor).filter(row => row.scenario === scenario);

async function verifyMatrix() {
  await withPage('response-matrix', async page => {
    await page.warm();
    for (const variant of [
      'offline', '404', '500', 'auth-html', 'auth-redirect', 'truncated',
      'missing-start', 'missing-end', 'wrong-mime', '203', 'timeout'
    ]) {
      await check('healthy-cache-rejects-' + variant, async () => {
        shell = variant;
        const offset = result.requests.length;
        if (variant === 'offline') await page.send('Network.emulateNetworkConditions', {
          offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0
        });
        try {
          let nav;
          let emulationNavigationError = null;
          try { nav = await page.navigate('/index.html'); }
          catch (error) {
            if (variant !== 'offline') throw error;
            emulationNavigationError = String(error);
            await page.send('Network.emulateNetworkConditions', {
              offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1
            });
            nav = await page.navigate('/index.html');
          }
          const visible = await page.status('暂未核实更新');
          const saved = await page.storage();
          const upstream = requestsSince(offset).filter(row => row.version === variant);
          const offline = variant === 'offline' ? await page.evaluate(() => !navigator.onLine) : null;
          const rejected = variant === 'offline' ? (upstream.length ? upstream.every(row => row.destroyedSocket) : offline)
            : variant === 'timeout' ? upstream.some(row => !!row.disconnectedMs || !row.finishedMs)
            : upstream.some(row => row.status === (endpoints[variant].status ?? 200));
          return { pass: isCached(nav) && visible.date === v1.date && visible.status.visible && rejected &&
            storageHealthy(saved, v1.hash), nav, visible, saved, upstream, offline, emulationNavigationError };
        } finally {
          if (variant === 'offline') await page.send('Network.emulateNetworkConditions', {
            offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1
          });
        }
      });
    }
    await check('socket-disconnect-fallback-actually-reaches-server', async () => {
      shell = 'offline';
      const offset = result.requests.length;
      const nav = await page.navigate('/');
      const visible = await page.status('暂未核实更新');
      const saved = await page.storage();
      const upstream = requestsSince(offset);
      return { pass: isCached(nav) && visible.status.visible && storageHealthy(saved, v1.hash) &&
        upstream.some(row => row.url === '/' && row.destroyedSocket), nav, visible, saved, upstream };
    });
  });
}

async function verifyInstall() {
  await withPage('install-update', async page => {
    await page.warm();
    await page.navigate('/');
    await page.status('与服务器一致');
    await page.evaluate(() => document.querySelector('#proto-tab-reading').click());
    const before = await page.snapshot();
    await check('install-updates-existing-healthy-copy', async () => {
      script = 'update';
      shell = 'v2';
      const offset = result.requests.length;
      await page.evaluate(async () => { await (await navigator.serviceWorker.getRegistration()).update(); });
      const saved = await until('waiting worker refreshed the existing shell', async () => {
        const value = await page.storage();
        return value.waiting === 'installed' && value.hash === v2.hash && value;
      });
      const after = await page.snapshot();
      const upstream = requestsSince(offset);
      return { pass: storageHealthy(saved, v2.hash) && before.timeOrigin === after.timeOrigin && before.date === after.date &&
        after.view === 'reading' && before.selected === after.selected &&
        upstream.some(row => row.url === '/index.html' && row.pragma === 'no-cache'), before, after, saved, upstream };
    });
  });
}

async function quotaState(page, quota, bytes = 800_000) {
  if (quota !== undefined) await page.send('Storage.overrideQuotaForOrigin', { origin, quotaSize: quota });
  const browserQuota = await page.send('Storage.getUsageAndQuota', { origin });
  const result = await page.evaluate(async bytes => {
    const estimate = await navigator.storage.estimate();
    const cache = await caches.open('s2-quota-probe');
    let write = 'ok';
    try {
      await cache.put('/quota-probe', new Response(new Uint8Array(bytes)));
    } catch (error) { write = error.name; }
    await caches.delete('s2-quota-probe');
    return { estimate, write };
  }, bytes);
  return { overrideBytes: quota, probeBytes: bytes, browserQuota, ...result };
}

async function verifyQuota() {
  await withPage('low-quota', async page => {
    await page.warm();
    await page.navigate('/');
    await page.status('与服务器一致');
    await check('low-quota-native-write-fails-but-preserves-healthy-copy', async () => {
      const probe = await quotaState(page, Buffer.byteLength(v1.html) + 65_536);
      const offset = result.requests.length;
      shell = 'v3';
      const nav = await page.navigate('/');
      const visible = await page.status('暂未核实更新');
      const saved = await page.storage();
      const upstream = requestsSince(offset);
      return { pass: probe.write === 'QuotaExceededError' && isCached(nav) && visible.status.visible &&
        storageHealthy(saved, v1.hash) && upstream.some(row => row.version === 'v3' && row.status === 200),
      probe, nav, visible, saved, upstream };
    });
  });
  await withPage('zero-quota', async page => {
    await check('zero-quota-cold-start-keeps-native-site-usable', async () => {
      await page.send('Page.navigate', { url: origin + '/quota-setup' });
      await until('same-origin quota setup loaded', () => page.evaluate(() =>
        location.pathname === '/quota-setup' && document.readyState === 'complete'));
      // Chrome on this host accepts a literal zero override but can still write.
      // A one-byte cap gives the installed worker zero writable bytes.
      await page.send('Storage.overrideQuotaForOrigin', { origin, quotaSize: 1 });
      const first = await page.navigate('/index.html?sw=1');
      await until('cold worker finishes attempted install', async () => (await page.storage()).active === 'activated');
      const probe = await quotaState(page, 1, 1);
      const next = await page.navigate('/');
      const visible = await page.status('本地副本不可用').catch(() => page.snapshot());
      const saved = await page.storage();
      return { pass: probe.write === 'QuotaExceededError' && probe.browserQuota.overrideActive &&
        probe.browserQuota.usage >= probe.browserQuota.quota && !first.doc.fromServiceWorker && notShellCache(first) &&
        notShellCache(next) && visible.status.visible && visible.status.text.includes('本地副本不可用') && !saved.hash,
      probe, first, next, visible, saved };
    });
  });
}

async function chooseDays(page, days) {
  await page.evaluate(async days => {
    const slider = document.getElementById('window-range');
    slider.value = String(days);
    slider.dispatchEvent(new Event('input', { bubbles: true }));
    await rollingPromise;
  }, days);
}

async function verifyArchive(page, name) {
  await check(name, async () => {
    const offset = result.requests.length;
    const before = await page.snapshot();
    await chooseDays(page, 7);
    const initial = await page.snapshot();
    await sleep(6200);
    await page.evaluate(() => document.getElementById('proto-tab-reading').click());
    const persistent = await page.snapshot();
    await page.evaluate(() => document.getElementById('lang-btn').click());
    const translated = await page.snapshot();
    await page.evaluate(() => document.getElementById('lang-btn').click());
    await chooseDays(page, 1);
    const single = await page.snapshot();
    await chooseDays(page, 7);
    const retry = await page.snapshot();
    archive = 'available';
    await chooseDays(page, 8);
    const recovered = await page.snapshot();
    const saved = await page.storage();
    const upstream = requestsSince(offset).filter(row => row.url === '/data/radar_latest.json');
    const text = `实际只显示 ${before.date} 当日副本／历史档案不可用`;
    const warnings = [initial, persistent, retry].every(item => item.warning.visible && item.warning.text === text &&
      item.papers === before.papers && item.days > 1);
    return { pass: warnings && persistent.view === 'reading' && translated.warning.visible &&
      translated.warning.text === `Showing only the ${before.date} daily copy / Historical archive unavailable` &&
      single.days === 1 && !single.warning.visible && recovered.days === 8 && !recovered.warning.visible &&
      upstream.map(row => row.status).join(',') === '503,503,200' && !saved.paths?.includes('/data/radar_latest.json'),
    before, initial, persistent, translated, single, retry, recovered, saved, upstream };
  });
}

async function verifyUnavailableApis() {
  await withPage('sw-unavailable', async page => {
    await check('service-worker-api-unavailable-keeps-native-site-usable', async () => {
      const first = await page.navigate('/index.html?sw=1');
      const snapshot = await page.status('本地副本不可用');
      const saved = await page.storage();
      return { pass: !first.doc.fromServiceWorker && notShellCache(first) && snapshot.status.visible &&
        saved.registrations === 0 && !saved.names?.length && !result.requests.some(row => row.scenario === scenario && row.url === '/sw.js'),
      first, snapshot, saved };
    });
    await verifyArchive(page, 'archive-warning-persists-with-service-worker-unavailable');
  }, { beforeDocument: "Object.defineProperty(Navigator.prototype, 'serviceWorker', { configurable: true, get() { return undefined; } });" });
  await withPage('cache-unavailable', async page => {
    await check('cache-storage-access-denied-keeps-native-site-usable', async () => {
      const first = await page.navigate('/index.html?sw=1');
      const snapshot = await page.status('本地副本不可用');
      const saved = await page.storage();
      return { pass: !first.doc.fromServiceWorker && notShellCache(first) && snapshot.status.visible &&
        saved.registrations === 0 && saved.storageError === 'SecurityError' &&
        !result.requests.some(row => row.scenario === scenario && row.url === '/sw.js'), first, snapshot, saved };
    });
  }, { beforeDocument: "Object.defineProperty(window, 'caches', { configurable: true, get() { throw new DOMException('Storage blocked by test', 'SecurityError'); } });" });
  await withPage('worker-cache-unavailable', async page => {
    await check('worker-cache-open-failure-falls-through-to-network', async () => {
      script = 'blocked-cache';
      const first = await page.navigate('/index.html?sw=1');
      await until('worker without storage activates', async () => (await page.storage()).active === 'activated');
      const next = await page.navigate('/');
      const visible = await page.status('本地副本不可用');
      const saved = await page.storage();
      return { pass: !first.doc.fromServiceWorker && notShellCache(first) && notShellCache(next) &&
        visible.status.visible && !saved.names.length, first, next, visible, saved };
    });
  });
  await withPage('archive-with-shell-mobile', async page => {
    await page.warm();
    await page.navigate('/');
    await page.status('与服务器一致');
    await verifyArchive(page, 'archive-warning-persists-with-controlled-shell-on-mobile');
  }, { mobile: true });
}

async function verifyRetirement() {
  await withPage('retirement', async page => {
    staleCanonical = true;
    await page.warm();
    await page.navigate('/');
    await page.status('与服务器一致');
    await page.evaluate(async () => {
      await caches.open('thoradar-shell-earlier-test-version');
      await caches.open('s2-unrelated-cache');
    });
    await page.evaluate(() => document.querySelector('#proto-tab-reading').click());
    const before = await page.snapshot();
    const initial = await page.storage();
    await check('retirement-cleans-prefix-unregisters-and-notifies-open-reader', async () => {
      script = 'retire';
      await page.evaluate(async () => { await (await navigator.serviceWorker.getRegistration()).update(); });
      const after = await page.status('本地副本已停用');
      const saved = await page.storage();
      return { pass: initial.names.includes('thoradar-shell-earlier-test-version') && initial.hash === v1.hash &&
        saved.registrations === 0 && saved.names.join(',') === 's2-unrelated-cache' && before.timeOrigin === after.timeOrigin &&
        before.selected === after.selected && before.date === after.date && after.view === 'reading', before, after, initial, saved };
    });
    if (mutation !== 'none') return;
    await check('post-retirement-next-open-gets-current-edition-from-origin', async () => {
      shell = 'v2';
      const offset = result.requests.length;
      const next = await page.navigate('/');
      const saved = await page.storage();
      const upstream = requestsSince(offset);
      return { pass: !next.doc.fromServiceWorker && !next.doc.fromDiskCache && next.page.date === v2.date &&
        !next.page.status.visible && !next.page.status.text && saved.registrations === 0 && !saved.controller &&
        upstream.some(row => row.url === '/' && row.version === 'v2' && row.status === 200), next, saved, upstream };
    });
    await check('reinstall-fetches-fresh-canonical-and-does-not-restore-stale-http-copy', async () => {
      shell = 'v1';
      const prime = await page.evaluate(async () => /"briefing_date":"([\d-]+)"/.exec(
        await (await fetch('/index.html', { cache: 'reload' })).text())?.[1]);
      shell = 'v2';
      script = 'regular';
      const beforeStaleRead = result.requests.length;
      const stale = await page.evaluate(async () => /"briefing_date":"([\d-]+)"/.exec(
        await (await fetch('/index.html', { cache: 'force-cache' })).text())?.[1]);
      const staleHit = !requestsSince(beforeStaleRead).some(row => row.url === '/index.html');
      const offset = result.requests.length;
      const reinstall = await page.warm(v2.hash);
      const saved = await page.storage();
      const again = await page.navigate('/');
      const verified = await page.status('与服务器一致');
      const upstream = requestsSince(offset);
      return { pass: prime === v1.date && stale === v1.date && staleHit && !reinstall.doc.fromServiceWorker &&
        reinstall.page.date === v2.date && isCached(again) && verified.date === v2.date &&
        storageHealthy(saved, v2.hash) && upstream.some(row => row.url === '/index.html' &&
          row.version === 'v2' && row.pragma === 'no-cache' && row.status === 200),
      prime, stale, staleHit, reinstall, saved, again, verified, upstream };
    });
  });
}

console.log('RUN ' + JSON.stringify(result));
let browser;
let browserExit;
let profile;
const temp = resolve(tmpdir());
const prefix = 'thoradar-sol-s2-chrome-';
try {
  await new Promise((done, fail) => {
    site.once('error', fail);
    site.listen(0, '127.0.0.1', done);
  });
  origin = 'http://127.0.0.1:' + site.address().port;
  result.origin = origin;
  profile = await mkdtemp(join(temp, prefix));
  browser = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',
    [...chromeArgs(0, profile), '--no-proxy-server'], { stdio: ['ignore', 'inherit', 'inherit'], windowsHide: true });
  browserExit = new Promise(done => {
    browser.once('error', error => done({ error: error.message }));
    browser.once('exit', (code, signal) => done({ code, signal }));
  });
  const port = await until('Chrome debugging port', async () => {
    const active = await readFile(join(profile, 'DevToolsActivePort'), 'utf8').catch(() => '');
    return active.includes('/devtools/browser/') && active.trim().split(/\r?\n/)[0];
  }, 18_000);
  const versionResponse = await fetch('http://127.0.0.1:' + port + '/json/version').then(response => response.json());
  cdp = await connect(versionResponse.webSocketDebuggerUrl);
  result.environment.chrome = await cdp.send('Browser.getVersion');
  console.log('BROWSER ' + JSON.stringify(result.environment.chrome));
  cdp.on('Network.responseReceived', ({ type, loaderId, response }, session) => {
    if (!sessions.has(session) || type !== 'Document' || !response.url.startsWith(origin + '/')) return;
    result.documents.push({ session: sessions.get(session), url: response.url, loaderId, status: response.status,
      fromServiceWorker: response.fromServiceWorker, fromDiskCache: response.fromDiskCache,
      source: response.serviceWorkerResponseSource ?? null });
  });
  cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }, session) => {
    if (sessions.has(session)) result.errors.push({ session: sessions.get(session), kind: 'page',
      message: exceptionDetails.exception?.description ?? exceptionDetails.text });
  });
  cdp.on('ServiceWorker.workerErrorReported', ({ errorMessage }, session) => {
    if (sessions.has(session)) result.errors.push({ session: sessions.get(session), kind: 'worker', errorMessage });
  });
  if (mutation === 'none') {
    for (const scenarioTest of [verifyMatrix, verifyInstall, verifyQuota, verifyUnavailableApis]) {
      try { await scenarioTest(); }
      catch (error) { await check(scenarioTest.name + '-completed', () => { throw error; }); }
    }
  }
  await verifyRetirement();
  await check('no-uncaught-page-or-worker-errors', () => ({ pass: !result.errors.length, errors: result.errors }));
} catch (error) {
  await check('harness-completed', () => { throw error; });
} finally {
  try {
    if (cdp) await cdp.send('Browser.close');
  } catch (error) { console.error('Browser.close: ' + error.message); }
  cdp?.close();
  if (browser) {
    let exit = await Promise.race([browserExit, sleep(5000).then(() => null)]);
    const forced = !exit && !!browser.pid && browser.kill();
    if (!exit) exit = await Promise.race([browserExit, sleep(5000).then(() => null)]);
    result.cleanup = { pid: browser.pid, exit, forced, profileRemoved: false };
  }
  if (site.listening) await new Promise(done => {
    site.close(done);
    site.closeAllConnections();
  });
  if (profile && dirname(resolve(profile)) === temp && basename(profile).startsWith(prefix)) {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    result.cleanup.profileRemoved = true;
  }
  console.log('CLEANUP ' + JSON.stringify(result.cleanup));
  result.endedAt = new Date().toISOString();
  result.summary = { passed: result.checks.filter(row => row.pass).length, failed: result.checks.filter(row => !row.pass).length };
  await writeFile(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log('SUMMARY ' + JSON.stringify(result.summary));
  if (result.summary.failed) process.exitCode = 1;
}
