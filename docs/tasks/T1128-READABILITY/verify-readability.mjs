import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Tab, connect, freePort, launch, startServer, wire } from '../../../tests/aicls/lib.mjs';
const evidence = dirname(fileURLToPath(import.meta.url));
const repo = fileURLToPath(new URL('../../../', import.meta.url));
const baseRev = '2826461b93d0ae7d099746e12544bfbaaf960f93';
const scratch = mkdtempSync(join(tmpdir(), 'thoradar-readability-'));
const shots = join(evidence, 'screens');
mkdirSync(shots, { recursive: true });
const result = { baseRev, rows: [], cleanup: {} };
let browser, harness, server;
try {
  const baseline = join(scratch, 'baseline.html');
  writeFileSync(baseline, execFileSync('git', ['-C', repo, 'show', `${baseRev}:index.html`], { encoding: 'utf8' }));
  server = await startServer({ target: join(repo, 'index.html'), baseline });
  browser = await launch({ chrome: 'C:/Program Files/Google/Chrome/Application/chrome.exe', profile: join(scratch, 'profile'), port: await freePort(), label: 'readability' });
  harness = { cdp: await connect(browser.ver.webSocketDebuggerUrl), tabs: new Map(), origin: server.origin };
  wire(harness);
  for (const [variant, path] of [['baseline', '/baseline.html'], ['candidate', '/index.html']]) {
    for (const [w, h, lang] of [[1422,800,'zh'],[1422,800,'en'],[2134,1073,'en'],[1366,768,'en'],[1180,900,'en'],[1024,900,'en'],[901,1000,'en'],[900,1000,'en'],[390,844,'zh'],[390,844,'en']]) {
      const t = new Tab(harness, `${variant}-${w}-${lang}`);
      const cdp = (method, params) => harness.cdp.send(method, params, t.sid);
      try {
        await t.open(`${server.origin}/index.html`);
        await cdp('Network.setBypassServiceWorker', { bypass: true });
        await cdp('Storage.clearDataForOrigin', { origin: server.origin, storageTypes: 'all' });
        await cdp('Emulation.setDeviceMetricsOverride', { width:w, height:h, deviceScaleFactor:1, mobile:w===390 });
        await t.goto(`${server.origin}${path}`);
        await t.eval(`setLang(${JSON.stringify(lang)})`);
        const measured = await t.eval(`(() => {
          const q=s=>document.querySelector(s), r=e=>{const x=e.getBoundingClientRect();return {x:x.x,y:x.y,right:x.right,bottom:x.bottom,width:x.width,height:x.height}};
          const fs=e=>parseFloat(getComputedStyle(e).fontSize), header=r(q('.topbar'));
          const children=[...q('.topbar').children].filter(e=>e.checkVisibility()).map(e=>({name:e.id||e.className,...r(e)}));
          const sep=(a,b)=>a.right<=b.x+.5||b.right<=a.x+.5||a.bottom<=b.y+.5||b.bottom<=a.y+.5;
          const inside=(a,b)=>a.x>=b.x-.5&&a.right<=b.right+.5&&a.y>=b.y-.5&&a.bottom<=b.bottom+.5;
          const textBox=e=>{const range=document.createRange();range.selectNodeContents(e);return r({getBoundingClientRect:()=>range.getBoundingClientRect()})};
          const controls=[...document.querySelectorAll('.proto-view-btn'),q('.filters-toggle')].filter(e=>e.checkVisibility()).map(e=>({id:e.id||e.className,box:r(e),text:textBox(e),clientWidth:e.clientWidth,scrollWidth:e.scrollWidth}));
          const active=q('.proto-view-btn[aria-selected="true"]'),inactive=q('.proto-view-btn[aria-selected="false"]');
          const switcher=q('.proto-view-switcher'),brand=q('.brand'),sub=q('.brand-sub');
          const controlContentOK=controls.every(e=>e.scrollWidth<=e.clientWidth+1&&inside(e.text,e.box))&&switcher.scrollWidth<=switcher.clientWidth+1&&brand.scrollWidth<=brand.clientWidth+1&&inside(textBox(sub),r(brand));
          return {title:document.title,brand:q('.brand-name').textContent,brandSize:fs(q('.brand-name')),subtitle:q('.brand-sub').textContent,subtitleSize:fs(q('.brand-sub')),searchPh:q('#search').placeholder,scanDate:q('#scan-date').textContent,scanNote:q('#scan-time').textContent,
            queue:q('.queue-panel h2').textContent,scope:q('.scope-head h1').textContent,eyebrow:q('.scope-head .eyebrow').textContent,hub:q('.scope-hub small').textContent,
            visibleTerminologyOK:!/\\bsignals?\\b|信号/i.test([q('.topbar'),q('.queue-title'),q('.scope-head'),q('.scope-foot')].map(e=>e.innerText).join('\\n')),
            tabSize:fs(active),tabHeight:r(active).height,activeBg:getComputedStyle(active).backgroundColor,inactiveBg:getComputedStyle(inactive).backgroundColor,
            activeColor:getComputedStyle(active).color,inactiveColor:getComputedStyle(inactive).color,
            filterSize:fs(q('.filters-toggle')),filterHeight:r(q('.filters-toggle')).height,
            docWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,controlContentOK,controls,
            switcherWidth:switcher.clientWidth,switcherScrollWidth:switcher.scrollWidth,brandWidth:brand.clientWidth,brandScrollWidth:brand.scrollWidth,
            headerOK:children.every((a,i)=>a.x>=header.x-.5&&a.right<=header.right+.5&&a.y>=header.y-.5&&a.bottom<=header.bottom+.5&&children.slice(i+1).every(b=>sep(a,b)))};
        })()`);
        const checks = variant === 'candidate' ? {
          brand: measured.brand === 'Thoradar',
          labels: measured.title === (lang==='zh'?'Thoradar · 胸科文献雷达':'Thoradar · Thoracic Literature Radar') && measured.queue === (lang==='zh'?'文献队列':'Literature queue') && measured.scope === (lang==='zh'?'胸科文献雷达':'Thoracic literature radar') && measured.eyebrow === (lang==='zh'?'每日新文献':'Daily new research') && measured.hub === (lang==='zh'?'文献':'PAPERS'),
          searchAndMeta: measured.searchPh === (lang==='zh'?'检索文献…':'Search the literature…') && measured.scanDate.endsWith(lang==='zh'?'数据日期':'DATA DATE') && measured.scanNote.includes(lang==='zh'?'出版状态已标注':'Publication status annotated'),
          visibleTerminology: measured.visibleTerminologyOK,
          brandProminent: measured.brandSize >= (w===1422||w===2134?24:22) && measured.subtitleSize >= (w===1422||w===2134?12:w===390?10.5:11),
          tabsVisible: measured.tabSize >= 12 && measured.tabHeight >= 36 && (measured.activeBg !== measured.inactiveBg || measured.activeColor !== measured.inactiveColor),
          filterVisible: measured.filterSize >= 12 && measured.filterHeight >= 36,
          noOverflow: Math.max(measured.docWidth, measured.bodyWidth) <= w,
          headerOK: measured.headerOK,
          controlContentOK: measured.controlContentOK,
          noErrors: t.errors.length === 0,
        } : { rendered: measured.brand === 'Thoradar' };
        const row = { variant, viewport:[w,h], lang, pass:Object.values(checks).every(Boolean), checks, measured, errors:[...t.errors] };
        result.rows.push(row);
        console.log(`${row.pass?'PASS':'FAIL'} ${variant} ${w}x${h} ${lang} ${JSON.stringify(row)}`);
        const image = await cdp('Page.captureScreenshot', { format:'png' });
        writeFileSync(join(shots, `${variant}-${w}x${h}-${lang}.png`), Buffer.from(image.data,'base64'));
      } finally { await t.close(); }
    }
  }
} catch (error) { result.harnessError = String(error); } finally {
  harness?.cdp.close();
  if (browser) result.cleanup.residual = await browser.stop();
  if (server?.server) await new Promise(resolve => server.server.close(resolve));
  rmSync(scratch, { recursive:true, force:true });
}
const candidateRows = result.rows.filter(x => x.variant === 'candidate');
const baseline901 = result.rows.find(x => x.variant === 'baseline' && x.viewport[0] === 901);
const baseline1422 = result.rows.find(x => x.variant === 'baseline' && x.viewport[0] === 1422 && x.lang === 'en');
result.negativeControls = {
  baseline901InternalClippingDetected: baseline901?.measured.controlContentOK === false,
  baseline1422LegacyTerminologyDetected: baseline1422?.measured.visibleTerminologyOK === false,
};
result.summary = {
  passed:result.rows.filter(x=>x.pass).length,
  failed:result.rows.filter(x=>!x.pass).length,
  candidateChecksPassed:candidateRows.reduce((n,row)=>n+Object.values(row.checks).filter(Boolean).length,0),
  candidateChecksTotal:candidateRows.reduce((n,row)=>n+Object.keys(row.checks).length,0),
};
writeFileSync(join(evidence,'browser-check.json'),JSON.stringify(result,null,2)+'\n');
console.log('SUMMARY '+JSON.stringify(result.summary)+' NEGATIVE '+JSON.stringify(result.negativeControls));
if(result.harnessError||result.summary.failed||result.cleanup.residual||Object.values(result.negativeControls).some(x=>!x))process.exitCode=1;
