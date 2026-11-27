#!/usr/bin/env node
// T1125-POOLUP 功能探针。用法：node tests/poolup/poolup_probe.mjs [--target index.html] [--base 06d08e8] [--only S02,S03] [--label run] [--chrome ...]
// 退出码 0=全绿，1=有红，2=探针故障。零真 Key／零真 LLM；NCBI 全 mock。
import {readFileSync,mkdirSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import vm from 'node:vm';
import {ROOT,sleep,sha256,norm,argOf,gitRead,ledger,startServer,connect,Tab,wire,launch,freePort,P,inlineScripts,readI18n,between,block,lineOf,
  EXT_KEY,CACHE_KEY,MIX_KEY,JOURNALS,dayShift,item,cacheFor,LS,seedFresh,POOL_IDS,QUEUE_POOL,XML_ARTICLE,fulfill,
  cacheHighYield,cacheLocalWindow,XML_MULTI_DATES,YMD} from './lib.mjs';
const argv=process.argv.slice(2),TARGET=resolve(ROOT,argOf(argv,'--target',join(ROOT,'index.html'))),LABEL=argOf(argv,'--label','run');
const BASE=argOf(argv,'--base','06d08e8'),CHROME=argOf(argv,'--chrome','C:/Program Files/Google/Chrome/Application/chrome.exe');
const ONLY=argOf(argv,'--only','').split(',').map(s=>s.trim()).filter(Boolean),skip=id=>ONLY.length&&!ONLY.includes(id);
const SCRATCH_ROOT=resolve(process.env.POOLUP_SCRATCH||join(tmpdir(),`thoradar-t1125-poolup-probe-${LABEL}`)),SCRATCH=join(SCRATCH_ROOT,'harness');
const L=ledger(),{check,note}=L,begin=(id,name)=>{if(!skip(id))L.begin(id,name)},end=()=>L.end();
const src=norm(readFileSync(TARGET,'utf8')),base=norm(gitRead(['show',`${BASE}:index.html`]));
let anchor='',officialPmid='',papers0='',site0='';
async function toRecords(tab,nlm='9900001'){
  for(const expr of [P.view('personal'),P.tab('sectors')]){const r=await tab.eval(expr);if(r!=='ok')throw new Error('入口失败 '+r)}
  if(await tab.eval('!!document.querySelector("[data-scheme-new]")'))await tab.eval(P.click('[data-scheme-new]'));
  const edit=await tab.eval(P.click('[data-scheme-edit]'));if(edit!=='ok')throw new Error('方案编辑入口 '+edit);
  if(!await tab.eval('!!document.querySelector("[data-ext-records]")')){const r=await tab.eval(P.click('[data-ext-toggle]'));if(r!=='ok')throw new Error('池外刊入口 '+r)}
  const r=await tab.eval(P.click(`[data-ext-records="${nlm}"]`));if(r!=='ok')throw new Error('题录入口 '+r);
}
async function windowTo(tab,days){await tab.eval(`(()=>{const e=document.querySelector('#window-range');e.value=${days};e.dispatchEvent(new Event('input',{bubbles:true}));return 1})()`);await tab.eval('rollingPromise?rollingPromise.then(()=>1):1');await sleep(350)}
// FIX-4 守点用料：详情格逐格文本（badges 行也带 category_label，只查 textContent 会把阵地格的漏守盖掉）；四处官方口径计数面
const DETAIL_CELLS=`[...document.querySelectorAll('#detail .meta-cell')].map(c=>c.querySelector('small').textContent+'='+c.querySelector('b').textContent)`;
const FACE=`(()=>{const read=document.querySelector('#read-count').textContent,counter=document.querySelector('#filter-counter').textContent;
  return {dlegend:document.querySelector('#design-legend').textContent,hub:document.querySelector('#hub-count').textContent,
    readDenom:read.split('/')[1].trim(),counterDenom:counter.split('/')[1].trim(),counterNum:counter.split('/')[0].trim(),
    officialTotal:PAPERS.length,derived:poolPapersDerived().length,mixed:personalFiltered().length}})()`;
async function main(){
  rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});
  const srv=await startServer({target:TARGET}),port=await freePort(),profile=join(SCRATCH,'profile');
  const browser=await launch({chrome:CHROME,profile,port,label:LABEL});let cdp,tab;
  try{
    console.log(`poolup probe | ${browser.ver.Browser} | target=${TARGET} | sha256=${sha256(readFileSync(TARGET))} | base=${BASE} | label=${LABEL}`);
    if(!skip('S01')){begin('S01','静态：官方数据/筛选/雷达函数逐字守基线，T13 锚点零改，改动面限已合流功能与随仓探针');try{
      const dataBlock=s=>{const a=s.indexOf('__THORADAR_DATA_START__'),b=s.indexOf('__THORADAR_DATA_END__');return a>=0&&b>a?s.slice(a,b):null};
      check(dataBlock(src)===dataBlock(base),'SITE_DATA 注入区变化');
      for(const [name,fn] of [
        ['官方名册与书架锚点',x=>between(x,'const JOURNAL_IDS=','function sanitizeCollections')],['JCATS',x=>between(x,'const JCATS=[','];')],
        ['jcat 语义',x=>between(x,'const JCAT_OFFDIAL','\n};')],['mergePapers',x=>block(x,'function mergePapers(')],['inWindow',x=>block(x,'function inWindow(')],
        ['filtered',x=>block(x,'function filtered(')],['windowPapers',x=>lineOf(x,'const windowPapers=')],['findAnchor',x=>block(x,'function findAnchor(')],
        ['jcatUniverse',x=>block(x,'function jcatUniverse(')],['renderScope',x=>block(x,'function renderScope(')],['kwClassify',x=>block(x,'function kwClassify(')],['sectorAssign',x=>block(x,'function sectorAssign(')]
      ]){const a=fn(base),b=fn(src);check(Boolean(a)&&a===b,name+' 与基线不一致')}
      check(lineOf(src,'function shelfMetaFor(r)')===lineOf(base,'function shelfMetaFor(r)'),'T13 书架块首行／sanitizeCollections 锚点变化');
      const tables=readI18n(src);check(Boolean(tables)&&tables.zh.size===tables.en.size&&tables.literal.zh&&tables.literal.en,'I18N 双表不完整');
      for(const k of ['poolup.toggle','poolup.hint','poolup.badge','poolup.notier','poolup.uncategorized'])check(tables&&tables.zh.has(k)&&tables.en.has(k),'缺文案键 '+k);
      let scripts=0;for(const s of inlineScripts(src)){scripts++;new vm.Script(s)}check(scripts===2,'内联脚本段数不是 2');
      const changed=gitRead(['diff','--name-only',BASE]).split('\n').filter(Boolean),untracked=gitRead(['status','--porcelain','--untracked-files=all']).split('\n').filter(l=>l.startsWith('??')).map(l=>l.slice(3).trim().replace(/^"|"$/g,''));
      const allowed=/^index\.html$|^tests\/(?:poolup|aicls|ux)\/|^deliver\/|^docs\/(?:build-spec-个性化纵深|架构地图)\.md$/,stray=[...changed,...untracked].filter(f=>!allowed.test(f)&&!/^_dispatch\//.test(f));
      check(stray.length===0,'任务外改动面 '+stray.join(','));
      check(!/(?:api_key|Bearer\s+[A-Za-z0-9]|sk-[A-Za-z0-9]{8})/i.test(src),'产品件疑似真 Key／sk- 假 Key');
      note(`静态基线 ${BASE}；改动 ${changed.join(',')||'无'}；未跟踪 ${untracked.join(',')||'无'}`);
    }catch(e){check(false,'S01 执行故障 '+e.message)}end()}
    cdp=await connect(browser.ver.webSocketDebuggerUrl);const h={cdp,origin:srv.origin,tabs:new Map()};wire(h);tab=new Tab(h,'P');await tab.open(`${srv.origin}/index.html`);
    tab.responder=async(p,rec,t)=>fulfill(t,p,rec,{status:500,text:'{"error":"mock default fault"}'});

    if(!skip('S02')){begin('S02','默认混排带标＋官方/跨刊 PMID 去重＋详情/阅读＋开关跨刷新');try{
      const f=await seedFresh(tab,srv.origin,{days:1});anchor=f.anchor;officialPmid=f.officialPmid;papers0=f.papers;site0=f.site;
      const ids=await tab.eval(POOL_IDS),derived=await tab.eval('poolPapersDerived().map(p=>p.pmid)');
      check(ids.join(',')==='88000001','默认 1 天窗应仅混排锚点日池外条，实得 '+ids.join(','));
      check(!derived.includes(officialPmid)&&derived.filter(x=>x==='88000001').length===1,'官方／跨刊 PMID 去重失败 '+derived.join(','));
      check(await tab.eval('document.querySelector("#pool-mix-toggle").checked')===true,'默认开关不是开');
      check(await tab.eval('document.querySelector("#pool-mix-control p").textContent.includes("旧缓存")&&!document.querySelector("#pool-mix-control").textContent.includes("Key 只保存")'),'池外说明被 AI 钥匙文案串改');
      check(await tab.eval('document.querySelectorAll(".ai-note[data-i18n]").length===1&&!!document.querySelector(".ai-note[data-i18n]").closest("#ai-settings")'),'ai-note 语义类必须只在 AI 设置说明行（旧单A入口依赖）');
      check(await tab.eval('document.querySelectorAll("#queue-list [data-pool-badge]").length')===1,'概览池外徽章不是 1');
      check(await tab.eval('document.querySelector(".queue-title span").textContent.includes("按日期混排")'),'有池外时队列排序标题未更新');
      await tab.eval(P.click('[data-select="pool_88000001"]'));
      check(await tab.eval('document.querySelector("#detail .detail-title").textContent')==='Pool alpha anchor unique','池外详情未打开');
      check(await tab.eval('document.querySelector("#detail").textContent.includes("池外 · 无官方档位")')===true,'详情未明示无官方档位');
      const cells=await tab.eval(DETAIL_CELLS);
      check(cells.includes('期刊阵地=池外 · 未分类'),'详情阵地格未走池外口径：'+cells.join(' | '));
      check(await tab.eval('(()=>{const m=document.querySelector("#detail .journal-meta");return !!m.querySelector("[data-pool-badge]")&&m.textContent.includes("池外 · 无官方档位")&&!/v3|v4/.test(m.textContent)})()'),'详情档位徽记走了官方 v3/v4 分支');
      const mixedIds=await tab.eval('personalFiltered().map(p=>p.id)');
      await tab.eval(P.key('body','ArrowRight'));
      check(await tab.eval('state.selected')===mixedIds[1],'键盘下一信号未沿混排列表步进：'+await tab.eval('state.selected'));
      await tab.eval(P.key('body','ArrowLeft'));
      check(await tab.eval('state.selected')==='pool_88000001','键盘上一信号回不到池外条：'+await tab.eval('state.selected'));
      await tab.eval(P.view('reading'));check((await tab.eval(QUEUE_POOL)).join(',')==='pool_88000001','阅读前 12 条未混入池外：'+JSON.stringify(await tab.eval(QUEUE_POOL)));
      check(await tab.eval('document.querySelectorAll("#queue-list .proto-domain [data-pool-badge]").length')>=1,'阅读卡顶部阵地格缺池外徽章');
      await tab.eval(P.view('overview'));const officialIds=await tab.eval('JSON.stringify(filtered().map(p=>p.id))');
      const face=await tab.eval(FACE);   // FIX-4：设计图例／雷达中心／已读栏分母／列表计数分母 四面官方口径
      check(face.counterDenom===String(face.officialTotal+face.derived),'列表计数分母不含池外：'+face.counterDenom+' 应为 '+(face.officialTotal+face.derived));
      check(face.counterNum===String(face.mixed).padStart(2,'0'),'列表计数分子不是混排在列数：'+face.counterNum);
      check(face.readDenom===String(face.officialTotal+face.derived),'已读栏分母不含池外：'+face.readDenom+' 应为 '+(face.officialTotal+face.derived));
      await tab.eval(P.check('#pool-mix-toggle',false));check((await tab.eval(POOL_IDS)).length===0,'关闭后仍有池外 '+JSON.stringify(await tab.eval(POOL_IDS))+' poolMix='+await tab.eval('poolMix'));
      const off=await tab.eval(FACE);
      check(off.dlegend===face.dlegend,'设计图例把池外条算进去了');
      check(off.hub===face.hub,'雷达中心信号数把池外条算进去了：开 '+face.hub+'／关 '+off.hub);
      check(off.readDenom===String(off.officialTotal)&&off.counterDenom===String(off.officialTotal),'关闭后分母未回官方总数');
      check(await tab.eval('document.querySelector(".queue-title span").textContent===t("queue.title1")'),'关闭后排序标题未恢复官方文案');
      check(await tab.eval('JSON.stringify(personalFiltered().map(p=>p.id))')===officialIds,'关闭后官方顺序/内容变化');
      check(await tab.eval(`JSON.parse(localStorage.getItem('${MIX_KEY}')).mix`)===false,'关闭状态未落盘');
      await tab.goto(`${srv.origin}/index.html`);check(await tab.eval('poolMix===false&&document.querySelector("#pool-mix-toggle").checked===false'),'关闭状态未跨刷新');
      await tab.eval(P.check('#pool-mix-toggle',true));await tab.goto(`${srv.origin}/index.html`);check(await tab.eval('poolMix===true'),'重开状态未跨刷新');
      check(await tab.eval('JSON.stringify(PAPERS)')===papers0&&await tab.eval('JSON.stringify(SITE_DATA)')===site0,'PAPERS/SITE_DATA 被写');
      check(tab.log.length===0&&srv.ai.log.length===0,'混排/开关产生了 NCBI 或 AI 请求');note(`池外派生 ${derived.join(',')}；默认可见 ${ids.join(',')}；开关往返并重载均保持`);
    }catch(e){check(false,'S02 执行故障 '+e.message)}end()}

    if(!skip('S03')){begin('S03','筛选口径逐项：检索/刊源/合集生效；档位不影响池外；快筛/阵地/书架选中排除');try{
      await seedFresh(tab,srv.origin,{days:1,mix:true});
      check(await tab.eval('[...document.querySelectorAll("#journal-legend [data-journal]")].map(e=>e.dataset.journal).includes("Probe Ext A")'),'刊源图例不含池外刊');   // FIX-4 N09：图例真实 DOM，不是只调 toggleJournal
      await tab.eval(P.type('#search','88000001'));check((await tab.eval(POOL_IDS)).join(',')==='88000001','PMID 检索未命中');
      await tab.eval(P.type('#search','not-found-anywhere'));check((await tab.eval(POOL_IDS)).length===0,'检索未滤除池外');
      await tab.eval(P.type('#search',''));
      for(const tier of ['S','A','B','C','D'])await tab.eval(P.click(`#tier-filters [data-tier="${tier}"]`));
      check((await tab.eval(POOL_IDS)).join(',')==='88000001'&&await tab.eval('filtered().length')===0,'池外不应受档位开关影响');
      for(const tier of ['S','A','B','C','D'])await tab.eval(P.click(`#tier-filters [data-tier="${tier}"]`));
      await tab.eval(P.click('[data-quick="rct"]'));check((await tab.eval(POOL_IDS)).length===0,'RCT 快筛应排除无设计字段的池外');
      await tab.eval(P.click('[data-quick="all"]'));
      await tab.eval('toggleSectorFilter("1")');check((await tab.eval(POOL_IDS)).length===0,'官方阵地筛选应排除池外');await tab.eval('toggleSectorFilter("1")');
      await tab.eval('state.gsec="g_probe";render()');check((await tab.eval(POOL_IDS)).length===0,'自定义阵地筛选应排除池外');await tab.eval('state.gsec=null;render()');
      await tab.eval(`myJournalsStore={v:1,picks:[paperJournalKey(PAPERS[0])],filterOn:true};render()`);check((await tab.eval(POOL_IDS)).length===0,'书架筛选应排除池外');
      await tab.eval('myJournalsStore={v:1,picks:[],filterOn:false};render()');
      await tab.eval(`collectionsStore={version:1,active:'c_ext',collections:[{id:'c_ext',name:'ext',journals:[{k:'PROBE EXT A',nlm:'9900001'}]}]};render()`);
      check((await tab.eval(POOL_IDS)).join(',')==='88000001','含池外刊合集应保留池外');
      await tab.eval(`collectionsStore={version:1,active:'c_off',collections:[{id:'c_off',name:'off',journals:[{k:paperJournalKey(PAPERS[0])}]}]};render()`);
      check((await tab.eval(POOL_IDS)).length===0,'不含池外刊合集应排除池外');await tab.eval('collectionsStore={version:1,active:null,collections:[]};render()');
      await tab.eval('toggleJournal("Probe Ext A")');check((await tab.eval(POOL_IDS)).join(',')==='88000001','池外刊源筛选未生效');await tab.eval('toggleJournal("Probe Ext A")');
      note('检索、合集、刊源与官方同口径；池外无 tier/score，五档全关仍保留；快筛/书架/官方及自定义阵地选中时排除');
    }catch(e){check(false,'S03 执行故障 '+e.message)}end()}

    if(!skip('S04')){begin('S04','时间窗：精确 day 参与 anchor N 日；仅年份旧缓存不猜日期；窗口往返零 NCBI');try{
      const f=await seedFresh(tab,srv.origin,{days:7,mix:true});anchor=f.anchor;const m=tab.mark();
      check((await tab.eval(POOL_IDS)).sort().join(',')==='88000001,88000002','7 天窗应含锚点与前 1 日、不含前 7 日/仅年份');
      await windowTo(tab,1);check((await tab.eval(POOL_IDS)).join(',')==='88000001','1 天窗未收窄');
      await windowTo(tab,7);check((await tab.eval(POOL_IDS)).sort().join(',')==='88000001,88000002','7 天窗未恢复');
      check(!await tab.eval('poolPapersDerived().some(p=>p.pmid==="88000003"&&personalFiltered().includes(p))'),'仅年份旧缓存被猜日期混入');
      const ord=await tab.eval(`(()=>{const l=personalFiltered(),dates=l.map(p=>dateMs(p.briefing_date)||0);let desc=true,poolFirst=true,cross=false;
        dates.forEach((v,i)=>{if(i&&dates[i-1]<v)desc=false});if(new Set(l.map(p=>p.briefing_date)).size>1)cross=true;
        l.forEach((p,i)=>{for(let j=i+1;j<l.length;j++)if(l[i].briefing_date===l[j].briefing_date&&l[j].pool_ext&&!p.pool_ext)poolFirst=false});
        const off=l.filter(p=>!p.pool_ext),byDay=new Map();off.forEach(p=>{const d=p.briefing_date;if(!byDay.has(d))byDay.set(d,[]);byDay.get(d).push(filtered().findIndex(q=>q.id===p.id))});
        const officialKeepsScoreOrder=[...byDay.values()].every(r=>r.every((v,i)=>i===0||r[i-1]<v));   // 只在同日内比评分原序：跨日本来就按日期重排，与 filtered() 原序不同是对的
        return {desc,poolFirst,cross,n:l.length,officialKeepsScoreOrder}})()`);
      check(ord.cross&&ord.n>2,'场景失真：7 天窗混排列表没有跨日样本 '+JSON.stringify(ord));
      check(ord.desc,'混排未按日期新→旧：'+JSON.stringify(ord));   // FIX-4 N13
      check(ord.poolFirst,'同日池外不在前：'+JSON.stringify(ord));
      check(ord.officialKeepsScoreOrder,'同日官方未保持评分原序：'+JSON.stringify(ord));
      check(tab.since(m).length===0,'时间窗操作触发 NCBI');note(`anchor=${anchor}；day=${anchor} 与 ${dayShift(anchor,-1)} 入 7 日，${dayShift(anchor,-7)} 与空 day 不入`);
    }catch(e){check(false,'S04 执行故障 '+e.message)}end()}

    if(!skip('S05')){begin('S05','数据源纪律：无名册/无缓存零拉取；真实入口冷开 mock 拉取、精确 day 落缓存、24h 再开零请求、显式刷新');try{
      const f=await seedFresh(tab,srv.origin,{days:7,mix:true,cache:false});anchor=f.anchor;let m=tab.mark();
      check(tab.since(m).length===0&&(await tab.eval(POOL_IDS)).length===0,'无缓存首屏自动拉取/上盘');
      const days={[ '88000011']:anchor,['88000002']:dayShift(anchor,-1),['88000012']:dayShift(anchor,-7)};
      tab.responder=async(p,rec,t)=>{const u=new URL(rec.url);if(rec.kind==='esearch')return fulfill(t,p,rec,{text:JSON.stringify({esearchresult:{count:'3',idlist:Object.keys(days)}})});
        const xml=`<?xml version="1.0"?><PubmedArticleSet>${Object.entries(days).map(([id,d])=>XML_ARTICLE(id,'Cold fetched '+id,d)).join('')}</PubmedArticleSet>`;return fulfill(t,p,rec,{type:'application/xml',text:xml})};
      await toRecords(tab);await tab.waitFor('poolView&&!poolView.loading&&!poolView.failed&&poolView.at>0',20000,'冷开拉取');
      const reqs=tab.since(m),gap=reqs.length>1?reqs[1].t-reqs[0].t:0;
      check(reqs.length===2&&gap>=2990,'冷开应 esearch+efetch 串行且间隔≥3s：'+reqs.map(r=>r.kind).join(','));
      check((await tab.eval(POOL_IDS)).sort().join(',')==='88000002,88000011','冷取后精确日期未驱动 7 天混排');
      check(await tab.eval('!!document.querySelector("#queue-list [data-select=\\"pool_88000011\\"]")'),'冷取后真实队列 DOM 未出现池外条（只更新缓存不算上屏）');
      check(await tab.eval(`Object.values(JSON.parse(localStorage.getItem('${CACHE_KEY}')).byNlm['9900001'].items).every(x=>/^\\d{4}-\\d{2}-\\d{2}$/.test(x.day))`),'精确 day 未落盘');
      await tab.eval(P.click('#pool-close'));m=tab.mark();await tab.eval(P.click('[data-ext-records="9900001"]'));await tab.waitFor('poolView&&poolView.fresh&&!poolView.loading',15000,'24h 缓存重开收尾');const reopenN=tab.since(m).length;check(reopenN===0,'24h 内重开有请求 '+reopenN);
      await tab.eval(P.click('#pool-refresh'));await tab.waitFor('poolView&&!poolView.loading&&!poolView.failed',20000,'显式刷新');const refreshN=tab.since(m).length-reopenN;check(refreshN===2,'显式刷新未重新拉取，新增请求 '+refreshN);
      note(`冷开 ${reqs.map(r=>r.kind).join('→')}，gap=${gap}ms；24h 再开 ${reopenN} 请求；刷新 ${refreshN} 请求；全程 AI ${srv.ai.log.length}`);
    }catch(e){check(false,'S05 执行故障 '+e.message)}end()}

    if(!skip('S06')){begin('S06','断网/失败保留旧缓存与混排条；陈旧面板给失败文案，不空盘');try{
      await seedFresh(tab,srv.origin,{days:7,mix:true});await tab.eval(`(()=>{const c=JSON.parse(localStorage.getItem('${CACHE_KEY}'));c.byNlm['9900001'].until=0;localStorage.setItem('${CACHE_KEY}',JSON.stringify(c));return 1})()`);await tab.goto(`${srv.origin}/index.html`);
      const before=await tab.eval(`localStorage.getItem('${CACHE_KEY}')`),m=tab.mark();tab.responder=async(p,rec,t)=>fulfill(t,p,rec,{status:500,text:'{"error":"mock offline"}'});await toRecords(tab);await tab.waitFor('poolView&&!poolView.loading&&poolView.failed',15000,'失败回退');
      check(await tab.eval(`localStorage.getItem('${CACHE_KEY}')`)===before,'失败改写了旧缓存');check((await tab.eval(POOL_IDS)).includes('88000002'),'失败后第一本刊独有的旧池外条从混排消失');
      check(await tab.eval('document.querySelector("#pool-body").textContent.includes("保留旧缓存")'),'面板没有保留旧缓存文案');check(tab.since(m).length===1,'500 非限流错误不应重复烧请求');
      note(`失败后派生可见 ${JSON.stringify(await tab.eval(POOL_IDS))}｜内存缓存条数 ${await tab.eval('poolCache.byNlm["9900001"].items.length')}｜真实队列池外条 ${await tab.eval('document.querySelectorAll("#queue-list [data-select^=pool_]").length')}`);
    }catch(e){check(false,'S06 执行故障 '+e.message)}end()}

    if(!skip('S07')){begin('S07','无池外名册官方视图等价：派生队列为空、personalFiltered=filtered、雷达 DOM 与官方计数不变');try{
      await tab.eval(`localStorage.clear();1`);await tab.goto(`${srv.origin}/index.html`);const before=await tab.eval(`JSON.stringify({ids:filtered().map(p=>p.id),blips:document.querySelector('#blips').innerHTML,sectors:document.querySelector('#journal-sectors').innerHTML,hub:document.querySelector('#hub-count').textContent,papers:JSON.stringify(PAPERS),site:JSON.stringify(SITE_DATA)})`);
      const eq=await tab.eval(`personalFiltered().length===filtered().length&&personalFiltered().every((p,i)=>p===filtered()[i])&&poolPapersDerived().length===0`);
      check(eq,'无 ext 时派生结果不是逐对象同序等价');const after=await tab.eval(`JSON.stringify({ids:filtered().map(p=>p.id),blips:document.querySelector('#blips').innerHTML,sectors:document.querySelector('#journal-sectors').innerHTML,hub:document.querySelector('#hub-count').textContent,papers:JSON.stringify(PAPERS),site:JSON.stringify(SITE_DATA)})`);
      check(before===after,'无 ext 官方 DOM/数据变化');check(await tab.eval('!!document.querySelector("#pool-mix-toggle")'),'新开关缺失');
    }catch(e){check(false,'S07 执行故障 '+e.message)}end()}

    if(!skip('S08')){begin('S08','存储护栏：坏偏好回默认开；缓存 XSS 只作文字；非法 day 不入窗');try{
      const f=await seedFresh(tab,srv.origin,{days:1,mix:true});anchor=f.anchor;
      const bad={v:1,byNlm:{'9900001':{at:Date.now(),until:Date.now()+86400000,total:2,pmids:['88000021','88000022'],items:[item('88000021','<img id="pool-xss" src=x onerror=alert(1)> Pool escaped',anchor),item('88000022','Bad date must hide','2026-99-99')]}}};
      await tab.eval(`${LS(CACHE_KEY,bad)};localStorage.setItem('${MIX_KEY}','{"v":1,"mix":"yes"}');1`);await tab.goto(`${srv.origin}/index.html`);
      check(await tab.eval('poolMix===true'),'坏偏好未回默认开');check((await tab.eval(POOL_IDS)).join(',')==='88000021','非法 day 未排除');
      check(await tab.eval('!!document.querySelector("#pool-xss")')===false,'缓存标题 XSS 成 DOM');check(await tab.eval('document.querySelector("#queue-list").textContent.includes("<img id=\\"pool-xss\\"")'),'转义后的标题文字不可见');
      await tab.eval(P.view('reading'));   // FIX-4 N12：阅读卡是另一条渲染路径，转义须单独守
      check(await tab.eval('!!document.querySelector("#queue-list #pool-xss")')===false,'阅读卡缓存标题 XSS 成 DOM');
      check(await tab.eval('document.querySelector("#queue-list").textContent.includes("<img id=\\"pool-xss\\"")'),'阅读卡转义后的标题文字不可见');
      check(await tab.eval('document.querySelector("#queue-list strong")!==null'),'阅读卡标题节点缺失');
      await tab.eval(P.view('overview'));
    }catch(e){check(false,'S08 执行故障 '+e.message)}end()}
    if(!skip('S09')){begin('S09','FIX-2 池外时间窗独立锚本地当天（官方 inWindow 口径不变）＋FIX-4 入库日优先序');try{
      const f=await seedFresh(tab,srv.origin,{days:1,mix:true,cache:false});anchor=f.anchor;
      const today=await tab.eval('poolLocalToday()');
      await tab.eval(`${LS(CACHE_KEY,cacheLocalWindow(anchor,today))};1`);await tab.goto(`${srv.origin}/index.html`);
      const ids=(await tab.eval(POOL_IDS)).sort();
      check(ids.includes('88200001'),'本地当天池外条未入 1 天窗：'+ids.join(','));
      check(ids.includes('88200002'),'锚点日池外条应仍在 1 天窗（下界不变）：'+ids.join(','));
      check(!ids.includes('88200003'),'晚于本地当天的未来日不应入窗：'+ids.join(','));
      check(!ids.includes('88200004'),'无精确 day 旧缓存被猜日期混入：'+ids.join(','));
      if(today!==anchor){
        if(dayShift(today,-1)!==anchor)check(ids.includes('88200005'),'锚点与本地当天之间的池外条未入窗：'+ids.join(','));   // 与 cacheLocalWindow 造条条件一致：只差 1 天时没有这条料
        check(await tab.eval(`inWindow({briefing_date:${JSON.stringify(today)}})`)===false,'官方 inWindow 口径被改：晚于官方锚点的官方条不应入窗');
        check(await tab.eval(`poolInWindow({briefing_date:${JSON.stringify(today)}})`)===true,'poolInWindow 未把上界抬到本地当天');
      }else note('本地当天＝官方锚点日，FIX-2 抬上界分支无样本（只验到同历路径）');
      check(await tab.eval('filtered().every(p=>dateMs(p.briefing_date)<=dateMs(ANCHOR))'),'官方在列表出现晚于锚点的条');
      const m=tab.mark();await windowTo(tab,7);
      check((await tab.eval(POOL_IDS)).includes('88200001'),'7 天窗本地当天池外条消失');
      check(tab.since(m).length===0,'窗口操作触发 NCBI');await windowTo(tab,1);
      const wrap=x=>`<?xml version="1.0"?><PubmedArticleSet>${x}</PubmedArticleSet>`;
      const three=wrap(XML_MULTI_DATES('88300001',{entrez:YMD('2026-11-25'),article:YMD('2026-11-20'),journal:YMD('2026-01-02')}));
      const noEntrez=wrap(XML_MULTI_DATES('88300002',{entrez:'',article:YMD('2026-11-20'),journal:YMD('2026-01-02')}));
      const onlyJournal=wrap(XML_MULTI_DATES('88300003',{entrez:'',article:'',journal:YMD('2026-01-02')}));
      const got=await tab.eval(`[${JSON.stringify(three)},${JSON.stringify(noEntrez)},${JSON.stringify(onlyJournal)}].map(x=>parsePubmedXML(x,true)[0].day)`);
      check(got.join(',')==='2026-11-25,2026-11-20,2026-01-02','入库日优先序不是 entrez→ArticleDate→期刊日：'+got.join(','));
      check(await tab.eval(`parsePubmedXML(${JSON.stringify(three)},false)[0].day===undefined`),'poolDay=false 官方解析输出形状变了');
      note(`anchor=${anchor}｜本地当天=${today}｜1 天窗池外 ${ids.join(',')}｜三样本取日 ${got.join(',')}`);
    }catch(e){check(false,'S09 执行故障 '+e.message)}end()}

    if(!skip('S10')){begin('S10','FIX-1 阅读视图池外 ≤3、官方按混排原序补满（概览全列出不变）＋FIX-4 阅读视图选中校正');try{
      const f=await seedFresh(tab,srv.origin,{days:1,mix:true,cache:false});anchor=f.anchor;
      await tab.eval(`${LS(CACHE_KEY,cacheHighYield(anchor,17))};1`);await tab.goto(`${srv.origin}/index.html`);
      const all=await tab.eval('personalFiltered().map(p=>({id:p.id,pool:!!p.pool_ext}))'),poolAll=all.filter(x=>x.pool).map(x=>x.id);
      check(poolAll.length===17,'场景失真：高产池外不是 17 条：'+poolAll.length);
      check(all.slice(0,17).every(x=>x.pool),'概览同日池外在前规则变了');
      check(await tab.eval('document.querySelectorAll("#queue-list [data-select^=pool_]").length')===17,'概览完整队列未全列出 17 条池外');
      const expect=[];let pc=0;for(const x of all){if(expect.length>=12)break;if(x.pool){if(pc>=3)continue;pc++}expect.push(x.id)}   // 独立复算期望序列，不调用页面 readingTop12
      await tab.eval(P.view('reading'));
      const cards=await tab.eval('[...document.querySelectorAll("#queue-list [data-select]")].map(e=>e.dataset.select)'),readPool=cards.filter(id=>id.startsWith('pool_'));
      check(cards.length===12,'阅读视图不是 12 条：'+cards.length);
      check(readPool.length<=3,'阅读视图池外超过 3 条：'+readPool.length);
      check(cards.length-readPool.length>=9,'阅读视图官方不足 9 条：'+(cards.length-readPool.length));
      check(cards.join(',')===expect.join(','),'阅读视图序列≠按混排原序跳过第 4 条起池外：'+cards.join(','));
      check(readPool.join(',')===poolAll.slice(0,3).join(','),'阅读视图留下的不是混排前 3 条池外');
      check(await tab.eval('document.querySelectorAll("#queue-list .proto-domain [data-pool-badge]").length')===readPool.length,'阅读卡顶部阵地格池外徽章数与池外卡数不符');   // 每张池外卡顶部 1 枚＋meta 行 tierMark 1 枚，只数顶部那枚
      const rc=await tab.eval('document.querySelector("#proto-reading-count").textContent');
      check(rc.startsWith('显示 12 / '+all.length+' '),'阅读视图计数未披露 12/混排总数：'+rc);
      await tab.eval(P.view('overview'));
      const outside=all.find(x=>!x.pool&&!expect.includes(x.id));
      check(Boolean(outside),'场景失真：没有 top12 之外的官方条可用于选中校正');
      if(outside){
        await tab.eval(`state.selected=${JSON.stringify(outside.id)};render()`);
        check(await tab.eval('state.selected')===outside.id,'场景失真：概览里选不中 top12 之外的官方条');
        await tab.eval(P.view('reading'));
        check(await tab.eval('state.selected')===expect[0],'切阅读视图未把选中篇校正到 top12 第一条：'+await tab.eval('state.selected')+' 应为 '+expect[0]);
        check(await tab.eval(`document.querySelector("#queue-list [data-select=\\"${expect[0]}\\"]").classList.contains("selected")`),'校正后第一张卡不是选中态');
      }
      await tab.eval(P.view('overview'));await tab.eval(`state.selected=${JSON.stringify(expect[5])};1`);
      await tab.eval(P.view('reading'));
      check(await tab.eval('state.selected')===expect[5],'选中篇已在 top12 内却被改：'+await tab.eval('state.selected'));
      await tab.eval(P.view('overview'));
      note(`混排总长 ${all.length}（池外 ${poolAll.length}）｜阅读 12 条＝池外 ${readPool.length}＋官方 ${cards.length-readPool.length}｜top12 外官方条 ${outside&&outside.id}`);
    }catch(e){check(false,'S10 执行故障 '+e.message)}end()}

    if(!skip('S11')){begin('S11','FIX-3 诚实性：详情三格未核查（中英成对）＋过期缓存带标＋阅读卡标题不重复＋空态区分口径');try{
      const f=await seedFresh(tab,srv.origin,{days:1,mix:true});anchor=f.anchor;
      await tab.h.cdp.send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false},tab.sid);
      await tab.eval(P.click('[data-select="pool_88000001"]'));
      const cells=await tab.eval(DETAIL_CELLS);
      check(cells.includes('预警状态=未核查'),'池外预警格未改未核查：'+cells.join(' | '));
      check(cells.includes('精选状态=未核查 · 不参与精选'),'池外精选格未改未核查：'+cells.join(' | '));
      check(cells.includes('出版状态=未核查'),'池外出版状态格未改未核查：'+cells.join(' | '));
      check(!cells.includes('预警状态=正常')&&!await tab.eval('document.querySelector("#detail").textContent.includes("未入选 · 不凑数")'),'池外详情仍沿用官方已核查口径');
      check(await tab.eval('document.querySelector("#detail .status-pill").textContent')==='出版状态 · 未核查','状态胶囊未改无核查口径');
      await tab.eval(P.click('#lang-btn'));
      const en=await tab.eval(DETAIL_CELLS);
      check(en.includes('Watchlist status=Not checked')&&en.includes('Curation=Not checked · not part of curation')&&en.includes('Publication status=Not checked'),'英文详情三格未成对：'+en.join(' | '));
      check(await tab.eval('document.querySelector("#detail .status-pill").textContent')==='Publication status · not checked','英文状态胶囊未成对');
      const rows=await tab.eval(`(()=>{const el=document.querySelector('.queue-title [data-i18n="queue.title1"]'),r=document.createRange();r.selectNodeContents(el);return {lines:r.getClientRects().length,h:el.getBoundingClientRect().height,text:el.textContent}})()`);
      check(rows.lines>0&&rows.lines<=2,'英文队列标题仍折成三行以上：'+JSON.stringify(rows));note(`英文队列标题 ${rows.lines} 行／高 ${rows.h}px｜${rows.text}`);
      await tab.eval(P.click('#lang-btn'));
      await tab.eval(`(()=>{const c=JSON.parse(localStorage.getItem('${CACHE_KEY}'));Object.values(c.byNlm).forEach(x=>{x.until=Date.now()-1000});localStorage.setItem('${CACHE_KEY}',JSON.stringify(c));return 1})()`);
      await tab.goto(`${srv.origin}/index.html`);
      check((await tab.eval(POOL_IDS)).length>0,'场景失真：过期缓存不再混排');
      check(await tab.eval('document.querySelectorAll("#queue-list [data-pool-stale]").length')>0,'过期缓存混排条没有「已过期」陈旧标识');
      check(await tab.eval('[...document.querySelectorAll("#queue-list [data-pool-stale]")].every(e=>e.textContent==="已过期")'),'陈旧标识措辞与题录面板不一致');
      await tab.eval(P.view('reading'));
      const card=await tab.eval(`(()=>{const el=document.querySelector('#queue-list [data-select="pool_88000001"]');if(!el)return null;const sub=el.querySelector('.proto-title-en');
        return {strong:el.querySelector('strong').textContent,sub:sub.textContent,subHeight:sub.getBoundingClientRect().height,stale:el.querySelectorAll('[data-pool-stale]').length}})()`);
      check(Boolean(card),'阅读视图里找不到池外卡');
      if(card){
        check(card.strong==='Pool alpha anchor unique','阅读卡主标题变了：'+card.strong);
        check(card.sub===''&&card.subHeight===0,'阅读卡标题仍重复两遍：'+JSON.stringify(card));
        check(card.stale>=1,'阅读卡过期缓存条未带陈旧标识');
      }
      await tab.eval(P.view('overview'));
      for(const tier of ['S','A','B','C','D'])await tab.eval(P.click(`#tier-filters [data-tier="${tier}"]`));
      check(await tab.eval('filtered().length')===0,'场景失真：五档全关后官方仍在列');
      check((await tab.eval(POOL_IDS)).length>0,'场景失真：五档全关后池外也不在列');
      const empty=await tab.eval('document.querySelector("#scope-empty").textContent');
      check(empty.includes('官方当前筛选下无在列信号')&&empty.includes('池外缓存有'),'空态未给池外区分口径：'+empty);
      check(!empty.includes('当前数据窗口内无论文。请调整滑杆或刊源档位。'),'官方为空而池外在列时仍写「当前数据窗口内无论文」');
      for(const tier of ['S','A','B','C','D'])await tab.eval(P.click(`#tier-filters [data-tier="${tier}"]`));
      note('详情三格中英均「未核查」；过期缓存概览＋阅读卡均带「已过期」；阅读卡英文副标为空且不占位；空态区分官方与池外');
    }catch(e){check(false,'S11 执行故障 '+e.message)}end()}
    check(tab.errors.length===0,`全程页面异常 ${tab.errors.length} 条：${tab.errors.slice(0,3).join(' | ')}`);check(srv.ai.log.length===0,'全程出现 AI 请求');
  }finally{try{cdp&&cdp.close()}catch(e){}const left=await browser.stop();srv.server.close();rmSync(SCRATCH_ROOT,{recursive:true,force:true});console.log(`     cleanup | 临时目录 ${SCRATCH_ROOT} 已清｜残留进程 ${left}`)}
  process.exit(L.finish(`POOLUP PROBE [${LABEL}]`)?1:0);
}
main().catch(e=>{console.log('poolup 探针崩溃：'+(e&&e.stack||e));try{rmSync(SCRATCH_ROOT,{recursive:true,force:true})}catch(e2){}process.exit(2)});
