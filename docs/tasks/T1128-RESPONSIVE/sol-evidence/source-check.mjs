import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../../../', import.meta.url));
const git = (...args) => execFileSync('git', args, { cwd: root, maxBuffer: 8 * 1024 * 1024 });
const head = git('show', 'HEAD:index.html').toString('utf8');
const candidate = readFileSync(resolve(root, 'index.html'), 'utf8').replace(/\r\n/g, '\n');
const reportEqual = (name, old, current) => {
  assert.equal(old === current, true, `${name} differs`);
  console.log(`${name} MATCH sha256=${createHash('sha256').update(current).digest('hex')}`);
};
const oneSiteLine = html => {
  const lines = html.match(/^[ \t]*const SITE_DATA = [^\r\n]+/gm);
  assert.equal(lines?.length, 1);
  return lines[0];
};
const splitStyle = html => {
  const chunks = html.split(/<style>|<\/style>/);
  assert.equal(chunks.length, 3);
  return chunks;
};
const scripts = html => [...html.matchAll(/<script\b[^>]*>[\s\S]*?<\/script>/g)].map(m => m[0]);

console.log(`git rev-parse HEAD\n${git('rev-parse', 'HEAD').toString().trim()}`);
const [headBefore, headCss, headAfter] = splitStyle(head);
const [candidateBefore, candidateCss, candidateAfter] = splitStyle(candidate);
assert.notEqual(headCss === candidateCss, true, 'CSS is unchanged');
reportEqual('HTML outside the style element (LF-normalized checkout)', headBefore + headAfter, candidateBefore + candidateAfter);
reportEqual('SITE_DATA (complete line)', oneSiteLine(head), oneSiteLine(candidate));
const oldScripts = scripts(head);
const newScripts = scripts(candidate);
assert.equal(newScripts.length, oldScripts.length);
for (const [i, script] of oldScripts.entries()) reportEqual(`script ${i + 1}`, script, newScripts[i]);

const protectedPaths = ['sw.js', 'sw-retire.js', 'tests/', '.github/', 'README.md', '架构.md', 'docs/tasks/T1128-RESPONSIVE/acceptance-contract.md'];
console.log(`git diff --exit-code HEAD -- ${protectedPaths.join(' ')}`);
const diff = git('diff', '--exit-code', 'HEAD', '--', ...protectedPaths).toString();
assert.equal(diff, '');
console.log('exit=0; no tracked diff output');
const untracked = git('ls-files', '--others', '--exclude-standard', '--', 'tests/', '.github/').toString();
assert.equal(untracked, '');
console.log('git ls-files --others --exclude-standard -- tests/ .github/\n(no output)');
console.log(`git diff --name-only HEAD\n${git('diff', '--name-only', 'HEAD').toString().trim()}`);
assert.equal(git('diff', '--name-only', 'HEAD').toString().trim(), 'index.html');
console.log('git diff --check\n' + git('diff', '--check').toString() + 'exit=0');
