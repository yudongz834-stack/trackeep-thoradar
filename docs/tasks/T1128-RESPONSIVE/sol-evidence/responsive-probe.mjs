import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROOT, Tab, connect, freePort, gitRead, launch, startServer, wire } from '../../../../tests/aicls/lib.mjs';

const evidence = dirname(fileURLToPath(import.meta.url));
const [mode = 'compare', only] = process.argv.slice(2);
const viewports = [
  [1422, 800], [2134, 1073], [1920, 1080], [1366, 768], [1180, 900],
  [1024, 768], [901, 1000], [900, 1000], [768, 1024], [390, 844],
];
const tested = viewports.filter(([w, h]) => !only || only === `${w}x${h}`);
if (!['baseline', 'compare', 'mutation', 'serve'].includes(mode) || !tested.length) {
  throw new Error('Usage: node responsive-probe.mjs [baseline|compare|mutation|serve] [WIDTHxHEIGHT]');
}

function measure() {
  const q = selector => document.querySelector(selector);
  const all = selector => [...document.querySelectorAll(selector)].filter(e => e.checkVisibility());
  const n = value => Math.round(value * 100) / 100;
  const box = e => {
    if (typeof e === 'string') e = q(e);
    if (!e?.checkVisibility()) return null;
    const r = e.getBoundingClientRect();
    const style = getComputedStyle(e);
    return { x: n(r.x), y: n(r.y), w: n(r.width), h: n(r.height), right: n(r.right), bottom: n(r.bottom), font: style.fontSize, line: style.lineHeight };
  };
  const names = {
    header: '.topbar', deck: '.deck', queue: '.queue-panel', radar: '.scope-panel', detail: '.detail-panel',
    stage: '.scope-stage', dial: '#scope', radarHead: '.scope-head', radarFoot: '.scope-foot', footer: '.footer',
    filters: '.filters', queueList: '#queue-list', density: '.coll-head .proto-density',
    finding: '.proto-finding-text', title: '.proto-article .queue-text strong', excerpt: '#detail .excerpt',
    personal: '#coll-drawer', personalBody: '.coll-body',
  };
  const boxes = Object.fromEntries(Object.entries(names).map(([key, selector]) => [key, box(selector)]));
  const headerChildren = all('.topbar > *').map(e => ({ name: e.id || e.className, ...box(e) }));
  const filterChildren = all('.filters > *').map(e => ({ name: e.id || e.className, ...box(e) }));
  const labels = all('#scope-labels .scope-label').map(e => box(e));
  const clip = boxes.stage;
  const hits = (e, r, offsets) => offsets.map(([a, b]) => {
    const x = r.x + r.width * a;
    const y = r.y + r.height * b;
    return e.contains(document.elementFromPoint(x, y)) ? { x, y } : null;
  }).filter(Boolean);
  const samples = [[.5, .5], [.2, .2], [.8, .2], [.2, .8], [.8, .8], [.2, .5], [.8, .5], [.5, .2], [.5, .8]];
  const points = all('#blips .blip:not(.dim)').map(e => {
    const r = e.getBoundingClientRect();
    return { id: e.dataset.select, selected: e.classList.contains('selected'), center: hits(e, r, [samples[0]]).length === 1, target: hits(e, r, samples)[0] ?? null, ...box(e) };
  });
  const boundedControls = all('.topbar :is(button,input),.scope-head select,.scope-foot :is(summary,button),.filters-toggle,.filters :is(button,input),.coll-head :is(button,select),.proto-personal-tabs button');
  const controls = boundedControls.map(e => {
    const name = e.id || e.dataset.protoDensity || e.dataset.quick || e.dataset.journal || e.className || e.tagName;
    const r = e.getBoundingClientRect();
    const parent = e.closest('.topbar,.scope-panel,.queue-panel,.coll-drawer');
    const p = parent.getBoundingClientRect();
    const list = e.closest('.journal-legend');
    const scrollBox = list?.getBoundingClientRect();
    const inScrollBox = !list || (r.top >= scrollBox.top && r.bottom <= scrollBox.top + list.clientHeight);
    const inViewport = r.left >= -.5 && r.right <= innerWidth + .5 && r.top >= -.5 && r.bottom <= innerHeight + .5;
    const textClip = e.matches('button,summary,select') && e.scrollWidth > e.clientWidth + 1;
    const verticalBox = scrollBox || r;
    return {
      name, ...box(e), textClip, outsidePanel: r.left < p.left - .5 || r.right > p.right + .5 || verticalBox.top < p.top - .5 || verticalBox.bottom > p.bottom + .5,
      hit: inViewport && inScrollBox && !e.disabled ? e.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)) : null,
    };
  });
  const qRect = q('#queue-list').getBoundingClientRect();
  const firstCards = all('#queue-list > .queue-item');
  return {
    viewport: [innerWidth, innerHeight], dpr: devicePixelRatio, view: document.body.dataset.protoView,
    density: document.body.dataset.protoDensity, language: document.documentElement.lang,
    docWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth,
    grid: getComputedStyle(q('.deck')).gridTemplateColumns, filterGrid: getComputedStyle(q('.filters')).gridTemplateColumns,
    boxes, headerChildren, filterChildren, controls, points,
    clippedLabels: clip ? labels.filter(r => r.x < clip.x - .5 || r.right > clip.right + .5 || r.y < clip.y - .5 || r.bottom > clip.bottom + .5).length : 0,
    queueItems: firstCards.length,
    visibleQueueItems: firstCards.filter(e => {
      const r = e.getBoundingClientRect();
      return r.y >= qRect.y - .5 && r.bottom <= Math.min(qRect.bottom, innerHeight) + .5;
    }).length,
    findingChars: q('.proto-finding-text')?.textContent.trim().length ?? 0,
    excerptChars: q('#detail .excerpt')?.textContent.trim().length ?? 0,
    data: { date: SITE_DATA.briefing_date, injected: SITE_DATA.papers.length, merged: PAPERS.length, ids: PAPERS.map(p => p.id) },
  };
}

function judge(s, w, h, state) {
  const failures = [];
  const require = (ok, message) => { if (!ok) failures.push(message); };
  const { boxes: b } = s;
  const insideX = (item, frame) => item.x >= frame.x - .5 && item.right <= frame.right + .5;
  const separate = (a, b) => a.right <= b.x + .5 || b.right <= a.x + .5 || a.bottom <= b.y + .5 || b.bottom <= a.y + .5;
  require(s.viewport[0] === w && s.viewport[1] === h && s.dpr === 1, 'viewport and DPR');
  require(Math.max(s.docWidth, s.bodyWidth) <= w, `page horizontal overflow (${s.docWidth}/${s.bodyWidth} > ${w})`);
  for (const [i, item] of s.headerChildren.entries()) {
    require(insideX(item, b.header) && item.bottom <= b.header.bottom + .5, `header clipping ${item.name}`);
    for (const other of s.headerChildren.slice(i + 1)) require(separate(item, other), `header overlap ${item.name}/${other.name}`);
  }
  for (const c of s.controls) {
    require(!c.outsidePanel && !c.textClip, `control clipping ${c.name}`);
    require(c.hit !== false, `control center covered ${c.name}`);
  }
  if (s.view === 'personal') {
    require(b.personal && b.personalBody && b.personal.y >= b.header.bottom - 1 && b.personal.right <= w + .5, 'personal drawer placement');
    return failures;
  }
  require(Boolean(b.deck && b.queue && b.detail && b.footer), 'main panels and footer present');
  if (!b.deck || !b.queue || !b.detail || !b.footer) return failures;
  require(b.header.bottom <= b.deck.y + .5, 'header overlaps deck');
  const panels = s.view === 'overview' ? [b.queue, b.radar, b.detail] : [b.queue, b.detail];
  require(panels.every(p => p && insideX(p, b.deck)), 'panel outside deck');
  if (panels.every(Boolean)) {
    if (w > 900) {
      require(panels.every((p, i) => Math.abs(p.y - panels[0].y) <= .5 && (i === 0 || panels[i - 1].right <= p.x + .5)), 'desktop columns overlap or stack');
      require(Math.abs(b.footer.bottom - h) <= 1, 'desktop footer outside viewport');
    } else {
      const stacked = s.view === 'overview' ? [b.radar, b.detail, b.queue] : panels;
      require(stacked.every((p, i) => Math.abs(p.x - stacked[0].x) <= .5 && (i === 0 || stacked[i - 1].bottom <= p.y + .5)), 'single-column order or alignment');
    }
  }
  if (b.filters) {
    for (const [i, item] of s.filterChildren.entries()) {
      require(insideX(item, b.filters), `filter spills outside its panel: ${item.name}`);
      for (const other of s.filterChildren.slice(i + 1)) require(separate(item, other), `filter overlap ${item.name}/${other.name}`);
    }
  }
  if (s.view === 'overview') {
    require(Boolean(b.dial && b.stage && b.radarHead && b.radarFoot), 'radar and its controls present');
    if (!b.dial || !b.stage || !b.radarHead || !b.radarFoot) return failures;
    require(b.dial.w > 0 && Math.abs(b.dial.w - b.dial.h) <= .5, 'radar is square and visible');
    require(insideX(b.dial, b.stage) && b.dial.y >= b.stage.y - .5 && b.dial.bottom <= b.stage.bottom + .5, 'radar exceeds stage');
    require(b.dial.y >= b.radarHead.bottom - .5 && b.dial.bottom <= b.radarFoot.y + .5, 'radar overlaps its controls');
    require(s.clippedLabels === 0, `radar labels outside stage (${s.clippedLabels})`);
    require(s.points.length > 0 && s.points.every(p => p.target), `radar points without a pointer hit (${s.points.filter(p => !p.target).length}/${s.points.length})`);
  } else {
    const immersive = s.density === 'immersive';
    require(b.finding && s.findingChars > 0 && parseFloat(b.finding.font) >= (immersive ? 14 : 12) && b.finding.w >= 160, 'reading finding text size or width');
    require(b.excerpt && s.excerptChars > 0 && parseFloat(b.excerpt.font) >= 12 && b.excerpt.w >= 240, 'reading detail text size or width');
    if (state === 'reading') require(b.density && s.queueItems > 0 && s.visibleQueueItems > 0, 'reading controls or first card missing');
  }
  return failures;
}

async function runViewport(harness, path, dir, w, h, mutation) {
  const t = new Tab(harness, `${w}x${h}`);
  const states = {};
  const actions = {};
  const cdp = (method, params) => harness.cdp.send(method, params, t.sid);
  const shot = async name => {
    const { data } = await cdp('Page.captureScreenshot', { format: 'png' });
    writeFileSync(join(dir, `${w}x${h}-${name}.png`), Buffer.from(data, 'base64'));
  };
  const record = async (state, screenshot = false) => {
    const s = await t.eval(`(${measure})()`);
    states[state] = { ...s, failures: judge(s, w, h, state) };
    if (screenshot) await shot(state);
    return s;
  };
  const point = async ({ x, y }) => {
    await cdp('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await cdp('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  };
  const click = async selector => {
    const target = await t.eval(`(() => {
      const e = document.querySelector(${JSON.stringify(selector)});
      if (!e || e.disabled) return null;
      e.scrollIntoView({block:'center',inline:'nearest'});
      const r = e.getBoundingClientRect();
      const x = r.x + r.width / 2;
      for (const portion of [.5, .25, .75]) {
        const y = r.y + r.height * portion;
        if (e.contains(document.elementFromPoint(x,y))) return {x,y};
      }
      return null;
    })()`);
    if (target) await point(target);
    return Boolean(target);
  };
  const top = () => t.eval('window.scrollTo({top:0,left:0,behavior:"instant"}); new Promise(resolve => requestAnimationFrame(() => resolve(1)))');
  const view = (name) => t.eval(`document.body.dataset.protoView === ${JSON.stringify(name)}`);
  try {
    await t.open(`${harness.origin}/index.html`);
    await cdp('Network.enable', {});
    await cdp('Network.setBypassServiceWorker', { bypass: true });
    await cdp('Storage.clearDataForOrigin', { origin: harness.origin, storageTypes: 'all' });
    await cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w === 390 });
    await cdp('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }, { name: 'prefers-color-scheme', value: 'light' }] });
    await t.goto(`${harness.origin}${path}`);
    const overview = await record('overview', true);
    actions.overviewFilters = await click('.filters-toggle') && await t.eval('document.body.classList.contains("filters-open")');
    await top();
    await record('overview-filters');
    actions.overviewFiltersClose = await click('.filters-toggle') && await t.eval('!document.body.classList.contains("filters-open")');
    await top();
    actions.legend = await click('.jl-fold summary') && await t.eval('document.querySelector(".jl-fold").open');
    await top();
    await record('overview-legend', mutation);
    actions.legendJournal = await click('#journal-legend .journal-btn:last-child') && await t.eval('state.journal !== null');
    actions.legendClear = await click('#journal-clear') && await t.eval('state.journal === null');
    actions.legendClose = await click('.jl-fold summary') && await t.eval('!document.querySelector(".jl-fold").open');
    await top();
    const unselected = overview.points.filter(p => !p.selected && p.target).slice(0, 3);
    for (const p of unselected) {
      const current = await t.eval(`(${measure})()`);
      const hit = current.points.find(other => other.id === p.id)?.target;
      if (hit) await point(hit);
      actions[`radar:${p.id}`] = await t.eval(`String(state.selected) === ${JSON.stringify(p.id)}`);
      await top();
    }
    actions.radarTargetsExercised = unselected.length > 0;
    const selected = overview.points.find(p => p.selected && p.target);
    if (selected) {
      const current = await t.eval(`(${measure})()`);
      const hit = current.points.find(other => other.id === selected.id)?.target;
      if (hit) await point(hit);
    }
    await top();

    if ([1422, 2134, 1180, 1024, 390].includes(w)) {
      actions.readingTab = await click('#proto-tab-reading') && await view('reading');
      await top();
      await record('reading', true);
      actions.readingFilters = await click('.filters-toggle') && await t.eval('document.body.classList.contains("filters-open")');
      await record('reading-filters', true);
      actions.readingFiltersClose = await click('.filters-toggle') && await t.eval('!document.body.classList.contains("filters-open")');
      actions.immersive = await click('.coll-head [data-proto-density="immersive"]') && await t.eval('document.body.dataset.protoDensity === "immersive"');
      await record('reading-immersive');
      actions.compact = await click('.coll-head [data-proto-density="compact"]') && await t.eval('document.body.dataset.protoDensity === "compact"');
      const chosen = await t.eval('document.querySelector(".proto-article:not(.selected)")?.dataset.select');
      actions.readingCard = Boolean(chosen) && await click(`.proto-article[data-select=${JSON.stringify(chosen)}]`) && await t.eval(`String(state.selected) === ${JSON.stringify(chosen)}`);
      await top();
      if (w === 390) {
        await t.eval('document.querySelector("#detail .excerpt").scrollIntoView({block:"center",behavior:"instant"}); 1');
        await shot('reading-detail');
      }
      actions.detailMetadata = await click('.meta-fold summary') && await t.eval('document.querySelector(".meta-fold").open');
      actions.detailMetadataClose = await click('.meta-fold summary') && await t.eval('!document.querySelector(".meta-fold").open');
    }
    if ([1422, 2134, 390].includes(w)) {
      actions.personalTab = await click('#proto-tab-personal') && await view('personal');
      await record('personal', true);
      const tabs = await t.eval('[...document.querySelectorAll("[data-proto-personal-tab]")].map(e=>e.dataset.protoPersonalTab)');
      for (const tab of tabs) {
        const selector = `[data-proto-personal-tab=${JSON.stringify(tab)}]`;
        actions[`personal:${tab}`] = await click(selector) && await t.eval(`document.querySelector(${JSON.stringify(selector)}).getAttribute('aria-pressed') === 'true'`);
      }
      actions.backToOverview = await click('#proto-tab-overview') && await view('overview');
    }
    return { viewport: [w, h], emulation: w === 390 ? 'mobile viewport emulation' : 'desktop viewport emulation', states, actions, errors: t.errors };
  } finally {
    await t.close();
  }
}

const hash = text => createHash('sha256').update(text).digest('hex');
const baseline = gitRead(['show', 'HEAD:index.html']);
const target = join(ROOT, 'index.html');
const siteLine = html => html.match(/^\s*const SITE_DATA = [^\r\n]+/m)?.[0].trimStart();
const dataHash = hash(siteLine(baseline));
if (dataHash !== hash(siteLine(readFileSync(target, 'utf8')))) throw new Error('Official data differs from HEAD');
const scratch = mkdtempSync(join(evidence, '.matrix-'));
const headFile = join(scratch, 'head.html');
writeFileSync(headFile, baseline);
const server = await startServer({ target, baseline: headFile });

if (mode === 'serve') {
  console.log(`Candidate ${server.origin}/index.html | HEAD ${server.origin}/baseline.html`);
  const close = () => server.server.close(() => rmSync(scratch, { recursive: true }));
  process.once('SIGINT', close);
  process.once('SIGTERM', close);
} else {
  let browser;
  let harness;
  try {
    const chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
    browser = await launch({ chrome, profile: join(scratch, 'profile'), port: await freePort(), label: mode });
    harness = { cdp: await connect(browser.ver.webSocketDebuggerUrl), tabs: new Map(), origin: server.origin };
    wire(harness);
    const variants = { baseline: [['head', '/baseline.html']], compare: [['head', '/baseline.html'], ['candidate', '/index.html']], mutation: [['mutation', '/index.html']] }[mode];
    const headData = new Map();
    console.log(`browser=${browser.ver.Browser} origin=${server.origin} mode=${mode} SITE_DATA.sha256=${dataHash}`);
    for (const [variant, path] of variants) {
      const dir = join(evidence, variant);
      mkdirSync(dir, { recursive: true });
      const results = [];
      for (const [w, h] of tested) {
        const result = await runViewport(harness, path, dir, w, h, mode === 'mutation');
        results.push(result);
        const failures = Object.entries(result.states).flatMap(([state, s]) => s.failures.map(f => `${state}: ${f}`));
        failures.push(...Object.entries(result.actions).filter(([, ok]) => !ok).map(([action]) => `click: ${action}`), ...result.errors);
        const o = result.states.overview;
        const r = result.states.reading;
        const key = `${w}x${h}`;
        if (variant === 'head') headData.set(key, JSON.stringify(o.data));
        if (variant === 'candidate' && headData.get(key) !== JSON.stringify(o.data)) {
          failures.push('runtime paper IDs differ from HEAD');
          result.errors.push('runtime paper IDs differ from HEAD');
        }
        console.log(`${variant} ${w}x${h} ${failures.length ? 'FAIL' : 'PASS'} grid=${o.grid} dial=${o.boxes.dial?.w} stage=${o.boxes.stage?.w}x${o.boxes.stage?.h} points=${o.points.filter(p => p.target).length}/${o.points.length} overflow=${Math.max(0, o.docWidth - w, o.bodyWidth - w)} reading=${r ? `${r.boxes.finding?.font}/${r.boxes.excerpt?.font}` : '—'}${failures.length ? ' | ' + failures.join(' | ') : ''}`);
        if (variant !== 'head' && failures.length) process.exitCode = 1;
      }
      writeFileSync(join(dir, 'geometry.json'), JSON.stringify({ variant, browser: browser.ver.Browser, origin: server.origin, dataHash, results }, null, 2));
    }
  } finally {
    harness?.cdp.close();
    if (browser && await browser.stop()) process.exitCode = 2;
    await new Promise(resolve => server.server.close(resolve));
    rmSync(scratch, { recursive: true });
  }
}
