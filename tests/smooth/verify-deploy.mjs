import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmod, copyFile, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const [output, candidate] = process.argv.slice(2);
if (!output) throw new Error('Usage: node tests/smooth/verify-deploy.mjs <result.json> [workflow.yml]');

const root = fileURLToPath(new URL('../../', import.meta.url));
const workflow = resolve(candidate || join(root, '.github/workflows/deploy_oss.yml'));
const yaml = (await readFile(workflow, 'utf8')).replace(/\r\n/g, '\n');
const windows = process.platform === 'win32';
const gitBash = join(process.env.ProgramFiles || 'C:/Program Files', 'Git/bin/bash.exe');
const bash = windows && existsSync(gitBash) ? gitBash : 'bash';
const tests = [];

async function test(name, run) {
  try {
    await run();
    tests.push({ name, pass: true });
    console.log(`PASS ${name}`);
  } catch (error) {
    tests.push({ name, pass: false, error: error.message });
    console.error(`FAIL ${name}: ${error.message}`);
  }
}

// Extract the two Bash blocks as GitHub Actions passes them to its shell.
function section(start, end) {
  const from = yaml.indexOf(start);
  if (from < 0) return '';
  const to = end ? yaml.indexOf(end, from + start.length) : -1;
  return yaml.slice(from, to < 0 ? undefined : to);
}

function shellBlock(step) {
  const lines = step.split('\n');
  const start = lines.indexOf('        run: |');
  assert.notEqual(start, -1, 'missing Bash run block');
  const body = [];
  for (const line of lines.slice(start + 1)) {
    if (line && !line.startsWith('          ')) break;
    body.push(line.slice(10));
  }
  return body.join('\n') + '\n';
}

const verifyJob = section('\n  smooth-verify:\n', '\n  deploy-oss:\n');
const deployJob = section('\n  deploy-oss:\n');
const installStep = section('\n      - name: Install OSS and CDN tools\n', '\n      - name: Publish and verify site\n');
const deployStep = section('\n      - name: Publish and verify site\n');

await test('Windows Node 24 gate runs the real checks in order before the same revision deploys', () => {
  assert.match(verifyJob, /\n    if: github\.event_name == 'workflow_dispatch' \|\| github\.event\.workflow_run\.conclusion == 'success'\n/);
  assert.match(verifyJob, /\n    runs-on: windows-latest\n/);
  assert.match(verifyJob, /\n          fetch-depth: 0\n/);
  assert.match(verifyJob, /actions\/setup-node@v4\n        with:\n          node-version: '24'/);
  assert.match(deployJob, /\n    needs: smooth-verify\n/);
  assert.doesNotMatch(deployJob, /\n    if:/);
  for (const job of [verifyJob, deployJob]) {
    assert.match(job, /uses: actions\/checkout@v4\n        with:\n          ref: \$\{\{ github\.sha \}\}/);
    assert.doesNotMatch(job, /continue-on-error:|always\(\)|success\(\)\s*\|\|/);
  }
  let previous = -1;
  const commands = [
    ...['deploy', 'source', 's1', 's2', 's3'].map(suffix =>
      `run: node tests/smooth/verify-${suffix}.mjs "$env:RUNNER_TEMP/smooth-${suffix}.json"${suffix === 'source' ? ' --ci' : ''}`),
    'run: node tests/smooth/prepare-ci-ux-baseline.mjs "$env:GITHUB_SHA" "$env:RUNNER_TEMP/smooth-ux-baseline.html"',
    'node tests/ux/ux_probe.mjs --target index.html --base-html "$env:RUNNER_TEMP/smooth-ux-baseline.html" --label smooth-ci'
  ];
  for (const command of commands) {
    const current = verifyJob.indexOf(command + '\n');
    assert.ok(current > previous, `missing or out of order: ${command}`);
    previous = current;
  }
  assert.match(verifyJob, /\$env:XREV_SCRATCH = Join-Path \$env:RUNNER_TEMP 'smooth-ux'/);
  assert.doesNotMatch(verifyJob, /run-regressions|tests\/(aicls|poolup)\/|secrets\./);
});

await test('manual retire is a boolean defaulting to false and CLI aliases reuse the OSS secrets', () => {
  assert.match(yaml, /\n  workflow_dispatch:\n    inputs:\n      retire:\n        description: [^\n]+\n        type: boolean\n        default: false\n/);
  assert.match(deployStep, /\n          SMOOTH_RETIRE: \$\{\{ inputs\.retire && 'true' \|\| 'false' \}\}\n/);
  assert.match(deployStep, /\n          ALIBABA_CLOUD_ACCESS_KEY_ID: \$\{\{ secrets\.OSS_KEY_ID \}\}\n/);
  assert.match(deployStep, /\n          ALIBABA_CLOUD_ACCESS_KEY_SECRET: \$\{\{ secrets\.OSS_KEY_SECRET \}\}\n/);
});

await test('the Aliyun CLI download pins v3.5.4 and checks SHA-256 before extraction', () => {
  const download = 'https://github.com/aliyun/aliyun-cli/releases/download/v3.5.4/aliyun-cli-linux-3.5.4-amd64.tgz';
  const checksum = "echo 'e1eefcbbe9d772d61f770d4af8595e7297e081a0348b096765d2c41e581c3e72  aliyun/cli.tgz' | sha256sum -c -";
  assert.match(installStep, /\n          set -euo pipefail\n/);
  assert.ok(installStep.includes(download));
  assert.ok(installStep.indexOf(checksum) > installStep.indexOf(download));
  assert.ok(installStep.indexOf('tar -xzf aliyun/cli.tgz') > installStep.indexOf(checksum));
  assert.doesNotMatch(installStep, /secrets\./);
});

const localEnv = {};
for (const key of ['PATH', 'SystemRoot', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'TMPDIR']) {
  if (process.env[key] !== undefined) localEnv[key] = process.env[key];
}
const bashPath = path => windows ? path.replaceAll('\\', '/') : path;
const scratch = await mkdtemp(join(tmpdir(), 'thoradar-s5-deploy-'));
const simulations = {};
const shellRuns = {};
const domains = ['thoradar.online', 'www.thoradar.online'];
const urls = domains.flatMap(domain => ['/', '/index.html', '/sw.js', '/sw-retire.js'].map(path => `https://${domain}${path}`));
const refreshUrls = urls.filter(url => new URL(url).hostname === 'thoradar.online');
const workerMeta = 'Content-Type:application/javascript#Cache-Control:no-store';
const origin = 'oss://thoradar-online/';
const publishComplete = 'Publish verified on both domains';

function bashRun(args, options = {}) {
  const run = spawnSync(bash, ['--noprofile', '--norc', ...args], {
    cwd: scratch, env: localEnv, encoding: 'utf8', windowsHide: true, timeout: 60000, ...options
  });
  if (run.error) throw run.error;
  return { status: run.status, stdout: run.stdout, stderr: run.stderr };
}

async function mockCommand(path, tool) {
  const command = `#!/usr/bin/env bash\nexec "$SMOOTH_MOCK_NODE" "$SMOOTH_MOCK_SCRIPT" ${tool} "$@"\n`;
  await writeFile(path, command);
  await chmod(path, 0o755);
}

async function simulate(scenario, retire = false) {
  const label = retire ? `${scenario}-retire` : scenario;
  const trace = join(scratch, `trace-${label}.jsonl`);
  await writeFile(trace, '');
  const env = { ...localEnv, MSYS2_ARG_CONV_EXCL: '*', RUNNER_TEMP: bashPath(scratch),
    OSS_KEY_ID: 'mock-id', OSS_KEY_SECRET: 'mock-secret',
    ALIBABA_CLOUD_ACCESS_KEY_ID: 'mock-id', ALIBABA_CLOUD_ACCESS_KEY_SECRET: 'mock-secret',
    SMOOTH_RETIRE: String(retire), SMOOTH_MOCK_SCENARIO: scenario,
    SMOOTH_MOCK_NODE: bashPath(process.execPath), SMOOTH_MOCK_SCRIPT: fileURLToPath(new URL('./deploy-mock.mjs', import.meta.url)),
    SMOOTH_MOCK_TRACE: trace };
  const script = join(scratch, 'publish.sh');
  const run = bashRun([bashPath(script)], { env });
  const calls = (await readFile(trace, 'utf8')).trim().split('\n').filter(Boolean).map(line => JSON.parse(line));
  simulations[label] = { ...run, calls };
  return { ...run, calls, uploads: calls.filter(call => call.tool === 'ossutil' && call.args[0] === 'cp').map(call => call.args),
    refreshes: calls.filter(call => call.tool === 'aliyun').map(call => call.args),
    heads: calls.filter(call => call.tool === 'curl' && call.args.includes('-I')).map(call => call.args.at(-1)) };
}

function success(run) {
  assert.equal(run.status, 0, run.stderr);
  assert.ok(run.stdout.includes(publishComplete));
}

function failure(run, message) {
  assert.notEqual(run.status, 0, 'deployment exited 0');
  assert.match(run.stderr, message);
  assert.ok(!run.stdout.includes(publishComplete));
}

try {
  let deployScript;
  await test('Bash syntax for tool installation and production publish', () => {
    deployScript = shellBlock(deployStep);
    for (const [name, input] of [['install', shellBlock(installStep)], ['publish', deployScript]]) {
      const run = bashRun(['-n'], { input });
      shellRuns[name] = run;
      assert.equal(run.status, 0, run.stderr);
    }
  });
  assert.ok(deployScript, 'cannot simulate an absent publish step');
  const bin = join(scratch, 'bin');
  const aliyun = join(scratch, 'aliyun');
  await mkdir(bin);
  await mkdir(aliyun);
  await Promise.all([
    ...['index.html', 'sw.js', 'sw-retire.js', 'sitemap.xml'].map(file => copyFile(join(root, file), join(scratch, file))),
    mockCommand(join(scratch, 'ossutil'), 'ossutil'), mockCommand(join(aliyun, 'aliyun'), 'aliyun'),
    mockCommand(join(bin, 'curl'), 'curl'), mockCommand(join(bin, 'sleep'), 'sleep')
  ]);
  // Git Bash uses a Unix PATH. Use the host's Python for the real JSON parser on Windows.
  if (windows) {
    const python = join(bin, 'python3');
    await writeFile(python, '#!/usr/bin/env bash\nexec python "$@"\n');
    await chmod(python, 0o755);
  }
  await writeFile(join(scratch, 'publish.sh'), [
    'set -e', 'mock_bin="$RUNNER_TEMP/bin"',
    'if [[ "$OSTYPE" == msys* ]]; then mock_bin=$(cygpath -u "$mock_bin"); fi',
    'export PATH="$mock_bin:$PATH"',
    '# Hosted Windows may prefer system executables over no-extension PATH mocks.',
    'curl() { "$mock_bin/curl" "$@"; }',
    'sleep() { "$mock_bin/sleep" "$@"; }',
    deployScript
  ].join('\n'));

  for (const retire of [false, true]) {
    await test(`${retire ? 'retire' : 'normal'} uploads workers then index, refreshes four owned CDN URLs and verifies eight URLs`, async () => {
      const run = await simulate('healthy', retire);
      success(run);
      assert.deepEqual(run.uploads, [
        ...['favicon.ico', 'robots.txt', 'sitemap.xml'].map(file => ['cp', '-rf', '--update', file, origin]),
        ['cp', '-rf', '--update', '--meta', 'Cache-Control:no-cache', 'feed.xml', origin],
        ['cp', '-rf', '--update', '--meta', 'Cache-Control:public, max-age=60, s-maxage=300', 'data/radar_latest.json', `${origin}data/`],
        ['cp', '-rf', '--update', '--meta', 'Cache-Control:no-cache', 'api/', `${origin}api/`],
        ['cp', '-rf', '--update', 'thoradar-skill/', `${origin}thoradar-skill/`],
        ['cp', '-f', '--meta', workerMeta, 'sw-retire.js', `${origin}sw-retire.js`],
        ['cp', '-f', '--meta', workerMeta, retire ? 'sw-retire.js' : 'sw.js', `${origin}sw.js`],
        ['cp', '-f', '--meta', 'Cache-Control:public, max-age=60, s-maxage=3600', 'index.html', `${origin}index.html`]
      ]);
      const preflights = run.calls.filter(call => call.tool === 'curl' && call.args.includes('--connect-to'));
      assert.deepEqual(preflights.map(call => call.args.slice(-2)), domains.map(host =>
        [`${host}:443:thoradar-online.cn-shenzhen.taihangtop.cn:443`, `https://${host}/`]));
      const actions = run.calls.filter(call => call.tool === 'curl' || call.tool === 'aliyun');
      assert.deepEqual(actions.map(call => call.tool), ['curl', 'curl', 'aliyun', ...urls.map(() => 'curl')]);
      assert.deepEqual(run.refreshes, [['cdn', 'RefreshObjectCaches', '--region', 'cn-shenzhen', '--ObjectType', 'File', '--ObjectPath', refreshUrls.join('\n')]]);
      assert.match(run.stdout, /CDN RefreshTaskId="123456"/);
      assert.deepEqual(run.heads, urls);
      assert.ok(actions.slice(3).every(call => call.args.includes('Accept-Encoding: identity')));
    });
  }

  for (const scenario of ['refresh-retry', 'id-retry', 'refresh-error', 'missing-task-id']) {
    await test(`CDN ${scenario} uses at most one retry and requires a task ID`, async () => {
      const run = await simulate(scenario);
      assert.equal(run.refreshes.length, 2);
      assert.deepEqual(run.refreshes[0], run.refreshes[1]);
      assert.equal(run.calls.filter(call => call.tool === 'sleep').length, 1);
      if (scenario.endsWith('-retry')) {
        success(run);
        assert.deepEqual(run.heads, urls);
      } else {
        failure(run, /CDN refresh failed or returned no RefreshTaskId/);
        assert.deepEqual(run.heads, []);
      }
    });
  }

  await test('stale CDN content is polled again before publishing succeeds', async () => {
    const run = await simulate('stale-then-current', true);
    success(run);
    const workerUrl = 'https://www.thoradar.online/sw.js';
    assert.equal(run.heads.filter(url => url === workerUrl).length, 2);
    assert.ok(run.stdout.includes(`Waiting for ${workerUrl} (1/12)`));
  });

  for (const scenario of ['wrong-md5', 'wrong-mime', 'worker-cacheable', 'worker-404', 'head-error']) {
    await test(`post-publish verification rejects ${scenario}`, async () => {
      const run = await simulate(scenario, scenario === 'wrong-md5');
      const url = scenario === 'worker-cacheable' ? 'https://www.thoradar.online/sw-retire.js' : 'https://www.thoradar.online/sw.js';
      failure(run, /Verification failed for https:\/\/www\.thoradar\.online\/sw/);
      assert.equal(run.heads.filter(head => head === url).length, 12);
      assert.ok(!run.stdout.includes(`Verified ${url} `));
    });
  }

  await test('HTTPS origin preflight rejects 304 and blocks CDN refresh', async () => {
    const run = await simulate('preflight-304');
    failure(run, /www\.thoradar\.online 根路径 HTTPS 304/);
    assert.deepEqual(run.refreshes, []);
    assert.deepEqual(run.heads, []);
  });

  await test('failed worker upload blocks index upload and CDN refresh', async () => {
    const run = await simulate('upload-error');
    assert.notEqual(run.status, 0);
    assert.ok(!run.stdout.includes(publishComplete));
    assert.equal(run.uploads.at(-1).at(-1), `${origin}sw.js`);
    assert.deepEqual(run.refreshes, []);
    assert.deepEqual(run.heads, []);
  });
} finally {
  // Only remove this invocation's mkdtemp directory after all shell processes have exited.
  await rm(scratch, { recursive: true, maxRetries: 3, retryDelay: 100 });
}

const summary = { passed: tests.filter(test => test.pass).length, failed: tests.filter(test => !test.pass).length };
await writeFile(output, JSON.stringify({ workflow, shellRuns, tests, simulations, summary }, null, 2) + '\n', { flag: 'wx' });
console.log('SUMMARY ' + JSON.stringify(summary));
if (summary.failed) process.exitCode = 1;
