import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { arch, release, tmpdir, version } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { ROOT, connect, freePort, gitRead, launch, sha256, sleep } from '../aicls/lib.mjs';

const [output, workerPath = join(ROOT, 'sw.js')] = process.argv.slice(2);
if (!output) throw new Error('Usage: node tests/smooth/verify-s3.mjs <result.json> [worker.js]');
const worker = await readFile(workerPath);
const healthy = await readFile(join(ROOT, 'index.html'), 'utf8');
const neon = '<!doctype html><html><head><title>Stub</title></head><body><!-- /*__THORADAR_DATA_START__*//*__THORADAR_DATA_END__*/ --><p>Corrupted shell</p></body></html>';
const neonHash = '11e2ff0add51cd0cf4f21b39010925b11df3fe7c0d388906c0c56468a3a16b74';
if (Buffer.byteLength(neon) !== 156 || sha256(neon) !== neonHash) throw new Error('Neon fixture bytes differ');

const start = '/*__THORADAR_DATA_START__*/';
const end = '/*__THORADAR_DATA_END__*/';
const dataBlock = /const SITE_DATA = (\{[^\r\n]+\});\s*\/\*__THORADAR_DATA_END__\*\//.exec(healthy);
if (!dataBlock) throw new Error('Healthy fixture has no official SITE_DATA');
const data = JSON.parse(dataBlock[1]);
const zeroData = { ...data, briefing_date: '2026-11-28', papers: [] };
const zero = healthy.replace(dataBlock[1], () => JSON.stringify(zeroData));
if (zero === healthy || data.papers.length === 0) throw new Error('Expected distinct populated and zero-paper editions');
const shell = (block, after = '') => `<!doctype html><html><body><script>${start}\n${block}\n${end}\n${after}</script></body></html>`;
const cases = [
  ['neon-empty-markers-stub', neon],
  ['missing-site-data-between-markers', shell('const OTHER = {};', 'const SITE_DATA = {"briefing_date":"2026-11-28","papers":[]};')],
  ['invalid-json', shell('const SITE_DATA = {"briefing_date":"2026-11-28","papers":[],};')],
  ['wrong-briefing-date-type', shell('const SITE_DATA = {"briefing_date":20261128,"papers":[]};')],
  ['wrong-papers-type', shell('const SITE_DATA = {"briefing_date":"2026-11-28","papers":{}};')],
  ['empty-briefing-date', healthy.replace(dataBlock[1], () => JSON.stringify({ ...zeroData, briefing_date: '' }))],
  ['invalid-calendar-date', shell('const SITE_DATA = {"briefing_date":"2026-02-29","papers":[]} ;')],
  ['comment-wrapped-site-data-stub', `<!doctype html><html><body><!-- ${start} const SITE_DATA = {"briefing_date":"${zeroData.briefing_date}","papers":[]}; ${end} --><p>Comment stub</p></body></html>`],
  ['valid-zero-papers', zero]
];
const describe = body => ({ bytes: Buffer.byteLength(body), sha256: sha256(body) });
const result = {
  command: ['node', 'tests/smooth/verify-s3.mjs', ...process.argv.slice(2)], startedAt: new Date().toISOString(),
  runs: 1, seed: null, baseline: gitRead(['rev-parse', 'HEAD']).trim(),
  environment: { os: version(), release: release(), arch: arch(), node: process.version },
  sha256: { 'index.html': sha256(healthy), 'sw.js': sha256(worker),
    'tests/smooth/verify-s3.mjs': sha256(await readFile(new URL(import.meta.url))) },
  fixtures: Object.fromEntries([['healthy', healthy], ...cases].map(([name, body]) => [name, describe(body)])),
  checks: [], requests: [], documents: []
};
const mime = 'text/html; charset=utf-8';
let upstream = ['healthy', healthy];
const server = createServer((req, res) => {
  const { pathname } = new URL(req.url, 'http://127.0.0.1');
  const cacheControl = { 'Cache-Control': 'no-store' };
  if (pathname === '/driver') {
    res.writeHead(200, { ...cacheControl, 'Content-Type': mime });
    return res.end('<!doctype html><title>S3 test driver</title>');
  }
  if (pathname === '/sw.js') {
    res.writeHead(200, { ...cacheControl, 'Content-Type': 'text/javascript' });
    return res.end(worker);
  }
  if (pathname !== '/index.html' && pathname !== '/') {
    res.writeHead(404, cacheControl);
    return res.end();
  }
  const [name, body] = upstream;
  const request = { name, url: req.url, method: req.method, status: 200, mime,
    pragma: req.headers.pragma ?? null, at: new Date().toISOString(), ...result.fixtures[name] };
  result.requests.push(request);
  res.once('finish', () => { request.finished = true; });
  res.writeHead(200, { ...cacheControl, 'Content-Type': mime });
  res.end(body);
});

async function until(label, read) {
  const deadline = Date.now() + 10_000;
  do {
    const value = await read();
    if (value) return value;
    await sleep(40);
  } while (Date.now() < deadline);
  throw new Error('Timed out: ' + label);
}

function record(name, pass, detail) {
  result.checks.push({ name, pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name} ${JSON.stringify(detail)}`);
}

const temp = resolve(tmpdir());
const prefix = 'thoradar-sol-s3-chrome-';
let profile, browser, cdp;
try {
  console.log('RUN ' + JSON.stringify(result));
  await new Promise((done, fail) => {
    server.once('error', fail);
    server.listen(0, '127.0.0.1', done);
  });
  const origin = `http://127.0.0.1:${server.address().port}`;
  profile = await mkdtemp(join(temp, prefix));
  browser = await launch({ chrome: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    profile, port: await freePort() });
  cdp = await connect(browser.ver.webSocketDebuggerUrl);
  result.environment.chrome = await cdp.send('Browser.getVersion');
  console.log('BROWSER ' + JSON.stringify(result.environment.chrome));
  const sessions = new Map();
  cdp.on('Network.responseReceived', ({ type, loaderId, response }, session) => {
    if (type === 'Document' && sessions.has(session)) {
      result.documents.push({ case: sessions.get(session), loaderId, url: response.url,
        status: response.status, fromServiceWorker: response.fromServiceWorker,
        source: response.serviceWorkerResponseSource ?? null });
    }
  });

  for (const fixture of cases) {
    const [name] = fixture;
    const { browserContextId } = await cdp.send('Target.createBrowserContext');
    let sessionId;
    try {
      const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank', browserContextId });
      ({ sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true }));
      sessions.set(sessionId, name);
      const send = (method, params) => cdp.send(method, params, sessionId);
      await send('Page.enable');
      await send('Network.enable');
      await send('Page.addScriptToEvaluateOnNewDocument', { source: `
        navigator.serviceWorker?.addEventListener('message', event => {
          if (event.data?.type === 'thoradar-shell-state') window.s3Status = event.data.status;
        });` });
      async function evaluate(fn) {
        const { result: value, exceptionDetails } = await send('Runtime.evaluate', {
          expression: `(${fn})()`, awaitPromise: true, returnByValue: true
        });
        if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
        return value.value;
      }
      async function navigate(path) {
        const url = origin + path;
        const { loaderId, errorText } = await send('Page.navigate', { url });
        if (errorText) throw new Error(errorText);
        const document = await until('document ' + path, () => result.documents.find(row => row.loaderId === loaderId));
        await until('page loaded ' + path, () => evaluate(() =>
          document.readyState === 'complete' && location.href).then(actual => actual === url).catch(() => false));
        return document;
      }
      const cacheState = () => evaluate(async () => {
        const cache = await caches.open('thoradar-shell-v1');
        const response = await cache.match('/index.html');
        const bytes = await response.arrayBuffer();
        const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
        return { bytes: bytes.byteLength, sha256: Array.from(digest, value => value.toString(16).padStart(2, '0')).join('') };
      });
      const pageState = () => evaluate(() => ({ date: typeof SITE_DATA === 'undefined' ? null : SITE_DATA.briefing_date,
        papers: typeof SITE_DATA === 'undefined' ? null : SITE_DATA.papers.length,
        banner: document.getElementById('shell-status')?.textContent ?? null }));

      upstream = ['healthy', healthy];
      await navigate('/driver');
      await evaluate(async () => { await navigator.serviceWorker.register('/sw.js'); await navigator.serviceWorker.ready; });
      const before = await cacheState();
      const offset = result.requests.length;
      upstream = fixture;
      const first = await navigate('/index.html');
      const status = await until('worker completed refresh', () => evaluate(() =>
        ['current', 'updated', 'unavailable'].includes(window.s3Status) && window.s3Status));
      const after = await cacheState();
      const firstPage = await pageState();
      const requests = result.requests.slice(offset);
      const accepted = name === 'valid-zero-papers';
      const expected = result.fixtures[accepted ? name : 'healthy'];
      const next = await navigate('/?sw=1');
      const nextPage = await pageState();
      record(name, before.sha256 === result.fixtures.healthy.sha256 && first.source === 'cache-storage' &&
        firstPage.date === data.briefing_date && requests.some(request => request.name === name &&
          request.finished && request.pragma === 'no-cache') && status === (accepted ? 'updated' : 'unavailable') &&
        after.sha256 === expected.sha256 && after.bytes === expected.bytes && next.source === 'cache-storage' &&
        nextPage.date === (accepted ? zeroData.briefing_date : data.briefing_date) &&
        nextPage.papers === (accepted ? 0 : data.papers.length),
      { before, first, firstPage, status, after, expected, requests, next, nextPage });
    } catch (error) {
      console.error(error.stack);
      record(name, false, { error: error.message });
    } finally {
      sessions.delete(sessionId);
      await cdp.send('Target.disposeBrowserContext', { browserContextId });
    }
  }
} catch (error) {
  console.error(error.stack);
  record('harness', false, { error: error.message });
} finally {
  try { await cdp?.send('Browser.close'); }
  catch (error) { console.error('Browser.close: ' + error.message); }
  cdp?.close();
  if (browser) result.remainingProfileProcesses = await browser.stop();
  if (server.listening) await new Promise(done => {
    server.close(done);
    server.closeAllConnections();
  });
  if (profile && dirname(resolve(profile)) === temp && basename(profile).startsWith(prefix)) {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
  result.endedAt = new Date().toISOString();
  result.summary = { passed: result.checks.filter(check => check.pass).length,
    failed: result.checks.filter(check => !check.pass).length };
  await writeFile(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log('SUMMARY ' + JSON.stringify(result.summary));
  if (result.summary.failed || result.remainingProfileProcesses) process.exitCode = 1;
}
