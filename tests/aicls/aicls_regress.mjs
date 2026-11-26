#!/usr/bin/env node
// T1125-AICLS 零回归差分（tests/aicls/aicls_regress.mjs）——施工席自证件：不构成验收结论，验收权归独立复核席
// 用法：node tests/aicls/aicls_regress.mjs [--target <index.html>] [--baseline <rev>] [--only R12,R17] [--label 名称] [--chrome <chrome.exe|msedge.exe>]
//   --only：全序列照跑（后面的步骤依赖前面的状态），只比对并输出点名的步骤。
// 做什么：基线件（git show <baseline>:index.html，baseline 缺省取 git merge-base HEAD main）与施工后件，在同一浏览器同一页签里先后各跑一遍
//   同一套「只碰既有功能」的真实入口操作（合集／阵地方案／主题词 P1 路径／书架／池外刊入册与题录面板／语言／深色／时间窗／我的主题运行／键盘／删除与重载），
//   每一步之后比对四样：①页面＋浏览器存储快照（归一化后）②界面文案表（页面上所有带 data-i18n* 的元素按键取当前文案：基线有而施工后没有＝红、同键不同文＝红）
//   ③AI 请求种类序列 ④NCBI 请求序列（含相邻请求间隔是否 ≥3s——节拍回归也抓得住）。全部相等才算这一步零回归。
// 防「空对空」的三道闸（都是变异红证里真被存活变异揪出来的洞，补在这里）：
//   ①任一步执行故障＝红——两侧故障一字不差也不算过（故障说明这一步没比上；界面入口点不到就是没点到）。
//   ②某一步的快照与上一步一字不差＝红（入口没点到、或这一步什么都没做）。所以「开了又关」的操作一律拆成两步各比一次。
//   ③关键步骤带场景自检 meta（如书架筛选后的列表长度）：两侧都须满足「这一步真的改变了什么」，不满足＝红。
// 另有一道静态闸 R00：既有文案逐键不变——基线中英两表的每个键在施工后件里同名同值，白名单键（WHITE）除外；施工后新增的键单列不计。
// 归一化只抹天然差异：随机生成的 id（c_/s_/g_/t_ 按出现次序编号）、毫秒时间戳、标签间的排版空白、本机时间文本。施工后件独有的新界面件（分类进度行／深评块／
//   钥匙开关／AI 设置标题）取快照时从克隆节点里剔掉——它们是本单的新增面，不参与「既有功能零回归」的比对，由 aicls_probe.mjs 另行守。
// 快照一律在步骤做完、等各防抖落盘（250ms）走完之后取，避开两侧时序差；自动消失的提示条文本不计入快照。
// 同时断言：全程不出现分类／深评请求（不点新功能＝零新增调用）。退出码：0＝全部一致，1＝有差异，2＝探针自身崩溃。
import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {ROOT,sleep,sha256,norm,argOf,gitRead,ledger,startServer,connect,Tab,wire,launch,freePort,P,readI18n,FAKE_KEY_A} from './lib.mjs';

const argv=process.argv.slice(2);
const TARGET=resolve(ROOT,argOf(argv,'--target',join(ROOT,'index.html')));
const LABEL=argOf(argv,'--label','run');
const CHROME=argOf(argv,'--chrome','C:/Program Files/Google/Chrome/Application/chrome.exe');
const ONLY=argOf(argv,'--only','').split(',').map(s=>s.trim()).filter(Boolean);
const SCRATCH_ROOT=resolve(process.env.AICLS_SCRATCH||join(tmpdir(),`thoradar-t1125-aicls-regress-${LABEL}`));
const SCRATCH=join(SCRATCH_ROOT,'harness');
let BASE=argOf(argv,'--baseline','');
if(!BASE){try{BASE=gitRead(['merge-base','HEAD','main']).trim()||'HEAD'}catch(e){BASE='HEAD'}}
const L=ledger(),{check,note}=L;
const skip=id=>ONLY.length&&!ONLY.includes(id);   // --only R12,R17：全序列照跑（后面的步骤依赖前面的状态），只比对并输出点名的步骤
const WHITE=new Set(['ai.title']);   // 既有文案里本单有意改动的键（AI 设置标题改成「分类与深评共用」的说明）；此外任何一条既有文案被改都算回归

// ---------- 归一化：随机 id 按出现次序编号；毫秒时间戳抹平 ----------
let normIds={};
const normalize=s=>String(s)
  .replace(/\b([csgt])_([a-z0-9]{6,})/g,(m,p,id)=>{normIds[id]=normIds[id]||`${p}_#${Object.keys(normIds).length}`;return normIds[id]})
  .replace(/\b1[6-9]\d{11}\b/g,'<TS>')
  .replace(/>\s+</g,'><')                                                    // 标签之间的排版空白（模板缩进，不是内容）
  .replace(/\d{4}\/\d{1,2}\/\d{1,2} \d{1,2}:\d{2}:\d{2}/g,'<LOCALTS>')       // 本机时间文本（主题「上次运行」、题录面板「更新于」）：两侧必然不同
  .replace(/\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{2}:\d{2} [AP]M/g,'<LOCALTS>');
// 快照表达式：从克隆节点取 innerHTML（不动页面）；施工后件独有的新界面件两边都剔（基线里本就没有）
const STRIP='#cls-progress,#deep-box,.deep-note,.deep-err,.ai-session,[data-i18n="ai.title"]';   // .ai-session＝钥匙「仅本会话」开关行
const SNAP=`(()=>{const N=x=>x==null?x:String(x).replace(/>\\s+</g,'><').replace(/\\d{4}\\/\\d{1,2}\\/\\d{1,2} \\d{1,2}:\\d{2}:\\d{2}/g,'<LOCALTS>').replace(/\\d{1,2}\\/\\d{1,2}\\/\\d{4}, \\d{1,2}:\\d{2}:\\d{2} [AP]M/g,'<LOCALTS>');   // N：页内先抹「标签间排版空白」与「本机时间文本」——快照随后会被 JSON 转义，出来再抹就匹配不上了
  const S=s=>{const el=document.querySelector(s);if(!el)return null;const c=el.cloneNode(true);c.querySelectorAll(${JSON.stringify(STRIP)}).forEach(n=>n.remove());return N(c.innerHTML)},text=s=>{const el=document.querySelector(s);return el?N(el.textContent):null};
  return JSON.stringify({main:{queue:S('#queue-list'),queueHead:S('.queue-panel .panel-head'),filters:S('.queue-panel .filters'),blips:S('#blips'),sectors:S('#journal-sectors'),labels:S('#scope-labels'),detail:S('#detail'),jlegend:S('#journal-legend'),folds:S('#jcat-folds'),clegend:S('#jcat-legend'),dlegend:S('#design-legend'),funnel:S('#funnel'),counter:text('#filter-counter'),read:text('#read-count'),sub:text('#scope-subtitle'),hub:text('#hub-count'),sel:text('#journal-selection'),tiers:S('#tier-filters'),wlabel:text('#window-label'),wvalue:text('#window-value'),empty:S('#scope-empty'),mobile:S('#shelf-mobile-status'),skeleton:document.querySelector('#rolling-skeleton').hidden,scan:text('#scan-date')+'|'+text('#scan-time')},
    chrome:{head:S('header.topbar')},tabs:S('.proto-personal-tabs'),
    drawer:{collList:S('#coll-list'),collEditor:S('#coll-editor'),schemeList:S('#scheme-list'),schemeEditor:S('#scheme-editor'),topicList:S('#topic-list'),topicEditor:S('#topic-editor'),shelf:S('#myjournals-panel'),ai:S('#ai-settings'),hidden:document.querySelector('#coll-drawer').hidden,testStatus:text('#ai-test-status'),testBtn:document.querySelector('#ai-test').disabled},
    overlays:{topicBody:S('#topic-run-body'),topicStats:text('#topic-run-stats'),topicTitle:text('#topic-run-title'),topicHidden:document.querySelector('#topic-overlay').hidden,poolBody:S('#pool-body'),poolStats:text('#pool-stats'),poolTitle:text('#pool-title'),poolHidden:document.querySelector('#pool-overlay').hidden},
    ui:{view:document.body.dataset.protoView,density:document.body.dataset.protoDensity,lang:LANG,dark:document.documentElement.classList.contains('dark'),title:document.title,days:state.days,selected:String(state.selected),quick:state.quick,jcat:String(state.jcat),gsec:String(state.gsec),journal:String(state.journal),query:state.query,papers:PAPERS.length},
    ls:Object.fromEntries(Object.keys(localStorage).sort().map(k=>{let v=localStorage.getItem(k);if(k==='thoradar.ai.v1'){try{const o=JSON.parse(v);delete o.sessionOnly;v=JSON.stringify(o)}catch(e){}}return [k,v]}))})})()`;
// 界面文案表：页面上所有带 data-i18n* 的元素「键→当前文案」（文本或 title／placeholder／aria-label 属性）。改了一条既有文案、或一个既有文案件不见了，都从这里露出来
const I18NMAP=`(()=>{const N=v=>String(v==null?'':v).replace(/\\d{4}\\/\\d{1,2}\\/\\d{1,2} \\d{1,2}:\\d{2}:\\d{2}/g,'<LOCALTS>').replace(/\\d{1,2}\\/\\d{1,2}\\/\\d{4}, \\d{1,2}:\\d{2}:\\d{2} [AP]M/g,'<LOCALTS>').replace(/\\s+/g,' ').trim(),out={};
  for(const el of document.querySelectorAll('[data-i18n],[data-i18n-title],[data-i18n-ph],[data-i18n-aria]')){
    const k=el.getAttribute('data-i18n')||el.getAttribute('data-i18n-title')||el.getAttribute('data-i18n-ph')||el.getAttribute('data-i18n-aria');if(!k||k in out)continue;
    const attr=el.hasAttribute('data-i18n')?'':el.hasAttribute('data-i18n-title')?'title':el.hasAttribute('data-i18n-ph')?'placeholder':'aria-label';
    out[k]=attr?N(el.getAttribute(attr)):N(el.textContent);
  }
  return out})()`;
const LS=(k,v)=>`localStorage.setItem(${JSON.stringify(k)},${JSON.stringify(JSON.stringify(v))})`;
const clickN=(sel,i)=>`(()=>{const els=document.querySelectorAll(${JSON.stringify(sel)});const el=els[${i}];if(!el)return 'MISSING:'+${JSON.stringify(sel)}[${i}]+'（共 '+els.length+' 个）';el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return 'ok'})()`;   // 一律派发鼠标事件：雷达扇区是 SVG 元素，没有 click()
const setValue=(sel,v)=>`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING:'+${JSON.stringify(sel)};el.value=${JSON.stringify(v)};el.dispatchEvent(new Event('input',{bubbles:true}));return 'ok'})()`;
const keyOn=(target,key)=>`(()=>{const el=${target==='input'?'document.querySelector("#search")':'document.body'};el.dispatchEvent(new KeyboardEvent('keydown',{key:${JSON.stringify(key)},bubbles:true,cancelable:true}));return 1})()`;
const ensureSector=t=>t.eval(`(()=>{if(schemeEditingSector)return 'kept';const els=document.querySelectorAll('[data-sector-select]');if(!els.length)return 'MISSING:[data-sector-select]';els[0].dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return 'ok'})()`);   // 「选阵地」是开关：已选中就不再点
const needs=r=>{if(r!=='ok'&&r!=='kept')throw new Error('界面入口点不到：'+r)};
const windowTo=async(t,d)=>{needs(await t.eval(setValue('#window-range',String(d))));await t.eval('rollingPromise?rollingPromise.then(()=>"loaded"):"no-fetch"');await sleep(400)};
// 场景自检用的页内取值（都是只读或算完即还原，不落盘不重渲）
const PASSING=`const own=Object.prototype.hasOwnProperty,collKeys=collectionFilterKeys(),ok=p=>{const quickOk=state.quick==='all'||(state.quick==='nct'?Boolean(p.nct_id):designOf(p)===state.quick);return tierOk(p)&&journalOk(p)&&quickOk&&(!collKeys||collKeys.has(paperJournalKey(p)))}`;   // 「过得了除书架外的现有筛选」
const SHELFPLAN=`(()=>{${PASSING};const cnt=new Map();
  windowPapers().forEach(p=>{if(ok(p)){const k=paperJournalKey(p);cnt.set(k,(cnt.get(k)||0)+1)}});   // 除书架外的现有筛选下，每本刊有几篇在列；挑「最多的一本」与「零篇的一本」
  const ranked=[...cnt].filter(([k])=>own.call(JOURNAL_IDS,k)).sort((x,y)=>y[1]-x[1]||x[0].localeCompare(y[0])),top=ranked[0]||null;
  return {hit:top?top[0]:'',n:top?top[1]:0,others:[...cnt.values()].reduce((s,x)=>s+x,0)-(top?top[1]:0),miss:REGISTRY.map(r=>r.k).find(k=>!cnt.has(k))||''}})()`;
const M14=`(()=>{const keep=myJournalsStore.filterOn,list=filtered().length;myJournalsStore.filterOn=false;const noShelf=filtered().length;myJournalsStore.filterOn=keep;return {on:keep,list,noShelf,picks:myJournalsStore.picks.length}})()`;   // list＝当前列表长度；noShelf＝假如没有书架筛选
const shelfOn=v=>v.on===true&&v.list>0&&v.list<v.noShelf,shelfOff=v=>v.on===false&&v.list>0&&v.list===v.noShelf;
const M12=`(()=>{const s=activeScheme();let kw=0,un=0;windowPapers().forEach(p=>{kwClassify(s,p)===UNGROUPED_ID?un++:kw++});return {mode:s&&s.mode,kw,un}})()`;   // mode＝方案模式；kw＝关键词已归位的篇数
const M05=`(()=>{const keep=collectionsStore.active,list=filtered().length;collectionsStore.active=null;const noColl=filtered().length;collectionsStore.active=keep;return {active:Boolean(keep),list,noColl}})()`;   // list＝当前列表；noColl＝假如合集没启用（合集 id 是随机生成的，不进自检值）
const M06=`(()=>{const keep=state.jcat,list=filtered().length;state.jcat=null;const noSec=filtered().length;state.jcat=keep;return {jcat:String(keep),list,noSec}})()`;   // 官方扇区过滤记在 state.jcat；noSec＝假如没点扇区
const SECTORPICK=`(()=>{const group=j=>JCATS_LEGEND_MERGED.ids.includes(j)?JCATS_LEGEND_MERGED.id:j,cats=new Set(windowPapers().filter(p=>tierOk(p)&&journalOk(p)).map(p=>group(jcatOf(p)))),els=[...document.querySelectorAll('#journal-sectors .journal-sector')];const i=els.findIndex(e=>cats.has(e.dataset.jcat));return i})()`;   // 第一个「点了还有文章」的官方扇区（零篇的扇区照样画在盘上，点它＝空对空）
const TIERPICK=`(()=>{const have=new Set(windowPapers().filter(p=>journalOk(p)).map(p=>String(p.tier||'').toUpperCase())),els=[...document.querySelectorAll('#tier-filters [data-tier]')],el=els.find(e=>have.has(e.dataset.tier));return el?el.dataset.tier:''})()`;   // 第一个「关掉后还会少文章」的档位（窗内没有文章的档，关不关列表都不变）
const M07=`(()=>{const keep=new Set(state.tiers),list=filtered().length;state.tiers=new Set(TIERS);const all=filtered().length;state.tiers=keep;return {tiers:[...keep].join(''),off:TIERS.filter(x=>!keep.has(x)).join(''),list,all}})()`;   // all＝假如各档全开；off＝关掉的档
const M07b=`(()=>{const keep=state.quick,list=filtered().length;state.quick='all';const all=filtered().length;state.quick=keep;return {quick:keep,list,all}})()`;   // all＝假如快筛为「全部」
const M08=`(()=>{const keep=state.query,list=filtered().length;state.query='';const noQuery=filtered().length;state.query=keep;return {query:String(keep),list,noQuery}})()`;   // noQuery＝假如检索框是空的
const M10=`(()=>{const s=schemesStore.schemes.find(x=>x.id===schemesStore.active)||null;return {active:Boolean(s),n:s?s.sectors.reduce((a,g)=>a+g.journals.length,0):0,mode:s?s.mode:''}})()`;   // n＝方案里指派的刊数；方案 id 是随机生成的，不进自检值
// 挑场景用料（都按两侧各自的页面数据当场算：同一份数据→同一个结果；数据文件每天更新也不怕挑空）
const JPICK=`(()=>{const own=Object.prototype.hasOwnProperty,out=[];windowPapers().forEach(p=>{const k=paperJournalKey(p);if(own.call(JOURNAL_IDS,k)&&!out.includes(k))out.push(k)});return out})()`;   // 本窗内有文章的名册刊（按 PAPERS 顺序去重）
const JPICKF=`(()=>{${PASSING};const out=[];windowPapers().forEach(p=>{if(ok(p)){const k=paperJournalKey(p);if(own.call(JOURNAL_IDS,k)&&!out.includes(k))out.push(k)}});return out})()`;   // 现有筛选（档位／刊源／快筛／合集）下还有文章的名册刊
const QUICKPICK=`(()=>{const base=windowPapers().filter(p=>tierOk(p)&&journalOk(p)),count=q=>base.filter(p=>q==='all'||(q==='nct'?Boolean(p.nct_id):designOf(p)===q)).length,all=count('all');return ['rct','cohort','nct'].map(q=>({q,n:count(q),all}))})()`;   // 各快筛在当前档位下各剩几篇
const WORDPICK=`(()=>{const hay=p=>[p.title_en,p.title_zh,p.journal_abbr,p.journal_full,p.pmid,p.nct_id,p.category_label].join(' ').toLowerCase(),base=windowPapers().filter(p=>tierOk(p)&&journalOk(p)),all=base.length;let first='';   // 检索词：优先挑「能搜到、但搜不全」的词——搜索这条路才算真的被比到
  for(const p of windowPapers())for(const w of (String(p.title_en||'').match(/[A-Za-z]{6,}/g)||[])){const q=w.toLowerCase(),n=base.filter(x=>hay(x).includes(q)).length;if(n>0&&n<all)return w;if(n>0&&!first)first=w}
  return first})()`;

// ---------- NCBI 假应答（NLM 目录两种＋PubMed 两种）：池外刊添加器与题录面板、主题检索用 ----------
const POOL=Array.from({length:8},(_,i)=>String(70000001+i));
const CAT={uid:'900001',nlmuniqueid:'101617978',medlineta:'Ann Transl Med',title:'Annals of translational medicine.',issn:[['2305-5847','Electronic'],['2305-5839','Print']]};
const article=id=>`<PubmedArticle><MedlineCitation><PMID Version="1">${id}</PMID><Article><Journal><Title>Annals of translational medicine</Title><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue></Journal><ArticleTitle>Regression article ${id} on segmentectomy outcomes</ArticleTitle><Abstract><AbstractText Label="BACKGROUND">Background text for ${id}.</AbstractText><AbstractText Label="CONCLUSIONS">Conclusions text for ${id}.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>`;
const ncbi=async(p,rec,tab)=>{
  const u=new URL(rec.url),db=u.searchParams.get('db')||'',kind=rec.kind;let type='application/json',text='';
  if(db==='nlmcatalog'&&kind==='esearch')text=JSON.stringify({esearchresult:{count:'1',retmax:'8',retstart:'0',idlist:[CAT.uid]}});
  else if(db==='nlmcatalog'&&kind==='esummary')text=JSON.stringify({result:{uids:[CAT.uid],[CAT.uid]:{uid:CAT.uid,nlmuniqueid:CAT.nlmuniqueid,medlineta:CAT.medlineta,isoabbreviation:'',titlemainlist:[{sorttitle:'annals of translational medicine',title:CAT.title,aiid:''}],issnlist:CAT.issn.map(([issn,issntype])=>({issn,issntype,validyn:'Y'})),resourceinfolist:[{typeofresource:'Serial',resourceunit:'Serial'}]}}});
  else if(kind==='esearch'&&db==='pubmed')text=JSON.stringify({esearchresult:{count:String(POOL.length),retmax:'50',retstart:'0',idlist:POOL}});   // PubMed：池外题录式与主题检索式都回这 8 篇
  else if(kind==='efetch'){type='application/xml';text=`<?xml version="1.0"?><PubmedArticleSet>${POOL.map(article).join('')}</PubmedArticleSet>`}
  else text=JSON.stringify({einforesult:{dblist:['pubmed']}});
  await sleep(200);
  await tab.h.cdp.send('Fetch.fulfillRequest',{requestId:p.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:type},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from(text).toString('base64')},tab.sid);
  rec.code=200;
};
// AI 假应答：连通测试（max_tokens 64）回「OK」；主题判官按请求里的 PMID 逐条回判定（奇偶交替）。分类／深评请求在本流程里不该出现——出现了由断言报红
const aiRespond=rec=>rec.maxTokens<200?{status:200,text:'OK',delay:0}
  :{status:200,text:JSON.stringify([...String(rec.user||'').matchAll(/PMID (\d+)/g)].map((m,i)=>({pmid:m[1],related:i%2===0,why:'probe'}))),delay:0};

// ---------- 操作步骤：每步＝{id,name,run(tab,ctx)}；ctx.side＝本侧页面地址、ctx.origin＝本机服务地址（ctx 每侧各一份）；run 后取快照并记这一步新增的 AI／NCBI 请求 ----------
// meta＝步骤做完后的场景自检取值（页内表达式或 async (tab,ctx)=>对象），must＝两侧都得满足的判据——不满足＝这一步没真的改变什么（空对空），红
// needList='>0'＝这一步之后概览列表必须非空（列表一空，后面比的都是空态：第一版就栽在这里——合集挑了两本窗内没文章的刊，R05 起到收尾列表全是空的，照样 31 步全绿）
const STEPS=[
  {id:'R01',name:'空库首屏（默认 1 天窗·零外部请求）',needList:'>0',run:async()=>{}},
  {id:'R02',name:'切到阅读视图',needList:'>0',run:async t=>needs(await t.eval(P.view('reading')))},
  {id:'R03',name:'切到个性化·期刊合集分区',run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('collections')))}},
  {id:'R04',name:'新建合集→编辑器里按缩写检索→勾 2 刊（当场挑本窗内有文章的名册刊）',run:async(t,ctx)=>{
    ctx.pick=(await t.eval(JPICK)).slice(0,2);if(ctx.pick.length<2)throw new Error(`本窗内有文章的名册刊不足 2 本（${ctx.pick.length}）`);
    needs(await t.eval(P.click('[data-coll-new]')));
    for(const k of ctx.pick){needs(await t.eval(setValue('#coll-search',k)));await sleep(150);needs(await t.eval(P.click(`#coll-editor [data-coll-check="${k}"]`)))}}},
  {id:'R05',name:'合集重命名→启用→回概览（列表应只剩这 2 刊的文章）',needList:'>0',meta:M05,must:v=>v.active===true&&v.list>0&&v.list<v.noColl,run:async t=>{needs(await t.eval(P.click('[data-coll-rename]')));await t.eval(`(()=>{const el=document.querySelector('[data-coll-rename-input]');if(!el)return 'MISSING';el.value='回归合集';el.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 1})()`);
    await sleep(300);needs(await t.eval(clickN('#coll-list [data-coll-activate]',1)));needs(await t.eval(P.view('overview')))}},
  {id:'R05b',name:'再点「官方全集」停用合集→回概览（列表应放宽）',needList:'>0',meta:M05,must:v=>v.active===false&&v.list>0&&v.list===v.noColl,
   run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('collections')));needs(await t.eval(P.click('#coll-list [data-coll-activate=""]')));needs(await t.eval(P.view('overview')))}},
  {id:'R06',name:'点官方阵地扇区过滤（当场挑第一个点了还有文章的扇区；列表应收窄）',needList:'>0',meta:M06,must:v=>v.jcat!=='null'&&v.list>0&&v.list<v.noSec,
   run:async t=>{const i=await t.eval(SECTORPICK);if(i<0)throw new Error('没有一个官方扇区点了还有文章');needs(await t.eval(clickN('#journal-sectors .journal-sector',i)))}},
  {id:'R06b',name:'点清除扇区过滤（列表应放宽）',needList:'>0',meta:M06,must:v=>v.jcat==='null'&&v.list>0&&v.list===v.noSec,run:async t=>needs(await t.eval(P.click('#journal-clear')))},
  {id:'R07',name:'关掉一个档位（当场挑第一个还有文章的档；列表应收窄）',needList:'>0',meta:M07,must:v=>v.off!==''&&v.tiers.indexOf(v.off)<0&&v.list>0&&v.list<v.all,
   run:async(t,ctx)=>{ctx.tier=await t.eval(TIERPICK);if(!ctx.tier)throw new Error('没有一个档位关掉后还有文章');needs(await t.eval(P.click(`#tier-filters [data-tier="${ctx.tier}"]`)))}},
  {id:'R07b',name:'快筛（当场挑一个筛完还有文章的：RCT／队列／含试验号）',needList:'>0',meta:M07b,must:v=>v.quick!=='all'&&v.list>0,
   run:async(t,ctx)=>{const q=(await t.eval(QUICKPICK)).find(x=>x.n>0);if(!q)throw new Error('三个快筛筛完都是空的');ctx.quick=q.q;needs(await t.eval(P.click(`[data-quick="${q.q}"]`)))}},
  {id:'R08',name:'检索框输入一个词（当场挑：搜得到、但搜不全）',needList:'>0',meta:M08,must:v=>v.query!==''&&v.list>0&&v.list<v.noQuery,
   run:async(t,ctx)=>{ctx.word=await t.eval(WORDPICK);if(!ctx.word)throw new Error('挑不出检索词');needs(await t.eval(setValue('#search',ctx.word)))}},
  {id:'R08b',name:'键盘 Esc 清除检索（列表应放宽）',needList:'>0',meta:M08,must:v=>v.query===''&&v.list>0&&v.list===v.noQuery,run:async t=>{await t.eval(keyOn('body','Escape'))}},
  {id:'R09',name:'时间滑杆拖到 7 天（触发历史档案加载）',needList:'>0',run:async t=>windowTo(t,7)},
  {id:'R10',name:'新建阵地方案（期刊模式）→加阵地→按缩写检索指派 3 刊（当场挑现有筛选下还有文章的名册刊）→启用→回概览',needList:'>0',meta:M10,must:v=>v.active===true&&v.n===3&&v.mode!=='topic',   // 新建方案没有显式 mode 字段（缺省即期刊模式），只须不是 topic
   run:async(t,ctx)=>{ctx.pick3=(await t.eval(JPICKF)).slice(0,3);if(ctx.pick3.length<3)throw new Error(`现有筛选下有文章的名册刊不足 3 本（${ctx.pick3.length}）`);
     needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('sectors')));needs(await t.eval(P.click('[data-scheme-new]')));needs(await t.eval(P.click('[data-scheme-edit]')));
     needs(await t.eval(P.click('[data-sector-add]')));
     for(const k of ctx.pick3){needs(await t.eval(setValue('#scheme-search',k)));await sleep(150);needs(await t.eval(P.click(`#scheme-editor [data-sec-check="${k}"]`)))}
     needs(await t.eval(clickN('#scheme-list [data-scheme-activate]',1)));needs(await t.eval(P.view('overview')))}},
  {id:'R11',name:'方案编辑：转主题模式预览＋加 2 个主题词（关键词即算即用）→回概览',needList:'>0',run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('sectors')));needs(await t.eval(P.click('[data-scheme-edit]')));needs(await ensureSector(t));
    needs(await t.eval(P.click('[data-tw-mode-topic]')));
    for(const w of ['lung','segmentectomy']){needs(await t.eval(setValue('#tw-add-include',w)));needs(await t.eval(P.key('#tw-add-include','Enter')))}
    needs(await t.eval(P.view('overview')))}},
  {id:'R12',name:'无 Key 点「保存并重分类」（只应出关键词结果、零 AI 调用）',needList:'>0',meta:M12,must:v=>v.mode==='topic'&&v.kw>0,
   run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('sectors')));needs(await ensureSector(t));needs(await t.eval(P.click('[data-tw-save]')));needs(await t.eval(P.view('overview')))}},
  {id:'R13',name:'转回期刊模式',needList:'>0',run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('sectors')));needs(await t.eval(P.click('[data-tw-mode-journal]')));needs(await t.eval(P.view('overview')))}},
  {id:'R14',name:'书架：收藏「其余筛选下文章最多的一本刊」＋一本没有文章的刊→点「去概览只看书架」（列表应收窄到那一本刊）',needList:'>0',meta:M14,must:shelfOn,
   run:async(t,ctx)=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('shelf')));
     const plan=await t.eval(SHELFPLAN);   // 当场按页面数据挑刊（两侧同一份数据→同一本；挑的结果经 meta 核对）
     if(!plan.hit||!plan.miss||!(plan.n>0)||!(plan.others>0))throw new Error(`挑不出书架场景用的刊（须一本有文章、一本没有、且还有别的刊也有文章）：${JSON.stringify(plan)}`);
     ctx.hit=plan.hit;
     needs(await t.eval(P.click(`#myjournals-panel [data-shelf-toggle="${plan.hit}"]`)));await sleep(150);
     needs(await t.eval(P.click(`#myjournals-panel [data-shelf-toggle="${plan.miss}"]`)));await sleep(150);
     needs(await t.eval(P.click('#myjournals-panel [data-shelf-go-overview]')))}},
  {id:'R15',name:'书架筛选下：点顶栏书架钮关掉筛选（列表应放宽）',needList:'>0',meta:M14,must:shelfOff,run:async t=>needs(await t.eval(P.click('#myjournals-filter')))},
  {id:'R15b',name:'再点顶栏书架钮重开筛选（列表应收窄）',needList:'>0',meta:M14,must:shelfOn,run:async t=>needs(await t.eval(P.click('#myjournals-filter')))},
  {id:'R15c',name:'书架里取消收藏那本有文章的刊（只剩没文章的刊）→去概览＝空态→点「关闭书架筛选」',needList:'>0',meta:M14,must:shelfOff,
   run:async(t,ctx)=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('shelf')));
     needs(await t.eval(P.click(`#myjournals-panel [data-shelf-toggle="${ctx.hit}"]`)));
     needs(await t.eval(P.click('#myjournals-panel [data-shelf-go-overview]')));
     needs(await t.eval(P.click('#queue-list [data-shelf-close-filter]')))}},
  {id:'R16',name:'池外刊添加器：检索 NLM 目录→点候选→确认入册',run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('sectors')));needs(await t.eval(P.click('[data-scheme-edit]')));needs(await ensureSector(t));
    needs(await t.eval(P.click('[data-ext-toggle]')));needs(await t.eval(setValue('#ext-search','Ann Transl Med')));needs(await t.eval(P.key('#ext-search','Enter')));
    await t.waitFor('document.querySelectorAll("#ext-candidates [data-ext-pick]").length>0',15000,'池外刊候选');needs(await t.eval(P.click('[data-ext-pick]')));needs(await t.eval(P.click('[data-ext-confirm]')))}},
  {id:'R17',name:'池外刊题录面板冷开（按需拉 PubMed）',run:async t=>{needs(await t.eval(P.click('[data-ext-records]')));await t.waitFor('poolView&&!poolView.loading&&!poolView.failed&&poolView.at>0',30000,'题录面板冷开')}},
  {id:'R18',name:'题录面板关掉再开（24 小时内走缓存）→关掉',run:async t=>{needs(await t.eval(P.click('#pool-close')));needs(await t.eval(P.click('[data-ext-records]')));await t.waitFor('poolView&&!poolView.loading&&poolView.fresh',10000,'题录面板缓存开');needs(await t.eval(P.click('#pool-close')))}},
  {id:'R19',name:'移除池外刊（确认框）→回概览',needList:'>0',run:async t=>{needs(await t.eval(P.click('[data-ext-remove]')));needs(await t.eval(P.view('overview')))}},
  {id:'R20',name:'切换英文界面→看合集分区与书架分区（英文态）',run:async t=>{needs(await t.eval(P.click('#lang-btn')));needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('collections')));needs(await t.eval(P.tab('shelf')))}},
  {id:'R20b',name:'切回中文→回概览',needList:'>0',run:async t=>{needs(await t.eval(P.click('#lang-btn')));needs(await t.eval(P.view('overview')))}},
  {id:'R21',name:'切深色模式',needList:'>0',run:async t=>needs(await t.eval(P.click('#theme-btn')))},
  {id:'R22',name:'键盘：/ 聚焦检索→Esc 退出→→ 下一信号（选中篇应变）',needList:'>0',meta:async(t,ctx)=>({focusAfterSlash:ctx.f1,moved:String(await t.eval('state.selected'))!==ctx.before}),must:v=>v.focusAfterSlash==='search'&&v.moved===true,
   run:async(t,ctx)=>{ctx.before=String(await t.eval('state.selected'));await t.eval(keyOn('body','/'));ctx.f1=await t.eval('document.activeElement&&document.activeElement.id');await t.eval(keyOn('input','Escape'));await t.eval(keyOn('body','ArrowRight'))}},
  {id:'R22b',name:'键盘：← 上一信号（选中篇应回到原来那篇）',needList:'>0',meta:async(t,ctx)=>({back:String(await t.eval('state.selected'))===ctx.before}),must:v=>v.back===true,
   run:async t=>{await t.eval(keyOn('body','ArrowLeft'))}},
  {id:'R23',name:'写 AI 三件套（记住档）与一条主题后重载→测试连接',run:async(t,ctx)=>{await t.eval(`${LS('thoradar.ai.v1',{baseUrl:ctx.origin,apiKey:FAKE_KEY_A,model:'probe-mock'})};${LS('thoradar.topics.v1',{version:1,topics:[{id:'t_regress',name:'regress topic',query:'segmentectomy',days:7,cap:20,createdAt:1761900000000,lastRun:null}]})};1`);
    await t.goto(ctx.side);needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('topics')));needs(await t.eval(P.click('#ai-test')));await t.waitFor('!document.querySelector("#ai-test").disabled',10000,'连通测试结束')}},
  {id:'R24',name:'我的主题运行（PubMed＋AI 判官）→结果面板',run:async t=>{needs(await t.eval(P.click('[data-topic-run="t_regress"]')));await t.waitFor('runState&&!runState.running',40000,'主题运行结束')}},
  {id:'R25',name:'关闭结果面板→查看最近一次结果（本地存档）→关闭',run:async t=>{needs(await t.eval(P.click('#topic-close')));needs(await t.eval(P.click('[data-topic-view="t_regress"]')));needs(await t.eval(P.click('#topic-close')))}},
  {id:'R26',name:'新建一条主题（表单）→保存',run:async t=>{needs(await t.eval(P.tab('topics')));needs(await t.eval(P.click('[data-topic-new]')));needs(await t.eval(setValue('#topic-f-name','second topic')));needs(await t.eval(setValue('#topic-f-query','lobectomy')));needs(await t.eval(setValue('#topic-f-cap','30')));needs(await t.eval(P.click('[data-topic-save]')))}},
  {id:'R27',name:'整页重载：持久化状态恢复（合集／方案／书架／语言／深色／时间窗／AI 配置）',run:async(t,ctx)=>{await t.goto(ctx.side)}},
  {id:'R28',name:'时间滑杆拖到 90 天（全量历史档案）',needList:'>0',run:async t=>windowTo(t,90)},
  {id:'R29',name:'删除主题／方案／合集（确认框）',run:async t=>{needs(await t.eval(P.view('personal')));needs(await t.eval(P.tab('topics')));needs(await t.eval(P.click('[data-topic-delete]')));needs(await t.eval(P.tab('sectors')));needs(await t.eval(P.click('[data-scheme-delete]')));needs(await t.eval(P.tab('collections')));needs(await t.eval(P.click('[data-coll-delete]')))}},
  {id:'R30',name:'删完回概览→再重载一次',needList:'>0',run:async(t,ctx)=>{needs(await t.eval(P.view('overview')));await t.goto(ctx.side)}},
];
const STEP_OF=new Map(STEPS.map(s=>[s.id,s]));

async function runSide(tab,ctx){
  const out=[];let prevT=0;   // prevT＝上一步最后一个 NCBI 请求的到达时刻：相邻间隔跨步骤也接着算
  await tab.eval('localStorage.clear();sessionStorage.clear();1');
  await tab.goto(ctx.side);
  for(const st of STEPS){   // 步骤一律全序列执行（后面的步骤依赖前面的状态）；--only 只决定比对并输出哪几步
    const a0=srv.ai.log.length,m0=tab.mark(),d0=tab.dialogs.length;
    try{await st.run(tab,ctx)}catch(e){out.push({id:st.id,name:st.name,error:e.message});continue}
    await sleep(400);   // 等各存储的防抖落盘（250ms）走完再取快照
    try{
      normIds={};
      const reqs=tab.since(m0);
      const ncbi=reqs.map((r,i)=>`${r.db||'-'}:${r.kind}${(i?r.t-reqs[i-1].t:r.t-prevT)>=2990?'+':'-'}`).join(',');   // 每个请求后缀：距上一个到达 ≥3s 记「+」、更近记「-」（跨步骤也接着算，头一个请求之前没有请求＝「+」）——节拍回归也抓得住
      if(reqs.length)prevT=reqs[reqs.length-1].t;
      const snap=normalize(await tab.eval(SNAP));
      const raw=await tab.eval(I18NMAP),i18n={};
      for(const k of Object.keys(raw||{}))i18n[k]=normalize(raw[k]);
      const meta=st.meta?(typeof st.meta==='function'?await st.meta(tab,ctx):await tab.eval(st.meta)):null;
      const list=await tab.eval('filtered().length');   // 概览列表当前篇数：列成一空，这一步之后比的都是空态
      out.push({id:st.id,name:st.name,snap,i18n,meta,list,ai:srv.ai.log.slice(a0).map(r=>r.kind).join(','),ncbi,dialogs:tab.dialogs.length-d0});
    }catch(e){out.push({id:st.id,name:st.name,error:'取快照故障：'+e.message})}
  }
  return out;
}
const firstDiff=(a,b)=>{const out=[];let from=0;   // 一次列出前三处不同，免得改一处才能看见下一处
  for(let k=0;k<3;k++){let i=from;while(i<a.length&&i<b.length&&a[i]===b[i])i++;if(i>=a.length&&i>=b.length)break;
    out.push(`第 ${i} 字｜基线「…${a.slice(Math.max(0,i-40),i+110)}」｜施工后「…${b.slice(Math.max(0,i-40),i+110)}」`);from=i+160}
  return out.join('\n       ')};
const NEW_AI=/(^|,)(cls|deep)(,|$)/;

let srv;
async function main(){
  rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});
  const baseHtml=gitRead(['show',`${BASE}:index.html`]),baseFile=join(SCRATCH,'baseline.html');
  writeFileSync(baseFile,baseHtml);
  srv=await startServer({target:TARGET,baseline:baseFile});
  const port=await freePort(),profile=join(SCRATCH,'profile');
  const browser=await launch({chrome:CHROME,profile,port,label:LABEL});
  let cdp,tab;
  try{
    console.log(`aicls regress | ${browser.ver.Browser} | target=${TARGET}（sha256=${sha256(readFileSync(TARGET))}）| baseline=${BASE}（LF 件 sha256=${sha256(Buffer.from(norm(baseHtml)))}）| label=${LABEL}`);
    // ---- R00 静态闸：既有文案逐键不变 ----
    if(!skip('R00')){L.begin('R00','既有文案逐键不变（静态）：基线中英两表的每个键在施工后件里同名同值，仅白名单键除外；施工后新增键单列');
      try{
        const tgt=readI18n(norm(readFileSync(TARGET,'utf8'))),base=readI18n(norm(baseHtml));
        check(Boolean(tgt&&base),'取不到 I18N 中英双表');
        if(tgt&&base)for(const lang of ['zh','en']){
          const changed=[...base[lang]].filter(([k,v])=>tgt[lang].has(k)&&tgt[lang].get(k)!==v).map(([k])=>k),gone=[...base[lang]].filter(([k])=>!tgt[lang].has(k)).map(([k])=>k);
          const hard=changed.filter(k=>!WHITE.has(k)),added=[...tgt[lang].keys()].filter(k=>!base[lang].has(k));
          note(`${lang}：基线 ${base[lang].size} 键｜施工后 ${tgt[lang].size} 键｜白名单内有意改动 ${changed.filter(k=>WHITE.has(k)).join(',')||'无'}｜白名单外被改 ${hard.length}｜被删 ${gone.length}｜新增 ${added.length}`);
          check(hard.length===0,`${lang}：白名单之外的既有文案被改：${hard.join(', ')}`);
          check(gone.length===0,`${lang}：既有键被删：${gone.join(', ')}`);
        }
      }catch(e){check(false,'R00 执行故障：'+e.message)}L.end()}
    cdp=await connect(browser.ver.webSocketDebuggerUrl);
    const h={cdp,origin:srv.origin,tabs:new Map()};wire(h);
    tab=new Tab(h,'R');await tab.open(`${srv.origin}/index.html`);
    srv.ai.respond=aiRespond;tab.responder=ncbi;
    const A=await runSide(tab,{origin:srv.origin,side:`${srv.origin}/baseline.html`});   // 先跑基线
    const B=await runSide(tab,{origin:srv.origin,side:`${srv.origin}/index.html`});      // 再跑施工后件（同源共用存储：每侧都从清库重载起步）
    let diffs=0,steps=0;const seenAdded=new Set();
    for(let i=0;i<A.length;i++){
      const a=A[i],b=B[i]||{id:a.id,error:'施工后件缺这一步'};
      if(skip(a.id))continue;   // --only 点名的步骤才比对输出（其余照跑不比）
      const st=STEP_OF.get(a.id);
      L.begin(a.id,a.name);steps++;
      if(a.error||b.error){check(false,`执行故障（这一步没比上，两侧一样也不算过）：基线「${a.error||'无'}」｜施工后「${b.error||'无'}」`);diffs++;L.end();continue}
      note(`快照 ${a.snap.length} 字｜概览列表 ${a.list} 篇｜界面文案件 ${Object.keys(a.i18n).length} 个｜AI 请求 ${a.ai||'无'}｜NCBI 请求 ${a.ncbi||'无'}（后缀＋＝距上一个 ≥3s）｜确认框 ${a.dialogs} 次`);
      // 闸②：这一步得真的改变了什么（与上一步比）
      const prevA=i>0?A[i-1]:null,prevB=i>0?B[i-1]:null;
      if(prevA&&prevB)check(a.snap!==prevA.snap&&b.snap!==prevB.snap,`这一步的快照与上一步一字不差（基线侧 ${a.snap===prevA.snap?'没变':'变了'}、施工后侧 ${b.snap===prevB.snap?'没变':'变了'}）：入口没点到，或这一步什么都没做`);
      // 列表篇数两侧须一致；声明了 needList 的步骤列表还须非空
      check(a.list===b.list,`概览列表篇数两侧不同：基线 ${a.list}→施工后 ${b.list}`);
      if(st&&st.needList==='>0')check(a.list>0&&b.list>0,`场景失真：这一步之后概览列表是空的（基线 ${a.list} 篇、施工后 ${b.list} 篇）——筛选逻辑没真正被比到`);
      // 闸③：场景自检
      if(st&&st.meta){
        const ok=[a,b].every(x=>x.meta&&st.must(x.meta)),same=JSON.stringify(a.meta)===JSON.stringify(b.meta);
        note(`场景自检 基线 ${JSON.stringify(a.meta)}｜施工后 ${JSON.stringify(b.meta)}`);
        check(ok&&same,`场景失真或两侧自检值不同（这一步没有真的改变什么，空对空比不出差异）：基线 ${JSON.stringify(a.meta)}｜施工后 ${JSON.stringify(b.meta)}`);
      }
      // ②界面文案表：基线有而施工后没有＝红；同键不同文＝红（白名单除外）；施工后新增＝新功能自带，列一次
      const gone=Object.keys(a.i18n).filter(k=>!(k in b.i18n)),changed=Object.keys(a.i18n).filter(k=>k in b.i18n&&a.i18n[k]!==b.i18n[k]&&!WHITE.has(k)),added=Object.keys(b.i18n).filter(k=>!(k in a.i18n));
      check(gone.length===0,`基线页面上有的文案件在这一步不见了：${gone.join(', ')}`);
      check(changed.length===0,`同一条既有文案两侧不同：${changed.map(k=>`${k}「${a.i18n[k]}」→「${b.i18n[k]}」`).join('；')}`);
      const fresh=added.filter(k=>!seenAdded.has(k));fresh.forEach(k=>seenAdded.add(k));
      if(fresh.length)note(`施工后件新增文案件 ${fresh.length} 个（新功能自带，不计）：${fresh.join(',')}`);
      const sameSnap=a.snap===b.snap,sameAi=a.ai===b.ai,sameNcbi=a.ncbi===b.ncbi,sameDlg=a.dialogs===b.dialogs,noNew=!NEW_AI.test(b.ai);
      check(sameSnap,`页面／存储快照与基线不一致：${firstDiff(a.snap,b.snap)}`);
      check(sameAi,`AI 请求序列变了：基线「${a.ai||'无'}」→施工后「${b.ai||'无'}」`);
      check(sameNcbi,`NCBI 请求序列（含相邻间隔是否 ≥3s）变了：基线「${a.ncbi||'无'}」→施工后「${b.ncbi||'无'}」`);
      check(sameDlg,`确认框次数变了：基线 ${a.dialogs} 次→施工后 ${b.dialogs} 次`);
      check(noNew,`不点新功能却出现了分类／深评请求：${b.ai}`);
      if(!(sameSnap&&sameAi&&sameNcbi&&sameDlg&&noNew&&gone.length===0&&changed.length===0))diffs++;
      L.end();
    }
    console.log(`     · 差分汇总：比对的 ${steps} 步里 ${steps-diffs} 步四样逐字一致且零新增调用，${diffs} 步有差异`);
    if(!ONLY.length){   // 全量才出全程汇总（--only 单跑只看点名步骤；进程一律走完 finally 的清理再退）
      L.begin('R99','全程：两侧页面运行期异常为零、施工后件全程零分类／深评请求、AI 请求都带种子里的假钥匙、每一步都执行到位');
      check(tab.errors.length===0,`页面运行期异常 ${tab.errors.length} 条：${tab.errors.slice(0,2).join(' | ').slice(0,300)}`);
      const kinds=srv.ai.log.map(r=>r.kind);
      note(`两侧合计 AI 请求 ${kinds.length} 次（${kinds.join(',')}）｜其中分类／深评 ${kinds.filter(k=>k==='cls'||k==='deep').length} 次｜钥匙核对 ${[...new Set(srv.ai.log.map(r=>r.keyState))].join(',')}｜两侧步骤记录 ${A.length}＋${B.length} 条（应各 ${STEPS.length}）`);
      check(kinds.filter(k=>k==='cls'||k==='deep').length===0,'全程不该出现分类／深评请求');
      check(srv.ai.log.length>0&&srv.ai.log.every(r=>r.keyState==='对'),'AI 请求应都带种子里的假钥匙');
      check(A.length===STEPS.length&&B.length===STEPS.length&&[...A,...B].every(x=>!x.error),'两侧每一步都应执行到位（有执行故障的步骤见上）');
      L.end();
    }
  }finally{
    try{cdp&&cdp.close()}catch(e){}
    const left=await browser.stop();srv.server.close();
    let cleaned=true;try{rmSync(SCRATCH_ROOT,{recursive:true,force:true})}catch(e){cleaned=false}
    console.log(`     cleanup | 临时目录 ${SCRATCH_ROOT} ${cleaned?'已清空':'未清空'}${left?`｜仍有 ${left} 个带本探针 profile 标记的浏览器进程存活`:''}`);
  }
  process.exit(L.finish(`AICLS REGRESS [${LABEL}]`)?1:0);
}
main().catch(e=>{console.log('探针崩溃：'+(e&&e.stack||e));try{srv&&srv.server.close()}catch(e2){}process.exit(2)});
