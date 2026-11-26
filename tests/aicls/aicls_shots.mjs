#!/usr/bin/env node
// T1125-AICLS 样式自查截图（tests/aicls/aicls_shots.mjs）——施工席自证件：截图只供样式自查，不构成验收结论，验收权归独立复核席
// 用法：node tests/aicls/aicls_shots.mjs [--target <index.html>] [--out <目录>] [--label 名称] [--chrome <chrome.exe|msedge.exe>]
// 做什么：把本单新增的界面逐个摆到真实状态下截图，落 --out（缺省 deliver/shots/）：
//   ①钥匙「仅本会话」开关与一句话说明（记住档／会话档／英文）②分类进度行（无 Key／在途·含停止钮／完成）③深评块（默认关／在途／有结果／与「解读暂停」同位）④无 Key 点深评的引导
//   每处一张局部裁切，关键处另加一张整视口（1440×900）；另出窄屏（390×844，模拟）与深色若干张。
// 取景：view＝先把它瞬时滚进视口（不等平滑滚动）；clip＝截这些元素此刻的外接矩形（不再滚动，夹在视口内）；都不给＝整视口。
//   详情卡是 350px 宽的独立滚动栏，深评块在摘要之后——所以深评各图一律先把深评块滚进视口，再截整张详情卡。
// 状态一律走真实入口（种浏览器存储→重载→点界面），AI 请求打到本机假应答服务。
// 钥匙纪律：全程只用写死的假钥匙占位串；Key 框是密码框，截图里只见圆点。每张图落盘前断言「页面可见文本、非密码输入框的值、提示属性里都不含钥匙串，
//   且带钥匙的输入框仍是密码框」，不过＝这张图不落盘并报红。临时件只落系统临时目录、跑完即清；进程清理只按 PID。
import {readFileSync,writeFileSync,mkdirSync,rmSync,statSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {ROOT,sleep,sha256,argOf,ledger,startServer,connect,Tab,wire,launch,freePort,P,FAKE_KEY_A,FAKE_KEY_B} from './lib.mjs';

const argv=process.argv.slice(2);
const TARGET=resolve(ROOT,argOf(argv,'--target',join(ROOT,'index.html')));
const OUT=resolve(argOf(argv,'--out',join(ROOT,'deliver','shots')));
const LABEL=argOf(argv,'--label','shots');
const CHROME=argOf(argv,'--chrome','C:/Program Files/Google/Chrome/Application/chrome.exe');
const SCRATCH_ROOT=resolve(process.env.AICLS_SCRATCH||join(tmpdir(),`thoradar-t1125-aicls-shots-${LABEL}`));
const SCRATCH=join(SCRATCH_ROOT,'harness');
const L=ledger(),{check,note}=L;

const LS=(k,v)=>`localStorage.setItem(${JSON.stringify(k)},${JSON.stringify(JSON.stringify(v))})`;
const AI_CFG=origin=>({baseUrl:origin,apiKey:FAKE_KEY_A,model:'probe-mock'});
const SCHEME={version:2,schemes:[{id:'s_shots1',name:'我的随访方向',mode:'topic',sectors:[   // 主题词模式起步：关键词先出图、其余等 AI 分类
  {id:'g_a',name:'肺癌微创',folded:false,journals:[],words:{include:['lung','segmentectomy'],exclude:[]}},
  {id:'g_b',name:'食管癌',folded:false,journals:[],words:{include:['esophageal','esophag'],exclude:[]}}],order:['g_a','g_b']}],active:'s_shots1'};
// 合成论文：只进测试页内存里的 PAPERS（不落任何文件）——把窗内撑到 78 篇，保证「未分组」的够分 2 批以上
const seedPapers=(start,count)=>`(()=>{const out=[],T=['minimally invasive lobectomy','neoadjuvant esophagectomy','lung nodule screening'];
  for(let i=0;i<${count};i++){const n=${start}+i;out.push({id:'pmid_'+(90000000+n),pmid:String(90000000+n),title_en:'Probe synthetic paper '+n+' about '+T[n%3],title_zh:'',
    abstract_en:'Synthetic abstract '+n+' on '+T[n%3]+' outcomes.',results:'',briefing_date:ANCHOR,pub_date:ANCHOR,score_total:40-(n%20),tier:'B',tier_scheme:'v4',
    journal_abbr:'PROBE J',journal_full:'Probe Journal',category:'surgery',category_label:'probe',study_type:'RCT',publish_state:'ok',status:{kind:'ok'}})}
  PAPERS=PAPERS.concat(out);return out.length})()`;
const DEEP_TEXT='【研究问题】\n食管癌微创手术与开放手术相比，围术期结果有没有差别。\n\n【设计与样本】\n多中心随机对照试验；纳入 12 个中心、共 1,024 例可切除食管鳞癌患者。\n\n【主要发现】\n微创组肺部并发症更少；淋巴结清扫数目与 3 年总生存两组相近。\n\n【局限与待核实】\n以上是探针的假应答正文，只用来核对排版。\n\n【对临床实践的含义】\n结论只依据摘要所载信息，不替代阅读原文。';
// 页面侧：钥匙零回显断言（可见文本／非密码输入框的值／title·placeholder·alt 属性里都不得出现钥匙串；带钥匙的输入框必须是密码框）
const LEAK=`(()=>{const K=${JSON.stringify(FAKE_KEY_A)},B=${JSON.stringify(FAKE_KEY_B)},has=s=>s.includes(K)||s.includes(B);
  if(has(document.body.innerText))return '可见文本';
  for(const e of document.querySelectorAll('input,textarea')){if(e.type!=='password'&&has(String(e.value||'')))return '输入框明文：'+(e.id||e.name||e.type)}
  for(const e of document.querySelectorAll('[title],[placeholder],[alt]')){if(has((e.getAttribute('title')||'')+(e.getAttribute('placeholder')||'')+(e.getAttribute('alt')||'')))return '提示属性：'+(e.id||e.tagName)}
  return ''})()`;
const PROGRESS=['#scheme-editor .tw-chips','#cls-progress'];   // 进度行各图的裁切范围：主题词区（词块＋输入框）到进度行

let VW=1440,VH=900;
const metrics=(tab,w,h,mobile=false,scale=1)=>{VW=w;VH=h;return tab.h.cdp.send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:scale,mobile},tab.sid)};
let shotNo=0;
async function shot(tab,file,opt={}){   // opt＝{view:选择器, clip:[选择器…], block:'center'|'end'|'start', pad}
  shotNo++;
  const block=opt.block||'center',pad=opt.pad==null?10:opt.pad;
  if(opt.view){   // 先取景：瞬时滚动（页面上有平滑滚动，等它滚完再截）
    const v=await tab.eval(`(()=>{const el=document.querySelector(${JSON.stringify(opt.view)});if(!el)return 'MISSING:'+${JSON.stringify(opt.view)};el.scrollIntoView({block:${JSON.stringify(block)},inline:'nearest',behavior:'instant'});return 'ok'})()`);
    if(v!=='ok')throw new Error('取景目标不在页面里：'+v);
    await sleep(450);
  }
  let clip=null;
  if(opt.clip){
    const r=await tab.eval(`(()=>{const els=${JSON.stringify([].concat(opt.clip))}.map(s=>document.querySelector(s));if(els.some(e=>!e))return null;const bs=els.map(e=>e.getBoundingClientRect());
      return {x:Math.min(...bs.map(b=>b.x)),y:Math.min(...bs.map(b=>b.y)),r:Math.max(...bs.map(b=>b.right)),b:Math.max(...bs.map(b=>b.bottom))}})()`);
    if(!r)throw new Error('截图目标不在页面里：'+[].concat(opt.clip).join(' '));
    await sleep(200);
    const x=Math.max(0,r.x-pad),y=Math.max(0,r.y-pad);
    clip={x,y,width:Math.max(40,Math.min(VW-x,r.r+pad-x)),height:Math.max(40,Math.min(VH-y,r.b+pad-y)),scale:1};
    if(r.b<=0||r.y>=VH||r.r<=0||r.x>=VW)throw new Error(`裁切目标此刻不在视口内：${[].concat(opt.clip).join(' ')}（矩形 ${JSON.stringify(r)}）`);
  }
  const {data}=await tab.h.cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,...(clip?{clip}:{})},tab.sid);
  const leak=await tab.eval(LEAK),fileOut=join(OUT,file+'.png');
  if(leak){check(false,`${file}：页面里出现了钥匙（${leak}）——这张图不落盘`);return null}
  writeFileSync(fileOut,Buffer.from(data,'base64'));
  const bytes=statSync(fileOut).size;
  check(bytes>4000,`${file}：截图小得异常（${bytes} 字节，疑似空白）`);
  note(`落盘 ${file}.png｜${bytes} 字节｜范围 ${clip?`${Math.round(clip.width)}×${Math.round(clip.height)} @ (${Math.round(clip.x)},${Math.round(clip.y)})`:'整视口 '+VW+'×'+VH}｜钥匙零回显=是`);
  return clip;
}
async function group(id,name,fn){L.begin(id,name);try{await fn()}catch(e){check(false,'执行故障：'+e.message)}L.end()}
async function fresh(tab,seeds,origin){await tab.eval(`localStorage.clear();sessionStorage.clear();${seeds.join(';')};1`);await tab.goto(`${origin}/index.html`);await sleep(600)}
async function toEditor(tab){   // 真实入口：个性化→自定义阵地→编辑方案→选中第一个阵地（主题词区随之出现）
  await tab.eval(P.view('personal'));await sleep(500);await tab.eval(P.tab('sectors'));await sleep(300);
  const a=await tab.eval(P.click('[data-scheme-edit="s_shots1"]')),b=await tab.eval(P.click('[data-sector-select="g_a"]'));
  if(a!=='ok'||b!=='ok')throw new Error(`进不了方案编辑器：${a}／${b}`);
  await sleep(400);
}
const slow=text=>rec=>({status:200,text:typeof text==='function'?text(rec):text,delay:2600});   // 把应答拖住 2.6s：好在「在途」状态截图
const clsDefault=rec=>JSON.stringify(rec.payload.papers.map(p=>({pmid:p.pmid,sec:rec.payload.sectors[0].id})));
async function waitAiKind(srv,from,kind){for(let i=0;i<300;i++){if(srv.ai.log.slice(from).some(r=>r.kind===kind))return;await sleep(50)}throw new Error(kind+' 请求 15s 未到达')}
const CARD='#detail',BLOCK='#deep-box';   // 详情卡（独立滚动栏）／深评默认关块

async function main(){
  rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});mkdirSync(OUT,{recursive:true});   // 输出目录只增不删：同名覆盖，别的一概不碰
  const srv=await startServer({target:TARGET}),port=await freePort(),profile=join(SCRATCH,'profile');
  const browser=await launch({chrome:CHROME,profile,port,label:LABEL});
  let cdp,tab;
  try{
    console.log(`aicls shots | ${browser.ver.Browser} | target=${TARGET}（sha256=${sha256(readFileSync(TARGET))}）| out=${OUT} | label=${LABEL}`);
    cdp=await connect(browser.ver.webSocketDebuggerUrl);
    const h={cdp,origin:srv.origin,tabs:new Map()};wire(h);
    tab=new Tab(h,'A');await tab.open(`${srv.origin}/index.html`);await metrics(tab,1440,900);

    // ---- ① 钥匙两档的开关与一句话说明 ----
    await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
    await group('K1','钥匙开关·记住档（默认）：三件套已填、开关未勾',async()=>{
      await tab.eval(P.view('personal'));await sleep(500);await tab.eval(P.tab('topics'));await sleep(500);
      await shot(tab,'01a-ai-remember-viewport');
      await shot(tab,'01b-ai-remember',{clip:'#ai-settings',pad:14});
    });
    await group('K2','钥匙开关·仅本会话档：勾上后 Key 只在本页内存（框里仍是圆点）',async()=>{
      await tab.eval(P.check('#ai-session-only',true));await sleep(500);
      await shot(tab,'02-ai-session',{clip:'#ai-settings',pad:14});
    });
    await group('K3','钥匙开关·英文界面',async()=>{
      await tab.eval(P.click('#lang-btn'));await sleep(500);
      await shot(tab,'03-ai-session-en',{clip:'#ai-settings',pad:14});
      await tab.eval(P.click('#lang-btn'));await sleep(300);
    });

    // ---- ② 分类进度行 ----
    await fresh(tab,[LS('thoradar.sectors.v2',SCHEME)],srv.origin);
    await group('C1','进度行·无 Key：点「保存并重分类」只出关键词结果＋一句说明',async()=>{
      await toEditor(tab);
      const n0=srv.ai.log.length;
      await tab.eval(P.click('[data-tw-save]'));await tab.waitFor('clsRun&&!clsRun.running&&clsRun.note==="nokey"',8000,'无 Key 说明');
      await sleep(400);
      check(srv.ai.log.length-n0===0,'无 Key 点保存不得发 AI 请求');
      await shot(tab,'04b-cls-nokey',{view:'#cls-progress',block:'end',clip:PROGRESS,pad:12});
      await shot(tab,'04a-cls-nokey-viewport');
    });
    await fresh(tab,[LS('thoradar.sectors.v2',SCHEME),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
    await tab.eval(seedPapers(1,43));
    await group('C2','进度行·在途：批次进度＋停止钮',async()=>{
      await toEditor(tab);
      srv.ai.respond=slow(clsDefault);
      const n0=srv.ai.log.length;
      await tab.eval(P.click('[data-tw-save]'));await waitAiKind(srv,n0,'cls');await sleep(1200);
      check(await tab.eval('clsRun&&clsRun.running&&!!document.querySelector("#cls-progress [data-cls-stop]")')===true,'在途时进度行与停止钮应已就位');
      await shot(tab,'05b-cls-running',{view:'#cls-progress',block:'end',clip:PROGRESS,pad:12});
      await shot(tab,'05a-cls-running-viewport');
      srv.ai.respond=null;   // 在途截图拿到后，后面的批次不再拖时间
      await tab.waitFor('clsRun&&!clsRun.running',60000,'分类结束');
    });
    await group('C3','进度行·完成',async()=>{
      await sleep(500);
      const prog=await tab.eval('(()=>{const el=document.querySelector("#cls-progress");return el?el.textContent:null})()'),reqs=srv.ai.log.filter(r=>r.kind==='cls');
      note(`分类请求 ${reqs.length} 次，每批 ${reqs.map(r=>r.payload.papers.length).join('/')} 篇｜进度行「${prog}」`);
      check(reqs.length>=2,`截图流程里应至少分 2 批，实得 ${reqs.length} 次`);
      await shot(tab,'06b-cls-done',{view:'#cls-progress',block:'end',clip:PROGRESS,pad:12});
      await shot(tab,'06a-cls-done-viewport');
      await tab.eval(P.view('overview'));await sleep(600);
      await shot(tab,'06c-cls-done-overview');
    });

    // ---- ③ 深评块 ----
    await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
    await group('D1','深评块·默认关：详情卡解读位下一个按钮，不点不调用',async()=>{
      const n0=srv.ai.log.length;await sleep(500);
      check(srv.ai.log.length-n0===0,'不点深评不得发 AI 请求');
      await shot(tab,'07a-deep-off-viewport');
      await shot(tab,'07b-deep-off-card',{view:BLOCK,block:'end',clip:CARD,pad:6});
      await shot(tab,'07c-deep-off-block',{clip:BLOCK,pad:14});
    });
    await group('D2','深评块·在途：进度＋停止钮',async()=>{
      srv.ai.respond=slow(DEEP_TEXT);
      const n0=srv.ai.log.length;
      await tab.eval(P.click('#deepreview-btn'));await waitAiKind(srv,n0,'deep');await sleep(700);
      check(await tab.eval('deepRun&&deepRun.running&&!!document.querySelector("#deep-stop")')===true,'在途时应有进度与停止钮');
      await shot(tab,'08-deep-running-card',{view:BLOCK,block:'end',clip:CARD,pad:6});
      await tab.waitFor('deepRun===null',20000,'深评结束');
    });
    await group('D3','深评块·有结果：正文原样换行上屏，标注未经人审',async()=>{
      srv.ai.respond=null;await sleep(500);
      const n1=srv.ai.log.length;
      await shot(tab,'09b-deep-result-card',{view:'#detail .deep-note',block:'end',clip:CARD,pad:6});
      await shot(tab,'09a-deep-result-viewport');
      check(await tab.eval('!!document.querySelector("#detail .deep-note")&&!document.querySelector("#deepreview-btn")')===true,'有缓存后应直接显示正文、不再给按钮');
      check(await tab.eval('(()=>{const el=document.querySelector("#detail .deep-note");return el?getComputedStyle(el).whiteSpace:""})()')==='pre-wrap','深评正文应保留换行（white-space: pre-wrap）');
      await tab.eval(P.click('#next-btn'));await sleep(500);
      check(srv.ai.log.length===n1&&await tab.eval('!!document.querySelector("#deepreview-btn")')===true,'切到下一篇：零请求、回到按钮态');
      await shot(tab,'09c-deep-next-paper-card',{view:BLOCK,block:'end',clip:CARD,pad:6});
    });
    await group('D4','深评块·与「解读暂停」同位：同一张卡片里上下相邻',async()=>{
      await tab.eval(P.click('#prev-btn'));await sleep(300);
      await tab.eval('(()=>{const p=PAPERS.find(x=>x.id===state.selected);p.publish_state="degraded";render();return 1})()');await sleep(400);
      check(await tab.eval('!!document.querySelector("#detail .interpretation-paused:not(.deep-paused)")&&!!document.querySelector("#detail .deep-note")')===true,'应同时有「解读暂停」块与深评块');
      await shot(tab,'10-deep-beside-interpretation-paused',{view:'#detail .interpretation-paused:not(.deep-paused)',block:'start',clip:CARD,pad:6});
    });
    await group('D5','深评·无 Key 点击：引导到 AI 设置并提示',async()=>{
      await fresh(tab,[],srv.origin);await sleep(400);
      const n0=srv.ai.log.length;
      await tab.eval(P.click('#deepreview-btn'));await sleep(700);
      check(srv.ai.log.length-n0===0&&await tab.eval('document.body.dataset.protoView==="personal"&&!document.querySelector("#ai-settings").hidden&&!document.querySelector("#ai-guide-hint").hidden')===true,'无 Key 点击应切到 AI 设置并出提示、零请求');
      await shot(tab,'11a-deep-guide-viewport');
      await shot(tab,'11b-deep-guide',{clip:'#ai-settings',pad:14});
    });

    // ---- ④ 窄屏与深色（模拟，不是真机） ----
    await group('M1','窄屏 390×844（模拟）：阅读视图里滚到深评默认关块',async()=>{
      await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);await metrics(tab,390,844,true,2);await sleep(600);
      await tab.eval(P.view('reading'));await sleep(600);
      await shot(tab,'12a-mobile-deep-off',{view:BLOCK,block:'center'});
    });
    await group('M2','窄屏 390×844（模拟）：AI 设置的钥匙开关',async()=>{
      await tab.eval(P.view('personal'));await sleep(500);await tab.eval(P.tab('topics'));await sleep(500);await tab.eval(P.check('#ai-session-only',true));await sleep(400);
      await shot(tab,'12b-mobile-ai-session',{view:'#ai-settings',block:'center',clip:'#ai-settings',pad:12});
    });
    await group('M3','深色：深评有结果＋钥匙开关',async()=>{
      await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);await metrics(tab,1440,900);await sleep(400);
      await tab.eval(P.click('#theme-btn'));await sleep(400);
      srv.ai.respond=rec=>({status:200,text:DEEP_TEXT,delay:0});
      await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',15000,'深评上屏');await sleep(400);
      await shot(tab,'13a-dark-deep-result-card',{view:'#detail .deep-note',block:'end',clip:CARD,pad:6});
      await tab.eval(P.view('personal'));await sleep(500);await tab.eval(P.tab('topics'));await sleep(500);
      await shot(tab,'13b-dark-ai-remember',{clip:'#ai-settings',pad:14});
    });
    check(tab.errors.length===0,`全程页面运行期异常 ${tab.errors.length} 条：${tab.errors.slice(0,2).join(' | ').slice(0,300)}`);
    const kinds=srv.ai.log.map(r=>r.kind);
    note(`全程 AI 请求 ${kinds.length} 次（${kinds.join(',')}）｜逐请求钥匙 ${[...new Set(srv.ai.log.map(r=>r.keyState))].join(',')}｜截图 ${shotNo} 张落 ${OUT}`);
    check(srv.ai.log.every(r=>r.keyState==='对'),'AI 请求应都带假钥匙');
    check(srv.ai.log.filter(r=>r.kind==='cls').length>=2&&srv.ai.log.filter(r=>r.kind==='deep').length===2,`AI 请求构成应与流程相符（分类 ≥2 次、深评 2 次），实得 ${kinds.join(',')}`);
  }finally{
    try{cdp&&cdp.close()}catch(e){}
    const left=await browser.stop();
    srv.server.close();rmSync(SCRATCH_ROOT,{recursive:true,force:true});
    console.log(`     cleanup | 临时目录 ${SCRATCH_ROOT} 已清${left?'（注意：仍有带本探针 profile 标记的进程存活）':''}`);
  }
  process.exit(L.finish(`AICLS SHOTS [${LABEL}]`)?1:0);
}
main().catch(e=>{console.log('截图脚本崩溃：'+(e&&e.stack||e));try{rmSync(SCRATCH_ROOT,{recursive:true,force:true})}catch(e2){}process.exit(2)});
