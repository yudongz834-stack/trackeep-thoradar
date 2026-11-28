import { createHash } from 'node:crypto';
import { appendFileSync, readFileSync } from 'node:fs';

const [tool, ...args] = process.argv.slice(2);
const { SMOOTH_MOCK_TRACE: trace, SMOOTH_MOCK_SCENARIO: scenario, SMOOTH_RETIRE: retire,
  SMOOTH_MOCK_BLOB_MD5: blobMd5 } = process.env;
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
    const isWww = url.hostname === 'www.thoradar.online';
    const wwwWorker = isWww && url.pathname === '/sw.js';
    const wwwRetire = isWww && url.pathname === '/sw-retire.js';
    const proxyHeaders = ['HTTP/1.1 200 Connection established', 'Content-MD5: proxy', 'Location: https://proxy.invalid/', ''];
    const servesWwwIndex = (scenario === 'www-root-200' && url.pathname === '/') ||
      (scenario === 'www-index-200' && url.pathname === '/index.html');
    if ((isWww && !wwwWorker && !wwwRetire && !servesWwwIndex) || (wwwWorker && scenario === 'www-worker-redirect')) {
      const wrongHost = scenario === 'www-redirect-wrong-host' && url.search === '?from=www';
      const status = scenario === 'www-redirect-302' ? '302 Found' :
        url.pathname === '/index.html' || wrongHost ? '308 Permanent Redirect' : '301 Moved Permanently';
      const host = wrongHost ? 'other.invalid' : 'thoradar.online';
      const targetPath = scenario === 'www-redirect-wrong-location' ? '/index.html' : url.pathname;
      const query = scenario === 'www-redirect-lost-query' ? '' : url.search;
      process.stdout.write([...proxyHeaders, `HTTP/2 ${status}`,
        `lOcAtIoN: https://${host}${targetPath}${query}  `, 'Content-Type: application/octet-stream', '', ''].join('\r\n'));
      break;
    }
    const wwwWorkerSource = scenario === 'www-active-worker' ? 'sw.js' :
      scenario === 'www-worker-html' ? 'index.html' : 'sw-retire.js';
    const sources = { '/': 'index.html', '/index.html': 'index.html',
      '/sw.js': isWww ? wwwWorkerSource : retire === 'true' ? 'sw-retire.js' : 'sw.js',
      '/sw-retire.js': 'sw-retire.js' };
    const source = sources[url.pathname];
    if (!source) throw new Error('Unexpected mock object');
    const first = !prior.some(entry => entry.tool === 'curl' && entry.args.includes('-I') && entry.args.at(-1) === url.href);
    if (wwwWorker && scenario === 'head-error') process.exit(28);
    const waited = prior.filter(entry => entry.tool === 'sleep').reduce((seconds, entry) => seconds + Number(entry.args[0]), 0);
    const stale = (wwwWorker && (scenario === 'wrong-md5' || (scenario === 'stale-then-current' && first))) ||
      (!isWww && url.pathname === '/sw.js' && scenario === 'stale-during-propagation' && waited < 360);
    const status = wwwWorker && scenario === 'worker-404' ? '404 Not Found' : '200 OK';
    const homepageOctetStream = !isWww && (
      (scenario === 'homepage-octet-stream-root' && url.pathname === '/') ||
      (scenario === 'homepage-octet-stream-index' && url.pathname === '/index.html'));
    let mime = source.endsWith('.js') && !(wwwWorker && scenario === 'wrong-mime')
      ? 'Application/JavaScript ; charset=utf-8' : 'text/html; charset=utf-8';
    if (homepageOctetStream) mime = 'application/octet-stream';
    const cache = source.endsWith('.js') && !(wwwRetire && scenario === 'worker-cacheable')
      ? 'max-age=0, No-Store' : 'public, max-age=60, s-maxage=3600';
    const md5 = stale ? createHash('md5').update('stale CDN entry').digest('base64') : JSON.parse(blobMd5)[source];
    process.stdout.write([
      ...proxyHeaders, `HTTP/2 ${status}`,
      `cOnTenT-mD5: ${md5}  `, `content-type: ${mime}`, `Cache-Control: ${cache}`, '', ''
    ].join('\r\n'));
    break;
  }
  case 'sleep': break;
  default: throw new Error(`Unexpected mock command ${tool}`);
}
