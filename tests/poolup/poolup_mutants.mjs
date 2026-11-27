#!/usr/bin/env node
// T1125-POOLUP 变异红证。变异件只落系统临时目录；每个守卫删掉/改坏后对应场景须红。
// 用法：node tests/poolup/poolup_mutants.mjs [--target index.html] [--base 06d08e8] [--jobs 3] [--only M01,M02] [--out deliver/evidence/mutants] [--keep]
import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {ROOT,norm,argOf,sha256} from './lib.mjs';
const argv=process.argv.slice(2),TARGET=resolve(ROOT,argOf(argv,'--target',join(ROOT,'index.html'))),BASE=argOf(argv,'--base','06d08e8'),LABEL=argOf(argv,'--label','run');
const JOBS=Math.max(1,Number(argOf(argv,'--jobs','3'))||3),KEEP=argv.includes('--keep'),ONLY=argOf(argv,'--only','').split(',').map(s=>s.trim()).filter(Boolean),OUTDIR=argOf(argv,'--out','');
const SCRATCH=resolve(join(tmpdir(),`thoradar-t1125-poolup-mutants-${LABEL}`)),PROBE=join(ROOT,'tests','poolup','poolup_probe.mjs');
const MUTANTS=[
 {id:'M01',what:'默认混排被关掉',scene:'S02',find:'let poolMix=loadPoolMix();',repl:'let poolMix=false;'},
 {id:'M02',what:'PMID 官方/跨刊去重被拆',scene:'S02',find:'if(!pmid||seen.has(pmid))return;',repl:'if(!pmid)return;'},
 {id:'M03',what:'池外徽章不再输出',scene:'S02',find:'function poolBadge(p,long=false){return p&&p.pool_ext?',repl:'function poolBadge(p,long=false){return "";return p&&p.pool_ext?'},
 {id:'M04',what:'开关状态不落盘',scene:'S02',find:'poolMix=event.target.checked===true;persistPoolMix();render()',repl:'poolMix=event.target.checked===true;render()'},
 {id:'M05',what:'池外不参与时间窗',scene:'S04',find:'if(!poolInWindow(p)||state.quick!==',repl:'if(state.quick!=='},
 {id:'M06',what:'错误地让池外受官方档位筛选',scene:'S03',find:'if(!poolInWindow(p)||state.quick!==',repl:'if(!poolInWindow(p)||!tierOk(p)||state.quick!=='},
 {id:'M07',what:'池外检索过滤被拆',scene:'S03',find:'return hay.includes(state.query.trim().toLowerCase());',repl:'return true;'},
 {id:'M08',what:'显式刷新成功不重渲个人队列',scene:'S05',find:'if(poolView===view){renderPoolPanel();render()}',repl:'if(poolView===view){renderPoolPanel()}'},
 {id:'M09',what:'24h 缓存失效（每次打开都重拉）',scene:'S05',find:'if(!poolView.fresh)refreshPool();',repl:'refreshPool();'},
 {id:'M10',what:'拉取失败清空内存旧缓存',scene:'S06',find:'if(!view.stopped)view.failed=e&&e.message?e.message:String(e);',repl:'if(!view.stopped){view.failed=e&&e.message?e.message:String(e);if(poolCache.byNlm[view.nlm])poolCache.byNlm[view.nlm].items=[];}'},
 {id:'M11',what:'efetch 不解析精确入 PubMed 日',scene:'S05',find:'return parsePubmedXML(await res.text(),poolDay);',repl:'return parsePubmedXML(await res.text(),false);'},
 {id:'M12',what:'仅年份旧缓存被伪填成锚点日',scene:'S04',find:"const day=/^\\d{4}-\\d{2}-\\d{2}$/.test(String(it.day||''))?String(it.day):'';",repl:"const day=/^\\d{4}-\\d{2}-\\d{2}$/.test(String(it.day||''))?String(it.day):ANCHOR;"},
 {id:'M13',what:'派生层回写官方 PAPERS',scene:'S02',find:'  return out;\n}\nfunction poolStale',repl:'  PAPERS.push(...out);\n  return out;\n}\nfunction poolStale'},
 {id:'M14',what:'阵地筛选不再排除池外',scene:'S03',find:'||state.jcat||state.gsec||myJournalsFilterKeys()',repl:'||myJournalsFilterKeys()'},
 {id:'M15',what:'官方 windowPapers 不再按时间窗过滤',scene:'S01',find:'const windowPapers=()=>PAPERS.filter(inWindow);',repl:'const windowPapers=()=>PAPERS;'},
 {id:'M16',what:'概览标题不转义（缓存 XSS 穿透）',scene:'S08',find:'<span class="queue-text"><strong>${esc(p.title_zh||p.title_en||\'—\')}</strong>',repl:'<span class="queue-text"><strong>${p.title_zh||p.title_en||\'—\'}</strong>'},
 {id:'M17',what:'池外提示占用 AI 设置专属 ai-note 语义类',scene:'S02',find:'<p class="ai-help" data-i18n="poolup.hint">',repl:'<p class="ai-note" data-i18n="poolup.hint">'},
 {id:'M18',what:'有池外时仍伪称按评分排序',scene:'S02',find:'if(title)title.textContent=hasPool?t(\'poolup.sorted\'):t(\'queue.title1\');',repl:'if(title)title.textContent=t(\'queue.title1\');'},
 // ===== FIX-4：GLM（cc-glm／T1125-XREV-B）自备 15 只原样并入，锚点随 FIX-1 改动同步（N10）。原表 D:/claude-tmp/T1125-xrev-b/xrev_mut.mjs；当时 12 只存活＝本卷漏守点
 {id:'N01',what:'合并时给官方论文对象原地加字段（派生层写官方对象）',scene:'S02',find:'  const all=official.concat(pool);',repl:'  official.forEach(p=>{p.pool_ext=p.pool_ext||false});\n  const all=official.concat(pool);'},
 {id:'N02',what:'阅读卡不带池外徽章（阵地格回落官方标签）',scene:'S02',find:'${p.pool_ext?poolBadge(p):esc(jcatLabel(jcatOf(p)))}',repl:'${esc(jcatLabel(jcatOf(p)))}'},
 {id:'N03',what:'详情卡阵地格对池外显示官方「待定」',scene:'S02',find:"esc(p.pool_ext?t('poolup.uncategorized'):jcatLabel(jcatOf(p)))",repl:'esc(jcatLabel(jcatOf(p)))'},
 {id:'N04',what:'设计图例把池外条算进去',scene:'S02',find:'renderDesignLegend(officialList);',repl:'renderDesignLegend(list);'},
 {id:'N05',what:'雷达中心信号数把池外条算进去',scene:'S02',find:"$('#hub-count').textContent=list.length;",repl:"$('#hub-count').textContent=personalFiltered().length;"},
 {id:'N06',what:'已读栏分母不含池外',scene:'S02',find:'const readUniverse=PAPERS.concat(poolMix?poolPapersDerived():[]),',repl:'const readUniverse=PAPERS,'},
 {id:'N07',what:'列表计数分母不含池外',scene:'S02',find:'function personalPaperTotal(){return PAPERS.length+(poolMix?poolPapersDerived().length:0)}',repl:'function personalPaperTotal(){return PAPERS.length}'},
 {id:'N08',what:'键盘「下一／上一信号」跳过池外',scene:'S02',find:'  const list=personalFiltered();if(!list.length)return;',repl:'  const list=filtered();if(!list.length)return;'},
 {id:'N09',what:'刊源图例不含池外刊',scene:'S03',find:'const journals=journalUniverse(tierBase.concat(poolForJournals));',repl:'const journals=journalUniverse(tierBase);'},
 {id:'N10',what:'切进阅读视图时选中篇不按混排列表校正',scene:'S10',find:"if(view==='reading'){const items=readingTop12(personalFiltered());",repl:"if(view==='reading'){const items=readingTop12(filtered());"},
 {id:'N11',what:'取日跳过 entrez 日（只认 ArticleDate／期刊日）',scene:'S09',find:"const day=poolDay?poolPubmedDay(article.querySelector('PubmedData > History > PubMedPubDate[PubStatus=\"entrez\"]'))||poolPubmedDay(",repl:"const day=poolDay?poolPubmedDay("},
 {id:'N12',what:'阅读卡标题不转义（缓存 XSS 从阅读视图穿透）',scene:'S08',find:'<strong>${esc(title)}</strong><span class="proto-title-en">',repl:'<strong>${title}</strong><span class="proto-title-en">'},
 {id:'N13',what:'混排不按日期（只把池外排在最前，官方仍按评分）',scene:'S04',find:'    const dd=(dateMs(b.briefing_date)||0)-(dateMs(a.briefing_date)||0);if(dd)return dd;',repl:'    const dd=0;if(dd)return dd;'},
 {id:'N14',what:'详情卡档位徽记对池外走官方分支（伪称 v3）',scene:'S02',find:"  if(p.pool_ext)return poolBadge(p,true);",repl:''},
 {id:'N15',what:'开关分支被拆成永不含池外（开了也不混）',scene:'S02',find:'if(!poolMix||!extStore.journals.length)return official;',repl:'return official;'},
 // ===== FIX-1／FIX-2／FIX-3 自身红证：新守卫各自删一遍，对应场景必须红
 {id:'F01',what:'FIX-1 阅读视图池外上限被拆（top12 退回原样切片）',scene:'S10',find:'    const items=readingTop12(list);',repl:'    const items=list.slice(0,12);'},
 {id:'F02',what:'FIX-2 池外时间窗上界不抬到本地当天（退回官方锚点）',scene:'S09',find:'  const end=Number.isFinite(localEnd)&&localEnd>anchorEnd?localEnd:anchorEnd;',repl:'  const end=anchorEnd;'},
 {id:'F03',what:'FIX-3 池外预警格仍伪称「正常」',scene:'S11',find:"${p.pool_ext?t('poolup.unchecked'):p.warned ? t('warn.yes') : t('warn.no')}",repl:"${p.warned ? t('warn.yes') : t('warn.no')}"},
 {id:'F04',what:'FIX-3 过期缓存不带「已过期」陈旧标识',scene:'S11',find:'function poolStale(p){return Boolean(p&&p.pool_ext)&&Number(p.pool_cache_until)>0&&Number(p.pool_cache_until)<Date.now()}',repl:'function poolStale(p){return false}'},
 {id:'F05',what:'FIX-3 阅读卡英文副标照旧重复主标题',scene:'S11',find:"${esc(p.pool_ext?'':(p.title_en||t('title.en.missing')))}",repl:"${esc(p.title_en||t('title.en.missing'))}"},
 {id:'F06',what:'FIX-3 官方为空而池外在列时空态仍写官方无论文',scene:'S11',find:"if(poolN)$('#scope-empty').innerHTML=",repl:"if(false)$('#scope-empty').innerHTML="}
];
const count=(s,x)=>s.split(x).length-1,make=(src,m)=>{if(count(src,m.find)!==1)throw new Error(`${m.id} 锚点 ${count(src,m.find)} 次`);return src.replace(m.find,()=>m.repl)};
function run(target,label,scene){return new Promise(res=>{const args=[PROBE,'--target',target,'--base',BASE,'--only',scene,'--label',label];const child=spawn(process.execPath,args,{cwd:ROOT,env:{...process.env,POOLUP_SCRATCH:join(SCRATCH,'scratch-'+label)},stdio:['ignore','pipe','pipe']});let out='',timer=setTimeout(()=>child.kill(),180000);child.stdout.setEncoding('utf8');child.stderr.setEncoding('utf8');child.stdout.on('data',d=>out+=d);child.stderr.on('data',d=>out+=d);child.on('close',code=>{clearTimeout(timer);const text=`$ node ${args.join(' ')}\nEXIT=${code}\n\n${out}`;if(OUTDIR){mkdirSync(OUTDIR,{recursive:true});writeFileSync(join(OUTDIR,label+'.txt'),text)}res({code,out})})})}
const fails=out=>out.split(/\r?\n/).filter(l=>/^\s+✗ /.test(l)).map(l=>l.trim());
async function main(){rmSync(SCRATCH,{recursive:true,force:true});mkdirSync(SCRATCH,{recursive:true});const src=norm(readFileSync(TARGET,'utf8')),list=MUTANTS.filter(m=>!ONLY.length||ONLY.includes(m.id)),made=list.map(m=>({m,text:make(src,m)}));
 console.log(`poolup mutants | target=${TARGET} | sha256=${sha256(readFileSync(TARGET))} | mutants=${list.length} | jobs=${JOBS}`);
 const scenes=[...new Set(list.map(m=>m.scene))].join(','),ctl=await run(TARGET,'control',scenes);console.log(`CONTROL ${ctl.code===0?'GREEN':'NOT-GREEN'} scenes=${scenes}`);if(ctl.code!==0){fails(ctl.out).forEach(x=>console.log(x));process.exit(2)}
 let next=0;const results=[];async function worker(){for(;;){const i=next++;if(i>=made.length)return;const {m,text}=made[i],file=join(SCRATCH,m.id+'.html');writeFileSync(file,text);const r=await run(file,'m-'+m.id,m.scene),verdict=r.code===1?'KILLED':r.code===0?'SURVIVED':'CRASH';const f=fails(r.out);results.push({m,verdict,f});console.log(`${m.id} ${verdict} ${m.what} → ${m.scene}`);f.slice(0,4).forEach(x=>console.log('     '+x));if(!f.length)console.log('     '+r.out.trim().split(/\r?\n/).slice(-2).join(' | '))}}
 await Promise.all(Array.from({length:JOBS},worker));results.sort((a,b)=>a.m.id.localeCompare(b.m.id));const killed=results.filter(r=>r.verdict==='KILLED'),bad=results.filter(r=>r.verdict!=='KILLED');
 const text=results.map(r=>`${r.m.id} ${r.verdict} ${r.m.what}\n${r.f.join('\n')}`).join('\n\n')+'\n';if(OUTDIR){mkdirSync(OUTDIR,{recursive:true});writeFileSync(join(OUTDIR,'_results.txt'),text)}
 console.log(`\n==== POOLUP MUTANTS ${killed.length} KILLED / ${bad.length} NOT-KILLED / ${results.length} TOTAL ====`);if(KEEP)console.log('变异件保留 '+SCRATCH);else{rmSync(SCRATCH,{recursive:true,force:true});console.log('cleanup 变异临时目录已清')}process.exit(bad.length?1:0)}
main().catch(e=>{console.log('变异脚本故障 '+(e&&e.stack||e));if(!KEEP)try{rmSync(SCRATCH,{recursive:true,force:true})}catch(e2){}process.exit(2)});
