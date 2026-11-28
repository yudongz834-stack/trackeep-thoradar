import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { arch, release, tmpdir, version as osVersion } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { ROOT, chromeArgs, connect, gitRead, sha256, sleep } from '../aicls/lib.mjs';

const [output, mutation = 'none'] = process.argv.slice(2);
if (!output || !['none', 'no-local-return', 'allow-truncated'].includes(mutation)) {
  throw new Error('Usage: node tests/smooth/verify-s1.mjs <result.json> [none|no-local-return|allow-truncated]');
}
const result = {
  source: 'Worktree index.html and sw.js served over loopback to Google Chrome via CDP',
  startedAt: new Date().toISOString(),
  baselineCommit: gitRead(['rev-parse', 'HEAD']).trim(),
  environment: { os: osVersion(), release: release(), arch: arch(), node: process.version },
  runs: 1,
  mutation,
  checks: [],
  requests: [],
  browserErrors: []
};
const check = (name, pass, detail) => {
  result.checks.push({ name, pass: !!pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name} ${JSON.stringify(detail)}`);
};

function replaceOnce(source, before, after) {
  const at = source.indexOf(before);
  if (at < 0 || source.indexOf(before, at + before.length) >= 0) throw new Error(`Fixture anchor mismatch: ${before}`);
  return source.slice(0, at) + after + source.slice(at + before.length);
}

const sourceHtml = await readFile(join(ROOT, 'index.html'), 'utf8');
const sourceWorker = await readFile(join(ROOT, 'sw.js'), 'utf8');
result.sha256 = {
  'index.html': sha256(sourceHtml),
  'sw.js': sha256(sourceWorker),
  'tests/smooth/verify-s1.mjs': sha256(await readFile(new URL(import.meta.url)))
};
const firstDate = /const SITE_DATA = \{"generated_at":"(\d{4}-\d\d-\d\d)([^\"]*)","briefing_date":"(\d{4}-\d\d-\d\d)"/.exec(sourceHtml);
if (!firstDate) throw new Error('Official date fixture anchor missing');
const dateV1 = firstDate[3];
function fixtureVersion(offset) {
  const day = new Date(`${dateV1}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() + offset);
  const date = day.toISOString().slice(0, 10);
  const html = replaceOnce(sourceHtml, firstDate[0],
    `const SITE_DATA = {"generated_at":"${date}${firstDate[2]}","briefing_date":"${date}"`);
  return { date, html };
}
const v2 = fixtureVersion(1);
const broken = fixtureVersion(2);
const versions = {
  v1: { date: dateV1, html: sourceHtml }, v2,
  truncated: { date: broken.date, html: broken.html.replace(/<\/html>\s*$/i, '') }
};
result.fixtures = Object.fromEntries(Object.entries(versions).map(([key, { date, html }]) =>
  [key, { date, sha256: sha256(html), bytes: Buffer.byteLength(html) }]));
let servedWorker = sourceWorker.replaceAll('\r\n', '\n');
if (mutation === 'no-local-return') {
  servedWorker = replaceOnce(servedWorker, '    if (entry?.page) return entry.page;\n', '');
} else if (mutation === 'allow-truncated') {
  servedWorker = replaceOnce(servedWorker, " ||\n      !html.trimEnd().toLowerCase().endsWith('</html>')", '');
}
result.servedWorkerSha256 = sha256(servedWorker);
console.log('RUN ' + JSON.stringify({ ...result, fixtures: result.fixtures }));

let variant = 'v1';
let delayMs = 0;
const fakeAuthorization = 'Bearer S1-FAKE-LOCAL-ONLY';
const main = createServer((request, response) => {
  const row = {
    origin: 'site', method: request.method, url: request.url, startedAtMs: Date.now(),
    cacheControl: request.headers['cache-control'] ?? null, pragma: request.headers.pragma ?? null
  };
  result.requests.push(row);
  function reply(status, headers, body) {
    response.writeHead(status, headers);
    row.status = status;
    row.finishedAtMs = Date.now();
    response.end(body);
  }
  const { pathname } = new URL(request.url, 'http://127.0.0.1');
  if (pathname === '/sw.js' && request.method === 'GET') {
    reply(200, { 'Content-Type': 'text/javascript', 'Cache-Control': 'no-store' }, servedWorker);
  } else if (pathname === '/api/ai-probe' && request.method === 'POST') {
    let bytes = 0;
    request.on('data', chunk => { bytes += chunk.length; });
    request.on('end', () => {
      row.bodyBytes = bytes;
      row.fakeAuthorizationMatched = request.headers.authorization === fakeAuthorization;
      reply(200, { 'Content-Type': 'application/json' }, '{"result":"local mock"}');
    });
  } else if (request.method === 'GET' && (pathname === '/' || pathname === '/index.html')) {
    const { html } = versions[variant];
    row.variant = variant;
    row.delayMs = delayMs;
    row.finishedAtMs = null;
    const send = () => reply(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, max-age=3600' }, html);
    if (delayMs) setTimeout(send, delayMs);
    else send();
  } else {
    reply(404, { 'Content-Type': 'text/plain' }, 'Not found');
  }
});
const cross = createServer((request, response) => {
  result.requests.push({ origin: 'cross', method: request.method, url: request.url, status: 200, startedAtMs: Date.now() });
  response.writeHead(200, { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'text/plain' });
  response.end('cross-origin local mock');
});

async function listen(server) {
  await new Promise((done, fail) => {
    server.once('error', fail);
    server.listen(0, '127.0.0.1', done);
  });
  return `http://127.0.0.1:${server.address().port}`;
}

async function until(label, test, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  do {
    const value = await test();
    if (value) return value;
    await sleep(25);
  } while (Date.now() < deadline);
  throw new Error(`Timed out: ${label}`);
}

let profile;
let browser;
let browserExit;
let cdp;
let contextId;
let session;
const network = [];
const temp = resolve(tmpdir());
const tempPrefix = 'thoradar-sol-s1-';

async function evaluate(fn, ...args) {
  const expression = `(${fn})(${args.map(arg => JSON.stringify(arg)).join(',')})`;
  const { result: answer, exceptionDetails } = await cdp.send('Runtime.evaluate', {
    expression, awaitPromise: true, returnByValue: true
  }, session);
  if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
  return answer.value;
}

const snapshot = () => evaluate(() => {
  const banner = document.getElementById('shell-status');
  const rect = banner.getBoundingClientRect();
  const nav = performance.getEntriesByType('navigation')[0];
  return {
    url: location.href,
    date: SITE_DATA.briefing_date,
    points: document.querySelectorAll('#blips .blip').length,
    banner: banner.textContent,
    bannerInViewport: !banner.hidden && rect.height > 0 && rect.left >= 0 && rect.right <= innerWidth && rect.bottom <= innerHeight,
    documentId: window.__solS1Document,
    view: document.body.dataset.protoView,
    viewport: [innerWidth, innerHeight],
    timeOriginMs: performance.timeOrigin,
    domContentLoadedMs: nav.domContentLoadedEventEnd,
    firstContentfulPaintMs: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null
  };
});

const storage = () => evaluate(async () => {
  const registrations = await navigator.serviceWorker.getRegistrations();
  const names = await caches.keys();
  const shell = names.find(name => name.startsWith('thoradar-shell-'));
  const cache = shell && await caches.open(shell);
  const paths = cache ? (await cache.keys()).map(request => new URL(request.url).pathname) : [];
  const response = cache && await cache.match('/index.html');
  const html = response && await response.text();
  return {
    registrations: registrations.length,
    activated: registrations[0]?.active?.state === 'activated',
    controller: navigator.serviceWorker.controller !== null,
    names, paths,
    cachedDate: html ? /"briefing_date":"([\d-]+)"/.exec(html)?.[1] : null,
    complete: html ? html.trimEnd().endsWith('</html>') : null
  };
});

const waitForBanner = (text) => until(text, () => evaluate(text =>
  document.getElementById('shell-status').textContent.includes(text), text));

async function navigate(origin, path) {
  const url = origin + path;
  const previousDocument = await evaluate(() => window.__solS1Document ?? null);
  const { loaderId, errorText } = await cdp.send('Page.navigate', { url }, session);
  if (errorText) throw new Error(`Navigation failed for ${path}: ${errorText}`);
  const response = await until(`document response for ${path}`, () =>
    network.find(row => row.loaderId === loaderId && row.type === 'Document' && row.url === url));
  await until(`document rendered for ${path}`, async () => {
    try {
      return await evaluate((url, prior) => location.href === url && window.__solS1Document !== prior &&
        document.readyState === 'complete' && document.body.dataset.protoReady === 'true' &&
        performance.getEntriesByName('first-contentful-paint').length > 0, url, previousDocument);
    } catch (error) {
      if (!/context|navigat/i.test(error.message)) throw error;
      return false;
    }
  });
  return { response, page: await snapshot() };
}

async function verify(origin, crossOrigin) {
  const native = await navigate(origin, '/index.html');
  const nativeStorage = await storage();
  const nativeWorkerRequests = result.requests.filter(row => row.url === '/sw.js').length;
  check('native-default-zero-registrations-and-caches', native.page.points > 0 && !native.response.fromServiceWorker &&
    nativeStorage.registrations === 0 && nativeStorage.names.length === 0 && nativeWorkerRequests === 0,
  { ...native, storage: nativeStorage, nativeWorkerRequests });

  const first = await navigate(origin, '/index.html?sw=1');
  const firstStorage = await until('worker activated and canonical page warmed', async () => {
    const value = await storage();
    return value.activated && value.cachedDate === dateV1 && value;
  });
  const installRequest = result.requests.find(row => row.url === '/index.html' && row.pragma === 'no-cache');
  check('opt-in-first-open-native-and-install-reloads', !first.response.fromServiceWorker && !firstStorage.controller &&
    first.page.date === dateV1 && firstStorage.registrations === 1 && firstStorage.paths.join(',') === '/index.html' && !!installRequest,
  { ...first, storage: firstStorage, installRequest });

  variant = 'v2';
  delayMs = 1500;
  const second = await navigate(origin, '/index.html?sw=1');
  const refresh = result.requests.find(row => row.variant === 'v2' && row.url === '/index.html?sw=1' && row.pragma === 'no-cache');
  const pendingAtSnapshot = refresh?.finishedAtMs === null;
  const paintAtMs = second.page.timeOriginMs + second.page.firstContentfulPaintMs;
  check('second-open-uses-cache-storage-before-slow-origin', second.response.serviceWorkerResponseSource === 'cache-storage' &&
    second.page.date === dateV1 && second.page.points > 0 && second.page.bannerInViewport &&
    second.page.banner.includes(dateV1) && second.page.banner.includes('核对更新中') &&
    pendingAtSnapshot && paintAtMs < refresh.startedAtMs + delayMs,
  { ...second, pendingAtSnapshot, paintAtMs, refresh });
  if (mutation === 'no-local-return') return;

  await evaluate(() => document.getElementById('proto-tab-reading').click());
  await waitForBanner('有新版，下次打开生效');
  const still = await snapshot();
  const updatedStorage = await storage();
  check('background-update-keeps-document-and-reading-state', still.documentId === second.page.documentId &&
    still.timeOriginMs === second.page.timeOriginMs && still.view === 'reading' && still.date === dateV1 &&
    still.banner.includes(dateV1) && updatedStorage.cachedDate === v2.date &&
    refresh.finishedAtMs - refresh.startedAtMs >= delayMs - 5,
  { page: still, storage: updatedStorage, refresh });

  delayMs = 0;
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true }, session);
  const third = await navigate(origin, '/');
  await waitForBanner('与服务器一致');
  const mobile = await snapshot();
  const rootRequest = result.requests.find(row => row.url === '/' && row.variant === 'v2' && row.pragma === 'no-cache');
  check('third-open-root-uses-v2-and-reports-date-on-mobile', third.response.serviceWorkerResponseSource === 'cache-storage' &&
    mobile.date === v2.date && mobile.points > 0 && mobile.banner.includes(v2.date) && mobile.bannerInViewport &&
    mobile.viewport[0] === 390 && !!rootRequest, { ...third, mobile, rootRequest });

  const apiUrl = origin + '/api/ai-probe';
  const crossUrl = crossOrigin + '/entrez/probe';
  const mock = await evaluate(async (crossUrl, auth) => {
    const [post, cross] = await Promise.all([
      fetch('/api/ai-probe', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: auth }, body: '{}' }),
      fetch(crossUrl)
    ]);
    return { post: await post.json(), cross: await cross.text() };
  }, crossUrl, fakeAuthorization);
  const postResponse = network.find(row => row.url === apiUrl);
  const crossResponse = network.find(row => row.url === crossUrl);
  const postRequest = result.requests.find(row => row.url === '/api/ai-probe');
  const crossRequest = result.requests.find(row => row.origin === 'cross' && row.url === '/entrez/probe');
  check('ai-post-and-cross-origin-fetch-remain-native', !!postResponse && !postResponse.fromServiceWorker &&
    !!crossResponse && !crossResponse.fromServiceWorker && postRequest?.method === 'POST' && postRequest.fakeAuthorizationMatched &&
    crossRequest?.method === 'GET' && mock.post.result === 'local mock' && mock.cross === 'cross-origin local mock',
  { mock, postResponse, crossResponse, postRequest, crossRequest });

  variant = 'truncated';
  const unhealthy = await navigate(origin, '/index.html');
  await until('validation result for the truncated page', async () => {
    const { banner } = await snapshot();
    return banner.includes('暂未核实更新') || banner.includes('有新版');
  });
  const protectedPage = await snapshot();
  const protection = await storage();
  const badRequest = result.requests.find(row => row.variant === 'truncated' && row.url === '/index.html');
  check('truncated-html-cannot-overwrite-healthy-shell', unhealthy.response.serviceWorkerResponseSource === 'cache-storage' &&
    protectedPage.date === v2.date && protectedPage.banner.includes('暂未核实更新') && !!badRequest &&
    protection.paths.join(',') === '/index.html' && protection.cachedDate === v2.date && protection.complete,
  { ...unhealthy, page: protectedPage, storage: protection, badRequest });
  if (mutation !== 'none') return;

  variant = 'v2';
  await evaluate(async () => { await caches.open('sol-s1-unrelated'); });
  const exit = await navigate(origin, '/?sw=0');
  await waitForBanner('本地副本已停用');
  const cleared = await storage();
  const afterExit = await navigate(origin, '/');
  const finalStorage = await storage();
  check('query-opt-out-clears-only-shell-caches-and-returns-to-network', !exit.response.fromServiceWorker &&
    cleared.registrations === 0 && cleared.names.join(',') === 'sol-s1-unrelated' && !afterExit.response.fromServiceWorker &&
    !finalStorage.controller && finalStorage.registrations === 0 && finalStorage.names.join(',') === 'sol-s1-unrelated',
  { exit, cleared, afterExit, finalStorage });
}

try {
  const [origin, crossOrigin] = await Promise.all([listen(main), listen(cross)]);
  result.origins = { origin, crossOrigin };
  profile = await mkdtemp(join(temp, tempPrefix));
  const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  browser = spawn(chrome, [...chromeArgs(0, profile), '--no-proxy-server'], { stdio: ['ignore', 'inherit', 'inherit'] });
  browserExit = new Promise(done => {
    browser.once('error', error => done({ error: error.message }));
    browser.once('exit', (code, signal) => done({ code, signal }));
  });
  const activePort = await until('Chrome DevToolsActivePort', async () => {
    const contents = await readFile(join(profile, 'DevToolsActivePort'), 'utf8').catch(() => '');
    return contents.includes('/devtools/browser/') && contents.trim().split(/\r?\n/)[0];
  }, 18000);
  const devtools = await fetch(`http://127.0.0.1:${activePort}/json/version`).then(response => response.json());
  cdp = await connect(devtools.webSocketDebuggerUrl);
  result.environment.chrome = await cdp.send('Browser.getVersion');
  console.log('BROWSER ' + JSON.stringify(result.environment.chrome));
  ({ browserContextId: contextId } = await cdp.send('Target.createBrowserContext'));
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank', browserContextId: contextId });
  ({ sessionId: session } = await cdp.send('Target.attachToTarget', { targetId, flatten: true }));
  cdp.on('Network.responseReceived', ({ type, loaderId, response }, eventSession) => {
    if (eventSession !== session || ![origin, crossOrigin].includes(new URL(response.url).origin)) return;
    network.push({ type, loaderId, url: response.url, status: response.status,
      fromServiceWorker: response.fromServiceWorker, fromDiskCache: response.fromDiskCache,
      serviceWorkerResponseSource: response.serviceWorkerResponseSource ?? null });
  });
  cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }, eventSession) => {
    if (eventSession === session) result.browserErrors.push(exceptionDetails.exception?.description ?? exceptionDetails.text);
  });
  for (const domain of ['Page', 'Runtime', 'Network']) await cdp.send(`${domain}.enable`, {}, session);
  await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
    source: 'window.__solS1Document = crypto.randomUUID();'
  }, session);
  await verify(origin, crossOrigin);
  check('no-uncaught-page-errors', result.browserErrors.length === 0, result.browserErrors);
} catch (error) {
  console.error(error.stack);
  check('harness-completed', false, { error: String(error) });
} finally {
  try {
    if (contextId) await cdp.send('Target.disposeBrowserContext', { browserContextId: contextId });
    if (cdp) await cdp.send('Browser.close');
  } catch (error) {
    console.error(`Graceful Chrome cleanup: ${error.message}`);
  } finally {
    cdp?.close();
  }
  if (browser) {
    let exit = await Promise.race([browserExit, sleep(5000).then(() => null)]);
    const forced = !exit && !!browser.pid && browser.kill();
    if (!exit) exit = await Promise.race([browserExit, sleep(5000).then(() => null)]);
    result.cleanup = { browserPid: browser.pid, exit, forced };
  }
  for (const server of [main, cross]) if (server.listening) await new Promise(done => server.close(done));
  if (profile && dirname(resolve(profile)) === temp && basename(profile).startsWith(tempPrefix)) {
    try {
      await rm(profile, { force: true, recursive: true, maxRetries: 5, retryDelay: 100 });
      result.cleanup.profileRemoved = true;
    } catch (error) {
      console.error(error.stack);
      check('temporary-profile-removed', false, { error: String(error) });
    }
  }
  console.log('CLEANUP ' + JSON.stringify(result.cleanup));
  result.endedAt = new Date().toISOString();
  result.summary = { passed: result.checks.filter(row => row.pass).length, failed: result.checks.filter(row => !row.pass).length };
  result.network = network;
  await mkdir(dirname(resolve(output)), { recursive: true });
  await writeFile(output, JSON.stringify(result, null, 2) + '\n');
  console.log('SUMMARY ' + JSON.stringify({ ...result.summary, endedAt: result.endedAt }));
  if (result.summary.failed) process.exitCode = 1;
}
