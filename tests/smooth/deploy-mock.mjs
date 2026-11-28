import { createHash } from 'node:crypto';
import { appendFileSync, readFileSync } from 'node:fs';

const [tool, ...args] = process.argv.slice(2);
const { SMOOTH_MOCK_TRACE: trace, SMOOTH_MOCK_SCENARIO: scenario, SMOOTH_RETIRE: retire } = process.env;
const prior = readFileSync(trace, 'utf8').trim().split('\n').filter(Boolean).map(line => JSON.parse(line));
appendFileSync(trace, JSON.stringify({ tool, args }) + '\n');

switch (tool) {
  case 'ossutil': {
    if (!['config', 'mb', 'website', 'cp', 'ls'].includes(args[0])) throw new Error('Unexpected ossutil command');
    if (scenario === 'upload-error' && args.at(-1) === 'oss://thoradar-online/sw.js') process.exit(1);
    break;
  }
  case 'aliyun': {
    const first = !prior.some(entry => entry.tool === 'aliyun');
    if (scenario === 'refresh-error' || (scenario === 'refresh-retry' && first)) process.exit(1);
    const missing = scenario === 'missing-task-id' || (scenario === 'id-retry' && first);
    console.log(JSON.stringify(missing ? { RequestId: 'fixture-request' } : { RefreshTaskId: '123456' }));
    break;
  }
  case 'curl': {
    const url = new URL(args.at(-1));
    if (url.protocol !== 'https:' || !['thoradar.online', 'www.thoradar.online'].includes(url.host)) {
      throw new Error('Unexpected mock curl target');
    }
    if (args.includes('--connect-to')) {
      process.stdout.write(scenario === 'preflight-304' && url.hostname.startsWith('www.') ? '304' : '200');
      break;
    }
    if (!args.includes('-I')) throw new Error('Expected a HEAD request');
    const sources = { '/': 'index.html', '/index.html': 'index.html',
      '/sw.js': retire === 'true' ? 'sw-retire.js' : 'sw.js', '/sw-retire.js': 'sw-retire.js' };
    const source = sources[url.pathname];
    if (!source) throw new Error('Unexpected mock object');
    const primary = url.href === 'https://www.thoradar.online/sw.js';
    const first = !prior.some(entry => entry.tool === 'curl' && entry.args.includes('-I') && entry.args.at(-1) === url.href);
    if (primary && scenario === 'head-error') process.exit(28);
    const stale = primary && (scenario === 'wrong-md5' || (scenario === 'stale-then-current' && first));
    const body = stale ? 'stale CDN entry' : readFileSync(source);
    const status = primary && scenario === 'worker-404' ? '404 Not Found' : '200 OK';
    const mime = source.endsWith('.js') && !(primary && scenario === 'wrong-mime')
      ? 'Application/JavaScript ; charset=utf-8' : 'text/html; charset=utf-8';
    const retireUrl = url.href === 'https://www.thoradar.online/sw-retire.js';
    const cache = source.endsWith('.js') && !(retireUrl && scenario === 'worker-cacheable')
      ? 'max-age=0, No-Store' : 'public, max-age=60, s-maxage=3600';
    const md5 = createHash('md5').update(body).digest('base64');
    process.stdout.write([
      'HTTP/1.1 200 Connection established', 'Content-MD5: proxy', '', `HTTP/2 ${status}`,
      `cOnTenT-mD5: ${md5}  `, `content-type: ${mime}`, `Cache-Control: ${cache}`, '', ''
    ].join('\r\n'));
    break;
  }
  case 'sleep': break;
  default: throw new Error(`Unexpected mock command ${tool}`);
}
