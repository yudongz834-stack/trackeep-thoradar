import { spawn } from 'node:child_process';
import { readFile, writeFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { chromeArgs, connect, sleep } from 'file:///D:/trackeep/trackeep-product/trackeep-thoradar/tests/aicls/lib.mjs';
const profile = (await readFile('D:/claude-tmp/thoradar-www-legacy-path.txt', 'utf8')).trim();
const output = 'D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/online-release/www-legacy-migration-v3.json';
const result = { profile, startedAt: new Date().toISOString(), checks: [], network: [], errors: [] };
const check = (name, pass, detail) => { result.checks.push({ name, pass: !!pass, detail }); console.log(`${pass ? 'PASS' : 'FAIL'} ${name} ${JSON.stringify(detail)}`); };
await rm(join(profile, 'DevToolsActivePort'), { force: true });
const args = chromeArgs(0, profile).filter(arg => !arg.startsWith('--host-resolver-rules='));
const browser = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [...args, '--no-proxy-server'], { stdio: ['ignore', 'inherit', 'inherit'] });
let cdp;
const until = async (label, test, ms = 30000) => {
  const start = Date.now(); let last;
  while (Date.now() - start < ms) {
    try { last = await test(); if (last) return last; } catch (error) { last = { error: String(error) }; }
    await sleep(100);
  }
  throw new Error(`${label} timed out; last=${JSON.stringify(last)}`);
};
try {
  const active = await until('DevToolsActivePort', async () => {
    const text = await readFile(join(profile, 'DevToolsActivePort'), 'utf8').catch(() => '');
    return text.includes('/devtools/browser/') && text.trim();
  });
  const [port, websocketPath] = active.split(/\r?\n/);
  cdp = await connect(`ws://127.0.0.1:${port}${websocketPath}`);
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  for (const name of ['Page', 'Runtime', 'Network']) await cdp.send(`${name}.enable`, {}, sessionId);
  cdp.on('Network.responseReceived', ({ type, loaderId, response }) => {
    if (type === 'Document' || /\/sw(?:-retire)?\.js$/.test(new URL(response.url).pathname)) {
      result.network.push({ type, loaderId, url: response.url, status: response.status,
        fromServiceWorker: !!response.fromServiceWorker, source: response.serviceWorkerResponseSource || null });
    }
  });
  cdp.on('Runtime.exceptionThrown', ({ exceptionDetails }) => result.errors.push(exceptionDetails.exception?.description || exceptionDetails.text));
  const evaluate = async expression => {
    const answer = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
    if (answer.exceptionDetails) throw new Error(answer.exceptionDetails.exception?.description || answer.exceptionDetails.text);
    return answer.result.value;
  };
  const storage = () => evaluate(`(async()=>{const regs=await navigator.serviceWorker.getRegistrations();const names=await caches.keys();return {url:location.href,banner:document.getElementById('shell-status')?.textContent||'',registrations:regs.length,states:regs.map(r=>({active:r.active?.state||null,waiting:r.waiting?.state||null,installing:r.installing?.state||null})),names,shell:names.filter(n=>n.startsWith('thoradar-shell-')),sentinel:localStorage.getItem('canonical-migration-sentinel')}})()`);
  const navigate = async path => {
    const before = result.network.length;
    const nav = await cdp.send('Page.navigate', { url: 'https://www.thoradar.online' + path }, sessionId);
    if (nav.errorText) throw new Error(nav.errorText);
    await until('rendered ' + path, () => evaluate(`location.href`).then(async url => {
      const ready = await evaluate(`document.readyState === 'complete' && document.body?.dataset.protoReady === 'true'`);
      return ready && url;
    }));
    return { nav, page: await evaluate(`({url:location.href,date:SITE_DATA.briefing_date,papers:SITE_DATA.papers.length,controller:!!navigator.serviceWorker.controller})`), responses: result.network.slice(before) };
  };

  const first = await navigate('/index.html');
  await evaluate(`localStorage.setItem('canonical-migration-sentinel','keep')`);
  result.first = first;
  const legacyResponse = first.responses.find(row => row.loaderId === first.nav.loaderId && row.url === 'https://www.thoradar.online/index.html');
  check('legacy visit really starts from the old www cache', new URL(first.page.url).hostname === 'www.thoradar.online' &&
    first.page.controller && legacyResponse?.fromServiceWorker && legacyResponse?.source === 'cache-storage', { first, legacyResponse });

  const retired = await until('legacy worker retires and clears only shell storage', async () => {
    const state = await storage();
    return state.registrations === 0 && state.shell.length === 0 && state.sentinel === 'keep' && state;
  });
  result.retired = retired;
  check('www retirement unregisters workers and clears shell but preserves personal storage',
    retired.registrations === 0 && retired.shell.length === 0 && retired.sentinel === 'keep' && retired.banner.includes('本地副本已停用'), retired);

  const second = await navigate('/index.html?from=legacy');
  result.second = second;
  check('next legacy visit follows the permanent redirect to canonical with query preserved',
    second.page.url === 'https://thoradar.online/index.html?from=legacy' && second.page.date === '2026-11-28' &&
    second.page.papers === 43 && second.responses.some(row => row.status === 301 || row.status === 308), second);
  check('migration has no uncaught page errors', result.errors.length === 0, result.errors);
} catch (error) {
  result.harnessError = String(error);
  check('legacy migration harness completed', false, { error: String(error), network: result.network });
} finally {
  if (cdp) await cdp.send('Browser.close').catch(() => {});
  else browser.kill();
  cdp?.close();
  result.summary = { passed: result.checks.filter(row => row.pass).length, failed: result.checks.filter(row => !row.pass).length };
  result.endedAt = new Date().toISOString();
  await writeFile(output, JSON.stringify(result, null, 2) + '\n');
  console.log('SUMMARY ' + JSON.stringify(result.summary));
  if (result.summary.failed === 0 && profile.startsWith('D:/claude-tmp/thoradar-www-legacy-')) {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    console.log('LEGACY_PROFILE_REMOVED');
  } else {
    console.log('LEGACY_PROFILE_PRESERVED ' + profile);
  }
  if (result.summary.failed) process.exitCode = 1;
}
