import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

// Run from the S12 worktree. Each mutation operates on a separate copy of the publish workflow.
const evidence = 'docs/tasks/T1128-SMOOTH/online-release/sol-s12';
const workflow = '.github/workflows/deploy_oss.yml';
const mutations = {
  'www-refresh': {
    before: 'refresh_paths=$(printf \'https://thoradar.online%s\\n\' "${paths[@]}")',
    after: 'refresh_paths=$(printf \'https://thoradar.online%s\\n\' "${paths[@]}"; printf \'https://www.thoradar.online%s\\n\' "${paths[@]}")',
    failures: [
      'normal uploads workers then index, refreshes only four main URLs and verifies both domains',
      'retire uploads workers then index, refreshes only four main URLs and verifies both domains'
    ],
    statuses: { healthy: 0, 'healthy-retire': 0 }
  },
  'www-allow-200': {
    before: 'if (status != 301 && status != 308) exit 1',
    after: 'if (status == 200) exit 0\n                if (status != 301 && status != 308) exit 1',
    failures: ['www-root-200', 'www-index-200'],
    statuses: { 'www-root-200': 0, 'www-index-200': 0 }
  },
  'www-allow-302': {
    before: 'if (status != 301 && status != 308) exit 1',
    after: 'if (status != 301 && status != 302 && status != 308) exit 1',
    failures: ['www-redirect-302'],
    statuses: { 'www-redirect-302': 0 }
  },
  'www-ignore-location': {
    before: 'if (locations != 1 || location != expected) exit 1',
    after: 'if (locations != 1) exit 1',
    failures: ['www-redirect-wrong-location', 'www-redirect-lost-query'],
    statuses: { 'www-redirect-wrong-location': 0, 'www-redirect-lost-query': 0 }
  },
  'www-use-active-worker': {
    before: "verify_object 'https://www.thoradar.online/sw.js' sw-retire.js 1",
    after: `verify_object 'https://www.thoradar.online/sw.js' "$active_worker" 1`,
    failures: ['www-active-worker'],
    statuses: { 'www-active-worker': 0 }
  },
  'remove-md5-guard': {
    before: 'if (status != 200 || md5 != expected) exit 1',
    after: 'if (status != 200) exit 1',
    failures: ['wrong-md5'],
    statuses: { 'wrong-md5-retire': 0 }
  },
  'short-wait': {
    before: 'sleep 40',
    after: 'sleep 5',
    failures: ['main-domain CDN can take six minutes with two 5s sleeps followed by nine 40s sleeps'],
    statuses: { 'stale-during-propagation-retire': 1 }
  }
};

const names = process.argv.slice(2);
assert.ok(names.length, `Specify one or more mutations: ${Object.keys(mutations).join(', ')}`);

for (const name of names) {
  assert.ok(Object.hasOwn(mutations, name), `Unknown mutation: ${name}`);
  const { before, after, failures, statuses } = mutations[name];
  const dir = join(evidence, name);
  mkdirSync(dir);
  const candidate = join(dir, 'deploy.yml');
  copyFileSync(workflow, candidate);
  const source = readFileSync(candidate, 'utf8').replaceAll('\r\n', '\n');
  assert.equal(source.split(before).length, 2, `Expected exactly one mutation anchor: ${before}`);
  writeFileSync(candidate, source.replace(before, () => after));

  const result = join(dir, 'deploy.json');
  const args = ['tests/smooth/verify-deploy.mjs', result, candidate];
  const command = ['node', ...args].map(arg => arg.replaceAll('\\', '/')).join(' ');
  console.log(command);
  const run = spawnSync(process.execPath, args, { windowsHide: true });
  if (run.error) throw run.error;
  writeFileSync(join(dir, 'deploy.stdout.txt'), run.stdout);
  writeFileSync(join(dir, 'deploy.stderr.txt'), run.stderr);
  const check = JSON.parse(readFileSync(result, 'utf8'));
  const failed = check.tests.filter(test => !test.pass);
  const scenarioExitCodes = Object.fromEntries(Object.keys(statuses).map(scenario => [scenario, check.simulations[scenario]?.status]));
  const summary = { name, before, after, command, exitCode: run.status, summary: check.summary,
    failed, expectedFailures: failures, scenarioExitCodes, expectedScenarioExitCodes: statuses };
  writeFileSync(join(dir, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
  console.log(JSON.stringify({ exitCode: run.status, ...check.summary, failed: failed.map(test => test.name), scenarioExitCodes }));

  assert.equal(run.status, 1);
  for (const expected of failures) {
    assert.ok(failed.some(test => test.name === expected || test.name === `post-publish verification rejects ${expected}`),
      `Mutation did not break the intended test: ${expected}`);
  }
  assert.deepEqual(scenarioExitCodes, statuses);
}
