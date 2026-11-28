import { execFileSync, spawnSync } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const repo = process.cwd();
const evidence = resolve(process.argv[2]);
const daily = '28131f3';
const gateBase = '73dd34e';
const scratch = await mkdtemp(join(tmpdir(), 'thoradar-s5-daily-'));
const tree = join(scratch, 'tree');
const git = (args, options = {}) => execFileSync('git', args, { cwd: repo, encoding: 'utf8', ...options });
const files = ['index.html', 'sw.js', 'sw-retire.js', 'tests/smooth', '.github/workflows/deploy_oss.yml'];
const blockPattern = /\/\*__THORADAR_DATA_START__\*\/[\s\S]*?\/\*__THORADAR_DATA_END__\*\//;

try {
  await mkdir(tree);
  const archive = join(scratch, 'daily.tar');
  git(['archive', '--format=tar', `--output=${archive}`, daily]);
  execFileSync('tar', ['-xf', 'daily.tar', '-C', 'tree'], { cwd: scratch });
  const env = { ...process.env, GIT_DIR: git(['rev-parse', '--absolute-git-dir']).trim(),
    GIT_WORK_TREE: tree, GIT_INDEX_FILE: join(scratch, 'index'), GIT_OPTIONAL_LOCKS: '0',
    XREV_SCRATCH: join(scratch, 'ux') };
  delete env.XREV_ONLY;
  git(['read-tree', daily], { cwd: tree, env });
  const fresh = await readFile(join(tree, 'index.html'), 'utf8');
  for (const file of files) await cp(join(repo, file), join(tree, file), { recursive: true });
  const html = await readFile(join(tree, 'index.html'), 'utf8');
  const today = fresh.match(blockPattern)?.[0];
  const previous = html.match(blockPattern)?.[0];
  if (!today || !previous || today.replaceAll('\r\n', '\n') === previous.replaceAll('\r\n', '\n')) {
    throw new Error('Daily data fixture did not change');
  }
  await writeFile(join(tree, 'index.html'), html.replace(blockPattern, () => today));
  const runs = [];
  for (const [name, ...args] of [
    ['source', 'tests/smooth/verify-source.mjs', join(evidence, 'daily-source.json')],
    ['ux', 'tests/ux/ux_probe.mjs', '--target', 'index.html', '--base', gateBase, '--label', 's5-daily']
  ]) {
    const run = spawnSync(process.execPath, args, { cwd: tree, env, encoding: 'utf8', windowsHide: true, maxBuffer: 4 * 1024 * 1024 });
    if (run.error) throw run.error;
    await writeFile(join(evidence, `daily-${name}.stdout.txt`), run.stdout);
    await writeFile(join(evidence, `daily-${name}.stderr.txt`), run.stderr);
    runs.push({ name, command: ['node', ...args], exitCode: run.status });
    console.log(`${name} exit=${run.status}`);
    for (const line of run.stdout.split(/\r?\n/).filter(line => /^FAIL |SUMMARY|cleanup/.test(line))) console.log(line);
  }
  await writeFile(join(evidence, 'daily.run.json'), JSON.stringify({
    daily: git(['rev-parse', daily]).trim(), gateBase, runs,
    candidateDate: previous.match(/"briefing_date":"([^"]+)"/)?.[1],
    dailyDate: today.match(/"briefing_date":"([^"]+)"/)?.[1]
  }, null, 2) + '\n');
  if (runs.some(run => run.exitCode !== 1)) process.exitCode = 1;
} finally {
  await rm(scratch, { recursive: true, maxRetries: 3, retryDelay: 100 });
}
