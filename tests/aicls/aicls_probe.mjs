#!/usr/bin/env node
// T1125-AICLS 功能探针（tests/aicls/aicls_probe.mjs）——施工席自证件：不构成验收结论，验收样本与验收权归独立复核席
// 用法：node tests/aicls/aicls_probe.mjs [--target <index.html>] [--base <rev>] [--only S04,S07] [--label 名称] [--chrome <chrome.exe|msedge.exe>]
//   缺省 target＝本仓 index.html；--base 给了才跑 S01「机器禁区」（与该提交的 index.html 逐字比禁区区块），缺省取 git merge-base HEAD main。
//   指到「没修的件／变异件」上应对应场景变红（先红后绿；变异红证见 aicls_mutants.mjs）。
// 零 LLM、零真钥匙：页面的 BaseURL 指向本探针自起的本机假应答服务，钥匙只用 lib 里的假占位串；NCBI 由浏览器网络层拦截；外网 DNS 封死。
// 守的不变量（docs/build-spec-个性化纵深.md §3／§4／§6 P2 验收＋任务书五条）：
//   S01 机器禁区零改动＋改动文件面（静态）｜S02 文案走 I18N 中英成对、提示词常量无插值、消费端零字段面（静态）
//   S03 无 Key 只出 P1 结果不报错｜S04 20 篇/批串行、批间 ≥3s、无重叠＋PAPERS／SITE_DATA 全程深比对零变更
//   S05 ck 命中零新增请求｜S06 三连伪造零穿透落库（护栏③与落库写点各有函数级断言）｜S07 坏批回退（重试 1 次→整批回退关键词，渲染不断，报错打码）
//   S08 按序猜 PMID 兜底被禁｜S09 personalBusy 互斥闸（分类／主题／深评两两互斥，confirm 拒绝、零请求）
//   S10 ck 全等校验（篡改 ck／换内容／换模型／改词／删阵地＝陈旧）｜S11 编辑后旧响应不落盘（配置签名线＋代际 clsGen 线各测一次）
//   S12 深评按需（不点零调用／无 Key 引导／缓存／转义／失败打码）｜S13 钥匙两档（记住＝存本浏览器；仅本会话＝内存、盘上恒无、刷新即失；零日志零回显）
//   S14 h8 降级（拿不到 crypto.subtle＝djb2）不崩且照常命中｜S15 单次上限 200 篇＋起跑即出进度行与停止钮＋停止
//   S16 深评护栏（停止钮／60s 超时／空白应答／正文截 3000 字／缓存夹 200 丢最旧／盘上坏件清洗）；S06 另含分类缓存每方案 ≤2000 丢最旧
//   S17 钥匙零回显（服务商把钥匙回写进应答：连通测试回复／主题判官理由／判官报错报文／深评正文——四处都不得上屏、不得落盘、不得进控制台；反向：占位短 Key 不参与打码、正文不打烂；请求发出后才换 Key 的在途应答，回写的旧 Key 照样打码）
//   S18 分类在途时重命名阵地：逐批重渲不得打断重命名（打了一半的名字不被提交、焦点光标都在）；回车／失焦才提交、Esc 仍取消（S04 另含「在途时主题词输入框打字不被冲掉」）
//   S19 会话档盘上 Key 恒空·异常旧档（返修补证）：预置 sessionOnly:true 却仍带非空 apiKey 的档（正常路径不产生）→重载→盘上 apiKey 当场清空并回写一次、不捡回内存、页面仍是会话档；其它形状（钥匙带空白／纯空白／没这个字段／不是字符串）同样清成空串；已清空的档再重载零写盘（幂等）；记住档加载零写盘（原行为不变）
// 退出码：0＝全绿，1＝有红，2＝探针自身崩溃。
import {readFileSync,mkdirSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import vm from 'node:vm';
import {ROOT,sleep,sha256,norm,argOf,gitRead,ledger,startServer,aiText,connect,Tab,wire,eutilsOK,launch,freePort,P,FAKE_KEY_A,FAKE_KEY_B,
  between,block,lineOf,inlineScripts,readI18n} from './lib.mjs';

const argv=process.argv.slice(2);
const TARGET=resolve(ROOT,argOf(argv,'--target',join(ROOT,'index.html')));        // 一律绝对路径
const LABEL=argOf(argv,'--label','run');
const CHROME=argOf(argv,'--chrome','C:/Program Files/Google/Chrome/Application/chrome.exe');
const ONLY=argOf(argv,'--only','').split(',').map(s=>s.trim()).filter(Boolean);
const skip=id=>ONLY.length&&!ONLY.includes(id);
const SCRATCH_ROOT=resolve(process.env.AICLS_SCRATCH||join(tmpdir(),`thoradar-t1125-aicls-probe-${LABEL}`));   // 临时件只落系统临时目录；跑完即删
const SCRATCH=join(SCRATCH_ROOT,'harness');
const FLOOR=2990;                                   // ≥3000ms，容差 10ms
const djb2=s=>{let h=5381;for(let i=0;i<s.length;i++)h=((h<<5)+h+s.charCodeAt(i))|0;return (h>>>0).toString(16).padStart(8,'0')};   // 探针侧独立算 djb2（不取页面函数）
const L=ledger(),{check,note}=L;
const begin=(id,name)=>{if(!skip(id))L.begin(id,name)};   // --only 点名的才跑；没点名的不出现
const end=()=>L.end();
const noErrors=(tab,where)=>check(tab.errors.length===0,`${where}：页面运行期异常 ${tab.errors.length} 条：${tab.errors.slice(0,2).join(' | ').slice(0,300)}`);
const hasKey=(texts,key)=>texts.some(x=>String(x).includes(key));

// ---------- 静态材料 ----------
const tgtHtml=norm(readFileSync(TARGET,'utf8'));
const tgtSha=sha256(readFileSync(TARGET));
let BASE=argOf(argv,'--base','');
if(!BASE){try{BASE=gitRead(['merge-base','HEAD','main']).trim()||'HEAD'}catch(e){BASE='HEAD'}}
const baseHtml=()=>norm(gitRead(['show',`${BASE}:index.html`]));

// ---------- 探针用种子与页面侧小工具 ----------
const SECT=()=>({version:2,schemes:[{id:'s_probe1',name:'probe scheme',mode:'topic',sectors:[   // include 词 alphaq／betaq 不出现在任何论文里→关键词预分类恒未分组
  {id:'g_a',name:'Alpha',folded:false,journals:[],words:{include:['alphaq'],exclude:[]}},
  {id:'g_b',name:'Beta',folded:false,journals:[],words:{include:['betaq'],exclude:[]}}],order:['g_a','g_b']}],active:'s_probe1'});
const SECT_LUNG=()=>({version:2,schemes:[{id:'s_probe1',name:'probe scheme',mode:'topic',sectors:[
  {id:'g_a',name:'Alpha',folded:false,journals:[],words:{include:['lung'],exclude:[]}},
  {id:'g_b',name:'Beta',folded:false,journals:[],words:{include:['betaq'],exclude:[]}}],order:['g_a','g_b']}],active:'s_probe1'});
const TOPIC_CFG={version:1,topics:[{id:'t_probe1',name:'probe topic',query:'segmentectomy',days:7,cap:20,createdAt:1761900000000,lastRun:null}]};
const LS=(k,v)=>`localStorage.setItem(${JSON.stringify(k)},${JSON.stringify(JSON.stringify(v))})`;
const AI_CFG=origin=>({baseUrl:origin,apiKey:FAKE_KEY_A,model:'probe-mock'});
const K=JSON.stringify(FAKE_KEY_A),K2=JSON.stringify(FAKE_KEY_B);   // 只用于页内比较表达式，不进任何输出
const SK_LIKE='sk-PROBE0000000000fake0000000000';   // 一条「形似钥匙」的占位串（不是任何真钥匙）：模拟服务商在报错报文里回写一条别的钥匙串
// 合成论文：只进测试页内存里的 PAPERS（不落任何文件）。每个场景先固定取注入前 35 篇，再加 N 篇合成，
// 使原夹具总篇数与批次数不随每日数据更新漂移；SITE_DATA 与真实数据文件不动。
const seedPapers=(start,count)=>`(()=>{const out=[],T=['minimally invasive lobectomy','neoadjuvant esophagectomy','lung nodule screening'];
  for(let i=0;i<${count};i++){const n=${start}+i;out.push({id:'pmid_'+(90000000+n),pmid:String(90000000+n),title_en:'Probe synthetic paper '+n+' about '+T[n%3],title_zh:'',
    abstract_en:'Synthetic abstract '+n+' on '+T[n%3]+' outcomes.',results:'',briefing_date:ANCHOR,pub_date:ANCHOR,score_total:40-(n%20),tier:'B',tier_scheme:'v4',
    journal_abbr:'PROBE J',journal_full:'Probe Journal',category:'surgery',category_label:'probe',study_type:'RCT',publish_state:'ok',status:{kind:'ok'}})}
  PAPERS=INJECTED_PAPERS.slice(0,35).concat(out);return out.length})()`;
const X={   // 页面侧表达式
  items:`(()=>{const s=clsStore.schemes.s_probe1;return s?JSON.parse(JSON.stringify(s.items)):null})()`,
  assignAll:`(()=>{const s=schemesStore.schemes[0],km=schemeKeyMap(s);return windowPapers().map(p=>({pmid:String(p.pmid),a:sectorAssign(s,km,p),k:kwClassify(s,p)}))})()`,
  papers:'JSON.stringify(PAPERS)',
  site:'JSON.stringify(SITE_DATA)',
  clsState:`(()=>{const r=clsRun;return r?{running:r.running,note:r.note,stopped:r.stopped,done:r.done,cached:r.cached,failed:r.failed,plain:r.plain,batchDone:r.batchDone,batchTotal:r.batchTotal,skipped:r.skipped,error:r.error,gen:r.gen}:'null'})()`,
  progress:`(()=>{const el=document.querySelector('#cls-progress');return el?{hidden:el.hidden,text:el.textContent}:null})()`,
  deepNote:`(()=>{const el=document.querySelector('#detail .deep-note');return el?el.textContent:null})()`,
  deepBox:`(()=>{const b=document.querySelector('#deep-box'),e=document.querySelector('#detail .deep-err');return b?{text:b.textContent,title:b.getAttribute('title')||'',btn:!!document.querySelector('#deepreview-btn'),err:e?e.textContent:''}:null})()`,
  lsAI:'localStorage.getItem("thoradar.ai.v1")'
};
async function fresh(tab,seeds,origin){await tab.eval(`localStorage.clear();${seeds.join(';')};1`);await tab.goto(`${origin}/index.html`)}   // 清库→种存储→重载（存储先落盘再重载，不靠「新文档脚本」）
async function toEditor(tab){   // 真实入口：个性化→自定义阵地→编辑方案→选中阵地 Alpha（主题词区随之出现）
  await tab.eval(P.view('personal'));await tab.eval(P.tab('sectors'));
  const a=await tab.eval(P.click('[data-scheme-edit="s_probe1"]')),b=await tab.eval(P.click('[data-sector-select="g_a"]'));
  if(a!=='ok'||b!=='ok')throw new Error(`进不了方案编辑器：${a}／${b}`);
}
async function addWord(tab,word){await tab.eval(P.type('#tw-add-include',word));await tab.eval(P.key('#tw-add-include','Enter'))}
async function waitAi(srv,n,timeout=20000){const t0=Date.now();while(srv.ai.log.length<n){if(Date.now()-t0>timeout)throw new Error(`AI 请求第 ${n} 个 ${timeout}ms 未到达`);await sleep(50)}}
async function waitAiKind(srv,from,kind,timeout=30000){const t0=Date.now();while(!srv.ai.log.slice(from).some(r=>r.kind===kind&&r.done===0)){if(Date.now()-t0>timeout)throw new Error(`${kind} 请求 ${timeout}ms 未到达`);await sleep(100)}}
async function waitClsDone(tab,timeout=45000){await tab.waitFor('clsRun&&!clsRun.running',timeout,'分类结束')}
async function classifyOnce(tab,srv,origin,count){   // 造「已分类」底座：种方案＋假配置＋count 篇合成→走真实入口分类到结束→返回请求清单
  await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(origin))],origin);
  await tab.eval(seedPapers(1,count));
  await toEditor(tab);
  const n0=srv.ai.log.length;
  await tab.eval(P.click('[data-tw-save]'));
  await waitClsDone(tab);
  return srv.ai.log.slice(n0);
}
const ckShape=/^\d{7,16}\|[0-9a-f]{8}\|[0-9a-f]{8}\|cls-v1[^|]*\|probe-mock$/;   // ck＝pmid｜内容哈希｜配置哈希｜提示版本｜模型

// =====================================================================
async function main(){
  rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});
  const srv=await startServer({target:TARGET}),port=await freePort(),profile=join(SCRATCH,'profile');
  const browser=await launch({chrome:CHROME,profile,port,label:LABEL});
  let cdp,tab;
  try{
    console.log(`aicls probe | ${browser.ver.Browser} | target=${TARGET} | sha256=${tgtSha} | base=${BASE} | label=${LABEL}`);
    cdp=await connect(browser.ver.webSocketDebuggerUrl);
    const h={cdp,origin:srv.origin,tabs:new Map()};wire(h);
    tab=new Tab(h,'A');await tab.open(`${srv.origin}/index.html`);

    // ---- S01 机器禁区与改动文件面（静态） ----
    if(!skip('S01')){begin('S01','§7 机器禁区零改动＋改动文件面：注入区／官方名册／官方九阵地／雷达盘公共管线与基线逐字相等；引擎、.github、data 零改动');
      try{
        const base=baseHtml();
        note(`基线 ${BASE} 的 index.html（LF 归一后 ${sha256(Buffer.from(base))}）vs 目标（LF 归一后 ${sha256(Buffer.from(tgtHtml))}）`);
        const dataBlock=s=>{const a=s.indexOf('__THORADAR_DATA_START__'),b=s.indexOf('__THORADAR_DATA_END__');return a>=0&&b>a?s.slice(a,b):null};
        check(dataBlock(base)&&dataBlock(base)===dataBlock(tgtHtml),'注入区（SITE_DATA 数据行）字节变了');
        const registryLayer=x=>between(x,'const JOURNAL_IDS=','function sanitizeCollections');   // 官方名册钉表三句＋书架只读快照整段
        const normAi=b=>!b?null:b.split('\n').map(l=>l.includes('redactSecret(')?l.replace(/\s+\/\/.*$/,''):l).join('\n');   // 出口两行行尾的说明注释不比
        const wrapAi=b=>{   // 把基线 aiMessages 的出口两行套上打码＝施工后期望的样子；两处各须恰好命中一次
          const pairs=[[`throw new Error(\`\${tf('err.ai.http',{s:res.status})}\${detail?\`：\${detail}\`:''}\`);`,`throw new Error(redactSecret(\`\${tf('err.ai.http',{s:res.status})}\${detail?\`：\${detail}\`:''}\`,true,cfg.apiKey));`],
            [`return (Array.isArray(data&&data.content)?data.content:[]).filter(b=>b&&b.type==='text').map(b=>String(b.text||'')).join('');`,`return redactSecret((Array.isArray(data&&data.content)?data.content:[]).filter(b=>b&&b.type==='text').map(b=>String(b.text||'')).join(''),false,cfg.apiKey);`]];
          if(pairs.every(([,c])=>b.split(c).length-1===1))return b;   // 基线若已含单A打码，直接使用；不得重复包装
          for(const [a,c] of pairs){if(b.split(a).length-1!==1)throw new Error('基线 aiMessages 出口行与预期不符');b=b.replace(a,()=>c)}
          return b};        const normUxInterpretation=b=>{   // T1127-UX 已批准的唯一改形：说明从可见正文收进 title；函数其余字节仍与基线相同
          if(!b)return b;
          const before="  if(degraded)return `<div class=\"interpretation-paused\"><strong>${t('interp.paused.t')}</strong><br>${t('interp.paused.b')}</div>`;";
          const after="  if(degraded)return `<div class=\"interpretation-paused slim\" title=\"${t('interp.paused.b')}\"><strong>${t('interp.paused.t')}</strong></div>`;   /* UX 瘦身 mock：提示改一行轻字，说明收 title（Gemini 中8） */";
          return b.includes(after)?b.replace(after,before):b;
        };
        for(const [name,fn,fnBase] of [
          ['官方名册钉表读取层（JOURNAL_IDS／JOURNAL_BY_NLM／REGISTRY＋书架快照）',registryLayer],
          ['JCATS 九阵地表',x=>between(x,'const JCATS=[','];')],
          ['JCAT_OFFDIAL／合并图例／jcatLabel／jcatOf',x=>between(x,'const JCAT_OFFDIAL','\n};')],
          ['INJECTED_PAPERS／PAPERS 声明',x=>lineOf(x,'const INJECTED_PAPERS=')+'\n'+lineOf(x,'let PAPERS=INJECTED_PAPERS')],
          ['windowPapers',x=>lineOf(x,'const windowPapers=')],
          ['kwClassify（P1 纯函数）',x=>block(x,'function kwClassify(')],
          ['sectorAssign（方位归属唯一入口）',x=>block(x,'function sectorAssign(')],
          ['mergePapers',x=>block(x,'function mergePapers(')],['inWindow',x=>block(x,'function inWindow(')],['findAnchor',x=>block(x,'function findAnchor(')],
          ['filtered',x=>block(x,'function filtered(')],['jcatUniverse',x=>block(x,'function jcatUniverse(')],['jcatCounts',x=>block(x,'function jcatCounts(')],
          ['positions',x=>block(x,'function positions(')],['sectorMarkup',x=>block(x,'function sectorMarkup(')],['renderScope',x=>block(x,'function renderScope(')],
          ['interpretationMarkup（解读暂停块：T1127-UX 只许说明收 title）',x=>normUxInterpretation(block(x,'function interpretationMarkup('))],
          ['parseJudgeOutput（主题判官，按序兜底只许留在这里）',x=>block(x,'function parseJudgeOutput(')],
          // aiMessages：签名、请求构造、报错提取逐字不动；只许「出口两行各套一层 redactSecret」（钥匙零回显的最后一道——四处调用共用这一条路，S17／M61／M62 盯着它）。
          // 期望件＝把基线那两行原样套上打码后得到的函数；其余任何一行不同都算改动
          ['aiMessages（AI 传输层：签名与请求构造逐字不动，只许出口两行各套一层打码）',
            x=>normAi(block(x,'async function aiMessages(')),
            ()=>normAi(wrapAi(block(base,'async function aiMessages(')))]
        ]){const want=fnBase?fnBase():fn(base);check(fn(tgtHtml)&&want===fn(tgtHtml),`${name} 被改动`)}
        check(((block(tgtHtml,'async function aiMessages(')||'').match(/redactSecret\(/g)||[]).length===2,'aiMessages 里打码应恰两处（报错出口、应答出口），多一处少一处都算改动');
        const baseLines=new Set(base.split('\n')),tgtLines=new Set(tgtHtml.split('\n'));
        const added=tgtHtml.split('\n').filter(l=>!baseLines.has(l)),removed=base.split('\n').filter(l=>!tgtLines.has(l));
        note(`相对基线：新增或改写 ${added.length} 行，移除或改写 ${removed.length} 行`);
        for(const [name,re] of [
          ['写名册钉表',/\b(SITE_DATA\.\w+|JOURNAL_IDS(\[[^\]]*\])?)\s*=[^=]|delete\s+SITE_DATA|Object\.assign\(\s*SITE_DATA|\bREGISTRY\.(push|splice|pop|shift|length\s*=)/],
          ['改公共论文集',/\b(PAPERS|INJECTED_PAPERS)\s*=[^=]|\b(PAPERS|INJECTED_PAPERS)\.(push|splice|pop|shift|unshift|sort|reverse)\(/],
          ['给论文对象字段赋值',/\bp\.(tier|score_total|jcat|study_type|category|category_label|publish_state|ai_note|authors_conclusion)\s*=[^=]/],
          ['碰官方九阵地语义',/待定|JCATS\.(push|splice)|JCAT_OFFDIAL\s*=/],
          ['写 v1 方案键',/setItem\(\s*LS_SECTORS_V1|setItem\(\s*'thoradar\.sectors\.v1'/],
          ['疑似密钥',/api_key|[?&]apikey=|Bearer\s+[A-Za-z0-9]/i],   // 只抓 URL 参数／授权头形态（给 Key 变量赋值不算）
          ['新增裸 fetch',/\bfetch\(/],
          ['打印钥匙',/console\.\w+\([^)]*(apiKey|aiSessionKey|aiStore\b)/]
        ]){const hit=added.filter(l=>re.test(l));check(hit.length===0,`新增行『${name}』：${hit.slice(0,2).map(l=>l.trim().slice(0,140)).join(' | ')}`)}
        let scripts=0,badSyntax=0;for(const src of inlineScripts(tgtHtml)){scripts++;try{new vm.Script(src)}catch(e){badSyntax++;note('语法错：'+e.message)}}
        check(scripts===2&&badSyntax===0,`内联脚本语法（${scripts} 段／错 ${badSyntax}）`);
        const markers=(tgtHtml.match(/__THORADAR_DATA_(START|END)__|const\s+SITE_DATA\s*=/g)||[]).length;
        check(markers===3,'注入标记须各恰一次');
        const changed=gitRead(['diff','--name-only',BASE]).split('\n').filter(Boolean);
        const untracked=gitRead(['status','--porcelain','--untracked-files=all']).split('\n').filter(l=>l.startsWith('??')).map(l=>l.slice(3).trim().replace(/^"|"$/g));
        note(`相对基线 ${BASE} 的已跟踪改动：${changed.join(' , ')||'（无）'}｜未跟踪：${untracked.join(' , ')||'（无）'}`);
        check(!changed.some(f=>/thoradar_engine\.py|^\.github\/|^data\/|^api\/|^tools\/|^config\/|^thoradar-skill\//.test(f)),`补丁碰了禁区文件：${changed.join(',')}`);
        // 允许清单＝产品页、两套随仓探针与两件明确规格/地图文档；docs/ 下其余文件仍算任务外
        const allowed=/^index\.html$|^tests\/(?:aicls|poolup|ux)\/|^deliver\/|^docs\/(?:build-spec-个性化纵深|架构地图)\.md$/,stray=[...changed,...untracked].filter(f=>!allowed.test(f)&&!/^_dispatch\//.test(f));
        check(stray.length===0,`改动面含任务外文件：${stray.join(',')}`);   // _dispatch/＝派遣机落单目录（非施工产出），单列不计
      }catch(e){check(false,'S01 执行故障：'+e.message)}end()}

    // ---- S02 文案与提示词（静态） ----
    if(!skip('S02')){begin('S02','文案走 I18N 表：中英键集一致、页面内静态与字面取词键全部存在、表值全是字符串字面量；两段提示词是常量且无模板插值；消费端零字段面');
      try{
        const base=baseHtml(),tables=readI18n(tgtHtml),baseTables=readI18n(base);
        check(Boolean(tables)&&Boolean(baseTables),'I18N 双表取不到');
        if(tables&&baseTables){
          const zhKeys=[...tables.zh.keys()],enKeys=[...tables.en.keys()];
          const onlyZh=zhKeys.filter(k=>!tables.en.has(k)),onlyEn=enKeys.filter(k=>!tables.zh.has(k));
          check(onlyZh.length===0&&onlyEn.length===0,`中英键集不一致：只在中文 ${onlyZh.slice(0,6).join(',')}｜只在英文 ${onlyEn.slice(0,6).join(',')}`);
          check(tables.literal.zh&&tables.literal.en,`表值须全是字符串字面量（被认出的值条数应与键数相等）：中文 ${tables.zh.size}／${zhKeys.length}，英文 ${tables.en.size}／${enKeys.length}`);
          const src=inlineScripts(tgtHtml).join('\n');
          const staticKeys=[...tgtHtml.matchAll(/data-i18n(?:-title|-ph|-aria)?="([^"]+)"/g)].map(m=>m[1]);
          const litKeys=[...src.matchAll(/\b(?:t|tf)\(\s*'([^']+)'/g)].map(m=>m[1]);
          const expanded={'tw.':['tw.include.ph','tw.exclude.ph'],'ai.busy.':['ai.busy.cls','ai.busy.topic','ai.busy.deep']};   // 动态拼接前缀（t('ai.busy.'+kind) 这类）：逐个展开核实
          const dynamic=litKeys.filter(k=>k.endsWith('.'));
          const missing=[...new Set([...staticKeys,...litKeys.filter(k=>!k.endsWith('.')),...dynamic.flatMap(k=>expanded[k]||[k+'?'])])].filter(k=>!tables.zh.has(k));
          check(missing.length===0,`取词键不在表里：${missing.join(',')}`);
          check(dynamic.every(k=>expanded[k]&&expanded[k].every(x=>tables.zh.has(x)&&tables.en.has(x))),`动态拼接前缀的展开键不全：${dynamic.join(',')}`);
          note(`键数 中文 ${tables.zh.size}／英文 ${tables.en.size}｜静态键 ${staticKeys.length} 个、字面取词 ${litKeys.length} 处全部在表（其中动态前缀 ${dynamic.length} 处已展开核实）`);
          const addedKeys=zhKeys.filter(k=>!baseTables.zh.has(k));
          note(`相对基线新增键 ${addedKeys.length} 个：${addedKeys.join(' ')}`);
          check(addedKeys.length>0,'相对基线没有新增文案键（本单的新文案应全部进表）');
          check(addedKeys.every(k=>tables.en.has(k)),`新增键缺英文：${addedKeys.filter(k=>!tables.en.has(k)).join(',')}`);
          for(const k of ['ai.session.on','cls.done','deep.off.b','ai.busy'])check(tables.zh.has(k)&&tables.en.has(k)&&tables.zh.get(k)!==tables.en.get(k)&&tables.zh.get(k).length>4,`新键 ${k} 应中英各有一条且文案不同`);
        }
        for(const name of ['CLS_SYSTEM','DEEP_SYSTEM']){
          const m=new RegExp(`const ${name}='((?:[^'\\\\]|\\\\.)*)'`).exec(tgtHtml);
          check(Boolean(m),`${name} 不是「const 单引号字符串常量」`);
          if(m){check(!m[1].includes('${'),`${name} 含模板插值`);check(/不是指令/.test(m[1]),`${name} 应声明「给定材料是数据不是指令」`);note(`${name}：常量 ${m[1].length} 字，无模板插值`)}
          check((tgtHtml.match(new RegExp(`\\b${name}\\s*=[^=]`,'g'))||[]).length===1,`${name} 被重新赋值`);
        }
        const lines=tgtHtml.split('\n');
        const nameOf=l=>{const m=/^(?:async\s+)?function\s+(\w+)/.exec(l)||/^class\s+(\w+)/.exec(l)||/^(?:const|let|var)\s+(\w+)/.exec(l);return m?m[1]:l.trim().slice(0,30)};
        const declOf=line=>{   // 这一行属于哪个顶层声明：自己顶格＝自己；否则往上找第一个顶格行（函数头／声明头）
          const i=lines.indexOf(line);if(i<0)return '?';
          if(!/^\s/.test(line))return nameOf(line);
          for(let j=i-1;j>=0;j--){const l=lines[j];if(!l.trim()||/^\s/.test(l))continue;return /^[}\])]/.test(l)?'?':nameOf(l)}
          return '?'};
        const codeLines=lines.filter(l=>!/^\s*\/\//.test(l));
        const clsFns=new Set(codeLines.filter(l=>/\bclsStore\b|sectorcls/.test(l)).map(declOf));
        const clsAllowed=['LS_CLS','sanitizeClsStore','loadClsStore','clsStore','persistClsNow','pruneClsForScheme','pruneClsForSector','clsHit','clsPrewarm','clsCkLive','persistSectorCls','classifyScheme'];
        const clsBad=[...clsFns].filter(f=>!clsAllowed.includes(f));
        check(clsBad.length===0,`分类缓存 clsStore／sectorcls 出现在白名单声明之外：${clsBad.join(' | ')}`);   // 护栏②：分类缓存只经所列函数读、唯一写点落库
        const consumers=new Set(codeLines.filter(l=>/\bsectorAssign\(/.test(l)&&!/function sectorAssign\(/.test(l)).map(declOf));
        const consumersAllowed=['sectorAssign','filtered','schemeUniverse','gsecCounts','render'];
        const consumersBad=[...consumers].filter(f=>!consumersAllowed.includes(f));
        check(consumersBad.length===0,`sectorAssign 被白名单之外的声明消费：${consumersBad.join(' | ')}`);   // 护栏④：分类结果仅消费于方位归属
        note(`clsStore／sectorcls 出现在 ${clsFns.size} 个顶层声明里（全部在白名单内）｜sectorAssign 消费方：${[...consumers].join(' , ')}`);
      }catch(e){check(false,'S02 执行故障：'+e.message)}end()}

    // ---- S03 无 Key 只出 P1 ----
    if(!skip('S03')){begin('S03','无 Key：点「保存并重分类」只出 P1 关键词结果、零 AI 调用、不报错');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT_LUNG())],srv.origin);
        const papers0=await tab.eval(X.papers);
        await toEditor(tab);
        const n0=srv.ai.log.length;
        await tab.eval(P.click('[data-tw-save]'));
        await sleep(500);
        const st=await tab.eval(X.clsState),prog=await tab.eval(X.progress),dial=await tab.eval(X.assignAll);
        note(`运行态 ${JSON.stringify(st)}｜进度行「${prog?prog.text:'（无）'}」｜窗内 ${dial.length} 篇：关键词归 Alpha ${dial.filter(d=>d.k==='g_a').length} 篇、未分组 ${dial.filter(d=>d.k==='__ungrouped__').length} 篇`);
        check(srv.ai.log.length===n0,`无 Key 时不得发 AI 请求，实发 ${srv.ai.log.length-n0} 次`);
        check(st!=='null'&&st.note==='nokey'&&st.running===false&&st.done===0,`应停在「未配置 AI」态且零落库，实得 ${JSON.stringify(st)}`);
        check(dial.length>0&&dial.every(d=>d.a===d.k),'盘面归属应逐篇等于关键词预分类');
        check(await tab.eval('schemesStore.schemes[0].mode')==='topic','方案应已持久为 topic 模式');
        check(await tab.eval('JSON.stringify(clsStore)')==='{"v":1,"schemes":{}}','分类缓存应保持为空');
        check(await tab.eval(X.papers)===papers0,'PAPERS 被改动');
        check(Boolean(prog)&&!prog.hidden&&prog.text.includes('未配置 AI')&&prog.text.includes('零 AI 调用'),'进度行应给出「未配置 AI、零 AI 调用」的说明');
        check(await tab.eval('personalBusyKind()')===''&&await tab.eval('clsAbort')===null,'无 Key 的保存不得留下在途任务或中止器');
        noErrors(tab,'S03');
      }catch(e){check(false,'S03 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S04 批处理节奏＋深比对 ----
    if(!skip('S04')){begin('S04','有 Key：20 篇/批串行、批间 ≥3s、请求无重叠、逐批落库渲染不断；PAPERS／SITE_DATA 全程深比对零变更');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await tab.eval(seedPapers(1,43));   // 35 篇注入＋43 篇合成＝78 篇→4 批（20/20/20/18，末批不满）
        const papers0=await tab.eval(X.papers),site0=await tab.eval(X.site);
        await toEditor(tab);
        const n0=srv.ai.log.length,m=tab.mark();
        await tab.eval(P.click('[data-tw-save]'));
        await waitAi(srv,n0+1,15000);   // 第 1 批已发出＝分类在途；这时接着在主题词输入框里打字（没回车的词）——后面几批落库重渲时不得把它冲掉（这里等「请求已记账」而不等「在途」：默认应答即刻回包，在途窗口不足一个轮询间隔）
        const typing0=await tab.eval(`(()=>{const el=document.querySelector('#tw-add-include');if(!el)return 'MISSING';el.focus();el.value='unfinished';el.setSelectionRange(3,3);return document.activeElement.id})()`);   // 主题词输入框（P1 既有焦点保护罩着它）：逐批重渲不得把它冲掉
        let samples=0,drift=0,firstItems=0;   // 运行中采样：每 400ms 深比对一次，并记第一次看到的落库条数（应「已有、未齐」＝逐批落库）
        for(;;){
          await sleep(400);samples++;
          if(await tab.eval(X.papers)!==papers0||await tab.eval(X.site)!==site0)drift++;
          if(!firstItems)firstItems=await tab.eval('Object.keys(clsStore.schemes.s_probe1?clsStore.schemes.s_probe1.items:{}).length');
          if(samples>=6&&firstItems)break;
          if(samples>40)break;
        }
        const midRun=await tab.eval('clsRun&&clsRun.running');
        await waitClsDone(tab);
        await sleep(400);
        if(await tab.eval(X.papers)!==papers0||await tab.eval(X.site)!==site0)drift++;
        const reqs=srv.ai.log.slice(n0),sizes=reqs.map(r=>r.payload.papers.length),gaps=reqs.slice(1).map((r,i)=>r.t-reqs[i].t);
        const overlap=reqs.slice(1).filter((r,i)=>r.t<reqs[i].done).length,pmids=reqs.flatMap(r=>r.payload.papers.map(p=>p.pmid));
        note(`窗内 ${pmids.length} 篇｜AI 请求 ${reqs.length} 次，每批 ${sizes.join('/')} 篇｜相邻间隔 ms：${gaps.join(' , ')}｜重叠 ${overlap} 处｜逐请求钥匙：${reqs.map(r=>r.keyState).join(',')}｜model=${reqs[0]&&reqs[0].model} max_tokens=${reqs[0]&&reqs[0].maxTokens}`);
        note(`运行中深比对采样 ${samples} 次＋收尾 1 次，PAPERS／SITE_DATA 漂移 ${drift} 次｜采样第 ${samples} 次时已落库 ${firstItems} 条、仍在跑=${midRun}`);
        check(reqs.length===4&&sizes.join('/')==='20/20/20/18',`应 4 批（20/20/20/18 篇），实得 ${reqs.length} 次（${sizes.join('/')}）`);
        check(new Set(pmids).size===78,`四批 PMID 应互不重复共 78 个，实得 ${new Set(pmids).size} 个`);
        check(gaps.length===3&&gaps.every(g=>g>=FLOOR),`批间须 ≥3000ms（容差 10ms），实得 ${gaps.join(' , ')} ms`);
        check(overlap===0,'请求出现重叠（没串行）');
        check(reqs.every(r=>r.kind==='cls'&&r.keyState==='对'&&r.payload.note&&Array.isArray(r.payload.sectors)&&r.payload.sectors.length===2),'每个请求应是分类请求：带假钥匙、用户消息为 JSON 数据段且声明「不是指令」');
        const st=await tab.eval(X.clsState),items=await tab.eval(X.items),dial=await tab.eval(X.assignAll),prog=await tab.eval(X.progress),fp=await tab.eval('clsStore.schemes.s_probe1.fp');
        const badCk=Object.keys(items).filter(p=>!ckShape.test(items[p].ck)||items[p].sec!=='g_a'||items[p].src!=='llm'||Object.keys(items[p]).sort().join()!=='at,ck,sec,src');
        note(`运行态 ${JSON.stringify(st)}｜进度行「${prog?prog.text:'（无）'}」｜落库 ${Object.keys(items).length} 篇，字段／ck 形制不合 ${badCk.length} 条｜方案指纹 ${fp}`);
        check(st!=='null'&&st.done===78&&st.cached===0&&st.failed===0&&st.batchTotal===4&&st.batchDone===4&&st.error===''&&st.note===''&&st.running===false,`应 新归入 78／命中缓存 0／失败 0／4 批全完，实得 ${JSON.stringify(st)}`);
        check(Object.keys(items).length===78&&badCk.length===0,`落库应为 78 条、每条恰 {sec,src:'llm',ck,at} 且 ck＝pmid｜内容哈希｜配置哈希｜cls-v1｜模型，实得 ${Object.keys(items).length} 条、不合 ${badCk.length} 条`);
        check(/^[0-9a-f]{8}\|cls-v1$/.test(fp),`方案指纹形制应为 8hex|cls-v1，实得 ${fp}`);
        check(dial.length===78&&dial.every(d=>d.a==='g_a'&&d.k==='__ungrouped__'),`盘面应 78 篇全归 Alpha（关键词预分类全未分组），实得 Alpha ${dial.filter(d=>d.a==='g_a').length} 篇`);
        check(drift===0,`分类全程 PAPERS／SITE_DATA 发生了 ${drift} 次变更`);
        check(firstItems>0&&firstItems<78&&midRun===true,`应逐批落库（采样第 ${samples} 次时应已落库且未齐、仍在跑），实得已落库 ${firstItems} 条、仍在跑=${midRun}`);
        check(tab.since(m).length===0,'分类运行不得发 NCBI 请求');
        check(await tab.eval(X.papers)===papers0&&await tab.eval(X.site)===site0,'收尾后 PAPERS／SITE_DATA 与起跑前不一致');
        check(Boolean(prog)&&!prog.hidden&&prog.text.includes('新归入 78')&&prog.text.includes('命中缓存 0'),'进度行应显示完成统计');
        check(await tab.eval('document.querySelectorAll("#journal-sectors .journal-sector").length')>=2&&await tab.eval('document.querySelectorAll("#queue-list .queue-item").length')>0,'渲染后盘面扇区／队列缺失');
        // 分类在途时在主题词输入框里打字（没回车的词）：靠 P1 既有的「输入中不重拼编辑器」保护，逐批重渲不得把它冲掉
        const typing=await tab.eval(`(()=>{const el=document.querySelector('#tw-add-include');return {focus:document.activeElement?document.activeElement.id:'',value:el?el.value:null,caret:el?el.selectionStart:-1}})()`);
        note(`分类在途时在主题词输入框打字（没回车）：收尾后 ${JSON.stringify(typing)}｜共 ${st==='null'?0:st.batchTotal} 批逐批重渲`);
        check(typing0==='tw-add-include'&&typing.focus==='tw-add-include'&&typing.value==='unfinished'&&typing.caret===3,'分类逐批重渲不得冲掉用户正在输入的主题词：焦点、文字、光标都应还在，实得 '+JSON.stringify(typing));
        await tab.eval(`(()=>{const el=document.querySelector('#tw-add-include');if(el){el.value='';el.blur()}return 1})()`);   // 收摊：清掉探针打进去的字
        // 分类结果写不进浏览器存储（存储配额／隐私模式一类）：要提示、不崩，结果留在内存（函数级：直接调唯一落库点，只让这一个键写不进去）
        const quota=await tab.eval(`(()=>{const o=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='thoradar.sectorcls.v1')throw new DOMException('QuotaExceededError','QuotaExceededError');return o.call(this,k,v)};
          let n=0,err='';try{n=persistSectorCls('s_probe1',{'12345678901':{sec:'g_a',ck:'probe'}},'probe-fp')}catch(e){err=String(e)}
          const el=document.querySelector('#toast'),mem=clsStore.schemes.s_probe1.items['12345678901']!==undefined;
          delete clsStore.schemes.s_probe1.items['12345678901'];clsStore.schemes.s_probe1.fp=${JSON.stringify(fp)};   // 探针条目撤掉、指纹还原，不给后面的场景留尾巴
          Storage.prototype.setItem=o;persistClsNow();
          return {n,err,mem,toast:el?el.textContent:'',shown:Boolean(el)&&el.style.display!=='none',want:t('cls.save.fail'),after:Object.keys(clsStore.schemes.s_probe1.items).length}})()`);
        note(`盘写失败：落库点返回 ${quota.n}、异常「${quota.err}」｜条目在内存=${quota.mem}｜提示「${quota.toast}」可见=${quota.shown}｜还原后缓存 ${quota.after} 条`);
        check(quota.n===1&&quota.err===''&&quota.mem&&quota.toast===quota.want&&quota.shown&&quota.after===78,'分类结果写不进浏览器存储时应提示「浏览器未能保存分类结果」、不抛异常、结果留在内存');
        noErrors(tab,'S04');
      }catch(e){check(false,'S04 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S05 ck 命中零新增请求 ----
    if(!skip('S05')){begin('S05','ck 命中零新增请求：配置没变再点「保存并重分类」／直接跑编排器→缓存不清、零请求、全部命中');
      try{
        if(!await tab.eval('!!(clsStore.schemes.s_probe1&&Object.keys(clsStore.schemes.s_probe1.items).length)'))await classifyOnce(tab,srv,srv.origin,5);   // --only 单跑时自造底座
        const n0=srv.ai.log.length,items0=await tab.eval(X.items),total=Object.keys(items0).length;
        await toEditor(tab);
        await tab.eval(P.click('[data-tw-save]'));
        await waitClsDone(tab,20000);await sleep(300);
        const st=await tab.eval(X.clsState),prog=await tab.eval(X.progress),items=await tab.eval(X.items);
        const r=await tab.eval('classifyScheme("s_probe1")');await sleep(300);
        const sent=srv.ai.log.length-n0;
        note(`再保存：运行态 ${JSON.stringify(st)}｜进度行「${prog?prog.text:'（无）'}」｜两次触发合计新增 AI 请求 ${sent} 次｜直接跑编排器返回 ${JSON.stringify(r)}`);
        check(sent===0,`配置未变不得再发 AI 请求，实发 ${sent} 次`);
        check(st!=='null'&&st.running===false&&st.note===''&&st.cached===total&&st.done===0&&st.failed===0&&st.batchTotal===0,`再保存应全部 ck 命中（命中缓存 ${total}、0 批），实得 ${JSON.stringify(st)}`);
        check(JSON.stringify(items)===JSON.stringify(items0)&&Object.keys(items).length===total,'再保存不得改动已落库的分类缓存');
        check(r&&r.done===0&&r.cached===total&&r.failed===0,`直接跑编排器应返回 done 0／cached ${total}／failed 0，实得 ${JSON.stringify(r)}`);
        check((await tab.eval(X.assignAll)).every(d=>d.a==='g_a'),'盘面应仍全归 Alpha（缓存命中）');
        check(Boolean(prog)&&prog.text.includes('新归入 0')&&prog.text.includes(`命中缓存 ${total}`),'进度行应显示「新归入 0、命中缓存全部」');
        noErrors(tab,'S05');
      }catch(e){check(false,'S05 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S06 三连伪造零穿透 ----
    if(!skip('S06')){begin('S06','三连伪造零穿透：护栏③（输出校验）与落库写点各有一道防线——两道分别做函数级断言，再走真实流量：只有合法项落库，落库字段恰为 {sec,src,ck,at}');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await tab.eval(seedPapers(1,5));
        // 函数级·护栏③：sanitizeClsOutput 对各类伪造输入的输出（Map 的「pmid=sec」对；null＝整批不可解析）
        const unit=await tab.eval([
          '(()=>{const S=sanitizeClsOutput,V=["g_a","g_b"],B=["90000001","90000002"],J=JSON.stringify',
          'const c={ok:S(J([{pmid:"90000001",sec:"g_a"}]),B,V),',
          'fence:S("前言\\n```json\\n"+J([{pmid:"90000001",sec:"g_b"}])+"\\n```\\n后记",B,V),',
          'unknownPmid:S(J([{pmid:"1",sec:"g_a"}]),B,V),unknownSec:S(J([{pmid:"90000001",sec:"g_x"}]),B,V),',
          'none:S(J([{pmid:"90000001",sec:"none"}]),B,V),dup:S(J([{pmid:"90000001",sec:"g_a"},{pmid:"90000001",sec:"g_b"}]),B,V),',
          'extra:S(J([{pmid:90000001,sec:"g_a",tier:"S",score_total:9}]),B,V),',
          'arrSec:S(J([{pmid:"90000001",sec:["g_a"]}]),B,V),numSec:S(J([{pmid:"90000001",sec:1}]),B,V),objPmid:S(J([{pmid:{a:1},sec:"g_a"}]),B,V),',
          'arrPmid:S(J([{pmid:["90000001"],sec:"g_a"}]),B,V),boolPmid:S(J([{pmid:true,sec:"g_a"}]),B,V),floatPmid:S(J([{pmid:90000001.5,sec:"g_a"}]),B,V),expPmid:S(J([{pmid:9.0000001e7,sec:"g_a"}]),B,V),',
          'noPmid:S(J([{sec:"g_a"}]),B,V),notArray:S(J({pmid:"90000001",sec:"g_a"}),B,V),notJson:S("抱歉",B,V),empty:S("[]",B,V)}',
          'const shp=m=>m===null?"null":[...m.entries()].map(e=>e.join("=")).join(",")',
          'return Object.fromEntries(Object.entries(c).map(([k,v])=>[k,shp(v)]))})()'
        ].join('\n'));
        const wantUnit={ok:'90000001=g_a',fence:'90000001=g_b',unknownPmid:'',unknownSec:'',none:'90000001=none',dup:'90000001=g_a',extra:'90000001=g_a',arrSec:'',numSec:'',objPmid:'',arrPmid:'',boolPmid:'',floatPmid:'',expPmid:'90000001=g_a',noPmid:'',notArray:'null',notJson:'null',empty:''};   // expPmid：JSON 里的指数写法解析成安全整数＝与数字 PMID 同等对待
        note(`护栏③ 函数级：${Object.keys(wantUnit).map(k=>`${k}「${unit[k]}」${unit[k]===wantUnit[k]?'':'✗应「'+wantUnit[k]+'」'}`).join('｜')}`);
        check(Object.keys(wantUnit).every(k=>unit[k]===wantUnit[k]),'护栏③ sanitizeClsOutput 对伪造输入的输出与期望不符（见上）');
        // 函数级·落库写点：persistSectorCls 的拒收清单
        const write=await tab.eval([
          '(async()=>{const out={},fp=(await h8(clsCfgSig(schemesStore.schemes[0])))+"|"+CLS_PROMPT_VER+CLS_HASH_TAG',
          'clsStore.schemes.s_probe1={fp,items:{}}',
          'out.unknown=persistSectorCls("s_probe1",{"90000001":{sec:"g_zzz",ck:"x"}},fp)',
          'out.ungrouped=persistSectorCls("s_probe1",{"90000002":{sec:"__ungrouped__",ck:"x"}},fp)',
          'out.none=persistSectorCls("s_probe1",{"90000003":{sec:"none",ck:"x"}},fp)',
          'out.noCk=persistSectorCls("s_probe1",{"90000004":{sec:"g_a"}},fp)',
          'out.extra=persistSectorCls("s_probe1",{"90000005":{sec:"g_a",ck:"x",tier:"S",score_total:9,jcat:"1"}},fp)',
          'out.protoKey=persistSectorCls("s_probe1",{"constructor":{sec:"g_a",ck:"x"}},fp)',
          'out.gone=persistSectorCls("s_nosuch",{"90000006":{sec:"g_a",ck:"x"}},fp)',
          'out.left=Object.keys(clsStore.schemes.s_probe1.items).join(",")',
          'out.fields=Object.keys(clsStore.schemes.s_probe1.items["90000005"]||{}).sort().join(",")',
          'out.virus=(clsStore.schemes.s_probe1.items["90000005"]||{}).tier',
          'delete clsStore.schemes.s_probe1;persistClsNow();return out})()'
        ].join('\n'));
        note(`落库写点函数级：${JSON.stringify(write)}`);
        check(write.unknown===0&&write.ungrouped===0&&write.none===0&&write.noCk===0&&write.extra===1&&write.protoKey===0&&write.gone===0,`落库写点应拒收 陌生阵地／未分组／none／无 ck／非数字 PMID／不存在的方案，只收合法项，实得 ${JSON.stringify(write)}`);
        check(write.left==='90000005'&&write.fields==='at,ck,sec,src'&&write.virus===undefined,`落库条目应恰为 {sec,src,ck,at}（夹带字段不带入），实得 库中=${write.left} 字段=${write.fields} tier=${write.virus}`);
        // 函数级·每方案 ≤2000 条：丢 at 最旧（分两次写 1500＋1505 条，中间隔 8ms 让两批的 at 可分先后）
        const cap=await tab.eval([
          '(async()=>{const fp=(await h8(clsCfgSig(schemesStore.schemes[0])))+"|"+CLS_PROMPT_VER+CLS_HASH_TAG,mk=(a,b)=>Object.fromEntries(Array.from({length:b-a},(_,i)=>[String(81000000+a+i),{sec:"g_a",ck:"x"}]));',
          'clsStore.schemes.s_probe1={fp,items:{}};const out={first:persistSectorCls("s_probe1",mk(0,1500),fp)};await new Promise(r=>setTimeout(r,8));out.second=persistSectorCls("s_probe1",mk(1500,3005),fp);',
          'const items=clsStore.schemes.s_probe1.items;out.count=Object.keys(items).length;out.kept=[81000000,81001004,81001005,81001500,81003004].map(n=>String(n) in items).join(",");',
          'delete clsStore.schemes.s_probe1;persistClsNow();return out})()'
        ].join('\n'));
        note(`每方案条数上限 函数级：${JSON.stringify(cap)}（kept＝第一批第 1 条／第 1005 条／第 1006 条／第二批第 1 条／最后一条 是否还在：3005 条夹到 2000，应丢先写那批最早的 1005 条）`);
        check(cap.first===1500&&cap.second===1505&&cap.count===2000&&cap.kept==='false,false,true,true,true',`每方案应夹到 2000 条、丢 at 最旧的（先写那批最早的 1005 条），实得 ${JSON.stringify(cap)}`);
        // 函数级·读侧清洗 sanitizeClsStore：盘上超额时同样丢 at 最旧（与写侧、与它自己的注释同一口径——原写法留最旧，P2 写入侧上线后这条路才真正有数据可走）
        const read=await tab.eval([
          '(async()=>{const fp=(await h8(clsCfgSig(schemesStore.schemes[0])))+"|"+CLS_PROMPT_VER+CLS_HASH_TAG,mk=(a,b)=>Object.fromEntries(Array.from({length:b-a},(_,i)=>[String(81100000+a+i),{sec:"g_a",src:"llm",ck:"x",at:i+1}]));',
          'const st=sanitizeClsStore({v:1,schemes:{s_probe1:{fp,items:mk(0,2005)}}}).schemes.s_probe1,items=st.items;return {count:Object.keys(items).length,kept:[81100000,81100004,81100005,81102004].map(n=>String(n) in items).join(","),fp:st.fp}})()'
        ].join('\n'));
        note(`读侧清洗 函数级：${JSON.stringify(read)}（kept＝盘上第 1 条／第 5 条／第 6 条／最后一条 是否还在：2005 条读进来应丢最早的 5 条）`);
        check(read.count===2000&&read.kept==='false,false,true,true',`读侧 sanitizeClsStore 应夹到 2000 条、丢 at 最旧的 5 条（与注释、与写侧同一口径），实得 ${JSON.stringify(read)}`);
        const papers0=await tab.eval(X.papers),site0=await tab.eval(X.site),first0=await tab.eval('JSON.stringify(PAPERS[0])');
        await toEditor(tab);
        const n0=srv.ai.log.length,pm=await tab.eval('windowPapers().slice(0,21).map(p=>String(p.pmid))');
        let k=0;
        srv.ai.respond=rec=>{k++;return k>1?Object.assign({},srv.ai.default(rec),{delay:600}):aiText(rec,JSON.stringify([   // 第 2 批压 600ms 应答：留出「第 1 批已落库、第 2 批未应答」的窗口
          {pmid:pm[0],sec:'g_a',tier:'S',score_total:99,jcat:'1',category:'advanced',study_type:'AI',publish_state:'ok'},   // 合法项＋夹带字段
          {pmid:'99999999',sec:'g_a'},{pmid:pm[20],sec:'g_b'},               // 未知 PMID：不在窗内的／下一批才有的
          {pmid:pm[1],sec:'g_zzz'},{pmid:pm[2],sec:'__ungrouped__'},{pmid:pm[3],sec:'none '},{pmid:pm[4],sec:''},{pmid:'',sec:'g_a'},   // 未知阵地／未分组伪阵地／带空格／空值
          {pmid:pm[5],sec:'g_a'},{pmid:pm[5],sec:'g_b'},                     // 重复 PMID：首个胜
          {pmid:pm[6],sec:'none'},                                           // none＝不落库
          'garbage',{sec:'g_b'},{pmid:pm[7]},[pm[8],'g_a'],null,{pmid:pm[9],sec:['g_a']},{__proto__:{sec:'g_a'},pmid:pm[10],sec:'g_a'}
        ]))};
        await tab.eval(P.click('[data-tw-save]'));
        await waitAi(srv,n0+2,15000);   // 第 2 批请求已发出＝第 1 批已应答落库
        const mid=await tab.eval(X.items)||{};
        await waitClsDone(tab);await sleep(300);
        const items=await tab.eval(X.items)||{},dial=await tab.eval(X.assignAll),st=await tab.eval(X.clsState),byPmid=Object.fromEntries(dial.map(d=>[d.pmid,d]));
        const shapeBad=Object.keys(items).filter(p=>Object.keys(items[p]).sort().join()!=='at,ck,sec,src'||items[p].src!=='llm'||!ckShape.test(items[p].ck));
        const p0=JSON.parse(first0);
        note(`运行态 ${JSON.stringify(st)}｜第 1 批落库后（第 2 批应答前）库中 ${Object.keys(mid).length} 条｜最终落库 ${Object.keys(items).length} 条（第 1 批合法 3 条＋第 2 批 20 条），字段／ck 形制不合 ${shapeBad.length} 条`);
        note(`夹带项那篇论文：tier=${p0.tier} score_total=${p0.score_total} jcat=${JSON.stringify(p0.jcat)} publish_state=${p0.publish_state}（分类前后快照${first0===await tab.eval('JSON.stringify(PAPERS[0])')?'一致':'不一致'}）`);
        check(Object.keys(mid).length===3&&mid[pm[0]]&&mid[pm[5]]&&mid[pm[10]]&&!mid['99999999']&&!mid[pm[20]],`第 1 批后应恰落库 3 条合法项，未知 PMID（含下一批才有的）不得提前落库，实得 ${Object.keys(mid).length} 条`);
        check(Object.keys(items).length===23&&items[pm[0]].sec==='g_a'&&items[pm[5]].sec==='g_a'&&items[pm[10]].sec==='g_a'&&items[pm[20]].sec==='g_a',`最终应恰 23 条、合法三项归 Alpha、重复 PMID 取首个、下一批那篇按第 2 批应答归 Alpha，实得 ${Object.keys(items).length} 条`);
        check(!items['99999999']&&!items[pm[1]]&&!items[pm[2]]&&!items[pm[3]]&&!items[pm[4]]&&!items[pm[6]]&&!items[pm[7]]&&!items[pm[8]]&&!items[pm[9]]&&!items[''],'未知阵地／未分组伪阵地／none／无 PMID 的项一律不得落库');
        check(shapeBad.length===0,`落库字段应恰为 {sec,src:'llm',ck,at} 且 ck 形制合规，不合 ${shapeBad.length} 条`);
        check(first0===await tab.eval('JSON.stringify(PAPERS[0])')&&await tab.eval(X.papers)===papers0&&await tab.eval(X.site)===site0,`夹带的 tier／score／jcat／publish_state 渗进了论文对象（原值 tier=${p0.tier} score=${p0.score_total}）`);
        check([pm[1],pm[2],pm[3],pm[4],pm[6],pm[7],pm[8],pm[9]].every(p=>byPmid[p]&&byPmid[p].a==='__ungrouped__'),'被剪的各篇应按关键词回退为未分组');
        check(st!=='null'&&st.done===23&&st.failed===0&&st.plain===17&&st.running===false,`运行统计应 新归入 23／失败 0／回退关键词 17，实得 ${JSON.stringify(st)}`);
        noErrors(tab,'S06');
      }catch(e){check(false,'S06 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S07 坏批回退 ----
    if(!skip('S07')){begin('S07','坏批回退：整批不是 JSON（重试 1 次仍坏）与 HTTP 500（报文夹带钥匙）各一批→不落库、按关键词回退、渲染不断、节拍照旧 ≥3s；报错文案已打码');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await tab.eval(seedPapers(1,25));   // 60 篇→3 批
        await toEditor(tab);
        const n0=srv.ai.log.length;let k=0;
        srv.ai.respond=rec=>{k++;
          if(k<=2)return aiText(rec,'抱歉，我无法完成这次分类。');                                                   // 批 1：两次都不是 JSON→整批回退
          if(k<=4)return {status:500,text:`provider rejected the request for key ${FAKE_KEY_A} (token ${SK_LIKE})`,delay:0};       // 批 2：两次 500→整批回退（报文里夹带钥匙：本次带出去的那把＋一条形似钥匙的别的串）
          return srv.ai.default(rec)};                                                                              // 批 3：正常
        await tab.eval(P.click('[data-tw-save]'));
        await waitClsDone(tab);await sleep(300);
        const reqs=srv.ai.log.slice(n0),gaps=reqs.slice(1).map((r,i)=>r.t-reqs[i].t),items=await tab.eval(X.items)||{},dial=await tab.eval(X.assignAll),st=await tab.eval(X.clsState),prog=await tab.eval(X.progress);
        note(`AI 请求 ${reqs.length} 次（状态 ${reqs.map(r=>r.status).join(',')}）｜相邻间隔 ms：${gaps.join(' , ')}｜运行态 ${JSON.stringify(st)}`);
        note(`进度行「${prog?prog.text:''}」｜落库 ${Object.keys(items).length} 条`);
        check(reqs.map(r=>r.status).join(',')==='200,200,500,500,200',`应 5 次请求（坏、坏、500、500、好），实得 ${reqs.map(r=>r.status).join(',')}`);
        check(gaps.length===4&&gaps.every(g=>g>=FLOOR),`重试与批间都须 ≥3000ms（容差 10ms），实得 ${gaps.join(' , ')} ms`);
        check(st!=='null'&&st.done===20&&st.failed===40&&st.batchTotal===3&&st.batchDone===3&&st.running===false,`统计应 新归入 20／失败回退 40／3 批走完，实得 ${JSON.stringify(st)}`);
        check(Object.keys(items).length===20,'坏批与 500 批都不得落库');
        check(dial.slice(0,40).every(d=>d.a===d.k)&&dial.slice(40).every(d=>d.a==='g_a'),'前 40 篇应回退关键词、后 20 篇归 Alpha');
        check(!String(st.error).includes(FAKE_KEY_A)&&String(st.error).includes('[key]'),`失败文案里的钥匙必须打码，实得「${String(st.error).slice(0,120)}」`);
        check(!String(st.error).includes(SK_LIKE)&&!String(st.error).includes(SK_LIKE.slice(0,8)),`失败文案里形似钥匙的别的串也必须打码（不只认本次带出去的那把），实得「${String(st.error).slice(0,160)}」`);
        check(Boolean(prog)&&prog.text.includes('失败回退 40')&&!prog.text.includes(FAKE_KEY_A),'进度行应显示失败回退篇数且不含钥匙');
        check(await tab.eval('document.querySelectorAll("#journal-sectors .journal-sector").length')>=2&&await tab.eval('document.querySelectorAll("#queue-list .queue-item").length')>0,'坏批后盘面／队列渲染断了');
        noErrors(tab,'S07');
      }catch(e){check(false,'S07 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S08 按序猜 PMID 兜底被禁 ----
    if(!skip('S08')){begin('S08','按序猜 PMID 兜底被禁：应答条数恰等于批大小但条目没有可用 PMID（判官式字段／缺 pmid）→零落库');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await tab.eval(seedPapers(1,2));   // 37 篇→2 批（20/17）
        await toEditor(tab);
        const n0=srv.ai.log.length;let k=0;
        srv.ai.respond=rec=>{k++;return aiText(rec,JSON.stringify(rec.payload.papers.map(()=>k===1?{related:false,why:'probe'}:{sec:'g_a'})))};   // 两批条数都对得上：批 1 是判官式字段，批 2 缺 pmid
        await tab.eval(P.click('[data-tw-save]'));
        await waitClsDone(tab);await sleep(300);
        const reqs=srv.ai.log.slice(n0),items=await tab.eval(X.items)||{},dial=await tab.eval(X.assignAll),st=await tab.eval(X.clsState);
        note(`AI 请求 ${reqs.length} 次｜运行态 ${JSON.stringify(st)}｜落库 ${Object.keys(items).length} 条`);
        check(reqs.length===2,`应 2 次请求，实得 ${reqs.length}`);
        check(Object.keys(items).length===0&&st!=='null'&&st.done===0&&st.failed===0&&st.plain===37,`两批都不得按序对位落库，实得落库 ${Object.keys(items).length} 条、统计 ${JSON.stringify(st)}`);
        check(dial.length===37&&dial.every(d=>d.a==='__ungrouped__'),'盘面应全未分组（关键词回退）');
        noErrors(tab,'S08');
      }catch(e){check(false,'S08 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S09 互斥闸 ----
    if(!skip('S09')){begin('S09','personalBusy 互斥闸（并发＝1）：分类在途→主题运行／深评被 confirm 拒绝；主题在途→分类被拒；深评在途→分类／主题被拒；被拒＝零请求，在途任务照常跑完');
      try{
        const SEEDS=[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin)),LS('thoradar.topics.v1',TOPIC_CFG)];
        // (a)(c) 分类在途（第 2 批挂起）→ 点主题「运行」、点详情卡「深评」
        await fresh(tab,SEEDS,srv.origin);
        await tab.eval(seedPapers(1,5));tab.responder=eutilsOK;tab.dialogs.length=0;
        await toEditor(tab);
        const n0=srv.ai.log.length,m0=tab.mark();let release=null;
        srv.ai.respond=rec=>rec.n-n0===1?srv.ai.default(rec):new Promise(r=>{release=()=>r(srv.ai.default(rec))});
        await tab.eval(P.click('[data-tw-save]'));
        await waitAi(srv,n0+2,15000);
        const busy0=await tab.eval('personalBusyKind()');
        await tab.eval(P.tab('topics'));await tab.eval(P.click('[data-topic-run="t_probe1"]'));
        const d1=tab.dialogs.length;
        await tab.eval(P.view('overview'));await tab.eval(P.click('#deepreview-btn'));
        await sleep(300);
        const d2=tab.dialogs.length,topicState=await tab.eval('runState?{running:runState.running}:null'),busy1=await tab.eval('personalBusyKind()');
        note(`分类在途（${busy0}）→ 点主题运行：「${tab.dialogs[0]?tab.dialogs[0].message:'（无）'}」｜点深评：「${tab.dialogs[1]?tab.dialogs[1].message:'（无）'}」`);
        check(busy0==='cls'&&d1===1&&d2===2,`两次入口各应弹一次 confirm（实得对话框 ${d2} 次），分类应在途＝${busy0}`);
        check(tab.dialogs.every(d=>d.type==='confirm'&&d.message.includes('AI 正忙')),`应为 confirm 且文案为「AI 正忙」：${tab.dialogs.map(d=>d.type+':'+d.message.slice(0,24)).join(' | ')}`);
        check(Boolean(tab.dialogs[0])&&tab.dialogs[0].message.includes('「阵地 AI 分类」')&&tab.dialogs[0].message.includes('「主题检索」'),'拒主题运行的文案应点名「阵地 AI 分类在跑、要启动主题检索」');
        check(Boolean(tab.dialogs[1])&&tab.dialogs[1].message.includes('「阵地 AI 分类」')&&tab.dialogs[1].message.includes('「深评」'),'拒深评的文案应点名「阵地 AI 分类在跑、要启动深评」');
        check(tab.since(m0).length===0&&topicState===null,`主题运行不得起跑（NCBI 请求 ${tab.since(m0).length} 个、runState=${JSON.stringify(topicState)}）`);
        check(srv.ai.log.slice(n0).every(r=>r.kind==='cls'),'分类在途期间不得出现主题判官／深评请求');
        check(busy1==='cls'&&await tab.eval('clsRun.running')===true,'分类应仍在途');
        release();await waitClsDone(tab);
        check(await tab.eval('clsRun.done')===40,'被拒两次后分类应照常跑完 40 篇');
        // (b) 主题在途（判官请求挂起）→ 点「保存并重分类」
        await fresh(tab,SEEDS,srv.origin);tab.responder=eutilsOK;tab.dialogs.length=0;
        await toEditor(tab);await tab.eval(P.tab('topics'));
        const n1=srv.ai.log.length;let release2=null;
        srv.ai.respond=rec=>new Promise(r=>{release2=()=>r(aiText(rec,JSON.stringify([{pmid:'80000001',related:true,why:'probe'},{pmid:'80000002',related:false,why:'probe'}])))});
        await tab.eval(P.click('[data-topic-run="t_probe1"]'));
        await waitAiKind(srv,n1,'judge');
        const busyB=await tab.eval('personalBusyKind()');
        await tab.eval(P.tab('sectors'));await tab.eval(P.click('[data-tw-save]'));
        await sleep(300);
        const clsReq=srv.ai.log.slice(n1).filter(r=>r.kind==='cls').length,clsSt=await tab.eval(X.clsState),dlgB=tab.dialogs.slice();
        note(`主题在途（${busyB}）→ 点保存并重分类：「${dlgB[0]?dlgB[0].message:'（无）'}」｜分类请求 ${clsReq} 次｜分类运行态 ${JSON.stringify(clsSt)}`);
        check(busyB==='topic'&&clsReq===0,`主题在途时不得起跑分类（分类请求 ${clsReq} 次），实得 busy=${busyB}`);
        check(dlgB.length===1&&dlgB[0].message.includes('「主题检索」')&&dlgB[0].message.includes('「阵地 AI 分类」'),'应弹一次 confirm 并点名「主题检索在跑、要启动阵地 AI 分类」');
        check(clsSt==='null'||(clsSt.running===false&&clsSt.done===0&&clsSt.cached===0),'分类不得起跑或留下本轮运行记录');
        release2();await tab.waitFor('runState&&!runState.running',20000,'主题运行结束');
        check(await tab.eval('runState.phase')==='完成','被拒后主题运行应照常跑完');
        // (d) 深评在途（请求挂起）→ 点「保存并重分类」、点主题「运行」
        await fresh(tab,SEEDS,srv.origin);tab.responder=eutilsOK;tab.dialogs.length=0;
        const n2=srv.ai.log.length,m2=tab.mark();let release3=null;
        srv.ai.respond=rec=>new Promise(r=>{release3=()=>r(srv.ai.default(rec))});
        await tab.eval(P.click('#deepreview-btn'));
        await waitAiKind(srv,n2,'deep');
        const busyD=await tab.eval('personalBusyKind()');
        await toEditor(tab);await tab.eval(P.click('[data-tw-save]'));
        const dCls=tab.dialogs.length;
        await tab.eval(P.tab('topics'));await tab.eval(P.click('[data-topic-run="t_probe1"]'));
        await sleep(300);
        const reqsD=srv.ai.log.slice(n2).map(r=>r.kind);
        note(`深评在途（${busyD}）→ 点保存并重分类：「${tab.dialogs[0]?tab.dialogs[0].message:'（无）'}」｜点主题运行：「${tab.dialogs[1]?tab.dialogs[1].message:'（无）'}」`);
        check(busyD==='deep'&&dCls===1&&tab.dialogs.length===2,`两次入口各应弹一次 confirm（实得 ${tab.dialogs.length} 次），深评应在途＝${busyD}`);
        check(Boolean(tab.dialogs[0])&&tab.dialogs[0].message.includes('「深评」')&&tab.dialogs[0].message.includes('「阵地 AI 分类」')&&Boolean(tab.dialogs[1])&&tab.dialogs[1].message.includes('「深评」')&&tab.dialogs[1].message.includes('「主题检索」'),'文案应点名「深评在跑」与要启动的那一个');
        check(reqsD.join(',')==='deep',`被拒后只应有那 1 次深评请求，实得 ${reqsD.join(',')||'无'}`);
        check(tab.since(m2).length===0,`主题运行被拒后不得发 NCBI 请求，实得 ${tab.since(m2).length} 个`);
        release3();await tab.waitFor('deepRun===null',10000,'深评结束');
        check(await tab.eval('document.querySelectorAll("#detail .deep-note").length')===1,'放行后深评应照常完成上屏');
        noErrors(tab,'S09');
      }catch(e){check(false,'S09 执行故障：'+e.message)}finally{srv.ai.respond=null;tab.responder=null}end()}

    // ---- S10 ck 全等校验 ----
    if(!skip('S10')){begin('S10','ck 全等校验：盘上 ck 被篡改／论文内容变了／换了模型＝陈旧（回关键词、零请求）；内容没变只是换了对象＝照常命中；改词＝剪缓存重分类；调顺序＝缓存陈旧；删阵地＝连带剪');
      try{
        await classifyOnce(tab,srv,srv.origin,5);   // 40 篇→2 批，全归 Alpha
        const fp0=await tab.eval('clsStore.schemes.s_probe1.fp');
        const pm=await tab.eval('windowPapers().slice(0,3).map(p=>String(p.pmid))'),ck0=(await tab.eval(X.items))[pm[0]];
        const n0=srv.ai.log.length;
        // (a) 篡改盘上 ck
        await tab.eval(`clsStore.schemes.s_probe1.items[${JSON.stringify(pm[0])}].ck='deadbeef';persistClsNow();render();1`);
        const a=await tab.eval(X.assignAll);
        check(a[0].pmid===pm[0]&&a[0].a==='__ungrouped__'&&a[1].a==='g_a',`ck 被篡改的那篇应陈旧回未分组、其余照常命中，实得 ${a[0].a}／${a[1].a}`);
        // (b) 同 pmid 换了内容（新对象）＝陈旧；(c) 内容没变只是换了对象＝照常命中
        await tab.eval(`clsStore.schemes.s_probe1.items[${JSON.stringify(pm[0])}]=${JSON.stringify(ck0)};PAPERS=PAPERS.map(p=>String(p.pmid)===${JSON.stringify(pm[1])}?Object.assign({},p,{abstract_en:p.abstract_en+' CHANGED CONTENT'}):String(p.pmid)===${JSON.stringify(pm[2])}?Object.assign({},p):p);render();1`);
        await sleep(600);   // 内容哈希在后台重算（预热）后再判
        const bc=await tab.eval(X.assignAll),hitBC=bc.filter(d=>d.a==='g_a').length;
        check(bc[1].a==='__ungrouped__'&&bc[2].a==='g_a'&&bc[0].a==='g_a',`内容变了应陈旧（实得 ${bc[1].a}）、内容没变只换对象应仍命中（实得 ${bc[2].a}）、还原 ck 的那篇应命中（实得 ${bc[0].a}）`);
        // (d) 换模型（真实入口：Model 输入框）＝全部陈旧；换回＝恢复
        await tab.eval(P.tab('topics'));await tab.eval(P.type('#ai-model','probe-mock-2'));await tab.eval('render();1');await sleep(200);
        const dm=await tab.eval(X.assignAll);
        check(dm.every(d=>d.a==='__ungrouped__'),`换了模型应全部陈旧回未分组，实得仍命中 ${dm.filter(d=>d.a==='g_a').length} 篇`);
        await tab.eval(P.type('#ai-model','probe-mock'));await tab.eval('render();1');await sleep(200);
        const dm2=await tab.eval(X.assignAll);
        check(dm2.filter(d=>d.a==='g_a').length===hitBC&&hitBC===39,`换回原模型应恢复命中 39 篇（40 减内容变了的那 1 篇），实得 ${dm2.filter(d=>d.a==='g_a').length} 篇`);
        check(srv.ai.log.length===n0,`ck 校验全程不得发 AI 请求，实发 ${srv.ai.log.length-n0} 次`);
        // (e) 改词保存＝剪缓存重分类（真实入口：加词→保存并重分类）
        await toEditor(tab);
        const n1=srv.ai.log.length;
        await addWord(tab,'gammaq');await tab.eval(P.click('[data-tw-save]'));
        await waitClsDone(tab);await sleep(300);
        const fp1=await tab.eval('clsStore.schemes.s_probe1.fp'),items1=await tab.eval(X.items),sent=srv.ai.log.length-n1;
        check(sent===2&&fp1!==fp0&&Object.keys(items1).length===40,`改词后应剪旧缓存并重新分类（2 批、指纹换新、40 条新结果），实得请求 ${sent} 次、指纹${fp1===fp0?'没变':'已换'}、${Object.keys(items1).length} 条`);
        check(await tab.eval(X.assignAll).then(d=>d.every(x=>x.a==='g_a')),'重分类后盘面应 40 篇全归 Alpha');
        // (e2) 调整阵地顺序（不经「保存」这条线）＝配置签名变＝旧缓存整批陈旧（回关键词、零请求）；挪回去＝恢复命中
        const n2=srv.ai.log.length,hitE=await tab.eval(X.assignAll).then(d=>d.filter(x=>x.a==='g_a').length);
        await tab.eval('moveSector("s_probe1","g_b",-1);render();1');await sleep(400);
        const moved=await tab.eval(X.assignAll),orderMoved=await tab.eval('schemesStore.schemes[0].order.join()');
        await tab.eval('moveSector("s_probe1","g_b",1);render();1');await sleep(600);
        const back=await tab.eval(X.assignAll);
        note(`调整阵地顺序：挪动后顺序 ${orderMoved}、仍命中 ${moved.filter(d=>d.a==='g_a').length} 篇（应 0）｜挪回后命中 ${back.filter(d=>d.a==='g_a').length} 篇（应同挪动前 ${hitE}）｜AI 请求 ${srv.ai.log.length-n2} 次`);
        check(hitE===40&&orderMoved==='g_b,g_a'&&moved.every(d=>d.a==='__ungrouped__')&&back.filter(d=>d.a==='g_a').length===40&&srv.ai.log.length===n2,'阵地顺序一变，旧分类缓存应全部陈旧（回关键词→未分组）且不发请求；顺序挪回去应恢复命中');
        // (f) 删阵地＝连带剪
        const gone=await tab.eval('deleteSector("s_probe1","g_a");Object.keys(clsStore.schemes.s_probe1.items).length');
        check(gone===0,`删 Alpha 阵地应连带剪掉指向它的分类缓存，剩 ${gone} 条`);
        noErrors(tab,'S10');
      }catch(e){check(false,'S10 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S11 编辑后旧响应不落盘 ----
    if(!skip('S11')){begin('S11','编辑后旧响应不落盘：作废判定有两条线——①改词重存（配置签名变）②没改词直接再存（只有代际 clsGen 在守）；两种都是中止信号被架空、旧响应照常到达，也不得落库；旧一轮到此为止不再发后续批；③④批间删阵地／删方案（不经「保存」这条线）＝不再发下一批');
      try{
        const again=async reword=>{   // 起一轮、把第 1 批请求挂住；reword＝是否改词后再存。返回观测值
          await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
          await tab.eval(seedPapers(1,25));   // 60 篇→3 批
          await toEditor(tab);
          const n0=srv.ai.log.length;
          let release=null;
          srv.ai.respond=rec=>rec.n-n0===1   // 旧一轮的第 1 批挂起（放行时答「全归 Beta」）；新一轮一律答「全归 Alpha」
            ?new Promise(r=>{release=()=>r(aiText(rec,JSON.stringify(rec.payload.papers.map(p=>({pmid:p.pmid,sec:'g_b'})))))})
            :srv.ai.default(rec);
          await tab.eval(P.click('[data-tw-save]'));
          await waitAi(srv,n0+1,15000);
          await tab.eval('window.__oldRun=clsRun;window.__realAbort=AbortController.prototype.abort;AbortController.prototype.abort=function(){};1');   // 架空中止信号：旧请求拦不住，只能靠代际／签名校验
          if(reword)await addWord(tab,'gammaq');
          await tab.eval(P.click('[data-tw-save]'));
          await tab.waitFor('clsRun&&clsRun!==window.__oldRun&&!clsRun.running',30000,'新一轮分类结束');
          const mid=await tab.eval('window.__oldRun.running'),genBefore=await tab.eval('[window.__oldRun.gen,clsGen]');
          release();   // 旧响应此刻才到
          await sleep(800);
          const old=await tab.eval('({running:window.__oldRun.running,note:window.__oldRun.note,done:window.__oldRun.done})'),items=await tab.eval(X.items)||{},dial=await tab.eval(X.assignAll),reqs=srv.ai.log.slice(n0),secs={};
          Object.values(items).forEach(it=>{secs[it.sec]=(secs[it.sec]||0)+1});
          await tab.eval('AbortController.prototype.abort=window.__realAbort;1');
          return {old,mid,genBefore,secs,n:Object.keys(items).length,reqs:reqs.length,dialOk:dial.length===60&&dial.every(d=>d.a==='g_a')};
        };
        const r1=await again(true);
        note(`①改词重存｜旧一轮放行前 running=${r1.mid}｜放行后 ${JSON.stringify(r1.old)}｜AI 请求 ${r1.reqs} 次｜落库 ${r1.n} 条（${JSON.stringify(r1.secs)}）`);
        check(r1.mid===true&&r1.old.running===false&&r1.old.note==='stale'&&r1.old.done===0,`①旧一轮应被作废（不落库），实得放行前 running=${r1.mid}、放行后 ${JSON.stringify(r1.old)}`);
        check(r1.secs.g_b===undefined&&r1.secs.g_a===60&&r1.n===60&&r1.dialOk,`①旧响应（全归 Beta）一条也不得落库；库中应 60 条全归 Alpha，实得 ${JSON.stringify(r1.secs)}`);
        check(r1.reqs===4,`①旧一轮不得再发第 2、3 批：应 1 次旧＋3 次新＝4 次，实得 ${r1.reqs} 次`);
        check(await tab.eval('windowPapers().every(p=>clsHit(schemesStore.schemes[0],p)!==null)'),'①落库的 60 条应全部按新配置 ck 全等命中（不是旧配置的缓存混进来）');
        const r2=await again(false);
        note(`②没改词直接再存｜旧一轮代际=${r2.genBefore[0]}、当前代际=${r2.genBefore[1]}（配置签名未变，只有代际线在守）｜放行前 running=${r2.mid}｜放行后 ${JSON.stringify(r2.old)}｜AI 请求 ${r2.reqs} 次｜落库 ${r2.n} 条（${JSON.stringify(r2.secs)}）`);
        check(r2.mid===true&&r2.old.running===false&&r2.old.note==='stale'&&r2.old.done===0&&r2.genBefore[0]!==r2.genBefore[1],`②只有代际线时旧一轮也应被作废，实得 代际 ${r2.genBefore.join('→')}、放行前 running=${r2.mid}、放行后 ${JSON.stringify(r2.old)}`);
        check(r2.secs.g_b===undefined&&r2.secs.g_a===60&&r2.n===60&&r2.dialOk,`②旧响应一条也不得落库；库中应 60 条全归 Alpha，实得 ${JSON.stringify(r2.secs)}`);
        check(r2.reqs===4,`②旧一轮不得再发后续批：应 1 次旧＋3 次新＝4 次，实得 ${r2.reqs} 次`);
        // ③④ 配置在「保存」这条线之外变了（没有中止信号、代际也没动）：第 1 批落库后的那段「批间 ≥3s」等待里删掉一个阵地／删掉整个方案——不得再发下一批，这一轮按「已作废」收尾
        const midflight=async what=>{
          await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
          await tab.eval(seedPapers(1,25));   // 60 篇→3 批
          await toEditor(tab);
          const n0=srv.ai.log.length;let release=null;
          srv.ai.respond=rec=>rec.n-n0===1?new Promise(r=>{release=()=>r(aiText(rec,JSON.stringify(rec.payload.papers.map(p=>({pmid:p.pmid,sec:'g_a'})))))}):srv.ai.default(rec);   // 第 1 批挂一下再放行
          await tab.eval(P.click('[data-tw-save]'));
          await waitAi(srv,n0+1,15000);
          release();
          await tab.waitFor('Boolean(clsStore.schemes.s_probe1)&&Object.keys(clsStore.schemes.s_probe1.items).length===20',10000,'第 1 批落库');   // 此刻编排器正睡在「批间 ≥3s」里
          const removed=await tab.eval(what==='sector'?'deleteSector("s_probe1","g_b");render();1':'deleteScheme("s_probe1");render();1');
          const nAtChange=srv.ai.log.length-n0;
          await tab.waitFor('clsRun&&!clsRun.running',20000,'分类收尾');await sleep(600);
          const run=await tab.eval(X.clsState),n=await tab.eval('clsStore.schemes.s_probe1?Object.keys(clsStore.schemes.s_probe1.items).length:0'),gsec=await tab.eval('schemesStore.schemes[0]?schemesStore.schemes[0].sectors.map(g=>g.id).join(","):"（方案已删）"');
          return {removed,nAtChange,run,n,reqs:srv.ai.log.length-n0,gsec};
        };
        const r3=await midflight('sector');
        note(`③批间删掉阵地 Beta｜改配置那一刻已发 ${r3.nAtChange} 次（第 1 批）｜收尾 ${JSON.stringify(r3.run)}｜AI 请求共 ${r3.reqs} 次｜缓存剩 ${r3.n} 条｜方案现有阵地 ${r3.gsec}`);
        check(r3.removed===1&&r3.nAtChange===1&&r3.reqs===1&&r3.run!=='null'&&r3.run.note==='stale'&&r3.run.running===false&&r3.run.done===20&&r3.run.failed===0&&r3.gsec==='g_a',`③批间删阵地：不得再发第 2、3 批（共 1 次），这一轮按「已作废」收尾，实得 请求 ${r3.reqs} 次、${JSON.stringify(r3.run)}`);
        const r4=await midflight('scheme');
        note(`④批间删掉整个方案｜改配置那一刻已发 ${r4.nAtChange} 次｜收尾 ${JSON.stringify(r4.run)}｜AI 请求共 ${r4.reqs} 次｜缓存剩 ${r4.n} 条｜${r4.gsec}`);
        check(r4.removed===1&&r4.nAtChange===1&&r4.reqs===1&&r4.run!=='null'&&r4.run.note==='stale'&&r4.run.running===false&&r4.n===0,`④批间删方案：不得再发第 2、3 批（共 1 次）、缓存连带剪空，实得 请求 ${r4.reqs} 次、${JSON.stringify(r4.run)}、缓存 ${r4.n} 条`);
        noErrors(tab,'S11');
      }catch(e){try{await tab.eval('if(window.__realAbort)AbortController.prototype.abort=window.__realAbort;1')}catch(e2){}check(false,'S11 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S12 深评按需 ----
    if(!skip('S12')){begin('S12','深评按需：不点零调用；无 Key 点击→引导去 AI 设置（零调用）；有 Key 点击→1 次请求、正文转义上屏、按 PMID 缓存（切走切回／重载零请求）；失败文案打码、按钮可重试');
      try{
        // (1) 无 Key：浏览不产生调用；点按钮＝引导
        await fresh(tab,[],srv.origin);
        const n0=srv.ai.log.length;
        await tab.eval(P.click('#next-btn'));await tab.eval(P.click('#prev-btn'));await tab.eval(P.view('reading'));await tab.eval(P.view('personal'));await tab.eval(P.view('overview'));
        await sleep(400);
        const box0=await tab.eval(X.deepBox),keyType=await tab.eval('document.querySelector("#ai-key").type');
        await tab.eval(P.click('#deepreview-btn'));
        await sleep(600);
        const guided=await tab.eval('({view:document.body.dataset.protoView,settingsHidden:document.querySelector("#ai-settings").hidden,hintHidden:document.querySelector("#ai-guide-hint").hidden,hint:document.querySelector("#ai-guide-hint").textContent})');
        const sent0=srv.ai.log.length-n0;
        note(`无 Key：浏览＋点击合计 AI 请求 ${sent0} 次｜解读位「${box0?box0.text.replace(/\s+/g,' ').slice(0,60):'（无块）'}」｜点击后 view=${guided.view}、AI 设置 hidden=${guided.settingsHidden}、提示「${guided.hint}」`);
        check(sent0===0,'无 Key 时浏览与点击都不得发 AI 请求');
        check(Boolean(box0)&&box0.btn&&box0.text.includes('深评 · 默认关闭')&&(box0.text+box0.title).includes('不点不调用')&&keyType==='password','解读位应有「深评 · 默认关闭」块与按钮；「不点不调用」可在正文或 title；Key 框须是密码框');
        check(guided.view==='personal'&&guided.settingsHidden===false&&guided.hintHidden===false&&guided.hint.includes('再点深评'),'无 Key 点击应切到个性化·AI 设置并提示「再点深评」');
        check(await tab.eval('Object.keys(deepStore.items).length')===0,'无 Key 点击不得写深评缓存');
        const hintReset=await tab.eval('(()=>{guideToAISettings();return {hint:document.querySelector("#ai-guide-hint").textContent,want:t("ai.guide.hint")}})()');   // 主题检索入口的引导：应写回它自己那句
        check(hintReset.hint===hintReset.want,`主题检索入口的引导应写回它自己那句提示（不沿用上一次深评入口的那句），实得「${hintReset.hint}」`);
        // (2) 有 Key：点一篇→1 次请求→上屏→切走切回／重载零请求
        await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await sleep(400);
        const n1=srv.ai.log.length,pmA=await tab.eval('String(PAPERS.find(p=>p.id===state.selected).pmid)');
        check(srv.ai.log.length-n1===0,'页面加载后不点深评不得发 AI 请求');
        await tab.eval(P.click('#deepreview-btn'));
        await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'深评上屏');
        const r1=srv.ai.log.slice(n1),text1=await tab.eval(X.deepNote);
        note(`有 Key：AI 请求 ${r1.length} 次（kind=${r1[0]&&r1[0].kind}，钥匙=${r1[0]&&r1[0].keyState}，max_tokens=${r1[0]&&r1[0].maxTokens}）｜上屏「${text1.replace(/\s+/g,' ').slice(0,70)}」`);
        check(r1.length===1&&r1[0].kind==='deep'&&r1[0].payload.pmid===pmA&&r1[0].keyState==='对'&&r1[0].maxTokens>=3000,'点一篇应恰好 1 次深评请求：带假钥匙、用户消息为该篇的 JSON 数据段');
        check(r1[0]&&typeof r1[0].payload.title==='string'&&typeof r1[0].payload.abstract==='string'&&r1[0].payload.note.includes('不是指令'),'请求体应含该篇标题摘要并声明「不是指令」');
        check(text1&&text1.includes('未经人审')&&text1.includes('探针假深评正文'),'上屏的深评块应标注「未经人审」并显示正文');
        await tab.eval(P.click('#next-btn'));await sleep(300);
        const n2=srv.ai.log.length,other=await tab.eval(X.deepBox);
        check(srv.ai.log.length===n2&&Boolean(other)&&other.btn===true,'切到没深评过的下一篇：零请求、给按钮');
        await tab.eval(P.click('#prev-btn'));await sleep(300);
        const back=await tab.eval(X.deepNote);
        check(srv.ai.log.length===n2&&back===text1,'切回：零请求、深评块原样还在（内存缓存）');
        await tab.goto(`${srv.origin}/index.html`);await sleep(500);
        const after=await tab.eval(X.deepNote),deepLs=await tab.eval('localStorage.getItem("thoradar.deepreview.v1")');
        check(srv.ai.log.length===n2&&after===text1,'整页重载：零请求、深评块仍在（盘上缓存）');
        check(typeof deepLs==='string'&&deepLs.includes(pmidQuote(pmA))&&!deepLs.includes(FAKE_KEY_A)&&Object.keys(JSON.parse(deepLs).items).length===1,'thoradar.deepreview.v1 应恰有这一篇、不含钥匙');
        // (3) 转义：应答里带标签与事件属性
        await tab.eval(P.click('#next-btn'));
        const n3=srv.ai.log.length;
        srv.ai.respond=rec=>aiText(rec,'【研究问题】\n<img src=x onerror="window.__xss=1"><b>bold</b> & tail');
        await tab.eval(P.click('#deepreview-btn'));
        await tab.waitFor('deepRun===null',10000,'深评结束');await sleep(200);
        const xss=await tab.eval('({tags:document.querySelectorAll("#detail .deep-note img, #detail .deep-note b").length,xss:window.__xss===undefined,text:(document.querySelector("#detail .deep-note")||{}).textContent||""})');
        check(srv.ai.log.length-n3===1&&xss.tags===0&&xss.xss&&xss.text.includes('<img src=x'),'AI 输出里的标签只当文字显示、不执行');
        // (4) 失败：500＋报文夹带钥匙→打码、不写缓存、按钮可重试
        await tab.eval(P.click('#next-btn'));
        const pmD=await tab.eval('String(PAPERS.find(p=>p.id===state.selected).pmid)');
        srv.ai.respond=rec=>({status:500,text:`bad key ${FAKE_KEY_A}`,delay:0});
        await tab.eval(P.click('#deepreview-btn'));
        await tab.waitFor('deepRun===null',10000,'深评结束');await sleep(200);
        const fail=await tab.eval(X.deepBox),noRetry=await tab.eval(`deepStore.items[${JSON.stringify(pmD)}]===undefined`);
        note(`失败态：「${fail&&fail.err}」｜按钮在=${fail&&fail.btn}｜未写缓存=${noRetry}`);
        check(Boolean(fail)&&fail.err.includes('深评失败')&&!fail.err.includes(FAKE_KEY_A)&&fail.btn===true&&noRetry,'失败应显示打码后的原因、不写缓存、按钮留着可重试');
        srv.ai.respond=null;
        await tab.eval(P.click('#deepreview-btn'));
        await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'重试上屏');
        check(await tab.eval(X.deepNote)!==null,'重试应成功上屏');
        noErrors(tab,'S12');
      }catch(e){check(false,'S12 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S13 钥匙两档 ----
    if(!skip('S13')){begin('S13','钥匙两档：记住档＝存本浏览器（原行为）；仅本会话档＝Key 只在内存、盘上恒无、刷新即失；切回记住才落盘；全程零日志零回显');
      try{
        await fresh(tab,[],srv.origin);
        await tab.eval(P.view('personal'));await tab.eval(P.tab('topics'));
        const ls=async()=>JSON.parse((await tab.eval(X.lsAI))||'null');
        const onDisk=()=>tab.eval(`Object.keys(localStorage).some(k=>{const v=String(localStorage.getItem(k));return v.includes(${K})||v.includes(${K2})})`);
        const toggle=await tab.eval('(()=>{const el=document.querySelector("#ai-session-only");const lab=el.closest("label").textContent.trim();return {present:!!el,type:el.type,label:lab}})()');
        // 记住档：三件套存本浏览器（原行为）
        await tab.eval(P.type('#ai-baseurl',srv.origin));await tab.eval(P.type('#ai-key',FAKE_KEY_A));await tab.eval(P.type('#ai-model','probe-mock'));
        await sleep(500);
        let s=await ls();
        check(Boolean(toggle.present)&&toggle.type==='checkbox'&&toggle.label.includes('仅本会话')&&toggle.label.includes('不写入浏览器存储'),'AI 设置里应有「仅本会话」开关与一句话说明');
        check(Boolean(s)&&s.apiKey===FAKE_KEY_A&&s.sessionOnly===false&&s.baseUrl===srv.origin&&s.model==='probe-mock'&&await tab.eval('document.querySelector("#ai-session-only").checked')===false,'记住档（默认）：三件套应存本浏览器，开关未勾');
        // 切到仅本会话（真实入口）：盘上 Key 立即清空、内存仍可用
        const t0=Date.now();
        await tab.eval(P.check('#ai-session-only',true));
        s=await ls();
        const tRead=Date.now()-t0;
        const mem=await tab.eval(`({eff:aiEffective().apiKey===${K},box:document.querySelector('#ai-key').value===${K},type:document.querySelector('#ai-key').type,checked:document.querySelector('#ai-session-only').checked,base:aiStore.baseUrl===${JSON.stringify(srv.origin)},model:aiStore.model==='probe-mock'})`);
        check(Boolean(s)&&s.apiKey===''&&s.sessionOnly===true,`切到仅本会话：盘上 Key 应立即清空（切档后 ${tRead}ms 读到），实得 apiKey ${s&&s.apiKey?'非空':'空'}、sessionOnly=${s&&s.sessionOnly}`);
        check(mem.eff&&mem.box&&mem.checked&&mem.type==='password'&&mem.base&&mem.model,'会话档：Key 移入内存仍可用、输入框回显为密码框、BaseURL／Model 照旧记住');
        // 会话档下两句既有文案跟着换：Key 框占位语、下面那行说明（「只保存在本浏览器」在会话档不成立）
        const copy=()=>tab.eval('(()=>{const k=document.querySelector("#ai-key"),n=document.querySelector(".ai-note[data-i18n]");return {phKey:k.getAttribute("data-i18n-ph"),ph:k.getAttribute("placeholder"),noteKey:n.getAttribute("data-i18n"),note:n.textContent,wantPh:t("ai.key.ph.session"),wantNote:t("ai.note.session")}})()');
        let cp=await copy();
        note(`会话档文案：Key 框占位「${cp.ph}」｜说明行「${cp.note}」`);
        check(cp.phKey==='ai.key.ph.session'&&cp.noteKey==='ai.note.session'&&cp.ph===cp.wantPh&&cp.note===cp.wantNote&&!cp.ph.includes('保存在本浏览器')&&!cp.note.includes('只保存在本浏览器'),'会话档：Key 框占位语与说明行应换成会话档的说法');
        // 会话档改 Key：只进内存
        await tab.eval(P.type('#ai-key',FAKE_KEY_B));await sleep(500);
        s=await ls();
        check(Boolean(s)&&s.apiKey===''&&s.sessionOnly===true&&await tab.eval(`aiEffective().apiKey===${K2}`)&&!(await onDisk()),'会话档改 Key：只进内存；浏览器存储任一键值里都不得出现钥匙');
        // 会话档发一次请求：请求头带内存里的 Key，状态栏不回显
        srv.ai.expectKey=FAKE_KEY_B;
        const n0=srv.ai.log.length;
        await tab.eval(P.click('#ai-test'));
        await tab.waitFor('!document.querySelector("#ai-test").disabled',10000,'连通测试结束');
        const tr=srv.ai.log.slice(n0),status=await tab.eval('document.querySelector("#ai-test-status").textContent');
        check(tr.length===1&&tr[0].keyState==='对'&&tr[0].maxTokens<200,'会话档下「测试连接」应带内存 Key 发出 1 次请求');
        check(status.includes('连通')&&!status.includes(FAKE_KEY_B),`连通测试状态应显示连通且不含钥匙，实得「${status.slice(0,60)}」`);
        // 刷新：内存 Key 消失、档位偏好保留
        await tab.goto(`${srv.origin}/index.html`);
        const after=await tab.eval(`({eff:aiEffective().apiKey==='',mem:aiSessionKey==='',box:document.querySelector('#ai-key').value==='',checked:document.querySelector('#ai-session-only').checked,sess:aiStore.sessionOnly})`);
        s=await ls();
        note(`刷新后（会话档）：生效配置 Key 为空=${after.eff}、内存变量为空=${after.mem}、输入框为空=${after.box}、开关仍勾=${after.checked}｜盘上 apiKey 为空=${s&&s.apiKey===''}`);
        check(Object.values(after).every(Boolean)&&Boolean(s)&&s.apiKey==='','刷新后：会话档 Key 应即失（内存／输入框／生效配置全空），档位偏好保留');
        check(await tab.eval(`document.querySelector('#ai-baseurl').value===${JSON.stringify(srv.origin)}&&document.querySelector('#ai-model').value==='probe-mock'`),'刷新后 BaseURL／Model 应照旧记住');
        cp=await copy();
        check(cp.phKey==='ai.key.ph.session'&&cp.noteKey==='ai.note.session'&&cp.ph===cp.wantPh&&cp.note===cp.wantNote,`刷新后（会话档）：两句文案仍应是会话档的说法，实得占位「${cp.ph}」｜说明「${cp.note.slice(0,30)}…」`);
        await tab.eval('setLang("en");1');cp=await copy();await tab.eval('setLang("zh");1');
        note(`会话档切英文：占位「${cp.ph}」｜说明「${cp.note.slice(0,60)}…」`);
        check(cp.phKey==='ai.key.ph.session'&&cp.noteKey==='ai.note.session'&&cp.ph===cp.wantPh&&cp.note===cp.wantNote&&!/[一-鿿]/.test(cp.ph+cp.note),'会话档切英文：两句文案应跟着走英文表（换的是文案键，不是写死中文）');
        // 会话档填 Key→切回记住：写盘（用户明确选择记住）
        await tab.eval(P.view('personal'));await tab.eval(P.tab('topics'));await tab.eval(P.type('#ai-key',FAKE_KEY_B));await sleep(400);
        const stillOff=!(await onDisk());
        await tab.eval(P.check('#ai-session-only',false));
        s=await ls();
        check(stillOff&&Boolean(s)&&s.apiKey===FAKE_KEY_B&&s.sessionOnly===false&&await tab.eval('aiSessionKey')===''&&await tab.eval(`aiEffective().apiKey===${K2}`),'切回记住：此前盘上仍无 Key；切回后内存 Key 写盘、内存变量清空');
        cp=await copy();
        check(cp.phKey==='ai.key.ph'&&cp.noteKey==='ai.note'&&cp.ph===await tab.eval('t("ai.key.ph")')&&cp.note===await tab.eval('t("ai.note")'),`切回记住：两句文案应换回原说法，实得占位「${cp.ph}」｜键 ${cp.phKey}／${cp.noteKey}`);
        // 零日志零回显
        const dialogs=tab.dialogs.map(d=>d.message),bodyText=await tab.eval('document.body.innerText');
        note(`控制台文本 ${tab.consoleTexts.length} 条、异常 ${tab.errors.length} 条、对话框 ${dialogs.length} 次、页面可见文本 ${bodyText.length} 字：逐条搜两把假钥匙`);
        check(!hasKey(tab.consoleTexts,FAKE_KEY_A)&&!hasKey(tab.consoleTexts,FAKE_KEY_B)&&!hasKey(tab.errors,FAKE_KEY_A)&&!hasKey(tab.errors,FAKE_KEY_B)&&!hasKey(dialogs,FAKE_KEY_A)&&!hasKey(dialogs,FAKE_KEY_B),'钥匙不得进控制台／异常／对话框');
        check(!bodyText.includes(FAKE_KEY_A)&&!bodyText.includes(FAKE_KEY_B),'钥匙不得以明文出现在页面可见文本');
        noErrors(tab,'S13');
      }catch(e){check(false,'S13 执行故障：'+e.message)}finally{srv.ai.expectKey=FAKE_KEY_A}end()}

    // ---- S14 h8 降级 ----
    if(!skip('S14')){begin('S14','h8 降级：页面拿不到 crypto.subtle（file:// 一类场景）→走 djb2——指纹带算法标记、分类照常落库命中、页面零异常；与 SHA-256 算出的缓存互不相认');
      let B=null;
      try{
        B=new Tab(h,'B');
        B.preScript="Object.defineProperty(Crypto.prototype,'subtle',{get(){return undefined},configurable:true})";   // 页面脚本跑之前先拆掉 subtle
        await B.open(`${srv.origin}/index.html`);
        await fresh(B,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await B.eval(seedPapers(1,5));
        await toEditor(B);
        const n0=srv.ai.log.length;
        await B.eval(P.click('[data-tw-save]'));
        await waitClsDone(B);await sleep(300);
        const env=await B.eval('(async()=>({sha:CLS_SHA,tag:CLS_HASH_TAG,h:await h8("abc"),subtle:typeof crypto.subtle}))()'),fp=await B.eval('clsStore.schemes.s_probe1.fp'),dial=await B.eval(X.assignAll);
        note(`降级页签：crypto.subtle=${env.subtle}、CLS_SHA=${env.sha}、标记「${env.tag}」、h8("abc")=${env.h}（探针独立算 djb2＝${djb2('abc')}）｜指纹 ${fp}｜落库 ${Object.keys(await B.eval(X.items)).length} 条`);
        check(env.sha===false&&env.tag==='~djb2'&&env.subtle==='undefined'&&env.h===djb2('abc'),'拿不到 subtle 时应走 djb2 并给指纹带算法标记');
        check(/^[0-9a-f]{8}\|cls-v1~djb2$/.test(fp),'方案指纹应以「|cls-v1~djb2」结尾');
        check(dial.length===40&&dial.every(d=>d.a==='g_a')&&srv.ai.log.length-n0===2,'降级态下分类应照常 2 批落库、盘面全归 Alpha');
        await tab.goto(`${srv.origin}/index.html`);await sleep(600);   // 同一份盘上缓存拿到 SHA-256 页签里：指纹不等＝全部陈旧
        const dialA=await tab.eval(X.assignAll),envA=await tab.eval('({sha:CLS_SHA,tag:CLS_HASH_TAG})'),plainN=await tab.eval('PAPERS.length');
        note(`SHA-256 页签读同一份缓存：CLS_SHA=${envA.sha}、标记「${envA.tag}」｜窗内 ${dialA.length} 篇：归 Alpha ${dialA.filter(d=>d.a==='g_a').length} 篇、未分组 ${dialA.filter(d=>d.a==='__ungrouped__').length} 篇`);
        check(envA.sha===true&&envA.tag===''&&dialA.length===plainN&&dialA.every(d=>d.a==='__ungrouped__'),`两种哈希的 ck 互不相认：SHA 页签当前 ${plainN} 篇应全部保守回关键词，不应命中 djb2 页签写的缓存`);
        noErrors(B,'S14');noErrors(tab,'S14');
      }catch(e){check(false,'S14 执行故障：'+e.message)}finally{srv.ai.respond=null;if(B)await B.close()}end()}

    // ---- S15 单次上限与停止 ----
    if(!skip('S15')){begin('S15','单次上限 200 篇＋停止钮：窗内 230 篇→只排 10 批、余 30 篇标「未分类」；起跑后第 1 批还在途时进度行与停止钮已就位；点停止＝不再起新批、已落库批次保留');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await tab.eval(seedPapers(1,195));   // 35＋195＝230 篇
        await toEditor(tab);
        const n0=srv.ai.log.length;let release=null;
        srv.ai.respond=rec=>rec.n-n0===1?new Promise(r=>{release=()=>r(srv.ai.default(rec))}):srv.ai.default(rec);   // 第 1 批挂住：留出「已起跑、第 1 批未应答」的窗口
        await tab.eval(P.click('[data-tw-save]'));
        await waitAi(srv,n0+1,15000);
        const live=await tab.eval('({running:clsRun.running,batchTotal:clsRun.batchTotal,skipped:clsRun.skipped,batch:clsRun.batchDone,stopBtn:!!document.querySelector("[data-cls-stop]"),prog:(document.querySelector("#cls-progress")||{}).textContent||""})');
        const first=srv.ai.log[n0];
        release();   // 放行第 1 批（应答即落库），随后在「批间 ≥3s」的等待里点停止
        await sleep(350);
        const mid=await tab.eval(X.clsState);
        await tab.eval(P.click('[data-cls-stop]'));   // 真实入口：停止
        await waitClsDone(tab,10000);await sleep(400);
        const after=await tab.eval(X.clsState),items=await tab.eval(X.items)||{},sent=srv.ai.log.length-n0,prog=await tab.eval(X.progress);
        note(`起跑后（第 1 批在途未应答）：${JSON.stringify(live)}｜第 1 批 ${first.payload.papers.length} 篇｜放行后点停止前：已完批=${mid.batchDone} 落库=${mid.done}｜点停止后：${JSON.stringify(after)}｜落库 ${Object.keys(items).length} 条｜AI 请求 ${sent} 次｜进度行「${prog?prog.text:''}」`);
        check(live.running===true&&live.batchTotal===10&&live.skipped===30&&live.batch===0&&first.payload.papers.length===20,`230 篇应只排 10 批（200 篇）并记 30 篇未分类，实得 批数=${live.batchTotal} 未分类=${live.skipped} 已完批=${live.batch} 第 1 批=${first.payload.papers.length} 篇`);
        check(live.stopBtn===true&&live.prog.includes('分类中')&&live.prog.includes('另有 30 篇未分类')&&live.prog.includes('批次 0/10'),'第 1 批还在途时进度行就应显示「分类中 批次 0/10」、未分类篇数与停止钮');
        check(mid.batchDone===1&&mid.done===20&&mid.running===true,`放行后第 1 批应落库 20 条并停在批间等待里，实得 已完批=${mid.batchDone} 落库=${mid.done} 在跑=${mid.running}`);
        check(after!=='null'&&after.running===false&&after.stopped===true&&after.done===20&&Object.keys(items).length===20,`停止后应即刻收尾、已落库的 20 条保留，实得 ${JSON.stringify(after)}、落库 ${Object.keys(items).length} 条`);
        check(sent===1,`停止后不得再起新批：AI 请求应恰 1 次（只有第 1 批），实得 ${sent} 次`);
        check(Boolean(prog)&&prog.text.includes('已停止'),'停止后进度行应说明「已停止」');
        noErrors(tab,'S15');
      }catch(e){check(false,'S15 执行故障：'+e.message)}finally{srv.ai.respond=null}end()}

    // ---- S16 深评护栏 ----
    if(!skip('S16')){begin('S16','深评护栏：停止钮＝即刻中止在途、不落缓存、不报错、互斥闸放开；60s 超时＝判超时、不落缓存、按钮可重试；空白应答＝报错不写缓存；应答正文截 3000 字；缓存条数夹 200 丢最旧（读侧与写侧各一道）；盘上坏件清洗；盘写不进去＝提示、不崩');
      let restore=false,restoreStore=false;
      try{
        // (1) 函数级：sanitizeDeep 的清洗与上限；三个上限常量
        const unit=await tab.eval([
          '(()=>{const mk=n=>Object.fromEntries(Array.from({length:n},(_,i)=>[String(82000000+i),{text:"x".repeat(4000),at:1+i}])),S=sanitizeDeep,a=S({v:1,items:mk(205)}),keys=Object.keys(a.items);',
          'const bad=S({v:1,items:{"123":{text:"ok",at:5},abc:{text:"x",at:1},constructor:{text:"x",at:1},"456":{text:"",at:1},"789":{text:"   ",at:1},"234":{text:7,at:1},"345":{text:"x",at:"q"},"457":{text:"x"},"890":null,"1234":"str"}});',
          'return {count:keys.length,first:keys[0],last:keys[keys.length-1],len:a.items[keys[0]].text.length,proto:Object.getPrototypeOf(a.items)===null,v:a.v,badKeys:Object.keys(bad.items).join(","),badProto:Object.getPrototypeOf(bad.items)===null,none:Object.keys(S(null).items).length,wrongV:Object.keys(S({v:2,items:mk(3)}).items).length}})()'
        ].join('\n'));
        const consts=await tab.eval('[DEEP_MAX_ITEMS,DEEP_TEXT_MAX,DEEP_TIMEOUT_MS]');
        note(`sanitizeDeep 函数级：${JSON.stringify(unit)}｜上限常量 条数／正文字数／超时 ms＝${consts.join('/')}`);
        check(unit.count===200&&unit.first==='82000005'&&unit.last==='82000204'&&unit.len===3000&&unit.proto===true&&unit.v===1&&unit.badKeys==='123'&&unit.badProto===true&&unit.none===0&&unit.wrongV===0,`sanitizeDeep：205 条应夹到 200 条且丢 at 最旧的 5 条、正文截到 3000 字、坏件（非数字 PMID／原型名键／空正文／非字符串正文／坏时间戳／非对象）全剪、无原型字典，实得 ${JSON.stringify(unit)}`);
        check(consts.join('/')==='200/3000/60000',`上限常量应为 条数 200／正文 3000 字／超时 60000ms，实得 ${consts.join('/')}`);
        // (2) 停止钮（真实入口）：应答压 4s，留出在途窗口
        await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);await sleep(400);
        const pmA=await tab.eval('String(PAPERS.find(p=>p.id===state.selected).pmid)');
        let n0=srv.ai.log.length;
        srv.ai.respond=()=>({status:200,text:'late answer',delay:4000});
        await tab.eval(P.click('#deepreview-btn'));await waitAiKind(srv,n0,'deep');await sleep(300);
        const live=await tab.eval('({running:Boolean(deepRun&&deepRun.running),busy:personalBusyKind(),stop:!!document.querySelector("#deep-stop"),label:((document.querySelector("#deep-box")||{}).textContent||"").replace(/\\s+/g," ").slice(0,40)})');
        await tab.eval(P.click('#deep-stop'));
        const t0=Date.now();await tab.waitFor('deepRun===null',3000,'停止后收尾');const stopMs=Date.now()-t0;
        await sleep(4500);   // 等被中止的那次应答在假服务那边到点：迟到的应答回头不得写缓存
        const stopped=await tab.eval('({busy:personalBusyKind(),note:!!document.querySelector("#detail .deep-note"),btn:!!document.querySelector("#deepreview-btn"),err:(document.querySelector("#detail .deep-err")||{}).textContent||"",cached:Object.keys(deepStore.items).length,ls:localStorage.getItem("thoradar.deepreview.v1")})');
        note(`在途：${JSON.stringify(live)}｜点停止后 ${stopMs}ms 收尾：${JSON.stringify(stopped)}`);
        check(live.running===true&&live.busy==='deep'&&live.stop===true,`在途时应显示进度与停止钮、互斥闸记为深评在途，实得 ${JSON.stringify(live)}`);
        check(stopMs<2500&&stopped.busy===''&&stopped.note===false&&stopped.btn===true&&stopped.err===''&&stopped.cached===0&&stopped.ls===null,`点停止应即刻收尾：不落缓存、不报错、按钮留着可重试、互斥闸放开，实得 ${JSON.stringify(stopped)}（收尾 ${stopMs}ms）`);
        // (3) 空白应答
        n0=srv.ai.log.length;srv.ai.respond=rec=>aiText(rec,'   ');
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null',10000,'空白应答收尾');await sleep(200);
        const empty=await tab.eval('({err:(document.querySelector("#detail .deep-err")||{}).textContent||"",want:t("deep.empty"),cached:Object.keys(deepStore.items).length,btn:!!document.querySelector("#deepreview-btn")})');
        check(srv.ai.log.length-n0===1&&empty.err.includes(empty.want)&&empty.cached===0&&empty.btn===true,`空白应答应报「没有给出正文」、不写缓存、按钮留着，实得 ${JSON.stringify(empty)}`);
        // (4) 超长应答截 3000 字（内存／盘上／页面三处）
        n0=srv.ai.log.length;srv.ai.respond=rec=>aiText(rec,'长'.repeat(5000));
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'超长应答上屏');await sleep(200);
        const long=await tab.eval(`(()=>{const ls=(JSON.parse(localStorage.getItem("thoradar.deepreview.v1")||"{}").items||{})[${JSON.stringify(pmA)}];return {mem:deepStore.items[${JSON.stringify(pmA)}].text.length,ls:ls?ls.text.length:-1,dom:document.querySelector("#detail .deep-note").textContent.length}})()`);
        note(`5000 字应答：内存 ${long.mem} 字｜盘上 ${long.ls} 字｜页面连小标题 ${long.dom} 字`);
        check(srv.ai.log.length-n0===1&&long.mem===3000&&long.ls===3000&&long.dom>3000&&long.dom<3200,`5000 字的应答应截到 3000 字落内存与盘上，页面只多出小标题，实得 ${JSON.stringify(long)}`);
        // (5) 60s 超时：把页面上「60000ms 的定时器」临时缩到 300ms（只动这一个时长，测完还原）——定时器一响就走真实的超时收尾路径
        await tab.eval(P.click('#next-btn'));await sleep(300);
        const pmB=await tab.eval('String(PAPERS.find(p=>p.id===state.selected).pmid)');
        n0=srv.ai.log.length;srv.ai.respond=()=>({status:200,text:'too late',delay:6000});
        await tab.eval('(()=>{const o=window.setTimeout;window.__sto=o;window.setTimeout=function(fn,ms){return o.call(window,fn,ms===60000?300:ms)};return 1})()');restore=true;
        const t1=Date.now();
        await tab.eval(P.click('#deepreview-btn'));await waitAiKind(srv,n0,'deep');
        await tab.waitFor('deepRun===null',8000,'超时收尾');const timeoutMs=Date.now()-t1;
        await tab.eval('(()=>{window.setTimeout=window.__sto;delete window.__sto;return 1})()');restore=false;
        await sleep(1500);   // 等假服务那边 6s 的应答到点：迟到的应答同样不得回头写缓存
        const timed=await tab.eval(`({err:(document.querySelector("#detail .deep-err")||{}).textContent||"",want:t("deep.timeout"),busy:personalBusyKind(),cached:deepStore.items[${JSON.stringify(pmB)}]!==undefined,btn:!!document.querySelector("#deepreview-btn")})`);
        note(`应答压 6s 不回：${timeoutMs}ms 判超时「${timed.err}」｜互斥闸=${timed.busy||'空'}｜落缓存=${timed.cached}`);
        check(timeoutMs<5000&&timed.err.includes(timed.want)&&timed.busy===''&&timed.cached===false&&timed.btn===true,`悬挂的应答应在超时后判「深评超时」、不落缓存、闸放开、按钮留着，实得 ${JSON.stringify(timed)}（${timeoutMs}ms）`);
        // (6) 盘上超量：重载后读侧也夹到 200、丢最旧
        await tab.eval('localStorage.setItem("thoradar.deepreview.v1",JSON.stringify({v:1,items:Object.fromEntries(Array.from({length:205},(_,i)=>[String(83000000+i),{text:"t"+i,at:i}]))}));1');
        await tab.goto(`${srv.origin}/index.html`);await sleep(400);
        const loaded=await tab.eval('(()=>{const k=Object.keys(deepStore.items);return {n:k.length,first:k[0],last:k[k.length-1]}})()');
        check(loaded.n===200&&loaded.first==='83000005'&&loaded.last==='83000204',`盘上 205 条读进来应夹到 200 条且丢最旧的 5 条，实得 ${JSON.stringify(loaded)}`);
        // (7) 写侧也夹 200：盘上先放 199 条，再真实深评 2 篇→内存与盘上都是 200 条、最早那条被丢、两篇新评都在
        await tab.eval('localStorage.setItem("thoradar.deepreview.v1",JSON.stringify({v:1,items:Object.fromEntries(Array.from({length:199},(_,i)=>[String(84000000+i),{text:"t"+i,at:i+1}]))}));1');
        await tab.goto(`${srv.origin}/index.html`);await sleep(400);
        const pm1=await tab.eval('String(PAPERS.find(p=>p.id===state.selected).pmid)');
        srv.ai.respond=rec=>({status:200,text:'review '+rec.payload.pmid,delay:0});
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'第 1 篇深评上屏');
        await tab.eval(P.click('#next-btn'));await sleep(300);
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'第 2 篇深评上屏');await sleep(200);
        const trimmed=await tab.eval(`(()=>{const mem=Object.keys(deepStore.items),disk=Object.keys(JSON.parse(localStorage.getItem("thoradar.deepreview.v1")).items);return {mem:mem.length,disk:disk.length,oldest:mem.includes("84000000"),second:mem.includes("84000001"),newest:mem.includes(${JSON.stringify(pm1)})}})()`);
        note(`写侧上限：盘上 199 条＋新评 2 篇 → 内存 ${trimmed.mem} 条｜盘上 ${trimmed.disk} 条｜最早那条还在=${trimmed.oldest}｜第 2 旧还在=${trimmed.second}｜新评那篇在=${trimmed.newest}`);
        check(trimmed.mem===200&&trimmed.disk===200&&trimmed.oldest===false&&trimmed.second===true&&trimmed.newest===true,`写侧应同样夹到 200 条、丢 at 最旧的那条，新评两篇都在，实得 ${JSON.stringify(trimmed)}`);
        // (8) 盘写不进去（存储配额／隐私模式一类）：提示一句、不崩、正文照常上屏（留在内存）
        await tab.eval(P.click('#next-btn'));await sleep(300);
        const pmC=await tab.eval('String(PAPERS.find(p=>p.id===state.selected).pmid)');
        n0=srv.ai.log.length;srv.ai.respond=rec=>aiText(rec,'kept in memory only');
        await tab.eval(`(()=>{const o=Storage.prototype.setItem;window.__setItem=o;Storage.prototype.setItem=function(k,v){if(k==='thoradar.deepreview.v1')throw new DOMException('QuotaExceededError','QuotaExceededError');return o.call(this,k,v)};return 1})()`);restoreStore=true;   // 只让深评这一个键写不进去
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'盘写失败下深评上屏');await sleep(200);
        const quota=await tab.eval(`(()=>{const el=document.querySelector("#toast");return {toast:el?el.textContent:"",shown:Boolean(el)&&el.style.display!=='none',mem:typeof deepStore.items[${JSON.stringify(pmC)}]==='object',note:!!document.querySelector("#detail .deep-note"),want:t("deep.save.fail")}})()`);
        await tab.eval('Storage.prototype.setItem=window.__setItem;delete window.__setItem;1');restoreStore=false;
        note(`盘写失败：提示「${quota.toast}」（应为「${quota.want}」）｜提示可见=${quota.shown}｜正文在内存=${quota.mem}｜已上屏=${quota.note}｜AI 请求 ${srv.ai.log.length-n0} 次`);
        check(srv.ai.log.length-n0===1&&quota.toast===quota.want&&quota.shown&&quota.mem&&quota.note,'存储写不进去时应提示「浏览器未能保存深评结果」、不崩、正文照常上屏（留在内存）');
        noErrors(tab,'S16');
      }catch(e){check(false,'S16 执行故障：'+e.message)}finally{srv.ai.respond=null;if(restore)await tab.eval('(()=>{window.setTimeout=window.__sto;delete window.__sto;return 1})()').catch(()=>{});if(restoreStore)await tab.eval('Storage.prototype.setItem=window.__setItem;delete window.__setItem;1').catch(()=>{});}end()}

    // ---- S17 钥匙零回显（出口统一打码） ----
    if(!skip('S17')){begin('S17','钥匙零回显·出口打码：服务商在四处把钥匙回写出来——①连通测试的成功回复 ②主题检索判官的理由 ③判官的报错报文 ④深评正文——页面可见文本、落盘存储、控制台里都不得出现钥匙；⑤收口扫描 ⑥占位短 Key 不抹正文 ⑦请求发出后才换 Key 的在途应答，回写的旧 Key 照样打码');
      try{
        tab.responder=eutilsOK;
        await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin)),LS('thoradar.topics.v1',TOPIC_CFG)],srv.origin);
        await tab.eval(P.view('personal'));await tab.eval(P.tab('topics'));
        const overlay=()=>tab.eval('({body:(document.querySelector("#topic-run-body")||{}).textContent||"",ls:localStorage.getItem("thoradar.topicruns.v1")||""})');
        const has=x=>String(x).includes('PROBE-FAKE');   // 按假钥匙的固定前缀查（比查整串更严：被截短的半截钥匙也算回显）
        // ① 连通测试：成功回复里带着钥匙
        let n0=srv.ai.log.length;
        srv.ai.respond=rec=>aiText(rec,'OK '+FAKE_KEY_A);
        await tab.eval(P.click('#ai-test'));await tab.waitFor('!document.querySelector("#ai-test").disabled',10000,'连通测试结束');
        const st=await tab.eval('document.querySelector("#ai-test-status").textContent');
        note(`①连通测试回复「OK ＋钥匙」→ 状态栏「${st}」`);
        check(srv.ai.log.length-n0===1&&st.includes('probe-mock')&&st.includes('[key]')&&!has(st),`①连通测试状态栏不得回显钥匙（应显示「回复「OK [key]」」），实得「${st}」`);
        // ② 主题检索：判官理由里带着钥匙
        n0=srv.ai.log.length;
        srv.ai.respond=rec=>aiText(rec,JSON.stringify([...String(rec.user||'').matchAll(/PMID (\d+)/g)].map(m=>({pmid:m[1],related:true,why:'echo '+FAKE_KEY_A}))));
        await tab.eval(P.click('[data-topic-run="t_probe1"]'));await tab.waitFor('runState&&!runState.running',40000,'主题运行结束');await sleep(500);
        const run1=await overlay();
        note(`②判官理由夹带钥匙 → 结果面板 ${run1.body.length} 字，含「echo [key]」=${run1.body.includes('echo [key]')}，含钥匙=${run1.body.includes(FAKE_KEY_A)}｜存档含钥匙=${run1.ls.includes(FAKE_KEY_A)}`);
        check(run1.body.includes('echo [key]')&&!has(run1.body)&&!has(run1.ls),'②判官理由里的钥匙不得上屏、不得落进 thoradar.topicruns.v1');
        // ③ 主题检索：判官报错报文里带着钥匙（HTTP 500）
        await tab.eval(P.click('#topic-close'));await sleep(300);
        n0=srv.ai.log.length;
        srv.ai.respond=()=>({status:500,text:'bad key '+FAKE_KEY_A,delay:0});
        await tab.eval(P.click('[data-topic-run="t_probe1"]'));await tab.waitFor('runState&&!runState.running',40000,'主题运行结束');await sleep(500);
        const run2=await overlay();
        note(`③判官报错报文夹带钥匙 → 结果面板含「[key]」=${run2.body.includes('[key]')}，含钥匙=${run2.body.includes(FAKE_KEY_A)}｜存档含钥匙=${run2.ls.includes(FAKE_KEY_A)}｜AI 请求 ${srv.ai.log.length-n0} 次`);
        check(run2.body.includes('[key]')&&!has(run2.body)&&!has(run2.ls),'③判官报错报文里的钥匙不得上屏、不得落进 thoradar.topicruns.v1');
        // ④ 深评正文里带着钥匙
        await tab.eval(P.click('#topic-close'));await tab.eval(P.view('overview'));await sleep(300);
        n0=srv.ai.log.length;
        srv.ai.respond=rec=>aiText(rec,'【主要发现】\n服务商把钥匙回写了：'+FAKE_KEY_A+'。');
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'深评上屏');await sleep(300);
        const deep=await tab.eval('({dom:document.querySelector("#detail .deep-note").textContent,ls:localStorage.getItem("thoradar.deepreview.v1")||""})');
        note(`④深评正文夹带钥匙 → 页面含「[key]」=${deep.dom.includes('[key]')}，含钥匙=${deep.dom.includes(FAKE_KEY_A)}｜存档含钥匙=${deep.ls.includes(FAKE_KEY_A)}`);
        check(deep.dom.includes('[key]')&&!has(deep.dom)&&!has(deep.ls),'④深评正文里的钥匙不得上屏、不得落进 thoradar.deepreview.v1');
        // ⑤ 收口：除钥匙自己的存储键外，页面上、所有存储值、控制台、异常、对话框里都没有钥匙
        const sweep=await tab.eval(`(()=>{const K=${JSON.stringify(FAKE_KEY_A)};const ls=Object.keys(localStorage).filter(k=>k!=='thoradar.ai.v1').filter(k=>String(localStorage.getItem(k)).includes(K));return {body:document.body.textContent.includes(K),ls,bodyText:document.body.innerText.includes(K)}})()`);
        note(`⑤收口：页面 textContent 含钥匙=${sweep.body}｜可见文本含钥匙=${sweep.bodyText}｜除 thoradar.ai.v1 外含钥匙的存储键：${sweep.ls.join(',')||'无'}｜控制台文本 ${tab.consoleTexts.length} 条、异常 ${tab.errors.length} 条、对话框 ${tab.dialogs.length} 次`);
        check(sweep.body===false&&sweep.bodyText===false&&sweep.ls.length===0,'⑤除钥匙自己的存储键（thoradar.ai.v1）外，页面与浏览器存储里不得出现钥匙');
        check(!hasKey(tab.consoleTexts,'PROBE-FAKE')&&!hasKey(tab.errors,'PROBE-FAKE')&&!hasKey(tab.dialogs.map(d=>d.message),'PROBE-FAKE'),'⑤钥匙不得进控制台／异常／对话框');
        // ⑥ 反过来：太短的 Key（本地网关常用的占位串）不参与打码——否则正文里每个同字母都会被打成 [key]
        await fresh(tab,[LS('thoradar.ai.v1',{baseUrl:srv.origin,apiKey:'',model:'probe-mock',sessionOnly:true})],srv.origin);await sleep(300);
        await tab.eval('aiSessionKey="x";1');
        n0=srv.ai.log.length;srv.ai.respond=rec=>aiText(rec,'Exact text: no redaction expected for a short key.');
        await tab.eval(P.click('#deepreview-btn'));await tab.waitFor('deepRun===null&&!!document.querySelector("#detail .deep-note")',10000,'短 Key 深评上屏');await sleep(200);
        const short=await tab.eval('({dom:document.querySelector("#detail .deep-note").textContent,want:"Exact text: no redaction expected for a short key.",ls:localStorage.getItem("thoradar.ai.v1")})');
        note(`⑥会话档短 Key「x」→ 深评正文原句完整=${short.dom.includes(short.want)}｜片段「${short.dom.slice(-62)}」｜请求带出的 Key 长度＝${srv.ai.log[srv.ai.log.length-1].keyLen}｜盘上 thoradar.ai.v1＝${short.ls}`);
        check(srv.ai.log.length-n0===1&&srv.ai.log[srv.ai.log.length-1].keyLen===1&&short.dom.includes(short.want)&&short.ls.includes('"apiKey":""'),`⑥短 Key 不得把正文打烂（原句应原样在），且会话档的 Key 不落盘，实得「${short.dom.slice(-80)}」｜盘上 ${short.ls}`);
        // ⑦ 在途应答晚到：请求发出去之后用户才换了 Key——应答里回写的是「这次请求实际带出去的旧 Key」，照样不得上屏、不得落盘（打码认请求带出去的那把，不是此刻生效的那把）。报错路径与正文路径各走一遍
        const lateEcho=async reply=>{   // reply(rec)→应答；返回 {switched,err,dom,ls}
          await fresh(tab,[LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);await sleep(300);
          let release=null;srv.ai.respond=()=>new Promise(r=>{release=()=>r(reply())});
          const m0=srv.ai.log.length;
          await tab.eval(P.click('#deepreview-btn'));await waitAi(srv,m0+1,10000);   // 请求已带着旧 Key 发出、应答还挂着
          await tab.eval(P.view('personal'));await tab.eval(P.tab('topics'));await tab.eval(P.type('#ai-key',FAKE_KEY_B));await sleep(400);   // 这时才把 Key 换掉
          const switched=await tab.eval(`aiEffective().apiKey===${K2}&&aiStore.apiKey===${K2}`);
          release();await tab.waitFor('deepRun===null',10000,'换 Key 后在途深评收尾');await sleep(300);
          await tab.eval(P.view('overview'));await sleep(300);
          return Object.assign({switched,sentKey:srv.ai.log[m0].keyLen===FAKE_KEY_A.length},await tab.eval('({err:(document.querySelector("#detail .deep-err")||{}).textContent||"",dom:document.querySelector("#detail").textContent,ls:localStorage.getItem("thoradar.deepreview.v1")||""})'));
        };
        const late1=await lateEcho(()=>({status:500,text:'revoked key '+FAKE_KEY_A,delay:0}));
        note(`⑦a 请求带着旧 Key 发出后才换成新 Key（换 Key 生效=${late1.switched}，请求带的是旧 Key=${late1.sentKey}）→ 在途应答是 500、报文回写旧 Key：错误提示「${late1.err.slice(0,90)}」｜详情卡含旧 Key=${late1.dom.includes(FAKE_KEY_A)}`);
        check(late1.switched&&late1.sentKey&&late1.err.includes('[key]')&&!late1.err.includes(FAKE_KEY_A)&&!late1.dom.includes(FAKE_KEY_A),'⑦a 在途报错报文里回写的旧 Key 不得上屏，即使此刻生效的已换成别的 Key');
        const late2=await lateEcho(()=>aiText({},'old key echoed: '+FAKE_KEY_A));
        note(`⑦b 同一情形、应答是正文且回写旧 Key（换 Key 生效=${late2.switched}）→ 详情卡含「[key]」=${late2.dom.includes('[key]')}｜含旧 Key=${late2.dom.includes(FAKE_KEY_A)}｜存档含旧 Key=${late2.ls.includes(FAKE_KEY_A)}`);
        check(late2.switched&&late2.sentKey&&late2.dom.includes('[key]')&&!late2.dom.includes(FAKE_KEY_A)&&!late2.ls.includes(FAKE_KEY_A),'⑦b 在途应答正文里回写的旧 Key 不得上屏、不得落盘，即使此刻生效的已换成别的 Key');
        noErrors(tab,'S17');
      }catch(e){check(false,'S17 执行故障：'+e.message)}finally{srv.ai.respond=null;tab.responder=null;end()}}

    // ---- S18 分类在途时重命名阵地 ----
    if(!skip('S18')){begin('S18','分类逐批重渲不得打断正在进行的阵地重命名：重命名框「失焦即提交」，在途期间打了一半的名字不得被提交，焦点与光标都应还在；回车／失焦才提交，Esc 仍能取消（P1 既有语义不变）');
      try{
        await fresh(tab,[LS('thoradar.sectors.v2',SECT()),LS('thoradar.ai.v1',AI_CFG(srv.origin))],srv.origin);
        await tab.eval(seedPapers(1,43));   // 78 篇→4 批，逐批重渲
        await toEditor(tab);
        const n0=srv.ai.log.length;
        await tab.eval(P.click('[data-tw-save]'));
        await waitAi(srv,n0+1,15000);   // 第 1 批已发出＝分类在途
        await tab.eval(P.click('[data-sector-rename="g_a"]'));
        const typing0=await tab.eval(`(()=>{const el=document.querySelector('[data-sector-rename-input="g_a"]');if(!el)return 'MISSING';el.focus();el.value='renamed half';el.setSelectionRange(5,5);return document.activeElement===el?'focused':'not-focused'})()`);
        const snap=g=>tab.eval(`(()=>{const el=document.querySelector('[data-sector-rename-input="${g}"]');return {running:Boolean(clsRun&&clsRun.running),batchDone:clsRun?clsRun.batchDone:-1,batchTotal:clsRun?clsRun.batchTotal:-1,here:!!el,focus:document.activeElement===el,value:el?el.value:null,caret:el?el.selectionStart:-1,name:((schemesStore.schemes[0]||{}).sectors||[]).find(x=>x.id==='${g}')?schemesStore.schemes[0].sectors.find(x=>x.id==='${g}').name:null,renameId:sectorRenameId}})()`);
        let samples=0;for(;;){await sleep(400);samples++;const r=await snap('g_a');if(samples>=6&&r.batchDone>=2)break;if(samples>40)break}
        const mid=await snap('g_a');
        await waitClsDone(tab);await sleep(400);
        const after=await snap('g_a');
        note(`在途采样（${samples}×400ms）${JSON.stringify(mid)}｜全部跑完后 ${JSON.stringify(after)}`);
        check(typing0==='focused'&&mid.running===true&&mid.batchTotal===4&&mid.batchDone>=2&&mid.batchDone<4,`场景自检：采样时应已完成 ≥2 批且仍在跑（中途确有重渲），实得 ${JSON.stringify(mid)}`);
        check(mid.here&&mid.focus&&mid.value==='renamed half'&&mid.caret===5&&mid.name==='Alpha','分类在途时完成批次的重渲不得打断重命名：焦点、文字、光标都应还在，名字不得被提交，实得 '+JSON.stringify(mid));
        check(after.batchDone===4&&after.here&&after.focus&&after.value==='renamed half'&&after.caret===5&&after.name==='Alpha'&&after.renameId==='g_a',`分类全部跑完（4 批重渲）后重命名应原样还在、仍未提交，实得 ${JSON.stringify(after)}`);
        // 回车才提交
        await tab.eval(`(()=>{document.querySelector('[data-sector-rename-input="g_a"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 1})()`);await sleep(300);
        const done=await snap('g_a');
        note(`按回车后 ${JSON.stringify(done)}`);
        check(done.here===false&&done.name==='renamed half'&&done.renameId===null,'回车后应提交重命名并收起输入框');
        // Esc 仍能取消；失焦仍会提交（P1 既有语义不变）
        await tab.eval(P.click('[data-sector-rename="g_b"]'));await sleep(200);
        await tab.eval(`(()=>{const el=document.querySelector('[data-sector-rename-input="g_b"]');el.value='esc nope';el.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));return 1})()`);await sleep(300);
        const esc=await snap('g_b');
        note(`重命名 Beta 输入到一半按 Esc：${JSON.stringify(esc)}`);
        check(esc.here===false&&esc.focus===false&&esc.name==='Beta'&&esc.renameId===null,'Esc 应取消重命名：输入框收起、名字不变');
        await tab.eval(P.click('[data-sector-rename="g_b"]'));await sleep(200);
        await tab.eval(`(()=>{const el=document.querySelector('[data-sector-rename-input="g_b"]');el.value='Beta renamed';el.blur();return 1})()`);await sleep(300);
        const blur=await snap('g_b');
        note(`重命名 Beta 输入完点别处（失焦）：${JSON.stringify(blur)}`);
        check(blur.here===false&&blur.name==='Beta renamed'&&blur.renameId===null,'失焦应提交重命名（P1 既有语义不变）');
        noErrors(tab,'S18');
      }catch(e){check(false,'S18 执行故障：'+e.message)}finally{srv.ai.respond=null;end()}}

    // ---- S19 会话档异常旧档：加载时盘上 Key 幂等清洗（返修补证） ----
    // 「仅本会话」档的承诺是盘上 apiKey 恒空，且要对任意持久态成立：S13 走的是正常切档（盘上那把当场抹掉）；这里补的是「盘上已经是 sessionOnly:true＋非空 apiKey」的旧档／异常档——正常路径不产生，预置后看加载路径清不清。
    // 写盘次数靠「新文档脚本」包一层 Storage.prototype.setItem 记账（每次重载从零记起）；末尾做一次正向对照（正常编辑会落盘），证明记到 0 次不是记录器没生效
    if(!skip('S19')){begin('S19','会话档盘上 Key 恒空·异常旧档：预置 sessionOnly:true 却仍带非空 apiKey 的档（正常路径不产生）→重载→盘上 apiKey 当场清空并回写一次、BaseURL／Model 原样；页面仍是会话档（开关勾着、内存／输入框／生效配置全空——盘上那把不捡回内存）；钥匙带空白／纯空白／没这个字段／不是字符串等形状同样清成空串；已清空的档再重载零写盘（幂等）；记住档加载零写盘（原行为不变）');
      let recId=null;
      try{
        const LSAI='thoradar.ai.v1',n0=srv.ai.log.length;
        const onDisk=()=>tab.eval(`Object.keys(localStorage).some(k=>{const v=String(localStorage.getItem(k));return v.includes(${K})||v.includes(${K2})})`);
        const aiWrites=async()=>{const w=await tab.eval('window.__lsWrites');return Array.isArray(w)?w.filter(k=>k===LSAI).length:-1};   // 本次加载以来对 thoradar.ai.v1 的 setItem 次数；-1＝记录器不在（结果不可判读）
        const snap=model=>tab.eval(`(()=>{const k=document.querySelector('#ai-key'),c=document.querySelector('#ai-session-only'),n=document.querySelector('.ai-note[data-i18n]');let d=null;try{d=JSON.parse(localStorage.getItem('thoradar.ai.v1'))}catch(e){d={bad:1}}
          const o=d&&typeof d==='object'&&!d.bad;if(!o)return {have:false};   // 盘面只报「空不空／长几字／是不是那把」，钥匙值不进输出
          return {have:true,keyEmpty:d.apiKey==='',keyLen:String(d.apiKey===undefined||d.apiKey===null?'':d.apiKey).length,keyIsA:d.apiKey===${K},sess:d.sessionOnly===true,base:d.baseUrl===${JSON.stringify(srv.origin)},model:d.model===${JSON.stringify(model)},
            memEmpty:typeof aiSessionKey==='undefined'?null:aiSessionKey==='',effEmpty:typeof aiEffective==='function'?aiEffective().apiKey==='':null,effIsA:typeof aiEffective==='function'?aiEffective().apiKey===${K}:null,
            storeEmpty:typeof aiStore==='undefined'||!aiStore?null:aiStore.apiKey==='',boxEmpty:k?k.value==='':null,boxIsA:k?k.value===${K}:null,type:k?k.type:null,checked:c?c.checked:null,
            phKey:k?k.getAttribute('data-i18n-ph'):null,noteKey:n?n.getAttribute('data-i18n'):null}})()`);
        // ① 预置异常旧档（会话档却带着 Key）→重载：盘上当场清空，页面仍是会话档
        await tab.eval(`localStorage.clear();${LS(LSAI,{baseUrl:srv.origin,apiKey:FAKE_KEY_B,model:'probe-mock',sessionOnly:true})};1`);
        const seeded=await tab.eval(`(()=>{const d=JSON.parse(localStorage.getItem('thoradar.ai.v1'));return {sess:d.sessionOnly===true,keyLen:String(d.apiKey).length}})()`);
        await tab.goto(`${srv.origin}/index.html`);
        await tab.eval(P.view('personal'));await tab.eval(P.tab('topics'));
        const s1=await snap('probe-mock');
        note(`① 场景自检：种下的档＝sessionOnly:${seeded.sess}＋apiKey ${seeded.keyLen} 字｜重载后盘上 apiKey ${s1.keyLen} 字、sessionOnly=${s1.sess}｜内存空=${s1.memEmpty}、生效配置空=${s1.effEmpty}、输入框空=${s1.boxEmpty}、开关勾=${s1.checked}`);
        check(seeded.sess&&seeded.keyLen>0,'场景自检：预置的应是 sessionOnly:true＋非空 apiKey 的档');
        check(s1.have&&s1.keyEmpty,`异常旧档重载后盘上 apiKey 应当场清空，实得${s1.have?`非空（${s1.keyLen} 字）`:'盘上无档／坏档'}`);
        check(Boolean(s1.have&&s1.sess&&s1.base&&s1.model),'清洗只动 Key：盘上 sessionOnly／baseUrl／model 应原样');
        check(!(await onDisk()),'浏览器存储任一键值里都不得残留那把钥匙');
        check(s1.memEmpty===true&&s1.effEmpty===true&&s1.storeEmpty===true,'盘上那把不得捡回内存：内存变量／生效配置／内存档的 Key 应全空');
        check(s1.boxEmpty===true&&s1.type==='password'&&s1.checked===true,'页面应仍是会话档：开关勾着、Key 框为空且是密码框');
        check(s1.phKey==='ai.key.ph.session'&&s1.noteKey==='ai.note.session','Key 框占位语与说明行应仍是会话档的说法');
        // ①b 同一道清洗对其它形状的「会话档却不是空 Key」同样成立（承诺对任意持久态）：钥匙两侧带空白／纯空白／没有 apiKey 字段／钥匙不是字符串
        const odd=[];
        for(const [name,shape] of [
          ['钥匙两侧带空白',{baseUrl:srv.origin,apiKey:`  ${FAKE_KEY_B}  `,model:'probe-mock',sessionOnly:true}],
          ['纯空白',{baseUrl:srv.origin,apiKey:'   ',model:'probe-mock',sessionOnly:true}],
          ['没有 apiKey 字段',{baseUrl:srv.origin,model:'probe-mock',sessionOnly:true}],
          ['钥匙不是字符串',{baseUrl:srv.origin,apiKey:123456789012,model:'probe-mock',sessionOnly:true}]
        ]){
          await tab.eval(`localStorage.clear();${LS(LSAI,shape)};1`);await tab.goto(`${srv.origin}/index.html`);
          const s=await snap('probe-mock');odd.push([name,{...s,clean:!(await onDisk())}]);
        }
        note(`①b 其它形状重载后：${odd.map(([n,s])=>`${n}→盘上 apiKey ${s.have?s.keyLen:'?'} 字、${s.sess?'会话档':'非会话档'}${s.clean?'':'、存储里残留钥匙'}`).join('；')}`);
        check(odd.every(([,s])=>s.have&&s.keyEmpty&&s.sess&&s.base&&s.model&&s.clean&&s.memEmpty===true&&s.effEmpty===true&&s.storeEmpty===true&&s.checked===true&&s.boxEmpty===true),'会话档不论盘上 apiKey 是什么形状（钥匙带空白／纯空白／没这个字段／不是字符串），重载后盘上都应是空串、仍是会话档、内存与输入框全空、存储里无残留');
        // ② 已清空的会话档再重载：加载路径零写盘（幂等；也＝正常会话档加载零写盘），状态不变
        recId=(await tab.h.cdp.send('Page.addScriptToEvaluateOnNewDocument',{source:'(()=>{const o=Storage.prototype.setItem;window.__lsWrites=[];Storage.prototype.setItem=function(k,v){window.__lsWrites.push(String(k));return o.call(this,k,v)}})()'},tab.sid)).identifier;
        await tab.goto(`${srv.origin}/index.html`);
        const s2=await snap('probe-mock'),w2=await aiWrites();
        note(`② 已清空的会话档再重载：加载期写 thoradar.ai.v1 ${Math.max(w2,0)} 次｜盘上 apiKey ${s2.keyLen} 字、sessionOnly=${s2.sess}｜内存空=${s2.memEmpty}、输入框空=${s2.boxEmpty}、开关勾=${s2.checked}`);
        check(w2===0,`已清空的会话档再重载不得再写盘（幂等），实得写 ${Math.max(w2,0)} 次${w2<0?'｜写盘记录器不在，结果不可判读':''}`);
        check(Boolean(s2.have&&s2.keyEmpty&&s2.sess&&s2.base&&s2.model&&s2.memEmpty===true&&s2.effEmpty===true&&s2.boxEmpty===true&&s2.checked===true),'再重载后应仍是干净的会话档：盘上 Key 空、档位与 BaseURL／Model 不变、内存／输入框空、开关勾着');
        // ③ 记住档（原行为）：加载零写盘，Key 照旧在盘上并回填生效配置与输入框
        await tab.eval(`localStorage.clear();${LS(LSAI,{baseUrl:srv.origin,apiKey:FAKE_KEY_A,model:'probe-mock',sessionOnly:false})};1`);
        await tab.goto(`${srv.origin}/index.html`);
        await tab.eval(P.view('personal'));await tab.eval(P.tab('topics'));
        const s3=await snap('probe-mock'),w3=await aiWrites();
        note(`③ 记住档重载：加载期写 thoradar.ai.v1 ${Math.max(w3,0)} 次｜盘上钥匙仍是记住档那把=${s3.keyIsA}｜生效配置带钥匙=${s3.effIsA}、输入框回填=${s3.boxIsA}、开关勾=${s3.checked}`);
        check(w3===0&&Boolean(s3.have&&s3.keyIsA&&s3.base&&s3.model&&s3.effIsA===true&&s3.boxIsA===true&&s3.type==='password'&&s3.checked===false&&s3.memEmpty===true),`记住档加载应零写盘、Key 照旧在盘上并回填生效配置与输入框、开关未勾，实得写 ${Math.max(w3,0)} 次`);
        // ④ 记录器自检（正向对照）：正常改一次 Model＝防抖后落盘——上面的「0 次」才作数
        await tab.eval(P.type('#ai-model','probe-mock2'));await sleep(600);
        const w4=await aiWrites(),s4=await snap('probe-mock2');
        note(`④ 记录器自检：改一次 Model 后共写 thoradar.ai.v1 ${Math.max(w4,0)} 次｜盘上 model ${s4.model?'已更新':'未更新'}、钥匙仍是记住档那把=${s4.keyIsA}`);
        check(w4>=1&&Boolean(s4.have&&s4.model&&s4.keyIsA),'场景自检：写盘记录器应记下正常编辑触发的落盘（记不到＝上面的「零写盘」不作数）');
        // ⑤ 全程零外发零回显
        const bodyText=await tab.eval('document.body.innerText'),dialogs=tab.dialogs.map(d=>d.message);
        check(srv.ai.log.length===n0,`本场景不得发任何 AI 请求，实发 ${srv.ai.log.length-n0} 次`);
        check(!hasKey(tab.consoleTexts,FAKE_KEY_A)&&!hasKey(tab.consoleTexts,FAKE_KEY_B)&&!hasKey(tab.errors,FAKE_KEY_A)&&!hasKey(tab.errors,FAKE_KEY_B)&&!hasKey(dialogs,FAKE_KEY_A)&&!hasKey(dialogs,FAKE_KEY_B)&&!bodyText.includes(FAKE_KEY_A)&&!bodyText.includes(FAKE_KEY_B),'两把假钥匙不得进控制台／异常／对话框／页面可见文本');
        noErrors(tab,'S19');
      }catch(e){check(false,'S19 执行故障：'+e.message)}finally{if(recId)await tab.h.cdp.send('Page.removeScriptToEvaluateOnNewDocument',{identifier:recId},tab.sid).catch(()=>{});end()}}
  }finally{
    try{cdp&&cdp.close()}catch(e){}
    const left=await browser.stop();
    srv.server.close();
    let cleaned=true;
    try{rmSync(SCRATCH_ROOT,{recursive:true,force:true})}catch(e){cleaned=false;console.log('     cleanup | 临时件未能清空：'+e.message)}   // 连外层目录一起清（原先只清 harness 子目录，外层空壳会一个个留在临时目录里）
    console.log(`     cleanup | 临时目录 ${SCRATCH_ROOT} ${cleaned?'已清空':'未清空'}${left?`｜仍有 ${left} 个带本探针 profile 标记的浏览器进程存活`:''}`);
  }
  process.exit(L.finish(`AICLS PROBE [${LABEL}]`)?1:0);
}
const pmidQuote=pmid=>JSON.stringify(pmid).slice(1,-1);
main().catch(e=>{console.log('探针崩溃：'+(e&&e.stack||e));process.exit(2)});
