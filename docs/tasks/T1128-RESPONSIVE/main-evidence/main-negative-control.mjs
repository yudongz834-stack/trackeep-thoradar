import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, renameSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const evidence = fileURLToPath(new URL('./', import.meta.url));
const root = fileURLToPath(new URL('../../../../', import.meta.url));
const target = join(root, 'index.html');
const probe = join(evidence, 'responsive-probe.mjs');
const original = readFileSync(target);
const originalHash = createHash('sha256').update(original).digest('hex');
const needle = 'grid-template-columns:240px minmax(0,1fr) 315px';
const replacement = 'grid-template-columns:240px minmax(360px,1fr) 315px';
const text = original.toString('utf8');
assert.equal(text.split(needle).length - 1, 1, 'expected exactly one narrow-desktop grid rule');
writeFileSync(join(evidence, 'index.before-main-negative.html'), original);
let run = null;
let harnessError = null;
try {
  writeFileSync(target, Buffer.from(text.replace(needle, replacement), 'utf8'));
  run = spawnSync(process.execPath, [probe, 'mutation', '901x1000'], { cwd: root, encoding: 'utf8', timeout: 180000 });
  writeFileSync(join(evidence, 'negative.stdout.txt'), run.stdout || '');
  writeFileSync(join(evidence, 'negative.stderr.txt'), run.stderr || '');
} catch (error) {
  harnessError = String(error);
} finally {
  const temporary = join(root, `.index-main-restore-${process.pid}.tmp`);
  writeFileSync(temporary, original);
  renameSync(temporary, target);
}
const restoredHash = createHash('sha256').update(readFileSync(target)).digest('hex');
const restored = restoredHash === originalHash;
const discriminating = !harnessError && run && run.status === 1 && (run.stdout || '').includes('page horizontal overflow');
const result = {
  mutation: 'restore the old 360px minimum middle column at 901x1000',
  expectedFailure: 'page horizontal overflow',
  probeExit: run?.status ?? null,
  probeSignal: run?.signal ?? null,
  harnessError,
  discriminating: Boolean(discriminating),
  restored,
  originalHash,
  restoredHash,
};
writeFileSync(join(evidence, 'negative-result.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result));
if (!result.discriminating || !result.restored) process.exitCode = 1;
