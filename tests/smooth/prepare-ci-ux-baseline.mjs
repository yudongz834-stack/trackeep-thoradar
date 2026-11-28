import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { ROOT, gitRead, norm, sha256 } from '../aicls/lib.mjs';
import { parseOfficialData, splitOfficialData } from './official-data.mjs';

const [revision, output] = process.argv.slice(2);
if (!revision || !output) {
  throw new Error('Usage: node tests/smooth/prepare-ci-ux-baseline.mjs <release-sha> <baseline.html>');
}
const head = gitRead(['rev-parse', 'HEAD']).trim();
if (revision !== head) throw new Error('The release SHA must match the checked-out HEAD');
const parent = gitRead(['rev-parse', `${head}^1`]).trim();
const currentHtml = gitRead(['show', `${head}:index.html`]);
if (norm(await readFile(join(ROOT, 'index.html'), 'utf8')) !== norm(currentHtml)) {
  throw new Error('The UX target index.html differs from the release revision');
}

const parentHtml = gitRead(['show', `${parent}:index.html`]);
const parentPage = splitOfficialData(parentHtml);
const currentPage = splitOfficialData(currentHtml);
const currentData = parseOfficialData(currentPage.block);
const baseline = parentPage.before + currentPage.block + parentPage.after;
const prepared = splitOfficialData(baseline);
if (prepared.before !== parentPage.before || prepared.after !== parentPage.after ||
    prepared.block !== currentPage.block) {
  throw new Error('The UX baseline must contain the first-parent shell and the release SITE_DATA block');
}

await writeFile(output, baseline, { flag: 'wx' });
console.log(JSON.stringify({ revision, parent, output, briefingDate: currentData.briefing_date,
  paperCount: currentData.papers.length, parentDataSha256: sha256(parentPage.block),
  releaseDataSha256: sha256(currentPage.block), baselineSha256: sha256(baseline) }));
