#!/usr/bin/env node
// T1127-UX 随仓验收探针：折叠、阅读可达性、矮屏雷达、字号、英文态、窄屏/深色与官方数据面差分。
// 用法：node tests/ux/ux_probe.mjs [--target index.html] [--base main] [--only F1,F9] [--shots 目录] [--label 名称]
//   --base 给 F8 官方数据面差分提供基线提交；--page baseline 可把基线当负对照（新功能不存在应红）。
// 零真 Key／零真 LLM／NCBI 全拦；临时件只落系统临时目录。零依赖，复用 tests/aicls/lib.mjs 的 CDP 客户端。
import {writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {ROOT,sleep,ledger,startServer,connect,Tab,wire,launch,freePort,P,gitRead} from '../aicls/lib.mjs';

const argv=process.argv.slice(2);
const arg=(k,d)=>{const i=argv.indexOf(k);return i>=0&&argv[i+1]&&!argv[i+1].startsWith('--')?argv[i+1]:d};
const PAGE=arg('--page','index'),JUDGE=!argv.includes('--no-judge'),LABEL=arg('--label','run');
const SHOTS=arg('--shots',null);
const CHROME=arg('--chrome','C:/Program Files/Google/Chrome/Application/chrome.exe');
const CAND=resolve(arg('--target',process.env.XREV_CAND_HTML||join(ROOT,'index.html')));
const ONLYSET=arg('--only',process.env.XREV_ONLY||'').split(',').map(s=>s.trim()).filter(Boolean),ONLY=id=>ONLYSET.length===0||ONLYSET.includes(id);
const BASE_REV=arg('--base','main');
const SCRATCH_ROOT=resolve(process.env.XREV_SCRATCH||join(tmpdir(),'T1127-ux-probe'));
const BASE=join(SCRATCH_ROOT,`baseline-${BASE_REV.replace(/[^a-zA-Z0-9._-]/g,'_')}.html`);
const SCRATCH=join(SCRATCH_ROOT,`ux-harness-${LABEL}`),OUT=join(SCRATCH_ROOT,`out-${LABEL}`);
const L=ledger(),{check,note}=L;
const HAN=/[\u4e00-\u9fff]/;

// ---------- 页面侧量测（一段纯读表达式；元素不存在一律回 null，父提交件上也能跑） ----------
const SNAP=`(()=>{const q=s=>document.querySelector(s);
 const T=e=>(e.innerText||e.textContent||'').replace(/\\s+/g,' ').trim();
 const R=s=>{const e=typeof s==='string'?q(s):s;if(!e)return null;const r=e.getBoundingClientRect(),c=getComputedStyle(e);
   return {x:+r.x.toFixed(1),y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1),bottom:+r.bottom.toFixed(1),display:c.display,fs:c.fontSize,lh:c.lineHeight,ov:c.overflow,txt:T(e).slice(0,110)}};
 const list=q('#queue-list'),lr=list?list.getBoundingClientRect():null;
 const items=list?[...list.querySelectorAll('.queue-item')]:[];
 const frac=it=>{const r=it.getBoundingClientRect();return r.height>0&&lr?Math.max(0,Math.min(r.bottom,lr.bottom)-Math.max(r.top,lr.top))/r.height:0};   // 该条在列表可视框内露出的高度占比
 const inBox=it=>{const r=it.getBoundingClientRect();return !!lr&&r.height>0&&r.top>=lr.top-0.5&&r.bottom<=lr.bottom+0.5};
 const half=it=>{const r=it.getBoundingClientRect();return !!lr&&r.height>0&&!inBox(it)&&r.bottom>lr.top+0.5&&r.top<lr.bottom-0.5};
 const tg=q('.filters-toggle'),f=q('.filters'),sc=q('#scope'),sr=sc?sc.getBoundingClientRect():null;
 const attr=(s,a)=>{const e=q(s);return e?e.getAttribute(a):null};
 const C=sr&&sr.width>0?{x:sr.left+sr.width/2,y:sr.top+sr.height/2,r:sr.width/2}:null;
 const inDisc=(x,y)=>!!C&&((x-C.x)*(x-C.x)+(y-C.y)*(y-C.y)<=C.r*C.r);
 const nm=e=>((e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)||e.tagName).toString().split(' ')[0].slice(0,24);
 const probe=el=>{if(!el||!C)return null;const r=el.getBoundingClientRect();if(r.width===0||r.height===0)return {y:0,w:0,h:0,inDisc:0,covered:0,tops:''};let n=0,inn=0,cov=0;const tops={};   // 盒内 9×3 取样：落在盘圆内的比例／最上层元素属于盘（＝这点点不到控件）的比例
   for(let i=1;i<=9;i++)for(let j=1;j<=3;j++){const x=r.left+r.width*i/10,y=r.top+r.height*j/4;if(y<0||y>innerHeight||x<0||x>innerWidth)continue;n++;if(inDisc(x,y))inn++;const e=document.elementFromPoint(x,y);if(e&&sc.contains(e)){cov++;const k=nm(e);tops[k]=(tops[k]||0)+1}}
   return {y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1),inDisc:n?+(inn/n).toFixed(2):0,covered:n?+(cov/n).toFixed(2):0,tops:Object.keys(tops).join(',')}};
 const cover={};for(const [k,sel] of Object.entries({toolbar:'.journal-toolbar',clear:'#journal-clear',selection:'#journal-selection',jcatLegend:'#jcat-legend',jlSummary:'.jl-fold summary',design:'#design-legend',scheme:'#scheme-select',progress:'.read-progress'}))cover[k]=probe(q(sel));
 cover.folds=[...document.querySelectorAll('#jcat-folds .jcat-fold')].map(probe);
 const covered=Object.entries(cover).filter(([k,v])=>k!=='folds'&&v&&v.covered>0).map(([k,v])=>k+'_'+Math.round(v.covered*100)+'%').concat(cover.folds.map((v,i)=>v&&v.covered>0?'阵地折叠钮'+(i+1)+'_'+Math.round(v.covered*100)+'%':null).filter(Boolean));
 const blips=[...document.querySelectorAll('#blips .blip')].filter(b=>getComputedStyle(b).opacity!=='0');
 const out=blips.filter(b=>{const r=b.getBoundingClientRect();return sr&&(r.left<sr.left-1||r.right>sr.right+1||r.top<sr.top-1||r.bottom>sr.bottom+1)}).length;
 const FS={};for(const [k,s] of Object.entries({cardTitle:'#queue-list .queue-item .queue-text strong',cardTitleEn:'#queue-list .proto-title-en',cardFinding:'#queue-list .proto-finding-text',cardFindingLabel:'#queue-list .proto-finding-label',cardMeta:'#queue-list .proto-card-meta',cardExtra:'#queue-list .proto-extra-block',cardDomain:'#queue-list .proto-domain',queueSmall:'#queue-list .queue-text small',
   detailExcerpt:'#detail .excerpt',detailTitle:'.detail-title',detailJournalName:'.detail-journal .journal-name',detailJournalMeta:'.detail-journal .journal-meta',badge:'#detail .badge',metaCellB:'#detail .meta-cell b',metaCellSmall:'#detail .meta-cell small',paused:'#detail .interpretation-paused',deepStrong:'#deep-box strong',deepBtn:'#deepreview-btn',actionBtn:'.detail-actions .action-btn',excerptLabelB:'#detail .excerpt-label b',excerptLabelSpan:'#detail .excerpt-label span',honesty:'#detail .honesty-note',
   footer:'.footer',toggle:'.filters-toggle',tierChip:'.tier-chip',quickBtn:'.quick-btn',filterLabel:'.filter-label',jlSummary:'.jl-fold summary',foldChip:'.jcat-fold',designLegend:'.legend',scopeLabel:'.scope-label',toolbar:'.journal-toolbar',topbarName:'.brand-name',viewBtn:'.proto-view-btn',scoreBox:'.score-box b'})){const e=q(s);FS[k]=e?getComputedStyle(e).fontSize:null}
 const metaCells=[...document.querySelectorAll('.meta-fold .meta-cell')];
 return {
  view:document.body.dataset.protoView,filtersOpen:document.body.classList.contains('filters-open'),density:document.body.dataset.protoDensity,lang:document.documentElement.lang,dark:document.documentElement.classList.contains('dark'),
  vw:innerWidth,vh:innerHeight,docSH:document.documentElement.scrollHeight,bodySH:document.body.scrollHeight,docSW:document.documentElement.scrollWidth,bodySW:document.body.scrollWidth,bodyOv:getComputedStyle(document.body).overflow,
  toggle:tg?Object.assign(R(tg),{ariaExpanded:tg.getAttribute('aria-expanded'),ariaControls:tg.getAttribute('aria-controls'),title:tg.getAttribute('title')}):null,
  filters:f?Object.assign(R(f),{cols:getComputedStyle(f).gridTemplateColumns}):null,
  queue:{n:items.length,full:items.filter(inBox).length,vis90:items.filter(it=>frac(it)>=0.9).length,half:items.filter(half).length,list:R('#queue-list'),firstH:items[0]?+items[0].getBoundingClientRect().height.toFixed(1):null},
  panel:R('.queue-panel'),head:R('.panel-head'),qtitle:R('.queue-title'),rtoolbar:R('#proto-reading-toolbar'),
  topbar:R('.topbar'),search:R('.search'),viewSwitcher:R('#proto-view-switcher'),deck:R('.deck'),footer:R('.footer'),gapUnderFooter:q('.footer')?+(innerHeight-q('.footer').getBoundingClientRect().bottom).toFixed(1):null,
  scope:R('#scope'),stage:R('.scope-stage'),scopeHead:R('.scope-head'),foot:R('.scope-foot'),
  toolbar:R('.journal-toolbar'),folds:R('#jcat-folds'),jcatLegend:R('#jcat-legend'),designLegend:R('#design-legend'),funnel:R('#funnel'),
  jl:q('.jl-fold')?Object.assign(R('.jl-fold'),{open:q('.jl-fold').open,summary:R('.jl-fold summary'),legend:R('#journal-legend'),pills:document.querySelectorAll('#journal-legend .journal-btn').length,activePills:document.querySelectorAll('#journal-legend .journal-btn.active').length}):null,
  cover,covered,maxCovered:+Math.max(0,...Object.values(cover).filter(v=>v&&!Array.isArray(v)).map(v=>v.covered),...cover.folds.map(v=>v?v.covered:0)).toFixed(2),
  clearDisabled:q('#journal-clear')?q('#journal-clear').disabled:null,blipOut:out,blipN:blips.length,
  hint:R('.ai-help[data-i18n="poolup.hint"]'),mixLabelTitle:attr('#pool-mix-control label','title'),mixCtrl:R('#pool-mix-control'),
  detail:Object.assign(R('#detail'),{panel:R('.detail-panel'),scrollH:q('.detail-panel')?q('.detail-panel').scrollHeight:null,clientH:q('.detail-panel')?q('.detail-panel').clientHeight:null,
    title:R('.detail-title'),excerpt:R('#detail .excerpt'),excerptLabel:R('#detail .excerpt-label'),honesty:R('#detail .honesty-note'),paused:R('#detail .interpretation-paused'),deep:R('#deep-box'),actions:R('.detail-actions'),nav:R('.detail-nav'),
    metaFold:q('.meta-fold')?Object.assign(R('.meta-fold'),{open:q('.meta-fold').open,cells:metaCells.length,cellsVisible:metaCells.filter(c=>c.checkVisibility()).length}):null,
    metaGrid:R('#detail .meta-grid'),journalMeta:R('.detail-journal .journal-meta'),
    order:[...document.querySelectorAll('#detail .detail-inner > *')].map(e=>(e.className||e.tagName).toString().split(' ')[0]),
    pausedTitle:attr('#detail .interpretation-paused','title'),deepTitle:attr('#deep-box','title'),pausedBrInPaused:document.querySelectorAll('#detail .interpretation > .interpretation-paused br').length,
    deepBtn:!!q('#deepreview-btn'),deepBtnVisible:!!(q('#deepreview-btn')&&q('#deepreview-btn').checkVisibility()),
    actionsInFirstScreen:q('.detail-actions')?q('.detail-actions').getBoundingClientRect().top<=innerHeight:null,excerptInFirstScreen:q('#detail .excerpt')?q('#detail .excerpt').getBoundingClientRect().top<=innerHeight:null,
    excerptVisibleH:q('#detail .excerpt')?+Math.max(0,Math.min(innerHeight,q('.detail-panel').getBoundingClientRect().bottom)-q('#detail .excerpt').getBoundingClientRect().top).toFixed(1):null}),
  texts:{toggle:tg?T(tg):null,jlSummary:q('.jl-fold summary')?T(q('.jl-fold summary')):null,metaSummary:q('.meta-fold summary')?T(q('.meta-fold summary')):null,collOpen:T(q('#coll-open')),langBtn:T(q('#lang-btn')),docTitle:document.title,foot:q('.footer')?T(q('.footer')):null},
  fs:FS};
})()`;
// 英文态「界面骨架里还剩哪些中国字」：只扫界面骨架（不含论文题名/摘要等内容）＋title／aria-label／placeholder
const CJKSCAN=`(()=>{const han=/[\\u4e00-\\u9fff]/;const out=new Set();const roots=['.topbar','.queue-panel .panel-head','.filters','.queue-title','#proto-reading-toolbar','.scope-head','.scope-foot','.footer','#detail .detail-top','#detail .detail-journal','#detail .excerpt-label','#detail .detail-actions','#detail .detail-nav','#detail .meta-fold summary'];
 const walk=root=>{if(!root)return;const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){const s=n.nodeValue.replace(/\\s+/g,' ').trim();if(s&&han.test(s)&&!/\\d{6,}/.test(s))out.add('文:'+s.slice(0,40))}
   root.querySelectorAll('[title],[aria-label],[placeholder]').forEach(e=>{for(const a of ['title','aria-label','placeholder']){const v=e.getAttribute(a);if(v&&han.test(v))out.add(a+':'+v.slice(0,40))}});
   if(root.matches&&root.matches('[title],[aria-label],[placeholder]'))for(const a of ['title','aria-label','placeholder']){const v=root.getAttribute(a);if(v&&han.test(v))out.add(a+':'+v.slice(0,40))}};
 roots.forEach(s=>walk(document.querySelector(s)));
 const tg=document.querySelector('.filters-toggle');if(tg&&han.test(tg.textContent))out.add('文:'+tg.textContent.trim());
 return [...out].sort()})()`;
const snap=async tab=>tab.eval(SNAP);
const vis=s=>Boolean(s&&s.filters&&s.filters.display!=='none'&&s.filters.h>0);
const labelOpen=s=>Boolean(s&&s.toggle&&/^收起筛选/.test(s.toggle.txt));
const shot=async(h,tab,name)=>{if(!SHOTS)return null;const r=await h.cdp.send('Page.captureScreenshot',{format:'png'},tab.sid);const p=join(SHOTS,`${LABEL}-${name}.png`);writeFileSync(p,Buffer.from(r.data,'base64'));return p};
const size=async(h,tab,w,hh,mobile=false)=>{await h.cdp.send('Emulation.setDeviceMetricsOverride',{width:w,height:hh,deviceScaleFactor:1,mobile},tab.sid);await sleep(350)};
// 新页签：先落到同源页→定视口→清库→等 450ms（防上一幕防抖落盘写回）→再清→导航
const fresh=async(h,path,w=1440,hh=714,mobile=false)=>{const t=new Tab(h,'x');await t.open(`${h.origin}/index.html`);await size(h,t,w,hh,mobile);
  await t.eval('localStorage.clear();sessionStorage.clear();1');await sleep(450);await t.eval('localStorage.clear();sessionStorage.clear();1');await t.goto(`${h.origin}${path}`);await sleep(350);return t};
const errs=(tab,where)=>{const n=tab.errors.length;check(n===0,`${where}：页面运行期异常 ${n} 条：${tab.errors.slice(0,2).join(' | ').slice(0,300)}`);return n};
const covList=s=>s.scope&&s.scope.w?(s.covered.join('＋')||'无'):null;
const maxCovered=s=>s.scope&&s.scope.w?Math.max(0,...Object.values(s.cover).filter(v=>v&&!Array.isArray(v)).map(v=>v.covered),...s.cover.folds.map(v=>v?v.covered:0)):0;
const brief=s=>({view:s.view,filters:vis(s)?`${s.filters.display} ${s.filters.w}×${s.filters.h}`:'隐',toggle:s.toggle?s.toggle.txt:null,queue:`全见 ${s.queue.full}（≥90%可见 ${s.queue.vis90}）＋半截 ${s.queue.half}／共 ${s.queue.n}`,
  topbar:s.topbar.h,deck:s.deck.h,footer:`bottom=${s.footer.bottom} 余 ${s.gapUnderFooter}px`,scope:s.scope&&s.scope.w?`${s.scope.w}×${s.scope.h} 台高${s.stage.h}`:null,盘盖住:s.scope&&s.scope.w?covList(s):null,blipOut:s.blipOut});
const sec=(id,name)=>L.begin(id,name);
const save=(name,data)=>{mkdirSync(OUT,{recursive:true});writeFileSync(join(OUT,name),JSON.stringify(data,null,1))};
const clickSector=tab=>tab.eval(`(()=>{const ss=[...document.querySelectorAll('#journal-sectors .journal-sector')];if(!ss.length)return null;const s=ss[0];s.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));return s.dataset.jcat})()`);
const mousePoint=async(h,tab,p)=>{
  await h.cdp.send('Input.dispatchMouseEvent',{type:'mouseMoved',x:p.x,y:p.y,button:'none',pointerType:'mouse'},tab.sid);
  await h.cdp.send('Input.dispatchMouseEvent',{type:'mousePressed',x:p.x,y:p.y,button:'left',clickCount:1,pointerType:'mouse'},tab.sid);
  await h.cdp.send('Input.dispatchMouseEvent',{type:'mouseReleased',x:p.x,y:p.y,button:'left',clickCount:1,pointerType:'mouse'},tab.sid);
};
const mouseClick=async(h,tab,selector)=>{
  const p=await tab.eval(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;e.scrollIntoView({block:'center',inline:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  if(!p)throw new Error(`真实鼠标目标不存在：${selector}`);
  await mousePoint(h,tab,p);
};

async function main(){
  rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});if(SHOTS)mkdirSync(SHOTS,{recursive:true});
  mkdirSync(SCRATCH_ROOT,{recursive:true});writeFileSync(BASE,gitRead(['show',`${BASE_REV}:index.html`]));
  const srv=await startServer({target:CAND,baseline:BASE}),port=await freePort(),profile=join(SCRATCH,'profile');
  const browser=await launch({chrome:CHROME,profile,port,label:LABEL});
  const h={cdp:null,tabs:new Map(),origin:srv.origin};h.cdp=await connect(browser.ver.webSocketDebuggerUrl);wire(h);
  const path=PAGE==='baseline'?'/baseline.html':'/index.html';
  try{
    console.log(`ux probe | ${browser.ver.Browser} | page=${path}（${PAGE==='baseline'?`基线 ${BASE_REV}＝负对照`:`受测件 ${CAND}`}）| judge=${JUDGE} | label=${LABEL}`);
    {const t=await fresh(h,path);const m=await t.eval('({ready:document.body.dataset.protoReady,papers:PAPERS.length,anchor:ANCHOR,lang:LANG,site:SITE_DATA.briefing_date,degraded:PAPERS.filter(p=>String(p.publish_state)==="degraded").length,hasToggle:!!document.querySelector(".filters-toggle")})');console.log('页面概况：'+JSON.stringify(m));await t.close()}
    // ================= F1 折叠行为（任务书要点 2）：1440×714 =================
    if(ONLY('F1')){
      const t=await fresh(h,path);const steps=[];
      const step=async(name,fn)=>{if(fn)await fn();await sleep(250);const s=await snap(t);steps.push({name,...s});console.log(`  [${name}] ${JSON.stringify(brief(s))}`);return s};
      const clickToggle=()=>t.eval(P.click('.filters-toggle'));
      const s0=await step('A0 概览首屏（缺省）');
      const s1=await step('A1 概览点折叠钮①',clickToggle);
      const s2=await step('A2 概览点折叠钮②',clickToggle);
      const s3=await step('A3 概览点折叠钮③',clickToggle);
      const s4=await step('B1 切到阅读',()=>t.eval(P.view('reading')));await shot(h,t,'1440x714-reading-default');
      const s5=await step('B2 阅读点折叠钮（展开）',clickToggle);await shot(h,t,'1440x714-reading-filters-open');
      const s6=await step('B3 阅读再点（收起）',clickToggle);
      const s7=await step('B4 阅读再点（展开）',clickToggle);
      const s8=await step('C1 阅读(展开)→切概览',()=>t.eval(P.view('overview')));
      const s9=await step('C2 概览→切回阅读',()=>t.eval(P.view('reading')));
      await t.eval(P.view('overview'));await sleep(300);
      const s10=await step('D1 刷新后',()=>t.goto(`${h.origin}${path}`));await shot(h,t,'1440x714-overview-default');
      const matrix=[['A0',s0],['A1',s1],['A2',s2],['A3',s3],['B1',s4],['B2',s5],['B3',s6],['B4',s7],['C1',s8],['C2',s9],['D1',s10]].map(([n,s])=>({n,view:s.view,filtersVisible:vis(s),label:s.toggle?s.toggle.txt:'（无折叠钮）',labelSaysOpen:labelOpen(s)}));
      const mismatch=matrix.filter(m=>m.labelSaysOpen!==m.filtersVisible);
      console.log('  标签—状态矩阵：'+matrix.map(m=>`${m.n}[${m.view}] 筛选区${m.filtersVisible?'显':'隐'} 钮「${m.label}」${m.labelSaysOpen!==m.filtersVisible?' ✗错位':''}`).join(' ｜ '));
      save('f1-steps.json',steps.map(s=>({...s,fs:undefined,cover:{foldsN:s.cover.folds.length,covered:s.covered}})));
      if(JUDGE&&!s0.toggle){for(const [id,name] of [['F2a','阅读视图默认筛选区收起成一行'],['F2b','阅读视图点击展开、再点收起'],['F2c','概览默认展开、点击收起后队列条目数明显增多'],['F2d','概览→阅读切换时阅读恒收起'],['F2e','刷新后行为一致'],['F2f','折叠钮标签与筛选区实际状态一致'],['F2g','折叠钮带无障碍状态标注']]){sec(id,name);check(false,'页面没有折叠钮（功能不存在＝负对照应红）');L.end()}}
      if(JUDGE&&s0.toggle){
        sec('F2a','F2a 阅读视图默认筛选区收起成一行');check(s4.view==='reading'&&!vis(s4)&&s4.toggle&&s4.toggle.h>0&&s4.toggle.h<=40,`概览→阅读：筛选区应默认收起、只留一行钮；实得 filters display=${s4.filters.display} h=${s4.filters.h} 钮高 ${s4.toggle&&s4.toggle.h}`);note(`阅读进场：筛选区 display=${s4.filters.display}（高 ${s4.filters.h}px）｜钮「${s4.toggle.txt}」${s4.toggle.w}×${s4.toggle.h}px｜首屏全见阅读卡 ${s4.queue.full} 张（另 ${s4.queue.half} 张半截）`);L.end();
        sec('F2b','F2b 阅读视图点击展开、再点收起');check(vis(s5)&&s5.filters.display==='grid',`阅读展开后筛选区应可见（grid）；实得 display=${s5.filters.display} h=${s5.filters.h} cols=${s5.filters.cols}`);check(!vis(s6),`再点应收起；实得 display=${s6.filters.display}`);check(vis(s7),'再点应重新展开');note(`展开：${s5.filters.w}×${s5.filters.h}px，列=${s5.filters.cols}；首屏全见阅读卡 收起 ${s4.queue.full} 张 → 展开 ${s5.queue.full} 张`);L.end();
        sec('F2c','F2c 概览默认收起、点击展开后再收起，队列空间随动作增减');check(s0.view==='overview'&&!vis(s0),`概览缺省应收起筛选区；实得 display=${s0.filters.display}`);check(vis(s1)&&vis(s3),`概览点钮应展开；实得 A1 display=${s1.filters.display}／A3 display=${s3.filters.display}`);check(!vis(s2),'概览再点应收起');check(s2.queue.full>s1.queue.full,`收起后全见条目应增多：展开 ${s1.queue.full} 条 → 收起 ${s2.queue.full} 条`);note(`1440×714 队列全见条目：展开 ${s1.queue.full}（另 ${s1.queue.half} 条半截）→ 收起 ${s2.queue.full}（另 ${s2.queue.half} 条半截）｜列表可视高 ${s1.queue.list.h}px → ${s2.queue.list.h}px`);L.end();
        sec('F2d','F2d 双视图各自保留展开选择，切页不错位');check(!vis(s4),'首次进阅读应默认收起');check(vis(s8)&&s8.view==='overview','阅读展开时切概览，应恢复概览此前的展开态');check(vis(s9),`阅读此前已展开，切回后应仍展开；实得 display=${s9.filters.display}`);L.end();
        sec('F2e','F2e 刷新后回到双视图默认收起（不把临时展开态持久化）');check(s10.view==='overview'&&!vis(s10)&&s10.filtersOpen===false&&s10.toggle.txt===s0.toggle.txt,`刷新后应回概览且筛选收起；实得 view=${s10.view} filtersOpen=${s10.filtersOpen} 钮「${s10.toggle.txt}」`);note(`刷新后：概览、筛选区 display=${s10.filters.display}、钮「${s10.toggle.txt}」、队列全见 ${s10.queue.full} 条（首屏 ${s0.queue.full} 条）`);L.end();
        sec('F2f','F2f 折叠钮标签与筛选区实际状态一致（钮写「收起筛选」当且仅当筛选区正开着）');check(mismatch.length===0,`标签与实际状态错位 ${mismatch.length} 步：${mismatch.map(m=>`${m.n}[${m.view}] 筛选区${m.filtersVisible?'开着':'收着'}而钮写「${m.label}」`).join('；')}`);L.end();
        sec('F2g','F2g 折叠钮带无障碍状态标注');check(s0.toggle.ariaExpanded!==null,`折叠钮缺 aria-expanded（实得 ${s0.toggle.ariaExpanded}）；aria-controls=${s0.toggle.ariaControls}`);L.end();
        sec('F2h','F2h 折叠流页面零运行期异常');errs(t,'F1 折叠流');L.end();
      }
      await t.close();
    }
    // ================= F3 矮屏裁切（任务书要点 3）：多档视口高 =================
    if(ONLY('F3')){
      const t=await fresh(h,path);const rows=[];
      const ensureOpen=async()=>{const s=await snap(t);if(s.toggle&&!s.filtersOpen){await t.eval(P.click('.filters-toggle'));await sleep(200)}};
      for(const [w,hh,tag] of [[1440,714,'验收档'],[1440,900,'主控截图档'],[1366,768,'常见笔记本'],[1280,720,'720p'],[1536,864,'1080p@125%'],[1920,1080,'1080p'],[1440,660,'更矮'],[1440,600,'更矮']]){
        await size(h,t,w,hh);await ensureOpen();await sleep(200);
        const open=await snap(t);
        let closed=open;if(open.toggle){await t.eval(P.click('.filters-toggle'));await sleep(200);closed=await snap(t);await t.eval(P.click('.filters-toggle'));await sleep(200)}   // 父提交件无钮：原态即「展开态」
        if(w===1440&&hh===714){await shot(h,t,'1440x714-overview-open');if(open.toggle){await t.eval(P.click('.filters-toggle'));await sleep(200);await shot(h,t,'1440x714-overview-closed');await t.eval(P.click('.filters-toggle'));await sleep(150)}}
        if(w===1440&&hh===900){await shot(h,t,'1440x900-overview-open');if(open.toggle){await t.eval(P.click('.filters-toggle'));await sleep(200);await shot(h,t,'1440x900-overview-closed');await t.eval(P.click('.filters-toggle'));await sleep(150)}}
        await t.eval(P.view('reading'));await sleep(400);const rd=await snap(t);if(w===1440&&hh===714)await shot(h,t,'1440x714-reading');if(w===1440&&hh===900)await shot(h,t,'1440x900-reading');await t.eval(P.view('overview'));await sleep(300);
        const footerOK=open.footer.bottom<=hh+0.5&&open.footer.h>=35.5;
        rows.push({tag,size:`${w}×${hh}`,topbar:open.topbar.h,deck:open.deck.h,footerBottom:open.footer.bottom,footerH:open.footer.h,gap:open.gapUnderFooter,footerOK,footTxt:(open.texts.foot||'').slice(0,60),bodyOv:open.bodyOv,docSH:open.docSH,
          scope:`${open.scope.w}×${open.scope.h}`,stageH:open.stage.h,footH:open.foot.h,headH:open.scopeHead.h,foldN:open.cover.folds.length,covered:open.covered,maxCovered:maxCovered(open),cover:open.cover,blipOut:open.blipOut,
          qOpen:open.queue.full,qOpenHalf:open.queue.half,qClosed:closed.queue.full,qClosedHalf:closed.queue.half,filtersH:open.filters.h,hintH:open.hint.h,funnelH:open.funnel.h,
          readCards:rd.queue.full,readHalf:rd.queue.half,readListH:rd.queue.list.h,readFiltersH:rd.filters.h,detailPanelH:rd.detail.panel.h,excerptY:rd.detail.excerpt&&rd.detail.excerpt.y,excerptIn:rd.detail.excerptInFirstScreen,actionsY:rd.detail.actions&&rd.detail.actions.y,metaGridH:rd.detail.metaGrid.h});
        console.log(`  [${tag} ${w}×${hh}] 顶栏 ${open.topbar.h}｜主区 ${open.deck.h}｜页脚 bottom=${open.footer.bottom}（视口下余 ${open.gapUnderFooter}px，${footerOK?'完整':'被裁'}）｜盘 ${open.scope.w}×${open.scope.h}（台高 ${open.stage.h}）｜盘盖住：${covList(open)}｜出盘点 ${open.blipOut}/${open.blipN}｜队列全见 开${open.queue.full}(+${open.queue.half}半)/收${closed.queue.full}(+${closed.queue.half}半)｜阅读首屏卡 ${rd.queue.full}(+${rd.queue.half}半) 筛选区高 ${rd.filters.h}｜摘要顶 ${rd.detail.excerpt&&rd.detail.excerpt.y} 按钮顶 ${rd.detail.actions&&rd.detail.actions.y}`);
      }
      // 选了扇区之后：「清除」钮变成可点，它点得到吗（1440×714 与 1440×900）
      const sectorRows=[];
      for(const hh of [714,900]){await size(h,t,1440,hh);const jcat=await clickSector(t);await sleep(450);const s=await snap(t);await shot(h,t,`1440x${hh}-sector-selected`);const c=s.cover.clear;sectorRows.push({size:`1440×${hh}`,jcat,toolbarTxt:s.toolbar.txt,clearDisabled:s.clearDisabled,clearCovered:c&&c.covered,clearTops:c&&c.tops,clearRect:c&&`${c.w}×${c.h}@y${c.y}`,covered:s.covered});
        console.log(`  [选扇区 1440×${hh}] 扇区=${jcat}｜刊源行「${s.toolbar.txt}」｜清除钮 disabled=${s.clearDisabled} 盒 ${c?c.w+'×'+c.h+'@y'+c.y:null}｜取样点被盘盖住 ${c?Math.round(c.covered*100)+'%':'-'}（盖住它的元素：${c&&c.tops}）｜盘盖住：${covList(s)}`);
        await mouseClick(h,t,'#journal-clear');await sleep(350);sectorRows[sectorRows.length-1].clearWorked=await t.eval(`state.jcat===null&&state.journal===null&&state.gsec===null`)}
      save('f3-rows.json',{rows,sectorRows});
      if(JUDGE){
        const r=rows.find(x=>x.tag==='验收档');
        sec('F3a','F3a 视口高约 714px：页脚（临床免责声明）完整可见');check(r.footerOK&&r.gap>=0,`1440×714 页脚 bottom=${r.footerBottom} 应 ≤714 且高度不缩（实得余 ${r.gap}px）`);check(/临床|原文/.test(r.footTxt),`页脚应带临床免责文字；实得「${r.footTxt}」`);note(`1440×714：顶栏 ${r.topbar}px＋主区 ${r.deck}px＋页脚 ${r.footerH}px＝bottom ${r.footerBottom}，视口下余 ${r.gap}px｜页脚「${r.footTxt}…」｜body overflow=${r.bodyOv}`);L.end();
        sec('F3b','F3b 视口高约 714px：雷达盘不截断下方控件（#jcat-folds 等）');check(r.maxCovered===0&&r.blipOut===0,`1440×714 被盘盖住的控件：${covList({scope:{w:1},covered:r.covered})}；实得盘 ${r.scope}（台高 ${r.stageH}、头 ${r.headH}、脚 ${r.footH}）`);note(`1440×714 盘 ${r.scope}｜舞台高 ${r.stageH}px（盘 380px 居中，舞台比盘矮就上下溢出）｜头 ${r.headH}px 脚 ${r.footH}px（阵地折叠钮 ${r.foldN} 个）｜各控件被盖比例：${Object.entries(r.cover).filter(([k])=>k!=='folds').map(([k,v])=>`${k} ${v?Math.round(v.covered*100)+'%':'-'}`).join('、')}｜阵地折叠钮 ${r.cover.folds.map(v=>Math.round(v.covered*100)+'%').join('/')}｜出盘点 ${r.blipOut} 个`);L.end();
        const sr714=sectorRows.find(x=>x.size==='1440×714');
        sec('F3b2','F3b2 视口高约 714px：选了扇区后「清除」钮点得到（没被雷达盘盖住）');check(sr714&&sr714.clearDisabled===false&&sr714.clearCovered===0,`1440×714 清除钮 disabled=${sr714&&sr714.clearDisabled}、取样点被盘盖住 ${sr714?Math.round(sr714.clearCovered*100)+'%':'-'}（盖住它的元素：${sr714&&sr714.clearTops}）`);check(sr714&&sr714.clearWorked===true,'真鼠标点击「清除」后刊源/阵地筛选应归零');note(sectorRows.map(x=>`${x.size}：刊源行「${x.toolbarTxt}」清除钮盒 ${x.clearRect} 被盖 ${Math.round(x.clearCovered*100)}%｜真鼠标清除=${x.clearWorked}`).join('｜'));L.end();
        const std=rows.filter(x=>x.tag!=='更矮'),short=rows.filter(x=>x.tag==='更矮');
        sec('F3c','F3c 720px 及以上各档视口：页脚可见、盘不盖控件');const bad=std.filter(x=>!(x.footerOK&&x.maxCovered===0));check(bad.length===0,`出问题：${bad.map(x=>`${x.size} 页脚余${x.gap}px、盘盖住 ${x.covered.join('＋')}`).join('；')||'无'}`);note(std.map(x=>`${x.size}：顶栏 ${x.topbar}·主区 ${x.deck}px·页脚余 ${x.gap}px·盘 ${x.scope}·台高 ${x.stageH}px·盖 ${x.covered.join('＋')||'无'}·队列 开${x.qOpen}/收${x.qClosed}`).join('｜'));L.end();
        sec('F3d','F3d 页脚下方不留空带（主区高度按实际顶栏高扣减）');check(Math.abs(r.gap)<=1,`1440×714 页脚下留了 ${r.gap}px 空带（.deck 高度仍按 100vh−112px 扣，顶栏已 76→58）`);note(`页脚下空带：${rows.map(x=>`${x.size}＝${x.gap}px`).join('、')}`);L.end();
        L.results[L.results.length-1].notes.push(...short.map(x=>`更矮视口（不计入判定，仅留痕）${x.size}：顶栏 ${x.topbar}·主区 ${x.deck}px·页脚余 ${x.gap}px·盘 ${x.scope}·台高 ${x.stageH}px·盘盖住 ${x.covered.join('＋')||'无'}·队列全见 开${x.qOpen}/收${x.qClosed}·阅读首屏卡 ${x.readCards}`));
        sec('F3e','F3e 多档视口流页面零运行期异常');errs(t,'F3 视口流');L.end();
      }
      await t.close();
    }
    // ================= F4 阅读舒适性（任务书要点 5）：字号 =================
    if(ONLY('F4')){
      const t=await fresh(h,path);const out={};
      const take=async(name)=>{const s=await snap(t);out[name]=s;console.log(`  [${name}] 字号 ${JSON.stringify(s.fs)}｜详情块序 ${s.detail.order.join(' > ')}｜摘要首屏=${s.detail.excerptInFirstScreen} 按钮首屏=${s.detail.actionsInFirstScreen}`);return s};
      await t.eval(P.view('reading'));await sleep(450);await take('阅读·紧凑');
      await t.eval(P.click('[data-proto-density="immersive"]'));await sleep(450);await take('阅读·沉浸');await shot(h,t,'1440x714-reading-immersive');
      await t.eval(P.click('[data-proto-density="compact"]'));await sleep(300);
      await t.eval(P.view('overview'));await sleep(450);await take('概览');await shot(h,t,'1440x714-overview-default');
      save('f4-fonts.json',Object.fromEntries(Object.entries(out).map(([k,s])=>[k,{fs:s.fs,detail:{...s.detail,cover:undefined},texts:s.texts}])));
      if(JUDGE){
        const g=out['概览'],rc=out['阅读·紧凑'].fs,ri=out['阅读·沉浸'].fs;
        sec('F4a','F4a 摘要正文字号未缩（详情卡摘要 12px）');check(g.fs.detailExcerpt==='12px',`详情卡摘要 .excerpt 字号实得 ${g.fs.detailExcerpt}（施工前 12px）`);note(`详情卡摘要 .excerpt＝${g.fs.detailExcerpt}／行高 ${g.detail.excerpt.lh}（父提交 12px／20.64px）｜摘要小标 ${g.fs.excerptLabelB}｜作者结论/生成解读块 ${g.fs.honesty}｜操作钮 ${g.fs.actionBtn}｜详情标题 ${g.fs.detailTitle}（父提交 19px）`);L.end();
        sec('F4b','F4b 阅读卡「一句话结论」字号未缩');check(rc.cardFinding==='12px'&&ri.cardFinding==='14px',`一句话结论字号：紧凑 ${rc.cardFinding}（应 12px）、沉浸 ${ri.cardFinding}（应 14px）`);note(`一句话结论：紧凑 ${rc.cardFinding}／沉浸 ${ri.cardFinding}；附加块 ${ri.cardExtra}；英文副标 紧凑 ${rc.cardTitleEn}／沉浸 ${ri.cardTitleEn}`);L.end();
        sec('F4c','F4c 阅读卡标题：紧凑档降号，沉浸档大标题不被压');check(rc.cardTitle==='14px',`紧凑档标题实得 ${rc.cardTitle}（施工方自报 16→14）`);check(ri.cardTitle==='21px',`沉浸档标题实得 ${ri.cardTitle}（施工前 21px）`);note(`阅读卡标题：紧凑 ${rc.cardTitle}（父提交 16px）、沉浸 ${ri.cardTitle}（父提交 21px）｜沉浸档结论正文 ${ri.cardFinding}`);L.end();
        sec('F4d','F4d 详情卡摘要提前到首屏（1440×714），块序＝摘要→按钮→元数据折叠');check(g.detail.excerptInFirstScreen,`1440×714 摘要首屏可见：摘要顶 ${g.detail.excerpt.y}px`);check(g.detail.order.indexOf('interpretation')<g.detail.order.indexOf('detail-actions')&&g.detail.order.indexOf('detail-actions')<g.detail.order.indexOf('meta-fold'),`块序应为 摘要→按钮→元数据折叠；实得 ${g.detail.order.join(' > ')}`);note(`1440×714 详情块序：${g.detail.order.join(' > ')}｜摘要顶 ${g.detail.excerpt.y}px、首屏内可见 ${g.detail.excerptVisibleH}px｜原文/题录按钮顶 ${g.detail.actions.y}px（首屏${g.detail.actionsInFirstScreen?'内':'外'}：排在整段摘要之后）｜刊源行「${g.detail.journalMeta.txt}」`);L.end();
        sec('F4e','F4e 字号流页面零运行期异常');errs(t,'F4 字号流');L.end();
      }
      await t.close();
    }
    // ================= F5 详情卡元数据折叠 / 刊源图例折叠 / 漏斗 / 说明书墙 =================
    if(ONLY('F5')){
      const t=await fresh(h,path);
      const a=await snap(t);
      let b=a,c=a;if(a.detail.metaFold){await t.eval(P.click('.meta-fold summary'));await sleep(250);b=await snap(t);await t.eval(P.click('.meta-fold summary'));await sleep(200)}
      if(a.jl){await t.eval(P.click('.jl-fold summary'));await sleep(250);c=await snap(t);await shot(h,t,'1440x714-journal-legend-open');await t.eval(P.click('.jl-fold summary'));await sleep(200)}
      const paused=await t.eval(`(()=>{const p=personalFiltered().find(x=>String(x.publish_state)==='degraded');if(!p)return null;const el=document.querySelector('#queue-list [data-select="'+p.id+'"]');if(el)el.click();return {pmid:String(p.pmid),state:p.publish_state,clicked:!!el}})()`);
      await sleep(400);const d=await snap(t);await shot(h,t,'1440x714-detail-paused');
      console.log(`  [详情] 元数据折叠 open=${a.detail.metaFold&&a.detail.metaFold.open} 格 ${a.detail.metaFold&&a.detail.metaFold.cells}（可见 ${a.detail.metaFold&&a.detail.metaFold.cellsVisible}）→点开 open=${b.detail.metaFold&&b.detail.metaFold.open} 可见 ${b.detail.metaFold&&b.detail.metaFold.cellsVisible}｜刊源图例 open=${a.jl&&a.jl.open} 胶囊 ${a.jl&&a.jl.pills}→点开 open=${c.jl&&c.jl.open} 图例高 ${c.jl&&c.jl.legend.h}｜漏斗 display=${a.funnel.display}｜说明书 display=${a.hint.display}｜混排开关 title ${a.mixLabelTitle?'有':'无'}`);
      console.log(`  [详情·解读暂停篇 ${paused?paused.pmid+' clicked='+paused.clicked:'（窗内没找到）'}] 暂停块「${d.detail.paused&&d.detail.paused.txt}」 title=${JSON.stringify(d.detail.pausedTitle)}｜深评块「${d.detail.deep&&d.detail.deep.txt}」 title ${d.detail.deepTitle?'有('+d.detail.deepTitle.length+'字)':'无'}｜深评钮 ${d.detail.deepBtn} 可点=${d.detail.deepBtnVisible}｜刊源图例展开时盘盖住：${covList(c)}`);
      save('f5-detail.json',{a:{detail:{...a.detail,cover:undefined},texts:a.texts,jl:a.jl,funnel:a.funnel,hint:a.hint,mixLabelTitle:a.mixLabelTitle,fs:a.fs},b:{metaFold:b.detail.metaFold},c:{jl:c.jl,covered:c.covered,stageH:c.stage.h},d:{detail:{...d.detail,cover:undefined},fs:d.fs},paused});
      if(JUDGE&&!a.detail.metaFold){sec('F5a','F5a 元数据折叠：缺省收起、点开见 11 格、内容没丢');check(false,'页面没有元数据折叠结构（功能不存在＝负对照应红）');L.end()}
      if(JUDGE&&!a.jl){sec('F5b','F5b 刊源图例折叠：缺省收起、点开见胶囊');check(false,'页面没有刊源图例折叠结构（功能不存在＝负对照应红）');L.end()}
      if(JUDGE){
        const mf=a.detail.metaFold||{open:null,cells:0,cellsVisible:0,w:0,h:0};
        if(a.detail.metaFold){
        sec('F5a','F5a 元数据折叠：缺省收起、点开见 11 格、内容没丢');check(mf&&!mf.open&&mf.cells===11&&mf.cellsVisible===0,`缺省应收起且 11 格不可见；实得 open=${mf&&mf.open} 格=${mf&&mf.cells} 可见=${mf&&mf.cellsVisible}`);check(b.detail.metaFold.open&&b.detail.metaFold.cellsVisible===11,'点开后 11 格应可见');note(`缺省 open=${mf.open}（${mf.w}×${mf.h}px，标题「${a.texts.metaSummary}」）→ 点开可见 ${b.detail.metaFold.cellsVisible}/11 格`);L.end();}
        if(a.jl){
        sec('F5b','F5b 刊源图例折叠：缺省收起、点开见胶囊');check(a.jl&&!a.jl.open&&a.jl.pills>0,`缺省应收起且有胶囊；实得 open=${a.jl&&a.jl.open} 胶囊=${a.jl&&a.jl.pills}`);check(c.jl.open&&c.jl.legend.h>0&&c.jl.legend.h<=127,`点开后图例应可见且限高；实得 open=${c.jl&&c.jl.open} 高=${c.jl&&c.jl.legend.h}`);check(maxCovered(c)===0,`图例展开后雷达仍盖住控件：${covList(c)}`);note(`缺省 open=${a.jl.open}（${a.jl.w}×${a.jl.h}px，标题「${a.texts.jlSummary}」）胶囊 ${a.jl.pills} 个｜点开 图例高 ${c.jl.legend.h}px、台高 ${c.stage.h}px｜图例展开时（1440×714）盘盖住：${covList(c)}`);L.end();}
        if(a.jl===null){sec('F5b','F5b 刊源图例折叠：缺省收起、点开见胶囊');check(false,'页面没有刊源图例折叠结构（功能不存在＝负对照应红）');L.end()}
        sec('F5c','F5c 管线漏斗撤下、说明书墙收起（开关留 title）');check(a.funnel.display==='none','漏斗应 display:none，实得 '+a.funnel.display);check(a.hint.display==='none','说明书墙应 display:none，实得 '+a.hint.display);check(Boolean(a.mixLabelTitle),'混排开关应留 title');note(`#funnel display=${a.funnel.display}（文字仍在 DOM：「${a.funnel.txt.slice(0,60)}」）｜.ai-help[data-i18n=poolup.hint] display=${a.hint.display}｜混排开关 title「${a.mixLabelTitle}」`);L.end();
        sec('F5d','F5d 双提示框改轻行后要点还在');check(d.detail.deepBtn===true&&d.detail.deepBtnVisible===true,'深评钮应在且可见');check(d.detail.pausedBrInPaused===0,`解读暂停块内 <br> 应为 0，实得 ${d.detail.pausedBrInPaused}`);note(`解读暂停块可见文字「${d.detail.paused&&d.detail.paused.txt}」·title「${d.detail.pausedTitle}」｜深评块可见文字「${d.detail.deep&&d.detail.deep.txt}」·title ${d.detail.deepTitle?'有':'无'}`);L.end();
        sec('F5e','F5e 折叠流页面零运行期异常');errs(t,'F5 详情流');L.end();
      }
      await t.close();
    }
    // ================= F6 英文态：本单新增文案是否跟着切 =================
    if(ONLY('F6')){
      const t=await fresh(h,path);
      const zh=await snap(t);await t.eval(P.click('#lang-btn'));await sleep(450);const en=await snap(t);await shot(h,t,'1440x714-overview-en');const enScan=await t.eval(CJKSCAN);
      await t.eval(P.view('reading'));await sleep(400);const enR=await snap(t);await shot(h,t,'1440x714-reading-en');
      const items=[['折叠钮',en.texts.toggle],['刊源图例折叠标题',en.texts.jlSummary],['元数据折叠标题',en.texts.metaSummary]].filter(([,s])=>s!==null);
      console.log(`  [英文态 lang=${en.lang} 文档标题「${en.texts.docTitle}」] ${items.map(([k,s])=>`${k}「${s}」${HAN.test(s)?'（中国字）':''}`).join('｜')}｜对照·旧有 合集钮「${en.texts.collOpen}」`);
      console.log(`  [英文态·界面骨架残留中国字 ${enScan.length} 条] ${enScan.join(' ｜ ')}`);
      save('f6-lang.json',{zh:zh.texts,en:en.texts,enR:enR.texts,enScan});
      if(JUDGE){
        const leaked=items.filter(([,s])=>HAN.test(s));
        sec('F6a','F6a 英文态下本单新增的界面文案跟着切语言');check(leaked.length===0,`切英文后仍是中文：${leaked.map(([k,s])=>`${k}「${s}」`).join('；')}`);note(`切英文后（文档标题已是「${en.texts.docTitle}」）：${items.map(([k,s])=>`${k}「${s}」${HAN.test(s)?'（中文）':''}`).join('｜')}`);L.end();
        sec('F6b','F6b 语言流页面零运行期异常');errs(t,'F6 语言流');L.end();
      }
      await t.close();
    }
    // ================= F7 窄屏 390×844（手机）＋深色：截图复拍 ＋ 横向溢出 =================
    if(ONLY('F7')){
      const t=await fresh(h,path,390,844,true);const DEV=390;
      const o1=await snap(t);await shot(h,t,'390-overview-default');
      await t.eval(P.click('.filters-toggle'));await sleep(300);const o2=await snap(t);await shot(h,t,'390-overview-after-toggle');
      await t.eval(P.view('reading'));await sleep(500);const r1=await snap(t);await shot(h,t,'390-reading-default');
      await t.eval(P.click('.filters-toggle'));await sleep(350);const r2=await snap(t);await shot(h,t,'390-reading-filters-open');
      const r2cols=await t.eval(`[...document.querySelectorAll('.filters > *')].map(e=>{const r=e.getBoundingClientRect();return (e.id||e.className||e.tagName)+':'+Math.round(r.x)+'+'+Math.round(r.width)})`);
      await t.eval(P.click('.filters-toggle'));await sleep(250);
      await t.eval(P.click('#theme-btn'));await sleep(600);const dk=await snap(t);await shot(h,t,'390-reading-dark');
      await t.eval(P.view('overview'));await sleep(500);await shot(h,t,'390-overview-dark');const od=await snap(t);
      await size(h,t,1440,714,false);await sleep(500);await shot(h,t,'1440x714-overview-dark');const dd=await snap(t);
      await t.eval(P.view('reading'));await sleep(500);await shot(h,t,'1440x714-reading-dark');const dr=await snap(t);
      await t.eval(P.view('overview'));await sleep(300);await t.eval(P.click('#theme-btn'));await sleep(500);
      const narrow=s=>({视口宽:s.vw,文档宽:s.docSW,右溢出:+(s.docSW-DEV).toFixed(1),filters:s.filters&&{display:s.filters.display,w:s.filters.w,h:s.filters.h,cols:s.filters.cols},面板宽:s.panel.w,toggle:s.toggle&&s.toggle.txt,cards:s.queue.full});
      console.log(`  [390 概览缺省] ${JSON.stringify(narrow(o1))}`);
      console.log(`  [390 概览点钮后] ${JSON.stringify(narrow(o2))}`);
      console.log(`  [390 阅读缺省] ${JSON.stringify(narrow(r1))}`);
      console.log(`  [390 阅读展开筛选] ${JSON.stringify(narrow(r2))}｜筛选区各列位置（x+宽）：${r2cols.join('、')}`);
      console.log(`  [深色 html.dark=${dk.dark}] 390 阅读深色 文档宽 ${dk.docSW}｜390 概览深色 文档宽 ${od.docSW} 页脚「${(od.texts.foot||'').slice(0,40)}」｜1440×714 概览深色 页脚余 ${dd.gapUnderFooter}px 盘盖住 ${covList(dd)} 文档宽 ${dd.docSW}｜阅读深色 首屏卡 ${dr.queue.full}`);
      save('f7-narrow.json',{o1:narrow(o1),o2:narrow(o2),r1:narrow(r1),r2:narrow(r2),r2cols,dark:{dk:dk.dark,odW:od.docSW,ddGap:dd.gapUnderFooter,ddCovered:dd.covered,ddSW:dd.docSW}});
      if(JUDGE){
        sec('F7a','F7a 390 窄屏：阅读缺省收起、无横向溢出且顶栏不压主区');check(r1.view==='reading'&&!vis(r1),`390 阅读缺省筛选区应收起；实得 display=${r1.filters.display}`);check(r1.vw===DEV&&r1.docSW<=DEV+0.5,`390 阅读缺省不应横向溢出；实得 视口宽 ${r1.vw}／文档宽 ${r1.docSW}`);check(r1.panel.y>=r1.search.bottom-0.5,`顶栏不得压住主区：搜索框 bottom=${r1.search.bottom}、队列 top=${r1.panel.y}`);note(`390×844 阅读：筛选区 display=${r1.filters.display}，钮「${r1.toggle?r1.toggle.txt:'（无折叠钮）'}」，视口宽 ${r1.vw}／文档宽 ${r1.docSW}，首屏全见卡 ${r1.queue.full} 张｜顶栏高 ${r1.topbar.h}、搜索框底 ${r1.search.bottom}、队列顶 ${r1.panel.y}`);L.end();
        sec('F7b','F7b 390 窄屏：阅读点开筛选后不横向溢出、三块都落在面板内');check(vis(r2),'390 阅读点钮后筛选区应展开');check(r2.vw===DEV&&r2.docSW<=DEV+0.5&&r2cols.every(c=>{const [x,w]=c.split(':')[1].split('+').map(Number);return x>=0&&x+w<=DEV+0.5}),`展开后：视口宽 ${r2.vw}／文档宽 ${r2.docSW}（设备宽 ${DEV}）；筛选区 display=${r2.filters.display}、列=${r2.filters.cols}；各列位置 ${r2cols.join('、')}`);note(`展开后：筛选区 display=${r2.filters.display} 宽 ${r2.filters.w}px 高 ${r2.filters.h}px 列=${r2.filters.cols}｜面板宽 ${r2.panel.w}px｜视口宽 ${r2.vw}／文档宽 ${r2.docSW}（设备宽 ${DEV}）｜各列 ${r2cols.join('、')}`);L.end();
        sec('F7c','F7c 390 窄屏：概览不横向溢出且顶栏不压主区');check(o1.vw===DEV&&o1.docSW<=DEV+0.5,`概览缺省 视口宽 ${o1.vw}／文档宽 ${o1.docSW}`);check(o1.panel.y>=o1.search.bottom-0.5,`概览顶栏不得压主区：搜索框 bottom=${o1.search.bottom}、队列 top=${o1.panel.y}`);L.end();
        sec('F7d','F7d 深色模式可切换、文档不横溢、页脚可见（1440×714）');check(dd.dark===true,'点主题钮后应进深色');check(dd.docSW<=dd.vw+0.5&&dd.gapUnderFooter>=0&&dd.footer.bottom<=714.5,`深色 1440×714：文档宽 ${dd.docSW}／页脚 bottom ${dd.footer.bottom}`);note(`深色 html.dark=${dd.dark}；1440×714 概览深色 文档宽 ${dd.docSW}、页脚 bottom ${dd.footer.bottom}（视口下余 ${dd.gapUnderFooter}px）、盘盖住 ${covList(dd)}、队列全见 ${dd.queue.full} 条；390 阅读深色 文档宽 ${dk.docSW}`);L.end();
        sec('F7e','F7e 窄屏/深色流页面零运行期异常');errs(t,'F7 窄屏深色流');L.end();
      }
      await t.close();
    }
    // ================= F10 雷达点径、形状与点击热区 =================
    if(ONLY('F10')){
      const measureMarks=tab=>tab.eval(`(()=>{const es=[...document.querySelectorAll('#blips .blip')].filter(e=>e.getBoundingClientRect().width&&getComputedStyle(e).opacity!=='0');let centerOwn=0,lowMismatch=0,lowFadeBad=0,zeroLabels=0,reviewN=0,reviewShapeBad=0;const widths=[];
        for(const e of es){const r=e.getBoundingClientRect(),p=PAPERS.find(x=>x.id===e.dataset.select);widths.push(parseFloat(getComputedStyle(e).width));if(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===e)centerOwn++;
          if(p){const sn=Number(p.score_total),score=Number.isFinite(sn)?Math.max(0,Math.min(100,sn)):0,low=score<45;if(e.classList.contains('proto-low')!==low)lowMismatch++;if(low&&!e.classList.contains('selected')&&!e.classList.contains('read')&&!e.classList.contains('dim')&&parseFloat(getComputedStyle(e).opacity)>.69)lowFadeBad++}
          if(e.classList.contains('proto-kind-review')){reviewN++;if(!getComputedStyle(e,'::before').clipPath.includes('polygon'))reviewShapeBad++}}
        zeroLabels=[...document.querySelectorAll('#scope-labels .scope-label')].filter(e=>/·\\s*0$/.test(e.textContent.trim())).length;
        return {n:es.length,min:Math.min(...widths),max:Math.max(...widths),centerOwn,lowMismatch,lowFadeBad,zeroLabels,reviewN,reviewShapeBad}})()`);
      const dTab=await fresh(h,path,1440,900,false),d=await measureMarks(dTab);await shot(h,dTab,'1440x900-radar-small');
      const mTab=await fresh(h,path,390,844,true),m=await measureMarks(mTab);await shot(h,mTab,'390-radar-small');
      const point=await mTab.eval(`(()=>{
        const es=[...document.querySelectorAll('#blips .blip')].filter(e=>e.getBoundingClientRect().width&&!e.classList.contains('dim'));
        for(const e of es){
          const r=e.getBoundingClientRect();
          for(const [dx,dy] of [[r.width/2+4,0],[-r.width/2-4,0],[0,r.height/2+4],[0,-r.height/2-4]]){
            const x=r.x+r.width/2+dx,y=r.y+r.height/2+dy;
            if(x>0&&x<innerWidth&&y>0&&y<innerHeight&&document.elementFromPoint(x,y)===e){return {x,y,id:e.dataset.select};}
          }
        }
        return null;
      })()`);
      let hitPass=false;if(point){await mousePoint(h,mTab,point);await sleep(300);hitPass=await mTab.eval(`state.selected===${JSON.stringify(point.id)}`)}
      const keyboardId=await mTab.eval(`(()=>{const e=[...document.querySelectorAll('#blips .blip')].find(e=>e.getBoundingClientRect().width&&!e.classList.contains('dim')&&e.dataset.select!==state.selected);if(!e)return null;e.focus();return e.dataset.select})()`);
      if(keyboardId){await h.cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,nativeVirtualKeyCode:13,text:'\r'},mTab.sid);await h.cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,nativeVirtualKeyCode:13},mTab.sid);await sleep(300)}
      const keyboardPass=keyboardId?await mTab.eval(`state.selected===${JSON.stringify(keyboardId)}`):false;
      console.log(`  [雷达点径] 桌面 ${JSON.stringify(d)}｜390 ${JSON.stringify(m)}｜透明区点击=${hitPass}｜键盘 Enter=${keyboardPass}`);
      save('f10-radar.json',{desktop:d,mobile:m,point,hitPass,keyboardId,keyboardPass});
      if(JUDGE){
        sec('F10a','F10a 桌面点径 5–9px，0 篇不占标签，低分淡化且研究设计形状保留');check(d.n>0&&d.min>=4.99&&d.max<=9.01,`桌面点径实得 ${d.min}–${d.max}px`);check(d.zeroLabels===0&&d.lowMismatch===0&&d.lowFadeBad===0,`0 篇标签 ${d.zeroLabels}、低分标记错 ${d.lowMismatch}、低分未淡 ${d.lowFadeBad}`);check(d.reviewN>0&&d.reviewShapeBad===0,`综述三角形缺失 ${d.reviewShapeBad}/${d.reviewN}`);L.end();
        sec('F10b','F10b 手机点径为桌面 75%，且每个点中心都命中自己');check(m.n>0&&m.min>=3.74&&m.max<=6.76,`手机点径实得 ${m.min}–${m.max}px`);check(m.centerOwn===m.n&&d.centerOwn===d.n,`中心命中：桌面 ${d.centerOwn}/${d.n}、手机 ${m.centerOwn}/${m.n}`);L.end();
        sec('F10c','F10c 小点仍有可用热区，且键盘 Enter 可选中');check(Boolean(point)&&hitPass,'透明热区真点击未选中目标');check(Boolean(keyboardId)&&keyboardPass,'键盘 Enter 未选中目标');L.end();
        sec('F10d','F10d 雷达点径流页面零运行期异常');check(dTab.errors.length===0&&mTab.errors.length===0,`桌面 ${dTab.errors.length}／手机 ${mTab.errors.length} 条异常`);L.end();
      }
      await dTab.close();await mTab.close();
    }
    // ================= F9 阅读视图第 13 篇起可达 =================
    if(ONLY('F9')){
      const t=await fresh(h,path);await t.eval(P.view('reading'));await sleep(450);
      const measure=()=>t.eval(`(()=>{const cards=[...document.querySelectorAll('#queue-list [data-select]')];const more=document.querySelector('#proto-reading-more');return {shown:cards.length,total:personalFiltered().length,more:more?more.textContent:null,ids:cards.map(e=>e.dataset.select)}})()`);
      const before=await measure();await shot(h,t,'1440x714-reading-first12');
      if(before.more)await mouseClick(h,t,'#proto-reading-more');await sleep(450);
      const after=await measure();await shot(h,t,'1440x714-reading-all');
      const thirteenth=after.ids[12]||null;
      if(thirteenth)await t.eval(`(()=>{const e=[...document.querySelectorAll('#queue-list [data-select]')][12];e.scrollIntoView({block:'center'});e.click();return 1})()`);await sleep(350);
      const selected=await t.eval(`({selected:state.selected,title:document.querySelector('#detail .detail-title')?.textContent||''})`);
      console.log(`  [阅读可达性] 首屏条目 ${before.shown}/${before.total}，按钮「${before.more}」→ 展开 ${after.shown}/${after.total}｜第 13 篇 ${thirteenth||'无'} 点击后 selected=${selected.selected}`);
      if(JUDGE){
        sec('F9a','F9a 阅读默认仍为前 12 篇，且有明确入口显示其余');check(before.total>12,'当前数据须超过 12 篇，才能验证第 13 篇可达');check(before.shown===12&&Boolean(before.more),`默认应 12 篇且有「显示其余」钮；实得 ${before.shown}／钮 ${before.more}`);L.end();
        sec('F9b','F9b 真鼠标点「显示其余」后所有在筛文献可达');check(after.shown===after.total&&after.more===null,`展开后应显示全部 ${after.total} 篇且不再留钮；实得 ${after.shown}／钮 ${after.more}`);check(Boolean(thirteenth)&&selected.selected===thirteenth&&selected.title.length>0,'第 13 篇应可点击锁定并出详情');L.end();
        sec('F9c','F9c 阅读展开流页面零运行期异常');errs(t,'F9 阅读可达性');L.end();
      }
      await t.close();
    }
    // ================= F8 官方面逐键差分（被审件 vs 父提交，同种子同数据） =================
    if(ONLY('F8')){
      const SEED_COLL={version:1,collections:[{id:'c_test1',name:'probe collection',journals:[{k:'ANN TRANSL MED',nlm:'101617978'},{k:'CHEST',nlm:'0231335'}]}],active:'c_test1'};
      const SEED_SECT={version:2,schemes:[{id:'s_test1',name:'probe scheme',mode:'journal',sectors:[{id:'g_test1',name:'probe sector',folded:false,journals:[{k:'ANN TRANSL MED',nlm:'101617978'}],words:{include:[],exclude:[]}}],order:['g_test1']}],active:null};
      const LS=(k,v)=>`localStorage.setItem(${JSON.stringify(k)},${JSON.stringify(JSON.stringify(v))})`;
      const SEEDS=`${LS('thoradar.collections.v1',SEED_COLL)};${LS('thoradar.sectors.v2',SEED_SECT)};localStorage.setItem('thoradar.poolview.v1','{"v":1,"mix":false}')`;
      const KEYS=`(()=>{const q=s=>{const el=document.querySelector(s);if(!el)return null;const c=el.cloneNode(true);c.querySelectorAll('#cls-progress,#deep-box,.deep-note,.deep-err,.ai-session,[data-i18n="ai.title"],#pool-mix-control,.proto-reading-more-item').forEach(n=>{const x=n.nextSibling;if(x&&x.nodeType===3&&!x.nodeValue.trim())x.remove();n.remove()});return c.innerHTML};
        const blipSig=()=>[...document.querySelectorAll('#blips .blip')].map(e=>[e.dataset.select,e.style.left,e.style.top,[...e.classList].find(c=>c.startsWith('proto-kind-'))||'',e.style.getPropertyValue('--proto-domain')].join(':')).join('|');
        const labelSig=()=>[...document.querySelectorAll('#scope-labels .scope-label')].filter(e=>!/·\\s*0$/.test(e.textContent.trim())).map(e=>e.textContent.trim()+'@'+e.style.left+','+e.style.top).join('|');
        return {queue:q('#queue-list'),blips:blipSig(),sectors:q('#journal-sectors'),labels:labelSig(),detail:q('#detail'),jlegend:q('#journal-legend'),folds:q('#jcat-folds'),clegend:q('#jcat-legend'),dlegend:q('#design-legend'),funnel:q('#funnel'),scan:q('#scan-date')+q('#scan-time'),read:q('#read-count'),counter:q('#filter-counter'),sub:q('#scope-subtitle'),hub:q('#hub-count'),collList:q('#coll-list'),collEditor:q('#coll-editor'),topicList:q('#topic-list'),ai:q('#ai-settings')}})()`;
      const STATE=`(()=>{try{const tierEls=[...document.querySelectorAll('.tier-chip')];return JSON.stringify({sel:state.selected,journal:state.journal===undefined?null:state.journal,days:state.days,tiers:[...state.tiers],filtered:filtered().map(p=>p.id),personal:personalFiltered().map(p=>p.id),papers:PAPERS.length,counter:document.querySelector('#filter-counter').textContent,read:document.querySelector('#read-count').textContent,windowLabel:document.querySelector('#window-label').textContent,windowValue:document.querySelector('#window-value').textContent,schemeValue:document.querySelector('#scheme-select').value,schemeOptions:[...document.querySelectorAll('#scheme-select option')].map(o=>o.textContent),tierBtns:tierEls.map(b=>b.textContent.trim()+(b.classList.contains('active')?'*':'')),queueIds:[...document.querySelectorAll('#queue-list [data-select]')].map(e=>e.dataset.select),journalSel:document.querySelector('#journal-selection').textContent,quickActive:(document.querySelector('#quick-filters button.active')||{dataset:{}}).dataset.quick})}catch(e){return 'ERR '+e.message}})()`;
      const BLOCKS=`(()=>{const inner=document.querySelector('#detail .detail-inner');if(!inner)return null;const out={};for(const el of inner.children){let k=(el.className||el.tagName).toString().split(' ')[0],html=el.innerHTML;if(k==='meta-fold'){k='meta-grid';html=el.querySelector('.meta-grid').innerHTML}if(k==='detail-journal'){const jm=el.querySelector('.journal-meta');const clone=el.cloneNode(true);const j2=clone.querySelector('.journal-meta');j2.innerHTML=j2.innerHTML.replace(/\\s·\\sIF [^<]*$/,'');html=clone.innerHTML}
    if(k==='interpretation'){const clone=el.cloneNode(true);const db=clone.querySelector('#deep-box');if(db)db.remove();const pb=clone.querySelector('.interpretation-paused');if(pb){const body=pb.getAttribute('title')||[...pb.childNodes].filter(n=>n.nodeType===3).map(n=>n.nodeValue).join('').replace(/\\s+/g,' ').trim();const st=pb.querySelector('strong');pb.outerHTML='PAUSED['+(st?st.textContent:'')+'|'+body+']'}html=clone.innerHTML}   // 解读暂停块：标题＋说明文字（施工前说明在块内、施工后在 title）两版归一；深评块本单有意改形，单列不比
    out[k]=html}return JSON.stringify(Object.keys(out).sort().map(k=>k+'='+out[k]))})()`;   // 详情卡各块内容（不管先后、不管元数据有没有包进折叠、不管刊源行尾部新加的 IF/分区、不管暂停块改轻行）
      const run=async p=>{const t=await fresh(h,p);await t.eval(`localStorage.clear();${SEEDS}`);await t.goto(`${h.origin}${p}`);await sleep(450);const o={errors:t.errors};
        o.overview=await t.eval(KEYS);o.stateOv=await t.eval(STATE);o.blocksOv=await t.eval(BLOCKS);
        await t.eval(P.view('reading'));await sleep(450);o.reading=await t.eval(KEYS);o.stateRd=await t.eval(STATE);
        await t.eval(P.view('personal'));await sleep(450);o.personal=await t.eval(KEYS);o.statePn=await t.eval(STATE);
        await t.eval(P.view('overview'));await sleep(350);
        o.quick=await t.eval(`(()=>{const bs=[...document.querySelectorAll('#quick-filters button')];if(bs.length>1){bs[1].click();return bs[1].textContent.trim()}return null})()`);await sleep(350);o.stateQuick=await t.eval(STATE);   // 先点快筛（此时队列非空，动作看得出效果）
        await t.eval(`(()=>{const b=document.querySelector('#quick-filters [data-quick="all"]');if(b)b.click();return 1})()`);await sleep(350);o.stateQuickAll=await t.eval(STATE);
        o.sector=await clickSector(t);await sleep(450);o.stateSec=await t.eval(STATE);o.blocksSec=await t.eval(BLOCKS);o.clearEnabled=await t.eval(`!document.querySelector('#journal-clear').disabled`);
        o.chipN=await t.eval(`(()=>{const bs=[...document.querySelectorAll('.tier-chip')];if(!bs.length)return 0;bs[0].click();return bs.length})()`);await sleep(350);o.stateTier=await t.eval(STATE);
        await t.eval(`(()=>{const e=document.querySelector('#window-range');e.value=7;e.dispatchEvent(new Event('input',{bubbles:true}));return 1})()`);await t.eval('rollingPromise?rollingPromise.then(()=>1):1');await sleep(500);o.stateWin=await t.eval(STATE);
        await t.close();return o};
      const PREV={Quick:'Ov',Sec:'QuickAll',Tier:'Sec',Win:'Tier'},changed=(o,k)=>String(o['state'+k])!==String(o['state'+PREV[k]]);   // 每幕对上一幕：动作是否真改了状态（场景自检，防「两边一样坏」的空对空）
      const STATES=['stateOv','stateRd','statePn','stateQuick','stateQuickAll','stateSec','stateTier','stateWin'],ACTS=[['点快筛','Quick'],['点扇区','Sec'],['点档位','Tier'],['拉时间窗','Win']];
      const a=await run('/baseline.html'),b=await run(path);
      const diffKeys=[],stateDiff=[],blockDiff=[];
      for(const view of ['overview','reading','personal'])for(const k of Object.keys(a[view])){const x=String(a[view][k]),y=String(b[view][k]);if(x!==y){let i=0;while(i<Math.min(x.length,y.length)&&x[i]===y[i])i++;diffKeys.push(`${view}.${k}（基线 ${x.length} 字／被审 ${y.length} 字，首差 @${i}）`)}}
      for(const k of STATES){const x=String(a[k]),y=String(b[k]);if(x!==y){let i=0;while(i<Math.min(x.length,y.length)&&x[i]===y[i])i++;stateDiff.push(`${k} 首差 @${i}：基线…${x.slice(Math.max(0,i-50),i+90)}…‖被审…${y.slice(Math.max(0,i-50),i+90)}…`)}}
      for(const k of ['blocksOv','blocksSec'])if(String(a[k])!==String(b[k]))blockDiff.push(k);
      const total=Object.keys(a.overview).length;
      console.log(`  [官方面逐键差分·${total} 键×3 视图] 不一致的键：${diffKeys.join('；')||'（无）'}`);
      console.log(`  [详情卡各块内容（不管先后/折叠包裹/刊源行 IF 尾巴）] ${blockDiff.length?'不一致：'+blockDiff.join('、'):'概览态与选扇区态均逐字一致'}`);
      console.log(`  [状态面 8 幕（概览/阅读/个性化/点快筛/快筛复原/点扇区/点档位/拉时间窗）] ${stateDiff.length?'不一致：'+stateDiff.join('；'):'逐字一致'}｜动作自检（该幕较上一幕有变＝动作生效；基线／被审）：${ACTS.map(([n,k])=>n+' '+changed(a,k)+'／'+changed(b,k)).join('，')}｜快筛「${a.quick}」／「${b.quick}」 扇区=${a.sector}／${b.sector} 清除钮可点 ${a.clearEnabled}／${b.clearEnabled} 档位钮 ${a.chipN}／${b.chipN} 个`);
      console.log(`  [状态样例·被审件·时间窗幕后 160 字] …${String(b.stateWin).slice(-160)}`);
      save('f8-diff.json',{diffKeys,stateDiff,blockDiff,a:Object.fromEntries(Object.entries(a).filter(([k])=>/^state|^blocks|^clear/.test(k))),b:Object.fromEntries(Object.entries(b).filter(([k])=>/^state|^blocks|^clear/.test(k)))});
      if(JUDGE){
        const nonDetail=diffKeys.filter(d=>!/\.detail（/.test(d));
        sec('F8a','F8a 官方面逐键差分：数据承载面（队列/盘点/扇区/标签/图例/折叠/计数/合集/阵地/主题/AI 设置）与父提交逐字一致');check(nonDetail.length===0,`除详情卡外还有键变了：${nonDetail.join('；')}`);note(`${total} 键×3 视图＝${total*3} 格，不一致 ${diffKeys.length} 格：${diffKeys.join('；')||'无'}`);L.end();
        sec('F8b','F8b 状态面差分：选中项/筛选结果/档位钮/时间窗/队列序 在 8 幕里与父提交逐字一致，且各动作在两边都真改了状态');check(stateDiff.length===0,`状态面有变：${stateDiff.join('；')}`);const dead=ACTS.filter(([,k])=>!(changed(a,k)&&changed(b,k)));check(dead.length===0,`动作没生效（两边都没变＝空对空）：${dead.map(([n])=>n).join('、')||'无'}`);note(`8 幕状态串逐字${stateDiff.length?'不一致':'一致'}（幕长 ${STATES.map(k=>k.slice(5)+' '+String(a[k]).length).join('／')} 字）；动作自检 ${ACTS.map(([n,k])=>n+' '+changed(a,k)+'／'+changed(b,k)).join('、')}（基线／被审）`);L.end();
        sec('F8c','F8c 详情卡各块内容（不管先后/折叠包裹/刊源行 IF 尾巴）与父提交逐字一致');check(blockDiff.length===0,`详情卡有块内容变了：${blockDiff.join('、')}`);L.end();
        sec('F8d','F8d 差分流页面零运行期异常（两棵树）');check(a.errors.length===0&&b.errors.length===0,`基线 ${a.errors.length} 条／被审 ${b.errors.length} 条：${a.errors.concat(b.errors).slice(0,2).join(' | ').slice(0,300)}`);L.end();
      }
    }
    if(JUDGE){const bad=L.results.filter(r=>!r.ok),skipped=L.results.filter(r=>r.skipped).length;console.log(`\n==== UX PROBE [${LABEL}] SUMMARY ${L.results.length-bad.length-skipped} PASS / ${bad.length} FAIL：${L.results.map(r=>r.id+(r.ok?' ✓':' ✗')).join('  ')} ====`);process.exitCode=bad.length?1:0}
  }catch(e){console.log('探针自身故障：'+(e&&e.stack||e));process.exitCode=2}
  finally{await browser.stop();await new Promise(r=>srv.server.close(r));rmSync(SCRATCH,{recursive:true,force:true});console.log(`     cleanup | 临时目录 ${SCRATCH} 已清`)}
}
main();
