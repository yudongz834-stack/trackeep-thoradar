#!/usr/bin/env node
// T1125-AICLS 探针共用件（tests/aicls/lib.mjs）——供 aicls_probe.mjs / aicls_mutants.mjs / aicls_regress.mjs / aicls_shots.mjs 四件共用，本身不单独运行
// 性质：施工方自建探针＝自证手段，不构成验收结论（验收样本与验收权归独立复核席）。
// 零依赖：Node ≥22（自带 WebSocket/fetch/http）＋本机 Chrome 或 Edge（CDP 驱动、独立 profile）。
// 零 LLM、零真钥匙：AI 请求一律打到本探针自起的本机假应答服务（页面的 BaseURL 指向它）；NCBI 接口由浏览器网络层拦截应答；
//   浏览器侧另用 host-resolver-rules 封死外网 DNS。临时件只落系统临时目录、跑完即清；进程清理只按 PID。
// 钥匙纪律：探针只用写死的假钥匙占位串；输出里只报「带钥匙＝对／错／缺」，任何钥匙值都不进日志。
import {spawn,execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {readFileSync,mkdirSync,rmSync,existsSync} from 'node:fs';
import {dirname,extname,join,normalize,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import net from 'node:net';
import {createHash} from 'node:crypto';

export const HERE=dirname(fileURLToPath(import.meta.url));   // tests/aicls
export const ROOT=normalize(join(HERE,'..','..'));           // 仓根
export const sleep=ms=>new Promise(r=>setTimeout(r,ms));
export const sha256=data=>createHash('sha256').update(data).digest('hex');
export const norm=s=>String(s).replace(/\r\n/g,'\n');        // 行尾统一成 LF 再比（工作树件是 CRLF，仓内 blob 是 LF）
export const argOf=(argv,k,d)=>{const i=argv.indexOf(k);return i>=0&&argv[i+1]&&!argv[i+1].startsWith('--')?argv[i+1]:d};
export const gitRead=(args,cwd=ROOT)=>execFileSync('git',['-c','core.quotepath=false',...args],{cwd,maxBuffer:64*1024*1024}).toString('utf8');

// ---------- 结果账：begin／check／note／end；退出码 0＝全绿、1＝有红 ----------
export function ledger(){
  const results=[];let cur=null;
  const api={
    results,
    begin(id,name){cur={id,name,fails:[],notes:[]}},
    check(cond,msg){if(cur&&!cond)cur.fails.push(msg);return Boolean(cond)},
    note(msg){if(cur)cur.notes.push(msg)},
    skip(id,name,why){results.push({id,name,fails:[],notes:[why],ok:true,skipped:true});console.log(`SKIP ${id} ${name}\n     · ${why}`)},
    end(){
      const r=cur;cur=null;r.ok=r.fails.length===0;results.push(r);
      console.log(`${r.ok?'PASS':'FAIL'} ${r.id} ${r.name}`);
      r.notes.forEach(n=>console.log(`     · ${n}`));r.fails.forEach(f=>console.log(`     ✗ ${f}`));
      return r.ok;
    },
    finish(label){
      const bad=results.filter(r=>!r.ok),skipped=results.filter(r=>r.skipped).length;
      console.log(`\n==== ${label} SUMMARY ${results.length-bad.length-skipped} PASS / ${bad.length} FAIL / ${skipped} SKIP：${results.map(r=>r.id+(r.skipped?' ∅':r.ok?' ✓':' ✗')).join('  ')} ====`);
      return bad.length;
    }
  };
  return api;
}

// ---------- 站内服务：/index.html＝受测件，/baseline.html＝基线件，/v1/messages＝假 AI，其余只读映射仓根 ----------
export const FAKE_KEY_A='PROBE-FAKE-KEY-A-0000',FAKE_KEY_B='PROBE-FAKE-KEY-B-0000';   // 假钥匙占位串（记住档用 A、会话档用 B）——不是任何真钥匙
export function aiText(rec,text){return {status:200,text,delay:0}}
export async function startServer({target,baseline=null}){
  const mime={'.html':'text/html; charset=utf-8','.json':'application/json; charset=utf-8','.js':'text/javascript; charset=utf-8','.xml':'application/xml','.ico':'image/x-icon','.md':'text/markdown; charset=utf-8'};
  const ai={log:[],respond:null,expectKey:FAKE_KEY_A};   // respond(rec)→{status,text,delay}|Promise<…>；为空＝默认应答（分类＝全归第一个阵地；深评＝固定正文）
  ai.default=rec=>rec.kind==='cls'
    ?aiText(rec,JSON.stringify(rec.payload.papers.map(p=>({pmid:p.pmid,sec:rec.payload.sectors[0].id}))))   // 分类：全归 order 里第一个阵地
    :rec.kind==='deep'
    ?aiText(rec,`【研究问题】\n探针假深评正文 PMID ${rec.payload.pmid}。\n【设计与样本】\n摘要未报告。\n【主要发现】\n占位。`)
    :aiText(rec,'OK');   // 其余（连通测试／主题判官的纯文本消息）：回一句短话
  const server=createServer((req,res)=>{
    const u=new URL(req.url,'http://x');
    if(u.pathname==='/v1/messages'){   // 假 AI（Anthropic Messages 形制）：解析请求体→记账→交场景应答器
      let body='';
      req.on('data',c=>{body+=c});
      req.on('end',async()=>{
        let reqBody=null,payload=null;
        try{reqBody=JSON.parse(body);payload=JSON.parse(reqBody.messages[0].content)}catch(e){}
        const got=req.headers['x-api-key'];
        const rec={n:ai.log.length+1,t:Date.now(),done:0,keyState:got===undefined?'缺':ai.expectKey&&got===ai.expectKey?'对':'错',keyLen:got?String(got).length:0,
          model:reqBody&&reqBody.model,maxTokens:reqBody&&reqBody.max_tokens,anthropic:req.headers['anthropic-version']||'',
          user:reqBody&&reqBody.messages&&reqBody.messages[0]&&reqBody.messages[0].content,kind:payload&&Array.isArray(payload.sectors)?'cls':payload&&'pmid' in payload?'deep':'judge',payload,status:200,hung:false};
        ai.log.push(rec);
        try{
          const out=await (ai.respond||ai.default)(rec);
          if(out.delay)await sleep(out.delay);
          if(res.writableEnded){rec.status='client-gone';return}
          rec.status=out.status;
          res.writeHead(out.status,{'content-type':'application/json','cache-control':'no-store'});
          res.end(JSON.stringify(out.status===200?{id:'msg_probe',type:'message',role:'assistant',model:rec.model,stop_reason:'end_turn',content:[{type:'text',text:out.text}]}:{type:'error',error:{type:'api_error',message:out.text||'probe error'}}));
        }catch(e){rec.status='probe-fault:'+e.message;try{res.writeHead(500);res.end('{}')}catch(e2){}}
        rec.done=Date.now();
      });
      return;
    }
    let file=null,type=null;
    if(u.pathname==='/index.html'){file=target;type='text/html; charset=utf-8'}
    else if(u.pathname==='/baseline.html'&&baseline){file=baseline;type='text/html; charset=utf-8'}
    else{const rel=normalize(decodeURIComponent(u.pathname)).replace(/^[\\/]+/,'');file=join(ROOT,rel);if(!file.startsWith(ROOT))file=null}
    if(!file||!existsSync(file)){res.writeHead(404);res.end('not found');return}
    res.writeHead(200,{'content-type':type||mime[extname(file)]||'application/octet-stream','cache-control':'no-store'});
    res.end(readFileSync(file));
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  return {server,origin:`http://127.0.0.1:${server.address().port}`,ai};
}

// ---------- CDP 极简客户端 ----------
export async function connect(wsUrl){
  const ws=new WebSocket(wsUrl);
  await new Promise((res,rej)=>{ws.addEventListener('open',res,{once:true});ws.addEventListener('error',()=>rej(new Error('DevTools WebSocket 连不上')),{once:true})});
  let seq=0;const pending=new Map(),listeners=new Map();
  ws.addEventListener('message',ev=>{
    const msg=JSON.parse(ev.data);
    if(msg.id!=null){const p=pending.get(msg.id);if(!p)return;pending.delete(msg.id);msg.error?p.rej(new Error(`${p.method}: ${JSON.stringify(msg.error)}`)):p.res(msg.result)}
    else (listeners.get(msg.method)||[]).forEach(fn=>fn(msg.params,msg.sessionId));
  });
  return {
    send(method,params={},sessionId){const id=++seq;return new Promise((res,rej)=>{   // 每条命令 90s 兜底：CDP 不回话不许把探针挂死
      const timer=setTimeout(()=>{if(pending.delete(id))rej(new Error(`CDP 超时 90s：${method}`))},90000);
      pending.set(id,{res:v=>{clearTimeout(timer);res(v)},rej:e=>{clearTimeout(timer);rej(e)}});
      ws.send(JSON.stringify({id,method,params,sessionId}));
    })},
    on(method,fn){if(!listeners.has(method))listeners.set(method,[]);listeners.get(method).push(fn)},
    close(){ws.close()}
  };
}

// ---------- 页签：求值／等待／eutils 拦截／对话框自动应答／控制台与异常记账 ----------
export const EUTILS='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/';
export class Tab{
  constructor(h,name){this.h=h;this.name=name;this.onload=null;this.log=[];this.errors=[];this.consoleTexts=[];this.dialogs=[];this.responder=null;this.hooks={}}
  async open(url){
    const {targetId}=await this.h.cdp.send('Target.createTarget',{url:'about:blank'});
    const {sessionId}=await this.h.cdp.send('Target.attachToTarget',{targetId,flatten:true});
    this.targetId=targetId;this.sid=sessionId;this.h.tabs.set(sessionId,this);
    await this.h.cdp.send('Page.enable',{},sessionId);await this.h.cdp.send('Runtime.enable',{},sessionId);
    await this.h.cdp.send('Fetch.enable',{patterns:[{urlPattern:EUTILS+'*',requestStage:'Request'}]},sessionId);   // eutils 全拦，不打真网
    if(this.preScript){const r=await this.h.cdp.send('Page.addScriptToEvaluateOnNewDocument',{source:this.preScript},sessionId);this.preScriptId=r.identifier}   // 可选：页面脚本跑之前先执行（如拆掉 crypto.subtle 模拟 file:// 降级）
    await this.goto(url);
  }
  async close(){try{if(this.preScriptId)await this.h.cdp.send('Page.removeScriptToEvaluateOnNewDocument',{identifier:this.preScriptId},this.sid)}catch(e){}try{await this.h.cdp.send('Target.closeTarget',{targetId:this.targetId})}catch(e){}this.h.tabs.delete(this.sid)}
  async goto(url){
    const loaded=new Promise(r=>{this.onload=r});
    await this.h.cdp.send('Page.navigate',{url},this.sid);
    await Promise.race([loaded,sleep(30000).then(()=>{throw new Error(`页面 30s 未触发 load：${url}`)})]);
    this.onload=null;
    await this.waitFor('document.body&&document.body.dataset.protoReady==="true"',20000,'protoReady');
  }
  async eval(expr){
    const r=await this.h.cdp.send('Runtime.evaluate',{expression:expr,awaitPromise:true,returnByValue:true},this.sid);
    if(r.exceptionDetails)throw new Error(`页面求值异常：${(r.exceptionDetails.exception&&r.exceptionDetails.exception.description)||r.exceptionDetails.text}\n  expr: ${expr.slice(0,200)}`);
    return r.result.value;
  }
  async waitFor(expr,timeout=10000,label=expr){
    const t0=Date.now();
    for(;;){
      let v=false;try{v=Boolean(await this.eval(expr))}catch(e){v=false}
      if(v)return Date.now()-t0;
      if(Date.now()-t0>timeout)throw new Error(`等待超时 ${timeout}ms：${label}`);
      await sleep(100);
    }
  }
  async paused(p){   // eutils 拦截：记账→按场景应答（默认压 200ms 让时间线可分辨）
    const u=new URL(p.request.url),rec={t:Date.now(),kind:u.pathname.split('/').pop().replace('.fcgi',''),db:u.searchParams.get('db')||'',url:p.request.url,code:null};
    this.log.push(rec);
    await sleep(200);
    try{await this.responder(p,rec,this)}catch(e){rec.code='mock-error:'+e.message}
    rec.done=Date.now();
  }
  mark(){return this.log.length}
  since(mark){return this.log.slice(mark)}
}
export function wire(h){   // 把 CDP 事件接到页签上
  h.cdp.on('Page.loadEventFired',(_p,sid)=>{const t=h.tabs.get(sid);if(t&&t.onload){const f=t.onload;t.onload=null;f()}});
  h.cdp.on('Fetch.requestPaused',(p,sid)=>{const t=h.tabs.get(sid);if(t)t.paused(p).catch(e=>console.log('mock fault',e.message))});
  const push=(arr,txt)=>arr.push(String(txt).slice(0,600));
  h.cdp.on('Runtime.exceptionThrown',(p,sid)=>{const t=h.tabs.get(sid);if(t)push(t.errors,(p.exceptionDetails&&(p.exceptionDetails.exception?p.exceptionDetails.exception.description:p.exceptionDetails.text))||'exception')});
  h.cdp.on('Runtime.consoleAPICalled',(p,sid)=>{   // 页面自己打的一切控制台文本都记账（含 info／warn／log）：供「钥匙零日志」断言逐字搜
    const t=h.tabs.get(sid);if(!t)return;
    const text=(p.args||[]).map(a=>a.value!==undefined?String(a.value):(a.description||a.type||'')).join(' ');
    push(t.consoleTexts,text);
    if(p.type==='error')push(t.errors,'console.error: '+text);
  });
  h.cdp.on('Page.javascriptDialogOpening',(p,sid)=>{   // 页面弹的 confirm／alert／prompt：记下原文并点「确定」，不让页面卡住
    const t=h.tabs.get(sid);if(t)t.dialogs.push({type:p.type,message:p.message,url:p.url});
    h.cdp.send('Page.handleJavaScriptDialog',{accept:true},sid).catch(()=>{});
  });
}
export const eutilsOK=async(p,rec,tab)=>{   // 主题检索用到的两种 NCBI 应答：esearch 回 2 个 PMID，efetch 回对应题录（签名同 Tab.responder：(p,rec,tab)）
  const u=new URL(rec.url),body=rec.kind==='esearch'
    ?JSON.stringify({esearchresult:{count:'2',retmax:'2',retstart:'0',idlist:['80000001','80000002']}})
    :`<?xml version="1.0"?><PubmedArticleSet>${['80000001','80000002'].map(id=>`<PubmedArticle><MedlineCitation><PMID Version="1">${id}</PMID><Article><Journal><Title>Probe journal</Title><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue></Journal><ArticleTitle>Probe topic article ${id}</ArticleTitle><Abstract><AbstractText>Probe abstract ${id}.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>`).join('')}</PubmedArticleSet>`;
  await tab.h.cdp.send('Fetch.fulfillRequest',{requestId:p.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:rec.kind==='esearch'?'application/json':'application/xml'},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from(body).toString('base64')},tab.sid);
  rec.code=200;
};

// ---------- 浏览器：起／停（清理只按 PID；命令行须带本探针的 profile 路径才认） ----------
export function chromeArgs(port,profile){return ['--headless=new',`--remote-debugging-port=${port}`,`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--disable-extensions','--disable-sync','--disable-background-networking','--disable-component-update','--disable-default-apps','--disable-client-side-phishing-detection','--disable-domain-reliability','--metrics-recording-only','--no-pings','--mute-audio','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding','--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1','--window-size=1440,900','about:blank']}
export async function freePort(){return new Promise((res,rej)=>{const s=net.createServer();s.once('error',rej);s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>res(p))})})}
async function waitDevtools(port){const t0=Date.now();for(;;){try{const r=await fetch(`http://127.0.0.1:${port}/json/version`);if(r.ok)return await r.json()}catch(e){}if(Date.now()-t0>20000)throw new Error('浏览器 DevTools 端口 20s 未起');await sleep(250)}}
const ps=cmd=>{try{return execFileSync('pwsh',['-NoProfile','-Command',cmd],{encoding:'utf8'})}catch(e){return ''}};
export async function launch({chrome,profile,port,label}){
  const tag=profile.replace(/\//g,'\\');   // 进程清理认人用：命令行里须含这段完整路径（通配符转义）
  const escTag=tag.replace(/[[\]*?]/g,ch=>'`'+ch);
  const probePids=()=>ps(`Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(chrome|msedge)' -and $_.CommandLine -like '*${escTag}*' } | Select-Object -ExpandProperty ProcessId`).split(/\r?\n/).map(x=>x.trim()).filter(x=>/^\d+$/.test(x));
  const proc=spawn(chrome,chromeArgs(port,profile),{stdio:'ignore'});
  const ver=await waitDevtools(port);
  const stop=async()=>{   // 先按 PID 结束主进程，再逐 PID 复查残留（只认命令行带本 profile 的），逐 PID 结束后再复查一次并贴原始结果
    const before=probePids();
    if(proc.exitCode===null&&proc.signalCode===null){proc.kill();const t0=Date.now();while(proc.exitCode===null&&proc.signalCode===null&&Date.now()-t0<8000)await sleep(100)}
    await sleep(1200);
    const alive=probePids(),killed=[];
    for(const pid of alive)ps(`Stop-Process -Id ${pid} -Force -ErrorAction SilentlyContinue`),killed.push(pid);
    await sleep(500);
    const still=probePids();
    console.log(`     cleanup | browser pid=${proc.pid} exitCode=${proc.exitCode} signalCode=${proc.signalCode} | 带 profile 标记的进程：收尾前=${before.join(',')||'无'} | 主进程结束后残留=${alive.join(',')||'无'} | 逐 PID 结束=${killed.join(',')||'无'} | 复查仍存活=${still.join(',')||'无'}`);
    return still.length;
  };
  return {proc,ver,stop};
}

// ---------- 页面侧小工具（经 evaluate 注入） ----------
export const P={
  view:v=>`(()=>{const b=document.querySelector('[data-proto-view="${v}"]');if(!b)return 'MISSING';b.click();return 'ok'})()`,
  tab:n=>`(()=>{const b=document.querySelector('[data-proto-personal-tab="${n}"]');if(!b)return 'MISSING';b.click();return 'ok'})()`,
  click:s=>`(()=>{const el=document.querySelector(${JSON.stringify(s)});if(!el)return 'MISSING:'+${JSON.stringify(s)};el.click();return 'ok'})()`,
  type:(s,v)=>`(()=>{const el=document.querySelector(${JSON.stringify(s)});if(!el)return 'MISSING:'+${JSON.stringify(s)};el.focus();el.value=${JSON.stringify(v)};el.dispatchEvent(new Event('input',{bubbles:true}));return 'ok'})()`,
  check:(s,on)=>`(()=>{const el=document.querySelector(${JSON.stringify(s)});if(!el)return 'MISSING:'+${JSON.stringify(s)};el.checked=${on?'true':'false'};el.dispatchEvent(new Event('change',{bubbles:true}));return 'ok'})()`,
  key:(s,k)=>`(()=>{const el=document.querySelector(${JSON.stringify(s)});if(!el)return 'MISSING:'+${JSON.stringify(s)};el.dispatchEvent(new KeyboardEvent('keydown',{key:${JSON.stringify(k)},bubbles:true,cancelable:true}));return 'ok'})()`,
};

// ---------- 静态材料（统一 LF）：区块提取／新增行／内联脚本语法／I18N 键集 ----------
export const between=(x,a,b)=>{const i=x.indexOf(a);const j=i>=0?x.indexOf(b,i):-1;return j>=0?x.slice(i,j+b.length):null};
export const block=(text,marker)=>{const i=text.indexOf(marker);if(i<0)return null;const j=text.indexOf('\n}\n',i);return j>=0?text.slice(i,j+3):null};
export const lineOf=(text,marker)=>text.split('\n').filter(l=>l.includes(marker)).join('\n');
export function inlineScripts(html){const out=[];for(const m of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))out.push(m[1]);return out}
export function readI18n(html){   // 从内联脚本里取 I18N 双表：返回 {zh:Map<键,值>,en:Map<键,值>}（值只认单／双引号字符串字面量）；取不到＝null（交给调用方报红）
  const src=inlineScripts(html).join('\n');
  const m=/const I18N=\{\s*zh:\{([\s\S]*?)\n\},\s*en:\{([\s\S]*?)\n\}\s*\n\};/.exec(src);
  if(!m)return null;
  const entry=body=>new Map([...body.matchAll(/(?:^|[,{\n])\s*'([^']+)'\s*:\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")/g)].map(x=>[x[1],x[2]!==undefined?x[2]:x[3]]));
  const keyCount=body=>[...body.matchAll(/(?:^|[,{\n])\s*'([^']+)'\s*:/g)].length;
  const zh=entry(m[1]),en=entry(m[2]);
  return {zh,en,literal:{zh:zh.size===keyCount(m[1]),en:en.size===keyCount(m[2])}};
}
export {readFileSync,mkdirSync,rmSync,existsSync,join,resolve,normalize,dirname,tmpdir};
