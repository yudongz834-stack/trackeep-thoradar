import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Tab, connect, freePort, launch, wire } from '../../../../tests/aicls/lib.mjs';

const evidence = dirname(fileURLToPath(import.meta.url));
const output = join(evidence, 'live-viewports.json');
const shots = join(evidence, 'live');
mkdirSync(shots, { recursive: true });
const scratch = mkdtempSync(join(tmpdir(), 'thoradar-responsive-live-'));
const expected = new Map([[1422, 477.7], [2134, 620], [901, 284], [390, 370]]);
const sizes = [[1422, 800], [2134, 1073], [901, 1000], [390, 844]];
const result = { headSha: execFileSync('git', ['-C', 'D:/trackeep/trackeep-product/trackeep-thoradar', 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), startedAt: new Date().toISOString(), rows: [], cleanup: {} };
let browser;
let harness;
try {
  browser = await launch({ chrome: 'C:/Program Files/Google/Chrome/Application/chrome.exe', profile: join(scratch, 'profile'), port: await freePort(), label: 'responsive-live' });
  harness = { cdp: await connect(browser.ver.webSocketDebuggerUrl), tabs: new Map(), origin: 'https://thoradar.online' };
  wire(harness);
  for (const [w, h] of sizes) {
    const t = new Tab(harness, `${w}x${h}`);
    const cdp = (method, params) => harness.cdp.send(method, params, t.sid);
    const row = { viewport: [w, h], expectedDial: expected.get(w), errors: [] };
    try {
      await t.open('https://thoradar.online/index.html');
      await cdp('Network.enable', {});
      await cdp('Network.setBypassServiceWorker', { bypass: true });
      await cdp('Network.setCacheDisabled', { cacheDisabled: true });
      await cdp('Storage.clearDataForOrigin', { origin: 'https://thoradar.online', storageTypes: 'all' });
      await cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w === 390 });
      await cdp('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
      await t.goto('https://thoradar.online/index.html');
      const measured = await t.eval(`(() => {
        const q = s => document.querySelector(s);
        const rect = e => { const r = e.getBoundingClientRect(); return { x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom }; };
        const stage = rect(q('.scope-stage'));
        const dial = rect(q('#scope'));
        const labels = [...document.querySelectorAll('#scope-labels .scope-label')].filter(e => e.checkVisibility()).map(rect);
        const points = [...document.querySelectorAll('#blips .blip:not(.dim)')].filter(e => e.checkVisibility());
        return {
          viewport:[innerWidth,innerHeight], ready:document.body.dataset.protoReady,
          date:SITE_DATA.briefing_date, papers:PAPERS.length,
          docWidth:document.documentElement.scrollWidth, bodyWidth:document.body.scrollWidth,
          grid:getComputedStyle(q('.deck')).gridTemplateColumns, dial, stage,
          labelsOutside:labels.filter(r => r.x < stage.x-.5 || r.right > stage.right+.5 || r.y < stage.y-.5 || r.bottom > stage.bottom+.5).length,
          points:points.length,
          excerptFont:getComputedStyle(q('#detail .excerpt')).fontSize
        };
      })()`);
      Object.assign(row, measured);
      row.checks = {
        ready: measured.ready === 'true' && measured.date === '2026-11-28' && measured.papers === 43,
        viewport: measured.viewport[0] === w && measured.viewport[1] === h,
        noHorizontalOverflow: Math.max(measured.docWidth, measured.bodyWidth) <= w,
        expectedDial: Math.abs(measured.dial.width - expected.get(w)) <= 0.75 && Math.abs(measured.dial.width - measured.dial.height) <= 0.5,
        labelsInside: measured.labelsOutside === 0,
        pointsPresent: measured.points === 36,
        textNotShrunk: parseFloat(measured.excerptFont) >= 12,
      };
      row.pass = Object.values(row.checks).every(Boolean);
      const image = await cdp('Page.captureScreenshot', { format: 'png' });
      writeFileSync(join(shots, `${w}x${h}-overview.png`), Buffer.from(image.data, 'base64'));
    } catch (error) {
      row.pass = false;
      row.errors.push(String(error));
    } finally {
      row.errors.push(...t.errors);
      if (t.errors.length) row.pass = false;
      await t.close();
    }
    result.rows.push(row);
    console.log(`${row.pass ? 'PASS' : 'FAIL'} ${w}x${h} ${JSON.stringify(row)}`);
  }
} catch (error) {
  result.harnessError = String(error);
} finally {
  harness?.cdp.close();
  if (browser) result.cleanup.residual = await browser.stop();
  rmSync(scratch, { recursive: true, force: true });
  result.cleanup.profileRemoved = true;
}
result.summary = { passed: result.rows.filter(row => row.pass).length, failed: result.rows.filter(row => !row.pass).length };
result.endedAt = new Date().toISOString();
writeFileSync(output, JSON.stringify(result, null, 2) + '\n');
console.log('SUMMARY ' + JSON.stringify(result.summary));
if (result.harnessError || result.summary.failed || result.cleanup.residual) process.exitCode = 1;
