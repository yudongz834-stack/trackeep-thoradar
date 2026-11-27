#!/usr/bin/env node
// T1125-POOLUP 探针共用件。复用单A的零依赖 CDP harness；本件不单独运行。
// 零真 Key／零真 LLM；NCBI 全部 CDP mock，浏览器 host-resolver-rules 封外网。假 Key 若场景需要，只用 fake-key-poolup（非 sk- 形制）。
export * from '../aicls/lib.mjs';
export const EXT_KEY='thoradar.journals.ext.v1',CACHE_KEY='thoradar.poolcache.v1',MIX_KEY='thoradar.poolview.v1';
export const JOURNALS=[{k:'PROBE EXT A',nlm:'9900001',title:'Probe External Journal A',isoabbr:'Probe Ext A',issn:'1234-5678',addedAt:1764200000000},{k:'PROBE EXT B',nlm:'9900002',title:'Probe External Journal B',isoabbr:'Probe Ext B',issn:'8765-4321',addedAt:1764200000001}];
export const dayShift=(iso,n)=>new Date(Date.parse(iso+'T00:00:00Z')+n*86400000).toISOString().slice(0,10);
export const item=(pmid,title,day,extra={})=>({pmid:String(pmid),title,journal:'Probe External Journal',date:String(day||'').slice(0,4),day:String(day||''),abstract:'Probe off-pool abstract '+title, ...extra});
export function cacheFor(anchor,officialPmid){
  const at=Date.now(),until=at+86400000;
  return {v:1,byNlm:{'9900001':{at,until,total:5,pmids:['88000001','88000002','88000003',officialPmid],items:[item('88000001','Pool alpha anchor unique',anchor),item('88000002','Pool beta prior day',dayShift(anchor,-1)),item('88000003','Pool legacy year only','',{date:anchor.slice(0,4)}),item(officialPmid,'Pool official duplicate',anchor)]},'9900002':{at,until,total:2,pmids:['88000001','88000004'],items:[item('88000001','Pool cross-journal duplicate',anchor),item('88000004','Pool seven days old',dayShift(anchor,-7))]}}};
}
export const LS=(k,v)=>`localStorage.setItem(${JSON.stringify(k)},${JSON.stringify(JSON.stringify(v))})`;
export function cacheHighYield(anchor,n=17){   // FIX-1 场景料：同一本池外刊在锚点日高产 n 条（GLM B2-1：17 条池外把阅读 top12 挤空）
  const at=Date.now(),until=at+86400000,ids=Array.from({length:n},(_,i)=>String(88100001+i));
  return {v:1,byNlm:{'9900001':{at,until,total:n,pmids:ids,items:ids.map((id,i)=>item(id,`Pool high yield ${String(i+1).padStart(2,'0')}`,anchor))}}};
}
export function cacheLocalWindow(anchor,today){   // FIX-2 场景料：本地当天／锚点日／本地明天（未来）／仅年份旧缓存 各一条
  const at=Date.now(),until=at+86400000;
  const rows=[item('88200001','Pool local today',today),item('88200002','Pool anchor day',anchor),item('88200003','Pool future local day',dayShift(today,1)),item('88200004','Pool legacy year only','',{date:today.slice(0,4)})];
  if(today!==anchor&&dayShift(today,-1)!==anchor)rows.push(item('88200005','Pool between anchor and today',dayShift(today,-1)));   // 锚点与本地当天之间还有日子时才造，免得与锚点日条重复语义
  return {v:1,byNlm:{'9900001':{at,until,total:rows.length,pmids:rows.map(r=>r.pmid),items:rows}}};
}
export const XML_MULTI_DATES=(id,{entrez,article,journal})=>`<PubmedArticle><MedlineCitation><PMID Version="1">${id}</PMID><Article><Journal><Title>Probe External Journal A</Title><JournalIssue><PubDate>${journal}</PubDate></JournalIssue></Journal><ArticleTitle>Multi date ${id}</ArticleTitle><Abstract><AbstractText>Mock abstract ${id}</AbstractText></Abstract>${article?`<ArticleDate>${article}</ArticleDate>`:''}</Article></MedlineCitation><PubmedData><History>${entrez?`<PubMedPubDate PubStatus="entrez">${entrez}</PubMedPubDate>`:''}</History></PubmedData></PubmedArticle>`;
export const YMD=iso=>{const [y,m,d]=iso.split('-').map(Number);return `<Year>${y}</Year><Month>${m}</Month><Day>${d}</Day>`};
export async function seedFresh(tab,origin,{days=1,mix=null,cache=true,extra=[]}={}){
  const facts=await tab.eval(`({anchor:ANCHOR,officialPmid:String(PAPERS[0].pmid),papers:JSON.stringify(PAPERS),site:JSON.stringify(SITE_DATA)})`);
  const seeds=[LS(EXT_KEY,{v:1,journals:JOURNALS}),LS('thoradar.view.v1',{v:1,days,tiers:['S','A','B','C','D'],jcatFolded:['8'],gsecFolded:[]}),...extra];
  if(cache)seeds.push(LS(CACHE_KEY,cacheFor(facts.anchor,facts.officialPmid)));
  if(mix!==null)seeds.push(LS(MIX_KEY,{v:1,mix}));
  await tab.eval(`localStorage.clear();sessionStorage.clear();${seeds.join(';')};1`);
  await tab.goto(`${origin}/index.html`);
  return facts;
}
export const POOL_IDS=`personalFiltered().filter(p=>p.pool_ext).map(p=>p.pmid)`;
export const QUEUE_POOL=`[...document.querySelectorAll('#queue-list [data-select^="pool_"]')].map(e=>e.dataset.select)`;
export const XML_ARTICLE=(id,title,day)=>{const [y,m,d]=day.split('-');return `<PubmedArticle><MedlineCitation><PMID Version="1">${id}</PMID><Article><Journal><Title>Probe External Journal A</Title><JournalIssue><PubDate><Year>${y}</Year><Month>${m}</Month><Day>${d}</Day></PubDate></JournalIssue></Journal><ArticleTitle>${title}</ArticleTitle><Abstract><AbstractText>Mock abstract ${id}</AbstractText></Abstract></Article></MedlineCitation><PubmedData><History><PubMedPubDate PubStatus="entrez"><Year>${y}</Year><Month>${m}</Month><Day>${d}</Day></PubMedPubDate></History></PubmedData></PubmedArticle>`};
export const fulfill=async(tab,p,rec,{status=200,type='application/json',text='{}'}={})=>{await tab.h.cdp.send('Fetch.fulfillRequest',{requestId:p.requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:type},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from(text).toString('base64')},tab.sid);rec.code=status};
