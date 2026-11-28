import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Tab, connect, freePort, launch, startServer, wire } from '../../../tests/aicls/lib.mjs';

const evidence = dirname(fileURLToPath(import.meta.url));
const repo = fileURLToPath(new URL('../../../', import.meta.url));
const live = process.env.THORADAR_LIVE === '1';
const outputFile = live ? join(evidence, 'online-release', 'browser-final.json') : join(evidence, 'browser-check.json');
const shots = live ? join(evidence, 'online-release', 'screens') : join(evidence, 'screens');
mkdirSync(shots, { recursive: true });
const scratch = mkdtempSync(join(tmpdir(), 'thoradar-branding-'));
const result = { rows: [], cleanup: {} };
let browser;
let harness;
let server;
try {
  server = live ? { origin: 'https://thoradar.online' } : await startServer({ target: join(repo, 'index.html'), baseline: join(repo, 'index.html') });
  browser = await launch({ chrome: 'C:/Program Files/Google/Chrome/Application/chrome.exe', profile: join(scratch, 'profile'), port: await freePort(), label: 'branding' });
  harness = { cdp: await connect(browser.ver.webSocketDebuggerUrl), tabs: new Map(), origin: server.origin };
  wire(harness);
  {
    for (const [w, h] of [[1422, 800], [2134, 1073], [901, 1000], [390, 844]]) {
      const t = new Tab(harness, `${w}x${h}`);
      const cdp = (method, params) => harness.cdp.send(method, params, t.sid);
      try {
        await t.open(`${server.origin}/index.html`);
        await cdp('Network.setBypassServiceWorker', { bypass: true });
        await cdp('Storage.clearDataForOrigin', { origin: server.origin, storageTypes: 'all' });
        await cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w === 390 });
        await t.goto(`${server.origin}/index.html`);
        for (const lang of ['zh', 'en']) {
          await t.eval(`setLang(${JSON.stringify(lang)})`);
          const measured = await t.eval(`(() => {
            const q = s => document.querySelector(s);
            const visible = e => !!e && e.checkVisibility();
            const r = e => { const x = e.getBoundingClientRect(); return { x:x.x,y:x.y,right:x.right,bottom:x.bottom,width:x.width,height:x.height }; };
            const header = r(q('.topbar'));
            const children = [...q('.topbar').children].filter(visible).map(e => ({ name:e.id||e.className, ...r(e) }));
            const separate = (a,b) => a.right <= b.x+.5 || b.right <= a.x+.5 || a.bottom <= b.y+.5 || b.bottom <= a.y+.5;
            return {
              lang:document.documentElement.lang,
              title:document.title,
              brand:q('.brand-name').textContent,
              subtitle:q('.brand-sub').textContent,
              docWidth:document.documentElement.scrollWidth,
              bodyWidth:document.body.scrollWidth,
              header,
              headerOK:children.every((a,i) => a.x >= header.x-.5 && a.right <= header.right+.5 && a.y >= header.y-.5 && a.bottom <= header.bottom+.5 && children.slice(i+1).every(b => separate(a,b))),
              footer:q('.footer').innerText,
              beian:visible(q('.beian')),
              oldFooterNode:!!q('[data-i18n="foot.note"]')
            };
          })()`);
          const expected = lang === 'zh' ? { title:'Thoradar · 滚动信号场', subtitle:'胸科医学文献 · 每日扫描与个性化追踪' } : { title:'Thoradar · Rolling Signal Field', subtitle:'Thoracic Medical Literature · Daily Scanning and Personalized Tracking' };
          const checks = {
            brand: measured.brand === 'Thoradar',
            title: measured.title === expected.title,
            subtitle: measured.subtitle === expected.subtitle,
            noHorizontalOverflow: Math.max(measured.docWidth, measured.bodyWidth) <= w,
            headerOK: measured.headerOK,
            footerRemoved: !measured.oldFooterNode && !/程序生成|Auto-generated|临床判断|clinical decisions/.test(measured.footer),
            beianVisible: measured.beian,
            noPageErrors: t.errors.length === 0,
          };
          const row = { viewport:[w,h], lang, pass:Object.values(checks).every(Boolean), checks, measured, errors:[...t.errors] };
          result.rows.push(row);
          console.log(`${row.pass ? 'PASS' : 'FAIL'} ${w}x${h} ${lang} ${JSON.stringify(row)}`);
          const image = await cdp('Page.captureScreenshot', { format:'png' });
          writeFileSync(join(shots, `${w}x${h}-${lang}.png`), Buffer.from(image.data, 'base64'));
        }
      } finally { await t.close(); }
    }
  }
} catch (error) { result.harnessError = String(error); } finally {
  harness?.cdp.close();
  if (browser) result.cleanup.residual = await browser.stop();
  if (server?.server) await new Promise(resolve => server.server.close(resolve));
  rmSync(scratch, { recursive:true, force:true });
  result.cleanup.profileRemoved = true;
}
result.summary = { passed:result.rows.filter(x => x.pass).length, failed:result.rows.filter(x => !x.pass).length };
writeFileSync(outputFile, JSON.stringify(result, null, 2) + '\n');
console.log('SUMMARY ' + JSON.stringify(result.summary));
if (result.harnessError || result.summary.failed || result.cleanup.residual) process.exitCode = 1;
