import { registerHooks } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const output = process.argv[2];
if (!output) throw new Error('Usage: node replay-neon-v2.mjs <output.json>');
const verifier = pathToFileURL(resolve('../trackeep-thoradar-neon-v1/tests/neon-v2-verify.mjs')).href;
const candidateLib = pathToFileURL(resolve('tests/aicls/lib.mjs')).href;
const oldAnchor = String.raw`    if (typeof data.briefing_date !== \'string\' || !Array.isArray(data.papers)) return null;`;
const newAnchor = '    if (!isBriefingDate(data.briefing_date) || !Array.isArray(data.papers)) return null;';

// Read the candidate from this worktree. Update the source-text mutation anchor in memory.
registerHooks({
  resolve(specifier, context, nextResolve) {
    const fromVerifier = context.parentURL === verifier && specifier === './aicls/lib.mjs';
    return nextResolve(fromVerifier ? candidateLib : specifier, context);
  },
  load(url, context, nextLoad) {
    const loaded = nextLoad(url, context);
    if (url !== verifier) return loaded;
    const source = Buffer.from(loaded.source).toString('utf8');
    if (source.split(oldAnchor).length !== 2) throw new Error('Neon date anchor mismatch');
    return { ...loaded, source: source.replace(oldAnchor, newAnchor) };
  }
});

process.argv = [process.execPath, fileURLToPath(verifier), output];
await import(verifier);
