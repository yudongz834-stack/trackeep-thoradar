import { execFileSync, spawn } from 'node:child_process';
import { createWriteStream } from 'node:fs';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { arch, release, tmpdir, version } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { finished } from 'node:stream/promises';
import { ROOT, gitRead, sha256 } from '../aicls/lib.mjs';

const name = process.argv[2] || 'sol-s2-regressions';
if (!/^[a-zA-Z0-9-]+$/.test(name)) throw new Error('Use a single evidence directory name');
const directory = join(ROOT, 'docs/tasks/T1128-SMOOTH', name);
await mkdir(directory);
const temp = resolve(tmpdir());
const prefix = 'thoradar-sol-s2-regress-';
const scratch = await mkdtemp(join(temp, prefix));
const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const chromeVersion = execFileSync('pwsh', ['-NoProfile', '-Command',
  `(Get-Item -LiteralPath '${chrome}').VersionInfo.ProductVersion`], { encoding: 'utf8' }).trim();
const metadata = {
  target: Object.fromEntries(await Promise.all(['index.html', 'sw.js', 'sw-retire.js'].map(async file =>
    [file, sha256(await readFile(join(ROOT, file)))]))),
  baseline: gitRead(['rev-parse', '73dd34e']).trim(),
  environment: { os: version(), release: release(), arch: arch(), node: process.version, chrome: chromeVersion },
  runs: 1,
  seed: null
};

const suites = [
  ['ux', 'tests/ux/ux_probe.mjs', '--base', 'sol-s2'],
  ['aicls', 'tests/aicls/aicls_regress.mjs', '--baseline', 'sols2'],
  ['poolup', 'tests/poolup/poolup_regress.mjs', '--baseline', 'sols2']
];
async function run([name, script, baseArg, label]) {
  const args = [script, '--target', 'index.html', baseArg, '73dd34e', '--label', label];
  const home = join(scratch, name);
  const env = { ...process.env, XREV_SCRATCH: home, AICLS_SCRATCH: home };
  delete env.XREV_ONLY;
  const stdout = join(directory, name + '.stdout.txt');
  const stderr = join(directory, name + '.stderr.txt');
  const stdoutStream = createWriteStream(stdout, { flags: 'wx' });
  const stderrStream = createWriteStream(stderr, { flags: 'wx' });
  const startedAt = new Date().toISOString();
  console.log('RUN node ' + args.join(' '));
  const child = spawn(process.execPath, args, { cwd: ROOT, env, windowsHide: true });
  child.stdout.pipe(stdoutStream);
  child.stderr.pipe(stderrStream);
  const [{ exitCode, signal }] = await Promise.all([
    new Promise((done, fail) => {
      child.once('error', fail);
      child.once('close', (exitCode, signal) => done({ exitCode, signal }));
    }),
    finished(stdoutStream), finished(stderrStream)
  ]);
  const log = await readFile(stdout, 'utf8');
  const endedAt = new Date().toISOString();
  if (name === 'ux') {
    await cp(join(home, 'out-' + label), join(directory, 'ux-measurements'), { recursive: true })
      .catch(error => { if (error.code !== 'ENOENT') throw error; });
  }
  const tests = Array.from(log.matchAll(/^(PASS|FAIL|SKIP)\s+(\S+)\s+(.*)$/gm), ([, result, id, title]) =>
    ({ result, id, title }));
  const summary = Object.fromEntries(['PASS', 'FAIL', 'SKIP'].map(key =>
    [key, tests.filter(test => test.result === key).length]));
  const reportedSummary = log.split(/\r?\n/).find(line => line.includes(' SUMMARY '));
  const result = { ...metadata, scriptSha256: sha256(await readFile(join(ROOT, script))),
    command: ['node', ...args], startedAt, endedAt, exitCode, signal, summary, reportedSummary, tests };
  await writeFile(join(directory, name + '.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(`${name} exit=${exitCode} ${reportedSummary || JSON.stringify(summary)}`);
  return exitCode;
}

const results = await Promise.allSettled(suites.map(run));
for (const result of results) if (result.status === 'rejected') console.error(result.reason);
if (dirname(resolve(scratch)) === temp && basename(scratch).startsWith(prefix)) {
  await rm(scratch, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
if (results.some(result => result.status === 'rejected' || result.value !== 0)) process.exitCode = 1;
