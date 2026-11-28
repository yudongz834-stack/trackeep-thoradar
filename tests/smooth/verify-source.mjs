import { execFileSync } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { ROOT, gitRead, norm, sha256 } from '../aicls/lib.mjs';
import { parseOfficialData, splitOfficialData } from './official-data.mjs';

const [output, mode, ...extra] = process.argv.slice(2);
if (!output || (mode !== undefined && mode !== '--ci') || extra.length) {
  throw new Error('Usage: node tests/smooth/verify-source.mjs <result.json> [--ci]');
}
const ci = mode === '--ci';
const c1Baseline = '73dd34e';
const scopeBaseline = ci ? 'HEAD' : c1Baseline;
const paths = ['index.html', 'sw.js', 'sw-retire.js', 'tests/smooth/verify-s1.mjs',
  'tests/smooth/verify-s2.mjs', 'tests/smooth/run-regressions.mjs', 'tests/smooth/verify-source.mjs',
  'tests/smooth/official-data.mjs', 'tests/smooth/prepare-ci-ux-baseline.mjs', 'tests/ux/ux_probe.mjs'];
const candidate = norm(await readFile(join(ROOT, 'index.html'), 'utf8'));
const baseline = norm(gitRead(['show', `${c1Baseline}:index.html`]));
const sections = [
  ['official-paper-initialization', 'const INJECTED_PAPERS=', 'let PAPERS=INJECTED_PAPERS.slice();'],
  ['official-window-and-merge', 'function inWindow(p){', 'const windowPapers=()=>PAPERS.filter(inWindow);']
];
const checks = [];
try {
  const block = splitOfficialData(candidate).block;
  if (ci) {
    const data = parseOfficialData(block);
    checks.push({ name: 'official-data', pass: true, briefingDate: data.briefing_date,
      paperCount: data.papers.length, candidateSha256: sha256(block) });
  } else {
    const original = splitOfficialData(baseline).block;
    checks.push({ name: 'official-data', pass: original === block,
      baselineSha256: sha256(original), candidateSha256: sha256(block) });
  }
} catch (error) {
  checks.push({ name: 'official-data', pass: false, error: error.message });
}
for (const [name, start, end] of sections) {
  const extract = source => {
    const from = source.indexOf(start);
    const to = source.indexOf(end, from + start.length);
    if (from < 0 || to < 0) throw new Error('Section missing: ' + name);
    return source.slice(from, to + end.length);
  };
  const from = extract(baseline);
  const to = extract(candidate);
  checks.push({ name, pass: from === to, baselineSha256: sha256(from), candidateSha256: sha256(to) });
}

const changed = (...args) => gitRead(['diff', '--name-only', '--no-renames', '-z', ...args, '--'])
  .split('\0').filter(Boolean);
const tracked = ci ? [...new Set([...changed('--cached', 'HEAD'), ...changed()])] : changed(c1Baseline);
const untracked = gitRead(['ls-files', '--others', '--exclude-standard', '-z']).split('\0').filter(Boolean);
const outOfScope = [...new Set([...tracked, ...untracked])].filter(path =>
  !['index.html', 'sw.js', 'sw-retire.js', '.github/workflows/deploy_oss.yml', 'tests/ux/ux_probe.mjs'].includes(path) &&
  !path.startsWith('tests/smooth/') && !path.startsWith('docs/tasks/T1128-SMOOTH/'));
checks.push({ name: 'write-scope', pass: outOfScope.length === 0, tracked, untracked, outOfScope });
const syntax = paths.slice(1).map(path => {
  execFileSync(process.execPath, ['--check', path], { cwd: ROOT, stdio: 'inherit' });
  return path;
});
for (const args of ci ? [['--cached', scopeBaseline], []] : [[scopeBaseline]]) {
  execFileSync('git', ['diff', '--check', ...args, '--'], { cwd: ROOT, stdio: 'inherit' });
}
checks.push({ name: 'node-syntax-and-git-diff-check', pass: true, syntax });
for (const check of checks) console.log((check.pass ? 'PASS ' : 'FAIL ') + check.name + ' ' + JSON.stringify(check));
const files = Object.fromEntries(await Promise.all(paths.map(async path =>
  [path, sha256(await readFile(join(ROOT, path)))])));
console.log('SHA256 ' + JSON.stringify(files));
const summary = { passed: checks.filter(check => check.pass).length, failed: checks.filter(check => !check.pass).length };
console.log('SUMMARY ' + JSON.stringify(summary));
await writeFile(output, JSON.stringify({ timestamp: new Date().toISOString(), runs: 1, seed: null,
  mode: ci ? 'ci' : 'local', baseline: gitRead(['rev-parse', c1Baseline]).trim(),
  scopeBaseline: gitRead(['rev-parse', scopeBaseline]).trim(), checks, files, summary }, null, 2) + '\n', { flag: 'wx' });
if (summary.failed) process.exitCode = 1;
