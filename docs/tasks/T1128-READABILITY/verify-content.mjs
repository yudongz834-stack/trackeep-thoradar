import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const evidence = dirname(fileURLToPath(import.meta.url));
const repo = fileURLToPath(new URL('../../../', import.meta.url));
const baseRev = '2826461b93d0ae7d099746e12544bfbaaf960f93';
const html = readFileSync(join(repo, 'index.html'), 'utf8');
const base = execFileSync('git', ['-C', repo, 'show', `${baseRev}:index.html`], { encoding: 'utf8' });
const checks = [];
const check = (name, pass, detail = '') => {
  checks.push({ name, pass:!!pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}${detail ? ` | ${detail}` : ''}`);
};
const translationBlock = s => s.slice(s.indexOf('const I18N='), s.indexOf("let LANG='zh';"));
const siteLine = s => s.match(/^[ \t]*const SITE_DATA = [^\r\n]+/m)?.[0];
const functionBlock = (s, name) => {
  const start = s.indexOf(`function ${name}(`);
  if (start < 0) return null;
  const open = s.indexOf('{', start);
  let depth = 0;
  for (let i = open; i < s.length; i++) {
    if (s[i] === '{') depth++;
    if (s[i] === '}' && --depth === 0) return s.slice(start, i + 1);
  }
  return null;
};
const git = args => execFileSync('git', ['-C', repo, ...args], { encoding:'utf8' });
const i18n = translationBlock(html);

check('Chinese document title', html.includes("'doc.title':'Thoradar · 胸科文献雷达'"));
check('English document title', html.includes("'doc.title':'Thoradar · Thoracic Literature Radar'"));
check('HTML and share titles', html.includes('<title>Thoradar · 胸科文献雷达</title>') && html.includes('property="og:title" content="Thoradar · 胸科文献雷达"'));
check('queue labels', html.includes("'queue.h2':'文献队列'") && html.includes("'queue.h2':'Literature queue'"));
check('scope labels', html.includes("'scope.h1':'胸科文献雷达'") && html.includes("'scope.h1':'Thoracic literature radar'"));
check('daily research eyebrow', html.includes("'scope.eyebrow':'每日新文献'") && html.includes("'scope.eyebrow':'Daily new research'"));
check('paper hub', html.includes("'scope.hub':'文献'") && html.includes("'scope.hub':'PAPERS'") && html.includes('data-i18n="scope.hub"'));
check('data date labels', html.includes("'scan.date':'数据日期'") && html.includes("'scan.date':'DATA DATE'") && !html.includes("' / ANCHOR'"));
check('publication status note', html.includes("'scan.note':'出版状态已标注'") && html.includes("'scan.note':'Publication status annotated'"));
check('search placeholders', html.includes("'search.ph':'检索文献…'") && html.includes("'search.ph':'Search the literature…'"));
check('paper selection legend', html.includes("'legend.tip':'点选文献查看详情 · 点按扇区筛刊'") && html.includes("'legend.tip':'Click a paper to select · click a sector to filter journals'"));
check('paper navigation', html.includes("'nav.prev':'← 上一文献'") && html.includes("'nav.next':'下一文献 →'") && html.includes("'nav.prev':'← Previous paper'") && html.includes("'nav.next':'Next paper →'"));
check('no signal wording in translations', !/\bsignals?\b|信号/i.test(i18n));
check('AbortSignal implementation untouched', (html.match(/AbortSignal/g) || []).length === (base.match(/AbortSignal/g) || []).length && html.includes('AbortSignal'));
check('brand typography', html.includes('.brand-name{font-size:24px;letter-spacing:.04em}') && html.includes('.brand-sub{margin-top:3px;font-size:12px;'));
check('tab typography and selected state', html.includes('.proto-view-btn{min-height:36px;padding:6px 12px;font-size:12.5px;color:var(--text-2)}') && html.includes('.proto-view-btn[aria-selected="true"]{color:var(--card);border-color:var(--text);background:var(--text);'));
check('filter prominence', html.includes('.filters-toggle{min-height:36px;font-size:12px;font-weight:650;color:var(--text);'));
check('mid-width overlap guards', html.includes('@media(min-width:1351px) and (max-width:1400px)') && html.includes('@media(max-width:1100px) and (min-width:901px)'));
check('official SITE_DATA unchanged', siteLine(html) === siteLine(base));
check('mergePapers unchanged', functionBlock(html.replaceAll('\r\n', '\n'), 'mergePapers') === functionBlock(base.replaceAll('\r\n', '\n'), 'mergePapers'));
check('inWindow unchanged', functionBlock(html.replaceAll('\r\n', '\n'), 'inWindow') === functionBlock(base.replaceAll('\r\n', '\n'), 'inWindow'));
for (const name of ['render', 'gatePause', 'classifyScheme']) {
  check(`${name} unchanged`, functionBlock(html.replaceAll('\r\n', '\n'), name) === functionBlock(base.replaceAll('\r\n', '\n'), name));
}
check('cache workers and deploy workflow unchanged', git(['diff', baseRev, '--', 'sw.js', 'sw-retire.js', '.github/workflows/deploy_oss.yml']) === '');
const changedTracked = git(['diff', '--name-only', baseRev]).split(/\r?\n/).filter(Boolean);
check('tracked source changes limited to page and UX contract', changedTracked.length === 2 && changedTracked.includes('index.html') && changedTracked.includes('tests/ux/ux_probe.mjs'), changedTracked.join(', '));
check('legacy translation negative control', /\bsignals?\b|信号/i.test(translationBlock(base)));
check('legacy typography negative control', !base.includes('.brand-name{font-size:24px;letter-spacing:.04em}'));

const result = {
  baseRev,
  checks,
  summary:{ passed:checks.filter(x=>x.pass).length, failed:checks.filter(x=>!x.pass).length },
};
writeFileSync(join(evidence, 'content-check.json'), JSON.stringify(result, null, 2) + '\n');
console.log('SUMMARY ' + JSON.stringify(result.summary));
if (result.summary.failed) process.exitCode = 1;
