#!/usr/bin/env node
// T1125-POOLUP 界面截图。用法：node tests/poolup/poolup_shots.mjs [--target index.html] [--out deliver/shots] [--label shots]
// 所有状态由 localStorage 种子＋真实界面点击构成；零网络、零 AI、零 Key。
import {readFileSync,writeFileSync,mkdirSync,rmSync,statSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {ROOT,sleep,sha256,argOf,ledger,startServer,connect,Tab,wire,launch,freePort,P,CACHE_KEY,seedFresh,LS,cacheHighYield} from './lib.mjs';
const argv=process.argv.slice(2),TARGET=resolve(ROOT,argOf(argv,'--target',join(ROOT,'index.html'))),OUT=resolve(argOf(argv,'--out',join(ROOT,'deliver','shots'))),LABEL=argOf(argv,'--label','shots');
const CHROME=argOf(argv,'--chrome','C:/Program Files/Google/Chrome/Application/chrome.exe'),SCRATCH_ROOT=resolve(process.env.POOLUP_SCRATCH||join(tmpdir(),`thoradar-t1125-poolup-shots-${LABEL}`)),SCRATCH=join(SCRATCH_ROOT,'harness');
const L=ledger(),{check,note}=L;let VW=1440,VH=900,count=0;
const metrics=(tab,w,h,mobile=false,scale=1)=>{VW=w;VH=h;return tab.h.cdp.send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:scale,mobile},tab.sid)};
async function shot(tab,name,clip=null){count++;if(clip){const moved=await tab.eval(`(()=>{const e=document.querySelector(${JSON.stringify(clip)});if(!e)return false;e.scrollIntoView({block:'center',behavior:'instant'});return true})()`);if(!moved)throw new Error('截图目标不存在 '+clip);await sleep(500);const r=await tab.eval(`(()=>{const e=document.querySelector(${JSON.stringify(clip)}),r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}})()`);if(r.bottom<=0||r.y>=VH||r.right<=0||r.x>=VW)throw new Error(`截图目标不在视口 ${clip} ${JSON.stringify(r)}`);const x=Math.max(0,r.x-8),y=Math.max(0,r.y-8),rect={x,y,width:Math.min(VW-x,r.right+8-x),height:Math.min(VH-y,r.bottom+8-y),scale:1};const {data}=await tab.h.cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,clip:rect},tab.sid);writeFileSync(join(OUT,name+'.png'),Buffer.from(data,'base64'))}else{const {data}=await tab.h.cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},tab.sid);writeFileSync(join(OUT,name+'.png'),Buffer.from(data,'base64'))}const bytes=statSync(join(OUT,name+'.png')).size;check(bytes>4000,name+' 文件过小 '+bytes);note(`${name}.png ${bytes} bytes｜viewport ${VW}x${VH}${clip?'｜clip '+clip:''}`)}
async function group(id,name,fn){L.begin(id,name);try{await fn()}catch(e){check(false,e.message)}L.end()}
async function seeded(tab,origin){const f=await seedFresh(tab,origin,{days:1,mix:true});await tab.eval(`(()=>{const c=JSON.parse(localStorage.getItem('${CACHE_KEY}'));c.byNlm['9900001'].items[1].day=${JSON.stringify(f.anchor)};c.byNlm['9900001'].items[1].date=${JSON.stringify(f.anchor.slice(0,4))};localStorage.setItem('${CACHE_KEY}',JSON.stringify(c));return 1})()`);await tab.goto(`${origin}/index.html`);await sleep(400);return f}
async function main(){rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});mkdirSync(OUT,{recursive:true});const srv=await startServer({target:TARGET}),port=await freePort(),profile=join(SCRATCH,'profile'),browser=await launch({chrome:CHROME,profile,port,label:LABEL});let cdp,tab;try{
 console.log(`poolup shots | ${browser.ver.Browser} | target=${TARGET} sha256=${sha256(readFileSync(TARGET))} | out=${OUT}`);cdp=await connect(browser.ver.webSocketDebuggerUrl);const h={cdp,origin:srv.origin,tabs:new Map()};wire(h);tab=new Tab(h,'S');await tab.open(`${srv.origin}/index.html`);await metrics(tab,1440,900);const f=await seeded(tab,srv.origin);
 await group('V1','概览：两条池外带标＋混排开关',async()=>{check(await tab.eval('document.querySelectorAll("#queue-list [data-pool-badge]").length')===2,'概览不是两条池外');await shot(tab,'01-overview-mixed');await shot(tab,'02-queue-and-toggle','.queue-panel')});
 await group('V2','阅读：池外卡在前 12 条且带标',async()=>{await tab.eval(P.view('reading'));await sleep(350);check(await tab.eval('document.querySelectorAll("#queue-list [data-pool-badge]").length')>=1,'阅读卡无池外徽章');await shot(tab,'03-reading-mixed');await shot(tab,'04-reading-card','#queue-list [data-select="pool_88000001"]')});
 await group('V3','详情：池外来源、无官方档位/阵地',async()=>{await tab.eval(P.view('overview'));await tab.eval(P.click('[data-select="pool_88000001"]'));await sleep(300);check(await tab.eval('document.querySelector("#detail").textContent.includes("池外 · 无官方档位")'),'详情缺池外说明');await shot(tab,'05-pool-detail','#detail')});
 await group('V4','开关关闭：同一缓存不再混入，官方条仍在',async()=>{await tab.eval(P.check('#pool-mix-toggle',false));await sleep(300);check(await tab.eval('document.querySelectorAll("#queue-list [data-pool-badge]").length')===0,'关闭后徽章仍在');await shot(tab,'06-mix-official-only')});
 await group('V5','英文界面：开关与徽章随 I18N',async()=>{await tab.eval(P.check('#pool-mix-toggle',true));await tab.eval(P.click('#lang-btn'));await sleep(350);check(await tab.eval('document.querySelector("#queue-list").textContent.includes("Off-pool")'),'英文徽章缺');await shot(tab,'07-english-mixed')});
 await group('V6','深色：池外徽章沿用既有徽章令牌',async()=>{await tab.eval(P.click('#lang-btn'));await tab.eval(P.click('#theme-btn'));await sleep(350);await shot(tab,'08-dark-mixed')});
 await group('V7','窄屏 390×844（模拟）：阅读池外卡不白板',async()=>{await metrics(tab,390,844,true,2);await tab.eval(P.view('reading'));await sleep(400);await shot(tab,'09-mobile-reading')});
 await group('V8','FIX-1：高产 17 条池外时概览全列出、阅读 top12 仅 3 池外＋9 官方',async()=>{
   await metrics(tab,1440,900);await tab.eval(P.view('overview'));await tab.eval(P.click('#theme-btn'));
   await tab.eval(`${LS(CACHE_KEY,cacheHighYield(f.anchor,17))};1`);await tab.goto(`${srv.origin}/index.html`);await sleep(400);
   check(await tab.eval('document.querySelectorAll("#queue-list [data-select^=pool_]").length')===17,'概览未全列出 17 条池外');
   await shot(tab,'10-overview-highyield','.queue-panel');
   await tab.eval(P.view('reading'));await sleep(350);
   const cards=await tab.eval('[...document.querySelectorAll("#queue-list [data-select]")].map(e=>e.dataset.select)');
   check(cards.length===12&&cards.filter(x=>x.startsWith('pool_')).length===3,'阅读视图不是 12 条含 3 池外：'+cards.join(','));
   await shot(tab,'11-reading-cap')});
 await group('V9','FIX-3：过期缓存带「已过期」标；官方空而池外在列时空态给区分口径',async()=>{
   await tab.eval(P.view('overview'));
   await tab.eval(`(()=>{const c=JSON.parse(localStorage.getItem('${CACHE_KEY}'));Object.values(c.byNlm).forEach(x=>{x.until=Date.now()-1000});localStorage.setItem('${CACHE_KEY}',JSON.stringify(c));return 1})()`);
   await tab.goto(`${srv.origin}/index.html`);await sleep(400);
   check(await tab.eval('document.querySelectorAll("#queue-list [data-pool-stale]").length')>0,'过期缓存条缺「已过期」标识');
   await shot(tab,'12-stale-badge','.queue-panel');
   for(const tier of ['S','A','B','C','D'])await tab.eval(P.click(`#tier-filters [data-tier="${tier}"]`));await sleep(300);
   check(await tab.eval('document.querySelector("#scope-empty").textContent.includes("池外缓存有")'),'空态未给池外区分口径');
   await shot(tab,'13-empty-scope-pool');
   for(const tier of ['S','A','B','C','D'])await tab.eval(P.click(`#tier-filters [data-tier="${tier}"]`))});
 check(tab.errors.length===0,'页面异常 '+tab.errors.join('|'));check(tab.log.length===0&&srv.ai.log.length===0,'截图流程发生网络/AI 请求');note(`共 ${count} 张，全部来自真实 DOM；NCBI=0 AI=0`);
 }finally{try{cdp&&cdp.close()}catch(e){}const left=await browser.stop();srv.server.close();rmSync(SCRATCH_ROOT,{recursive:true,force:true});console.log(`cleanup 临时目录已清｜残留 ${left}`)}process.exit(L.finish(`POOLUP SHOTS [${LABEL}]`)?1:0)}
main().catch(e=>{console.log('截图脚本崩溃 '+(e&&e.stack||e));try{rmSync(SCRATCH_ROOT,{recursive:true,force:true})}catch(e2){}process.exit(2)});
