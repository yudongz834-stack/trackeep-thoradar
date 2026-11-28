import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
const repo = 'D:/trackeep/trackeep-product/trackeep-thoradar';
const output = `${repo}/docs/tasks/T1128-RESPONSIVE/online-release/public-final.json`;
const md5 = name => createHash('md5').update(execFileSync('git', ['-C', repo, 'show', `HEAD:${name}`])).digest('base64');
const expected = { 'index.html': md5('index.html'), 'sw.js': md5('sw.js'), 'sw-retire.js': md5('sw-retire.js') };
const rows = [];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function head(url) {
  let row;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const response = await fetch(url, { method: 'HEAD', redirect: 'manual', headers: { 'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache', Pragma: 'no-cache' } });
      row = { url, status: response.status, location: response.headers.get('location'), md5: response.headers.get('content-md5'),
        mime: response.headers.get('content-type'), cacheControl: response.headers.get('cache-control'), attempts: attempt };
      break;
    } catch (error) {
      row = { url, error: String(error), cause: String(error.cause || ''), attempts: attempt };
      if (attempt < 3) await sleep(250);
    }
  }
  rows.push(row);
  return row;
}
function check(name, pass, row) { rows.at(-1).check = { name, pass: !!pass }; console.log(`${pass ? 'PASS' : 'FAIL'} ${name} ${JSON.stringify(row)}`); }
for (const [path, source] of [['/', 'index.html'], ['/index.html', 'index.html'], ['/sw.js', 'sw.js'], ['/sw-retire.js', 'sw-retire.js']]) {
  const url = 'https://thoradar.online' + path;
  const row = await head(url);
  check(`main ${path}`, !row.error && row.status === 200 && row.md5 === expected[source] &&
    (source === 'index.html' ? /^text\/html\b/i.test(row.mime || '') : /javascript/i.test(row.mime || '') && /(?:^|,)\s*no-store\s*(?:,|$)/i.test(row.cacheControl || '')), row);
}
for (const path of ['/', '/index.html', '/?from=www', '/some/path?x=1']) {
  const url = 'https://www.thoradar.online' + path;
  const row = await head(url);
  check(`www redirect ${path}`, !row.error && [301, 308].includes(row.status) && row.location === 'https://thoradar.online' + path, row);
}
for (const path of ['/sw.js', '/sw-retire.js']) {
  const url = 'https://www.thoradar.online' + path;
  const row = await head(url);
  check(`www retired worker ${path}`, !row.error && row.status === 200 && row.md5 === expected['sw-retire.js'] &&
    /javascript/i.test(row.mime || '') && /(?:^|,)\s*no-store\s*(?:,|$)/i.test(row.cacheControl || ''), row);
}
const summary = { passed: rows.filter(row => row.check?.pass).length, failed: rows.filter(row => !row.check?.pass).length };
await writeFile(output, JSON.stringify({ runId: 46156893720, headSha: execFileSync('git', ['-C', repo, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), checkedAt: new Date().toISOString(), expected, rows, summary }, null, 2) + '\n');
console.log('SUMMARY ' + JSON.stringify(summary));
if (summary.failed) process.exitCode = 1;
