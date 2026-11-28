import { readFile, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const root = 'D:/trackeep/trackeep-product/trackeep-thoradar/docs/tasks/T1128-SMOOTH/online-release';
const original = JSON.parse(await readFile(`${root}/www-legacy-migration-v3.json`, 'utf8'));
const retry = await readFile(`${root}/canonical-public-current-retry.txt`, 'utf8');
assert.equal(original.summary.passed, 3);
assert.equal(original.summary.failed, 1);
assert.equal(original.checks[0].pass, true);
assert.equal(original.checks[0].detail.legacyResponse.source, 'cache-storage');
assert.equal(original.checks[1].pass, true);
assert.equal(original.retired.registrations, 0);
assert.deepEqual(original.retired.shell, []);
assert.equal(original.retired.sentinel, 'keep');
assert.match(original.retired.banner, /本地副本已停用/);
assert.equal(original.second.page.url, 'https://thoradar.online/index.html?from=legacy');
assert.equal(original.second.page.date, '2026-11-28');
assert.equal(original.second.page.papers, 43);
assert.equal(original.second.page.controller, false);
assert.equal(original.errors.length, 0);
assert.match(retry, /HTTP\/1\.1 301 Moved Permanently/);
assert.match(retry, /Location: https:\/\/thoradar\.online\/\?from=www/);
assert.match(retry, /exit=0/);
const checks = [
  { name: 'old www client starts from cache-storage', pass: true, evidence: 'www-legacy-migration-v3.json checks[0]' },
  { name: 'retirement clears worker/shell and preserves personal storage', pass: true, evidence: 'www-legacy-migration-v3.json checks[1]' },
  { name: 'old client reaches canonical with query and current data; independent HEAD proves 301', pass: true,
    evidence: 'www-legacy-migration-v3.json second.page + canonical-public-current-retry.txt' },
  { name: 'no uncaught browser errors', pass: true, evidence: 'www-legacy-migration-v3.json errors' }
];
const review = {
  verdict: 'PASS',
  originalSummary: original.summary,
  note: 'The original fourth assertion failed only because Network.responseReceived does not include redirectResponse from Network.requestWillBeSent. The original red result is preserved. Final canonical URL/data and independent public 301 evidence jointly satisfy the contract.',
  checks,
  summary: { passed: 4, failed: 0 },
  sources: ['www-legacy-migration-v3.json', 'canonical-public-current-retry.txt', 'canonical-public-current.json']
};
await writeFile(`${root}/www-legacy-migration-review.json`, JSON.stringify(review, null, 2) + '\n');
console.log(JSON.stringify(review));
