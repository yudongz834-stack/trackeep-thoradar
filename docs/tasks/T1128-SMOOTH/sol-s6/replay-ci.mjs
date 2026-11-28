import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { cp, mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

const [c1Path, s5Path, releasePath, outputPath] = process.argv.slice(2);
if (!outputPath) throw new Error('Usage: node replay-ci.mjs <S6-worktree> <untouched-S5-worktree> <C2-release-tree> <new-evidence-dir>');
const [c1, s5, release, output] = [c1Path, s5Path, releasePath, outputPath].map(path => resolve(path));
await mkdir(output);
const scratch = await mkdtemp(join(tmpdir(), 'thoradar-s6-replay-'));
const tree = join(scratch, 'runner');
const runnerTemp = join(scratch, 'runner-temp');
await mkdir(runnerTemp);
const runs = [];
const products = ['index.html', 'sw.js', 'sw-retire.js'];
const gates = ['.github/workflows/deploy_oss.yml', 'tests/smooth/verify-deploy.mjs', 'tests/smooth/verify-source.mjs',
  'tests/smooth/official-data.mjs', 'tests/smooth/prepare-ci-ux-baseline.mjs', 'tests/ux/ux_probe.mjs'];
const officialDaily = '28131f314f92a05227fd5923607d717c426da2c5';
const source = 'tests/smooth/verify-source.mjs';
const prep = 'tests/smooth/prepare-ci-ux-baseline.mjs';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const lf = html => html.replaceAll('\r\n', '\n');
const env = { ...process.env, RUNNER_TEMP: runnerTemp, XREV_SCRATCH: join(runnerTemp, 'smooth-ux') };
for (const key of ['XREV_ONLY', 'XREV_CAND_HTML', 'XREV_SHOTS']) delete env[key];

const exec = (file, args, cwd) => {
  const result = spawnSync(file, args, { cwd, env, windowsHide: true, maxBuffer: 16 * 1024 * 1024 });
  if (result.error) throw result.error;
  return result;
};
const gitCommand = ['-c', 'core.hooksPath=NUL', '-c', 'user.name=S6 fixture', '-c', 'user.email=s6@example.invalid'];
const git = (args, cwd = tree) => {
  const result = exec('git', [...gitCommand, ...args], cwd);
  assert.equal(result.status, 0, result.stderr.toString());
  return result.stdout;
};
const gitText = (args, cwd) => git(args, cwd).toString('utf8').trim();
const commit = message => {
  git(['commit', '--no-gpg-sign', '-m', message]);
  return gitText(['rev-parse', 'HEAD']);
};
async function run(id, file, args, expected, cwd = tree) {
  const result = exec(file, args, cwd);
  const record = { id, cwd, command: [file === process.execPath ? 'node' : file, ...args], expected, exitCode: result.status };
  runs.push(record);
  await writeFile(join(output, `${id}.stdout.txt`), result.stdout, { flag: 'wx' });
  await writeFile(join(output, `${id}.stderr.txt`), result.stderr, { flag: 'wx' });
  console.log(`${id} exit=${result.status} expected=${expected}`);
  assert.equal(result.status, expected, result.stderr.toString());
  return result;
}
const readResult = async name => JSON.parse(await readFile(join(output, `${name}.json`), 'utf8'));
const node = (id, args, expected = 0) => run(id, process.execPath, args, expected);
const checkSource = async (id, name, expected, status = 1, ci = true) => {
  await node(id, [source, join(output, `${id}.json`), ...(ci ? ['--ci'] : [])], status);
  const result = await readResult(id);
  assert.equal(result.checks.find(check => check.name === name)?.pass, expected, `${id} ${name}`);
  return result;
};
const dataParts = html => {
  const match = /\/\*__THORADAR_DATA_START__\*\/[\s\S]*?\/\*__THORADAR_DATA_END__\*\//.exec(html);
  assert.ok(match, 'fixture markers missing');
  return [html.slice(0, match.index), match[0], html.slice(match.index + match[0].length)];
};
const replace = (text, from, to) => {
  const changed = text.replace(from, () => to);
  assert.ok(changed !== text, `fixture mutation did not change ${from}`);
  return changed;
};
async function withMutation(file, transform, test) {
  const path = join(tree, file);
  const backup = join(await mkdtemp(join(scratch, 'restore-')), 'original');
  await cp(path, backup);
  try {
    await writeFile(path, transform(await readFile(backup, 'utf8')));
    return await test();
  } finally {
    await cp(backup, path);
  }
}
const snapshots = async root => Object.fromEntries(await Promise.all(products.map(async file =>
  [file, hash(await readFile(join(root, file)))])));
const baselineLine = 'const baseline = parentPage.before + currentPage.block + parentPage.after;';

let worktreeAdded = false;
let cleanup;
try {
  const c1Before = await snapshots(c1);
  const releaseBefore = await snapshots(release);
  assert.deepEqual(c1Before, await snapshots(s5));
  await run('add-fixture', 'git', [...gitCommand, 'worktree', 'add', '--detach', tree, `${officialDaily}^1`], 0, c1);
  worktreeAdded = true;
  for (const name of [...products, '.github/workflows/deploy_oss.yml', 'tests/smooth']) {
    await cp(join(s5, name), join(tree, name), { recursive: true });
  }
  git(['add', '--', ...products, '.github/workflows/deploy_oss.yml', 'tests/smooth']);
  const s5Fixture = commit('S6 local fixture: S5 worktree inputs');
  for (const name of gates) await cp(join(c1, name), join(tree, name));
  git(['add', '--', ...gates]);
  const s6Fixture = commit('S6 local fixture: daily-compatible verification');
  const patch = await run('candidate-diff', 'git', ['diff', '--binary', s5Fixture, s6Fixture, '--'], 0);
  await writeFile(join(output, 'candidate.diff'), patch.stdout);
  await run('candidate-diff-check', 'git', ['diff', '--check', s5Fixture, s6Fixture, '--'], 0);
  assert.deepEqual(gitText(['diff', '--name-only', s5Fixture, s6Fixture]).split(/\r?\n/).sort(), [...gates].sort());
  await run('candidate-patch-reverse-check', 'git', ['apply', '--reverse', '--check', join(output, 'candidate.diff')], 0);

  // A difference outside the data block makes a self-baseline distinguishable from the first parent.
  const beforeDaily = lf(await readFile(join(tree, 'index.html'), 'utf8'));
  const parentMarker = '<meta name="s6-fixture-parent" content="first-parent-shell">';
  await writeFile(join(tree, 'index.html'), replace(beforeDaily, '</head>', `${parentMarker}\n</head>`));
  git(['add', '--', 'index.html']);
  const parent = commit('S6 local fixture: identify the first-parent shell');
  const dailyPaths = gitText(['diff', '--name-only', `${officialDaily}^1`, officialDaily]).split(/\r?\n/);
  assert.equal(dailyPaths.length, 16);
  for (const name of dailyPaths.filter(path => path !== 'index.html')) {
    await mkdir(dirname(join(tree, name)), { recursive: true });
    await writeFile(join(tree, name), git(['show', `${officialDaily}:${name}`]));
  }
  await cp(join(release, 'index.html'), join(tree, 'index.html'));
  const currentHtml = await readFile(join(tree, 'index.html'), 'utf8');
  const [parentBefore, parentBlock, parentAfter] = dataParts(git(['show', `${parent}:index.html`]).toString('utf8'));
  const [, currentBlock] = dataParts(lf(currentHtml));
  assert.ok(currentBlock === dataParts(git(['show', `${officialDaily}:index.html`]).toString('utf8'))[1]);
  assert.ok(parentBlock !== currentBlock && !currentHtml.includes(parentMarker));
  git(['add', '--', ...dailyPaths]);
  const daily = commit('S6 local fixture: replay all 16 files from the real daily update');
  assert.equal(gitText(['rev-parse', `${daily}^1`]), parent);
  assert.deepEqual(gitText(['diff', '--name-only', parent, daily]).split(/\r?\n/), dailyPaths);
  assert.deepEqual(await snapshots(tree), releaseBefore);
  assert.equal(gitText(['status', '--porcelain=v1', '-uall']), '');
  await run('daily-clean-before', 'git', ['status', '--porcelain=v1', '-uall'], 0);
  env.GITHUB_SHA = daily;

  const checked = await checkSource('source-ci-daily', 'official-data', true, 0);
  assert.equal(checked.scopeBaseline, daily);
  const scope = checked.checks.find(check => check.name === 'write-scope');
  assert.deepEqual([scope.tracked, scope.untracked], [[], []]);
  const strict = await checkSource('source-local-daily', 'official-data', false, 1, false);
  assert.ok(strict.checks.find(check => check.name === 'write-scope').outOfScope.includes('feed.xml'));

  const baseline = join(runnerTemp, 'smooth-ux-baseline.html');
  const prepared = await node('prepare-baseline', [prep, daily, baseline]);
  const metadata = JSON.parse(prepared.stdout.toString());
  assert.equal(metadata.parent, parent);
  assert.equal(metadata.briefingDate, '2026-11-28');
  assert.equal(metadata.paperCount, 43);
  const correctBaseline = html => {
    const [before, block, after] = dataParts(html);
    return before === parentBefore && block === currentBlock && after === parentAfter;
  };
  assert.ok(correctBaseline(await readFile(baseline, 'utf8')));
  const ux = ['tests/ux/ux_probe.mjs', '--target', 'index.html'];
  const liveUx = await node('ux-ci-daily', [...ux, '--base-html', baseline, '--label', 'smooth-ci']);
  const uxStdout = liveUx.stdout.toString();
  assert.match(uxStdout, /^==== UX PROBE \[smooth-ci\] SUMMARY 46 PASS \/ 0 FAIL：/m);
  assert.doesNotMatch(uxStdout, /^SKIP /m);
  for (const id of ['F8a', 'F8b', 'F8c', 'F8d']) assert.match(uxStdout, new RegExp(`^PASS ${id} `, 'm'));
  await cp(join(env.XREV_SCRATCH, 'out-smooth-ci'), join(output, 'ux-ci-measurements'), { recursive: true });

  const staleBaseline = join(runnerTemp, 'unmodified-parent.html');
  await writeFile(staleBaseline, git(['show', `${parent}:index.html`]));
  const stale = await node('ux-ci-stale-parent', [...ux, '--base-html', staleBaseline, '--only', 'F8', '--label', 's6-stale'], 1);
  for (const id of ['F8a', 'F8b', 'F8c']) assert.match(stale.stdout.toString(), new RegExp(`FAIL[^\n]*${id}`));
  await cp(join(env.XREV_SCRATCH, 'out-s6-stale'), join(output, 'ux-stale-measurements'), { recursive: true });

  const badJson = html => replace(html, 'const SITE_DATA = {', 'const SITE_DATA = {,');
  const invalidDate = html => replace(html, '"briefing_date":"2026-11-28"', '"briefing_date":"2026-02-29"');
  await withMutation('index.html', badJson, () => checkSource('source-bad-json', 'official-data', false));
  await withMutation('index.html', invalidDate, () => checkSource('source-invalid-date', 'official-data', false));
  await withMutation('index.html', html => {
    const [before, block, after] = dataParts(html);
    const data = JSON.parse(block.match(/const SITE_DATA = (\{.*\});/)[1]);
    return before + replace(block, /\{.*\};/, `${JSON.stringify({ ...data, papers: {} })};`) + after;
  }, () => checkSource('source-invalid-papers', 'official-data', false));
  await withMutation('index.html', html => replace(html, 'const INJECTED_PAPERS=', 'const INJECTED_PAPERS=/* changed */'),
    () => checkSource('source-initialization-change', 'official-paper-initialization', false));
  await withMutation('index.html', html => replace(html, 'function mergePapers(', 'function changedMergePapers('),
    () => checkSource('source-merge-change', 'official-window-and-merge', false));
  await withMutation('feed.xml', html => `${html.trimEnd()}\n<!-- S6 fixture write -->\n`, async () => {
    const result = await checkSource('source-dirty-feed', 'write-scope', false);
    assert.deepEqual(result.checks.find(check => check.name === 'write-scope').outOfScope, ['feed.xml']);
  });
  const feed = await readFile(join(tree, 'feed.xml'));
  try {
    await withMutation('feed.xml', html => `${html.trimEnd()}\n<!-- S6 fixture staged write -->\n`,
      () => git(['add', '--', 'feed.xml']));
    const result = await checkSource('source-staged-feed', 'write-scope', false);
    assert.deepEqual(result.checks.find(check => check.name === 'write-scope').outOfScope, ['feed.xml']);
  } finally {
    git(['reset', '--', 'feed.xml']);
    assert.deepEqual(await readFile(join(tree, 'feed.xml')), feed);
  }

  for (const [id, bad] of [
    ['prepare-old-data', 'parentPage.before + parentPage.block + parentPage.after'],
    ['prepare-wrong-block', 'parentPage.before + currentPage.block.replace("const SITE_DATA", "const WRONG_DATA") + parentPage.after'],
    ['prepare-self-baseline', 'currentHtml']
  ]) {
    const path = join(runnerTemp, `${id}.html`);
    const result = await withMutation(prep, script => replace(script, baselineLine, `const baseline = ${bad};`),
      () => node(id, [prep, daily, path], 1));
    assert.match(result.stderr.toString(), /must contain the first-parent shell and the release SITE_DATA block/);
    await assert.rejects(readFile(path), { code: 'ENOENT' });
  }
  await node('prepare-wrong-sha', [prep, parent, join(runnerTemp, 'wrong-sha.html')], 1);

  // Removing the validator lets bad data through. The earlier rejection assertions catch that regression.
  const parser = 'tests/smooth/official-data.mjs';
  await withMutation(parser, script => replace(script, 'data = JSON.parse(declaration[1]);',
    'data = { briefing_date: "2026-11-28", papers: [] };'),
  () => withMutation('index.html', badJson, () => checkSource('mutation-no-json-parser', 'official-data', true, 0)));
  await withMutation(parser, script => replace(script, ' ||\n      !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date', ''),
    () => withMutation('index.html', invalidDate, () => checkSource('mutation-no-calendar-check', 'official-data', true, 0)));

  const bypassPath = join(runnerTemp, 'mutant-baseline.html');
  await withMutation(prep, script => {
    const wrong = replace(script, baselineLine, 'const baseline = parentHtml;');
    return replace(wrong, /const prepared = splitOfficialData\(baseline\);[\s\S]+?(?=await writeFile)/, '');
  }, () => node('mutation-no-baseline-guard', [prep, daily, bypassPath]));
  assert.equal(correctBaseline(await readFile(bypassPath, 'utf8')), false, 'Independent baseline check must reject old data');

  assert.equal(gitText(['status', '--porcelain=v1', '-uall']), '');
  await run('daily-clean-after', 'git', ['status', '--porcelain=v1', '-uall'], 0);
  const c1After = await snapshots(c1);
  const releaseAfter = await snapshots(release);
  assert.deepEqual(c1After, c1Before);
  assert.deepEqual(releaseAfter, releaseBefore);
  assert.deepEqual(await snapshots(tree), releaseBefore);
  await writeFile(join(output, 'daily-case.json'), JSON.stringify({ officialDaily, s5Fixture, s6Fixture, parent, daily,
    dailyPaths, parentMarker, prepare: metadata, c1Before, c1After, releaseBefore, releaseAfter,
    oracleRejectedUnguardedStaleBaseline: true }, null, 2) + '\n');
} finally {
  if (worktreeAdded) {
    assert.equal(dirname(tree), scratch);
    assert.equal(dirname(scratch), resolve(tmpdir()));
    cleanup = await run('remove-fixture', 'git', [...gitCommand, 'worktree', 'remove', '--force', tree], 0, c1);
  }
  await writeFile(join(output, 'daily.runs.json'), JSON.stringify({ scratch, worktreeRemoved: cleanup?.status === 0, runs }, null, 2) + '\n');
}
