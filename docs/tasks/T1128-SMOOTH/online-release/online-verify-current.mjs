import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { arch, release, tmpdir, version as osVersion } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { chromeArgs, connect, sleep } from 'file:///D:/trackeep/trackeep-product/trackeep-thoradar/tests/aicls/lib.mjs';

const output = process.argv[2] || 'D:/claude-tmp/T1128-online-verify.json';
const repo = 'D:/trackeep/trackeep-product/trackeep-thoradar';
const domains = (process.env.THORADAR_ONLINE_DOMAINS || 'thoradar.online,www.thoradar.online').split(',').map(value => value.trim()).filter(Boolean);
const expectedDate = '2026-11-28';
const expectedPapers = 43;
const result = {
  startedAt: new Date().toISOString(),
  environment: { os: osVersion(), release: release(), arch: arch(), node: process.version },
  runs: 1, seed: null, headers: [], sites: [], checks: [], cleanup: {}
};
const check = (name, pass, detail) => {
  const row = { name, pass: !!pass, detail };
  result.checks.push(row);
  console.log(`${row.pass ? 'PASS' : 'FAIL'} ${name} ${JSON.stringify(detail)}`);
};
const md5 = bytes => createHash('md5').update(bytes).digest('base64');
const localMd5 = Object.fromEntries(['index.html', 'sw.js', 'sw-retire.js'].map(name =>
  [name, md5(execFileSync('git', ['-C', repo, 'show', `HEAD:${name}`]))]));

async function verifyHeaders() {
  for (const domain of domains) {
    for (const path of ['/', '/index.html', '/sw.js', '/sw-retire.js']) {
      const url = `https://${domain}${path}`;
      const source = path.endsWith('.js') ? path.slice(1) : 'index.html';
      const worker = source !== 'index.html';
      let row;
      for (let attempt = 1; attempt <= 3; attempt++) {
        try {
          const response = await fetch(url, { method: 'HEAD', redirect: 'follow', headers: {
            'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache', Pragma: 'no-cache'
          } });
          row = {
            url, status: response.status, md5: response.headers.get('content-md5'),
            expectedMd5: localMd5[source], mime: response.headers.get('content-type'),
            cacheControl: response.headers.get('cache-control'), attempts: attempt
          };
          break;
        } catch (error) {
          row = { url, error: String(error), cause: String(error.cause || ''), attempts: attempt };
          if (attempt < 3) await sleep(250);
        }
      }
      result.headers.push(row);
      check(`header ${url}`, !row.error && row.status === 200 && row.md5 === row.expectedMd5 &&
        (!worker || (/(?:application|text)\/(?:javascript|ecmascript)/i.test(row.mime || '') &&
          /(?:^|,)\s*no-store\s*(?:,|$)/i.test(row.cacheControl || ''))), row);
    }
  }
}

await verifyHeaders();

let profile;
let browser;
let browserExit;
let cdp;
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const until = async (label, test, timeoutMs = 15000) => {
  const deadline = Date.now() + timeoutMs;
  let last;
  do {
    try { last = await test(); if (last) return last; } catch (error) { last = { error: String(error) }; }
    await sleep(50);
  } while (Date.now() < deadline);
  throw new Error(`Timed out: ${label}; last=${JSON.stringify(last)}`);
};

try {
  profile = await mkdtemp(join(tmpdir(), 'thoradar-online-verify-'));
  // The shared offline-test helper blocks every external DNS name by design.
  // Live verification must remove that rule; never bypass this for local mock tests.
  const liveChromeArgs = chromeArgs(0, profile).filter(arg => !arg.startsWith('--host-resolver-rules='));
  browser = spawn(chrome, [...liveChromeArgs, '--no-proxy-server'], { stdio: ['ignore', 'inherit', 'inherit'] });
  browserExit = new Promise(done => {
    browser.once('error', error => done({ error: error.message }));
    browser.once('exit', (code, signal) => done({ code, signal }));
  });
  const activePort = await until('DevToolsActivePort', async () => {
    const text = await readFile(join(profile, 'DevToolsActivePort'), 'utf8').catch(() => '');
    return text.includes('/devtools/browser/') && text.trim().split(/\r?\n/)[0];
  }, 20000);
  const devtools = await fetch(`http://127.0.0.1:${activePort}/json/version`).then(r => r.json());
  cdp = await connect(devtools.webSocketDebuggerUrl);
  result.environment.chrome = await cdp.send('Browser.getVersion');

  for (const domain of domains) {
    const origin = `https://${domain}`;
    const site = { domain, network: [], failures: [], errors: [], checks: [] };
    result.sites.push(site);
    let contextId;
    let session;
    try {
      ({ browserContextId: contextId } = await cdp.send('Target.createBrowserContext'));
      const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank', browserContextId: contextId });
      ({ sessionId: session } = await cdp.send('Target.attachToTarget', { targetId, flatten: true }));
      for (const name of ['Page', 'Runtime', 'Network']) await cdp.send(`${name}.enable`, {}, session);
      await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
        source: 'window.__thoradarOnlineDocument=crypto.randomUUID();'
      }, session);
      const requestUrls = new Map();
      cdp.on('Network.requestWillBeSent', ({ requestId, request }, eventSession) => {
        if (eventSession === session) requestUrls.set(requestId, request.url);
      });
      cdp.on('Network.responseReceived', ({ requestId, type, loaderId, response }, eventSession) => {
        if (eventSession !== session) return;
        let url;
        try { url = new URL(response.url); } catch { return; }
        if (url.origin !== origin) return;
        site.network.push({ requestId, type, loaderId, url: response.url, status: response.status,
          fromServiceWorker: !!response.fromServiceWorker,
          serviceWorkerResponseSource: response.serviceWorkerResponseSource ?? null,
          fromDiskCache: !!response.fromDiskCache });
      });
      cdp.on('Network.loadingFailed', ({ requestId, errorText, canceled }, eventSession) => {
        if (eventSession !== session) return;
        const url = requestUrls.get(requestId) || '';
        if (!url.startsWith(origin)) return;
        site.failures.push({ requestId, url, errorText, canceled: !!canceled });
      });
      cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }, eventSession) => {
        if (eventSession === session) site.errors.push(exceptionDetails.exception?.description ?? exceptionDetails.text);
      });
      const evaluate = async (fn, ...args) => {
        const expression = `(${fn})(${args.map(arg => JSON.stringify(arg)).join(',')})`;
        const { result: answer, exceptionDetails } = await cdp.send('Runtime.evaluate', {
          expression, awaitPromise: true, returnByValue: true
        }, session);
        if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text);
        return answer.value;
      };
      const snapshot = () => evaluate(() => ({
        url: location.href, date: typeof SITE_DATA !== 'undefined' ? SITE_DATA.briefing_date : null,
        papers: typeof SITE_DATA !== 'undefined' ? SITE_DATA.papers?.length : null,
        rendered: typeof PAPERS !== 'undefined' ? PAPERS.length : null,
        points: document.querySelectorAll('#blips .blip').length,
        view: document.body.dataset.protoView,
        documentId: window.__thoradarOnlineDocument,
        timeOrigin: performance.timeOrigin,
        controller: !!navigator.serviceWorker.controller,
        banner: document.getElementById('shell-status')?.textContent || ''
      }));
      const storage = () => evaluate(async () => {
        const registrations = await navigator.serviceWorker.getRegistrations();
        const names = await caches.keys();
        const shellNames = names.filter(name => name.startsWith('thoradar-shell-'));
        const shell = shellNames[0];
        const cache = shell && await caches.open(shell);
        const paths = cache ? (await cache.keys()).map(request => new URL(request.url).pathname) : [];
        const response = cache && await cache.match('/index.html');
        const html = response && await response.text();
        let data = null;
        try {
          const match = html && /\/\*__THORADAR_DATA_START__\*\/\s*const SITE_DATA = (\{[\s\S]*\})\s*;?\s*\/\*__THORADAR_DATA_END__\*\//.exec(html);
          data = match ? JSON.parse(match[1]) : null;
        } catch {}
        return {
          registrations: registrations.length,
          activated: registrations[0]?.active?.state === 'activated',
          controller: !!navigator.serviceWorker.controller,
          names, shellNames, paths,
          cachedDate: data?.briefing_date ?? null,
          cachedPapers: data?.papers?.length ?? null,
          complete: html ? html.trimEnd().endsWith('</html>') : null,
          sentinel: localStorage.getItem('thoradar.online-verify-sentinel')
        };
      });
      const navigate = async path => {
        const url = origin + path;
        const previous = await evaluate(() => window.__thoradarOnlineDocument ?? null);
        const { loaderId, errorText } = await cdp.send('Page.navigate', { url }, session);
        if (errorText) throw new Error(`Navigation ${url}: ${errorText}`);
        const response = await until(`document response ${url}`, () =>
          site.network.find(row => row.loaderId === loaderId && row.type === 'Document' && row.url === url));
        await until(`rendered ${url}`, async () => {
          try {
            return await evaluate((url, previous, date, papers) => location.href === url &&
              window.__thoradarOnlineDocument !== previous && document.readyState === 'complete' &&
              document.body.dataset.protoReady === 'true' && SITE_DATA.briefing_date === date &&
              SITE_DATA.papers.length === papers, url, previous, expectedDate, expectedPapers);
          } catch (error) {
            if (/context|navigat/i.test(String(error))) return false;
            throw error;
          }
        });
        return { response, page: await snapshot() };
      };

      const first = await navigate('/index.html');
      await evaluate(() => { localStorage.setItem('thoradar.online-verify-sentinel', 'keep'); });
      let warmLast = null;
      const warm = await until(`${domain} worker activated and warmed`, async () => {
        const state = await storage();
        warmLast = state;
        return state.activated && state.cachedDate === expectedDate && state.cachedPapers === expectedPapers && state;
      }).catch(error => {
        throw new Error(`${error.message}; warmLast=${JSON.stringify(warmLast)}; failures=${JSON.stringify(site.failures)}`);
      });
      check(`${domain} cold first visit is native and warms current shell`, !first.response.fromServiceWorker &&
        first.page.date === expectedDate && first.page.papers === expectedPapers && first.page.points > 0 &&
        warm.paths.join(',') === '/index.html' && warm.complete, { first, warm });

      const second = await navigate('/index.html');
      await evaluate(() => document.getElementById('proto-tab-reading').click());
      await until(`${domain} background check reports current`, async () =>
        (await snapshot()).banner.includes('与服务器一致'), 18000);
      const during = await snapshot();
      const refreshed = await storage();
      check(`${domain} repeat visit uses cache storage and background check does not reload reading`,
        second.response.fromServiceWorker && second.response.serviceWorkerResponseSource === 'cache-storage' &&
        during.documentId === second.page.documentId && during.timeOrigin === second.page.timeOrigin &&
        during.view === 'reading' && during.date === expectedDate && refreshed.cachedDate === expectedDate,
        { second, during, refreshed });

      await cdp.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 }, session);
      let offline;
      try {
        offline = await navigate('/');
        check(`${domain} offline opens the current daily copy`, offline.response.fromServiceWorker &&
          offline.response.serviceWorkerResponseSource === 'cache-storage' && offline.page.date === expectedDate &&
          offline.page.papers === expectedPapers && offline.page.points > 0 && offline.page.banner.includes(expectedDate), offline);
      } finally {
        await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }, session);
      }

      const exit = await navigate('/?sw=0');
      await until(`${domain} local copy disabled`, async () => (await snapshot()).banner.includes('本地副本已停用'));
      const cleared = await storage();
      const after = await navigate('/');
      const finalStorage = await storage();
      // Contract: ?sw=0 is a single-page exit, not a persistent opt-out. A later
      // ordinary visit may start a fresh registration, but its first document
      // must still be native and no old shell cache or personal storage may survive.
      check(`${domain} single-page ?sw=0 clears shell and the next visit starts native and clean`,
        !exit.response.fromServiceWorker && cleared.registrations === 0 && cleared.shellNames.length === 0 &&
        cleared.sentinel === 'keep' && !after.response.fromServiceWorker && !after.page.controller &&
        finalStorage.shellNames.length === 0 && finalStorage.sentinel === 'keep',
        { exit, cleared, after, finalStorage, persistentOptOutRequired: false });
      check(`${domain} no uncaught page errors`, site.errors.length === 0, site.errors);
    } catch (error) {
      site.harnessError = String(error);
      check(`${domain} browser harness completed`, false, { error: String(error), network: site.network, failures: site.failures, pageErrors: site.errors });
    } finally {
      if (contextId) await cdp.send('Target.disposeBrowserContext', { browserContextId: contextId }).catch(() => {});
    }
  }
} catch (error) {
  check('online browser harness', false, { error: String(error) });
} finally {
  try {
    if (cdp) await cdp.send('Browser.close');
  } catch (error) {
    result.cleanup.gracefulError = String(error);
  } finally {
    cdp?.close();
  }
  if (browser) {
    let exit = await Promise.race([browserExit, sleep(5000).then(() => null)]);
    const forced = !exit && !!browser.pid && browser.kill();
    if (!exit) exit = await Promise.race([browserExit, sleep(5000).then(() => null)]);
    result.cleanup.browser = { pid: browser.pid, exit, forced };
  }
  if (profile && dirname(resolve(profile)) === resolve(tmpdir()) && basename(profile).startsWith('thoradar-online-verify-')) {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    result.cleanup.profileRemoved = true;
  }
  result.endedAt = new Date().toISOString();
  result.summary = { passed: result.checks.filter(row => row.pass).length,
    failed: result.checks.filter(row => !row.pass).length };
  await writeFile(output, JSON.stringify(result, null, 2) + '\n');
  console.log('CLEANUP ' + JSON.stringify(result.cleanup));
  console.log('SUMMARY ' + JSON.stringify(result.summary));
  if (result.summary.failed) process.exitCode = 1;
}
