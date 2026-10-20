// Loxa Partner Onboarding Console. One front end, two modes:
//  local:  served by console.py, runs both agents live on any URL in seconds
//  static: hosted on GitHub Pages, shows runs published by GitHub Actions; new URLs run via Actions
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = v => (v ?? 0).toLocaleString('en-GB');
const gbp = v => v == null || isNaN(v) ? 'n/a' : '£' + Math.round(v).toLocaleString('en-GB');
const median = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m-1] + s[m]) / 2; };
const countBy = (rows, f) => { const m = {}; rows.forEach(r => { const k = f(r) || 'Unknown'; m[k] = (m[k] || 0) + 1; }); return Object.entries(m).sort((a, b) => b[1] - a[1]); };
const C = {dial:'#0F1B33', gold:'#C9A227', emerald:'#1F9D7A', amber:'#D99A1E', ruby:'#C8433A', sapphire:'#2F5BEA', steel:'#EDF0F4', line:'#D8DEE7', muted:'#8E9AB3', plum:'#6D597A'};
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
let MODE = 'local', SITE = null, RUN = null, ISSUE_SCOPE = 'run', ISSUE_FILTER = null;

// What each view shows, and why it matters. Shared by the i buttons and the Start here tour.
const INFO = {
  runbar:   ['Enter a partner website', 'Type any retailer\'s address and both agents start.', 'Nothing is hard-coded, so the same tool onboards every future partner.'],
  live:     ['Two agents, side by side', 'Agent 1 reads the catalogue while Agent 2 reads the tech stack.', 'This is the work that normally fills the first two weeks of onboarding.'],
  ready:    ['Integration readiness', 'How ready the partner is to integrate, from 0 to 100.', 'Tells the team which partners can launch fast and which need scoping first.'],
  subdials: ['The catalogue at a glance', 'Catalogue size, stock, share in the launch plan, and the typical ticket.', 'Sizes the opportunity before anyone opens a spreadsheet.'],
  track:    ['Onboarding track', 'The five onboarding steps from the launch plan, and what the agents already completed.', 'Shows what is done, what needs a person, and what comes next.'],
  stock:    ['Stock position', 'Share of SKUs in stock, out of stock, or unknown.', 'In-stock items can be covered from day one.'],
  phases:   ['Launch phases', 'SKUs in each roll-out phase: core watches, then Rolex and Patek, then jewellery.', 'Launch order follows claims complexity, which protects the partner\'s trust.'],
  nextstep: ['Recommended next step', 'The agents\' first integration move for this partner.', 'Turns analysis into an action the partner\'s developers can take.'],
  a1proof:  ['How the catalogue was gathered', 'Route, number of requests, time taken, and robots.txt.', 'Respectful crawling protects the relationship with the partner.'],
  phasemap: ['Launch Phase Map', 'The live catalogue mapped onto the three launch phases.', 'Shows what each phase is worth before committing to dates.'],
  brands:   ['Brands and categories', 'SKUs by brand and category, after names are cleaned up.', 'Brand mix decides which cover to launch first.'],
  prices:   ['Price bands', 'How many SKUs sit in each price band.', 'Ticket size sets premium levels and claim exposure.'],
  quality:  ['Data quality', 'Duplicates removed, missing data, and pages that could not be read.', 'Gaps are shown, not hidden, so nobody prices cover on bad data.'],
  calc:     ['Cover Opportunity Calculator', 'Turns the live median ticket into premium per month. Orders and rate are inputs.', 'Links the catalogue straight to the commercial case.'],
  catalogue:['Full catalogue', 'Every SKU with price, stock and launch phase.', 'This is the export the integration team uploads.'],
  platform: ['Platform', 'The e-commerce platform, how sure the agent is, and the evidence.', 'The platform decides how Loxa plugs into the site.'],
  waterfall:['Where the score comes from', 'Starts at 100 and subtracts each risk found.', 'Every lost point is explained, so the score can be challenged.'],
  checklist:['Engineer checklist', 'Risks and open questions as tick-boxes.', 'Gives the partner\'s developers a shared to-do list.'],
  widgets:  ['Already on the site', 'Finance, reviews, rival cover, payments, consent and analytics tools.', 'Rival cover or finance offers can compete with Loxa at the same moment.'],
  signals:  ['Signal reliability', 'Each finding with its source and confidence.', 'Separates what was seen directly from what a person must confirm.'],
  ask:      ['Ask the agents', 'Ask about this partner. Answers come from this run\'s data.', 'Answers leadership or developer questions on the spot, with sources.'],
  problems: ['Problems log', 'Every error, warning and review item across runs, with a fix.', 'Nothing is hidden: problems are logged and actionable.'],
  crm:      ['Send to CRM', 'Will send the snapshot into the CRM.', 'The account team gets one source of truth from day one.'],
};
const ib = key => `<button class="i" data-info="${key}" aria-label="What is this?">i</button>`;
const head = (title, key, extra = '') => `<div class="panel-h"><h3>${title}</h3><span class="sp"></span>${extra}${ib(key)}</div>`;

// ---------------- SVG instruments ----------------
function bezel(score, size = 240) {
  const c = size / 2, col = score >= 80 ? C.emerald : score >= 60 ? C.gold : C.ruby, r = size * 0.36, circ = 2 * Math.PI * r;
  let ticks = '';
  for (let i = 0; i < 60; i++) {
    const a = i * 6 * Math.PI / 180, major = i % 5 === 0, r1 = size * (major ? 0.40 : 0.425), r2 = size * 0.455;
    ticks += `<line x1="${c + r1 * Math.sin(a)}" y1="${c - r1 * Math.cos(a)}" x2="${c + r2 * Math.sin(a)}" y2="${c - r2 * Math.cos(a)}" stroke="${major ? '#E3C766' : '#3A4E7C'}" stroke-width="${major ? 2.5 : 1.2}"/>`;
  }
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="Readiness ${score} out of 100">
    <circle cx="${c}" cy="${c}" r="${size * 0.48}" fill="none" stroke="${C.gold}" stroke-width="5"/>${ticks}
    <circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="#24365C" stroke-width="12"/>
    <circle class="arc" cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${col}" stroke-width="12" stroke-linecap="round" stroke-dasharray="0 ${circ}" data-to="${circ * score / 100} ${circ}" transform="rotate(-90 ${c} ${c})" style="transition:stroke-dasharray 1.2s ease"/>
    <g class="hand" style="transform-origin:${c}px ${c}px;transform:rotate(0deg);transition:transform 1.2s cubic-bezier(.3,1.3,.5,1)" data-to="${score * 3.6}">
      <line x1="${c}" y1="${c + 14}" x2="${c}" y2="${c - r + 6}" stroke="${C.gold}" stroke-width="3" stroke-linecap="round"/></g>
    <circle cx="${c}" cy="${c}" r="6" fill="${C.gold}"/>
    <text x="${c}" y="${c + size * 0.2}" text-anchor="middle" fill="#fff" font-family="Bahnschrift,Segoe UI,sans-serif" font-size="${size * 0.17}" class="num">${score}</text></svg>`;
}
function subdial(text, frac, color, size = 92) {
  const c = size / 2, r = size * 0.4, circ = 2 * Math.PI * r;
  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${C.steel}" stroke-width="7"/>
    <circle class="arc" cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${color}" stroke-width="7" stroke-linecap="round" stroke-dasharray="0 ${circ}" data-to="${circ * Math.max(0, Math.min(1, frac))} ${circ}" transform="rotate(-90 ${c} ${c})" style="transition:stroke-dasharray 1s ease"/>
    <text x="${c}" y="${c + 6}" text-anchor="middle" font-family="Bahnschrift,Segoe UI,sans-serif" font-size="${text.length > 6 ? 15 : 19}" fill="${C.dial}">${esc(text)}</text></svg>`;
}
function donut(segs, center, sub, size = 168) {
  const c = size / 2, r = size * 0.36, circ = 2 * Math.PI * r, total = segs.reduce((a, s) => a + s.value, 0) || 1;
  let off = 0, arcs = '';
  segs.forEach(s => { const len = circ * s.value / total; if (len > 0) arcs += `<circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${s.color}" stroke-width="${size * 0.14}" stroke-dasharray="${len} ${circ - len}" stroke-dashoffset="${-off}" transform="rotate(-90 ${c} ${c})"><title>${esc(s.label)}: ${num(s.value)}</title></circle>`; off += len; });
  return `<div style="text-align:center"><svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}"><circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${C.steel}" stroke-width="${size * 0.14}"/>${arcs}
    <text x="${c}" y="${c + 2}" text-anchor="middle" font-family="Bahnschrift,Segoe UI,sans-serif" font-size="26" fill="${C.dial}">${esc(center)}</text>
    <text x="${c}" y="${c + 22}" text-anchor="middle" font-family="Segoe UI,sans-serif" font-size="12" fill="#5E6A7D">${esc(sub)}</text></svg>
    <div class="legend">${segs.filter(s => s.value).map(s => `<span><i style="background:${s.color}"></i>${esc(s.label)} ${num(s.value)}</span>`).join('')}</div></div>`;
}
const hbars = (items, color, n = 7) => { const top = Math.max(1, ...items.map(i => i[1])); return items.slice(0, n).map(([k, v]) => `<div class="hbar"><span class="lb" title="${esc(k)}">${esc(k)}</span><div class="tr"><div class="f" style="width:0;background:${color}" data-w="${100 * v / top}%"></div></div><span class="n">${num(v)}</span></div>`).join('') || '<p class="lead">No data</p>'; };
function animate() {
  requestAnimationFrame(() => requestAnimationFrame(() => {
    $$('.arc[data-to]').forEach(a => { a.setAttribute('stroke-dasharray', a.dataset.to); a.removeAttribute('data-to'); });
    $$('.hand[data-to]').forEach(h => { h.style.transform = `rotate(${h.dataset.to}deg)`; h.removeAttribute('data-to'); });
    $$('.f[data-w]').forEach(f => { f.style.width = f.dataset.w; f.removeAttribute('data-w'); });
    $$('.col[data-h]').forEach(f => { f.style.height = f.dataset.h; f.removeAttribute('data-h'); });
  }));
}

// ---------------- data helpers ----------------
function parseSlug(t) {  // mirrors core/agents.py parse_target
  let s = t.trim(); if (!/^https?:\/\//.test(s)) s = 'https://' + s;
  try { const u = new URL(s); return (u.host.toLowerCase() + u.pathname.replace(/\/+$/, '')).replace('www.', '').replace(/[^a-z0-9.\-]+/g, '-').replace(/^-+|-+$/g, ''); } catch { return ''; }
}
const api = async (path, body) => { const r = await fetch(path, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {}); if (!r.ok) throw new Error(r.status); return r.json(); };
function download(name, text, type = 'text/plain') {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {type})); a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function toCSV(rows) {
  const cols = ['name', 'brand', 'category_path', 'variant', 'sku', 'price', 'currency', 'price_on_application', 'availability', 'product_url', 'source', 'phase'];
  const q = v => /[",\n]/.test(String(v ?? '')) ? `"${String(v).replace(/"/g, '""')}"` : String(v ?? '');
  return [cols.join(','), ...rows.map(r => cols.map(c => q(r[c])).join(','))].join('\n');
}
const sourceChip = (run, agent) => {
  if (MODE === 'static') return `<span class="chip">Run on GitHub, ${esc((run.meta || {}).started || '')}</span>`;
  const s = run.meta && run.meta.agents && run.meta.agents[agent] && run.meta.agents[agent].source;
  return s === 'snapshot' ? '<span class="chip snap">Saved backup</span>' : '<span class="chip live">Live</span>';
};

// ---------------- start-up ----------------
async function init() {
  const isStatic = document.querySelector('meta[name=loxa-mode]')?.content === 'static';
  if (isStatic) { SITE = await api('data/site.json'); MODE = 'static'; }
  else { SITE = await api('api/info'); MODE = 'local'; }
  $('#target').value = SITE.default_url || '';
  $('#examples').innerHTML = SITE.examples.map(q => `<button class="ex">${esc(q)}</button>`).join('');
  const latest = MODE === 'static' && SITE.runs[0] ? SITE.runs[0].readiness : null;
  $('#hero-dial').innerHTML = `<div class="dialpanel">${bezel(latest ?? 72, 300)}<div class="eff">${latest != null ? 'Readiness of the latest partner run' : 'Run a partner to set the dial'}</div></div>`;
  animate();
  if (MODE === 'local') { try { setTests(await api('api/selftest')); } catch { setTests(null); } }
  else { setTests(SITE.tests); const first = SITE.runs.find(r => r.slug === parseSlug(SITE.default_url || '')) || SITE.runs[0]; if (first) await openRun(first.slug, false); }
  refreshCount();
}
function setTests(st) {
  const vals = st ? Object.values(st) : [], p = vals.reduce((a, b) => a + b.passed, 0), t = vals.reduce((a, b) => a + b.total, 0), ok = vals.length && vals.every(v => v.ok);
  $('#testpill').className = 'testpill ' + (vals.length ? (ok ? 'ok' : 'bad') : '');
  $('#testpill').innerHTML = `<span class="led"></span><span>${vals.length ? `${p}/${t} self-test checks passed${MODE === 'static' ? ' on GitHub' : ''}` : 'Self-test unavailable'}</span>`;
}

// ---------------- views ----------------
function showView(v) {
  ['landing', 'live', 'snapshot', 'a1', 'a2', 'ask', 'problems'].forEach(x => $('#v-' + x).classList.toggle('hidden', x !== v));
  $$('#nav button').forEach(b => b.classList.toggle('on', b.dataset.view === v));
  if (v === 'problems') renderProblems();
  window.scrollTo({top: 0});
  animate();
}
function enableNav(on) { ['snapshot', 'a1', 'a2', 'ask'].forEach(v => $('#nav-' + v).disabled = !on); }

// ---------------- running ----------------
const STEPS = {harvester: ['Discover', 'Collect', 'Export', 'Report'], profiler: ['Read', 'Detect', 'Scan', 'Brief']};
function liveShell(base) {
  $('#v-live').innerHTML = `<div class="panel-h"><h2>Agents at work</h2><span class="sp"></span>${ib('live')}</div>
   <p class="lead" style="margin:0 0 14px">${esc(base)}</p>
   <div class="live"><div class="clock" id="clock"></div>
   ${['harvester', 'profiler'].map((a, i) => `<div class="panel agentrun"><div class="panel-h"><h3>Agent ${i + 1} · ${a === 'harvester' ? 'SKU Harvester' : 'Integration Profiler'}</h3><span class="sp"></span><span class="state" id="st-${a}">queued</span></div>
     <div class="steps">${STEPS[a].map((s, k) => `<div class="stp" id="stp-${a}-${k}"><span class="dot"></span>${s}</div>`).join('')}</div>
     <details class="log"><summary>Show log</summary><div class="term" id="log-${a}"></div></details></div>`).join('')}</div>`;
  showView('live'); clock(0);
}
function clock(sec) {
  const c = 100; let ticks = '';
  for (let i = 0; i < 60; i++) { const a = i * 6 * Math.PI / 180, r1 = i % 5 ? 82 : 76; ticks += `<line x1="${c + r1 * Math.sin(a)}" y1="${c - r1 * Math.cos(a)}" x2="${c + 88 * Math.sin(a)}" y2="${c - 88 * Math.cos(a)}" stroke="${i % 5 ? '#3A4E7C' : '#E3C766'}" stroke-width="${i % 5 ? 1.2 : 2.4}"/>`; }
  const a = sec * 6 * Math.PI / 180;
  $('#clock').innerHTML = `<svg viewBox="0 0 200 200" width="190" height="190"><circle cx="100" cy="100" r="95" fill="none" stroke="${C.gold}" stroke-width="4"/>${ticks}
    <line x1="${100 - 12 * Math.sin(a)}" y1="${100 + 12 * Math.cos(a)}" x2="${100 + 78 * Math.sin(a)}" y2="${100 - 78 * Math.cos(a)}" stroke="${C.gold}" stroke-width="2.5" stroke-linecap="round"/><circle cx="100" cy="100" r="5" fill="${C.gold}"/>
    <text x="100" y="146" text-anchor="middle" fill="#fff" font-family="Bahnschrift,Segoe UI,sans-serif" font-size="22">${sec.toFixed(1)}s</text></svg>`;
}
function logLine(l) {
  const el = $('#log-' + l.agent); if (!el) return;
  el.textContent += `${l.t.toFixed(1)}s  ${l.line}\n`; el.scrollTop = el.scrollHeight;
  const m = /\[(\d)\/4\]/.exec(l.line);
  if (m) { const k = +m[1] - 1; STEPS[l.agent].forEach((_, i) => { const s = $(`#stp-${l.agent}-${i}`); if (s) s.className = 'stp' + (i < k ? ' done' : i === k ? ' on' : ''); }); }
}
function setState(a, s) {
  const el = $('#st-' + a); if (!el) return; el.className = 'state ' + s; el.textContent = s;
  if (s === 'done') STEPS[a].forEach((_, i) => { const x = $(`#stp-${a}-${i}`); if (x) x.className = 'stp done'; });
}
async function startRun(target) {
  target = (target || '').trim(); if (!target) return;
  if (MODE === 'static') return staticRun(target);
  $('#runbtn').disabled = true; $('#runbtn').textContent = 'Running';
  let res; try { res = await api('api/run', {target}); } catch { $('#runbtn').disabled = false; $('#runbtn').textContent = 'Run both agents'; return; }
  liveShell(target);
  let since = 0;
  const poll = async () => {
    const v = await api(`api/job/${res.id}?since=${since}`); since = v.log_len;
    clock(v.elapsed); v.log.forEach(logLine); Object.entries(v.state).forEach(([a, s]) => setState(a, s));
    if (v.done) { $('#runbtn').disabled = false; $('#runbtn').textContent = 'Run both agents'; setTimeout(() => show(v), 700); }
    else setTimeout(poll, 350);
  };
  poll();
}
async function staticRun(target) {
  const slug = parseSlug(target), hit = SITE.runs.find(r => r.slug === slug);
  if (!hit) return notPublished(target);
  await openRun(slug, true);
}
async function openRun(slug, replay) {
  const run = await api(`data/${slug}.json`);
  if (!replay || reduce) return show(run);
  liveShell(run.base);  // replays the recorded GitHub run so viewers see how it worked
  const log = run.log || [], dur = 2600, last = Math.max(0.1, ...log.map(l => l.t)), t0 = performance.now();
  ['harvester', 'profiler'].forEach(a => setState(a, 'running'));
  let i = 0;
  const tick = () => {
    const el = (performance.now() - t0) / dur * last;
    clock(Math.min(el, last));
    while (i < log.length && log[i].t <= el) logLine(log[i++]);
    if (el < last) requestAnimationFrame(tick);
    else { while (i < log.length) logLine(log[i++]); ['harvester', 'profiler'].forEach(a => setState(a, run.result[a] ? 'done' : 'failed')); setTimeout(() => show(run), 600); }
  };
  tick();
}
function notPublished(target) {
  const repo = SITE.repo || '', url = repo ? `https://github.com/${repo}/actions/workflows/dashboard.yml` : '#';
  modal(`<h4>Run ${esc(target)} on GitHub</h4>
    <p class="what">This page is hosted on GitHub, which runs the agents for it. Open the workflow, press <b>Run workflow</b>, and paste the address.</p>
    <p class="why">It takes about two minutes, then this dashboard republishes with the new partner. On a laptop running the console, the same run takes seconds.</p>
    <div class="ctrl"><span class="dots"></span><button class="btn ghost" data-close>Close</button><a class="btn gold" href="${url}" target="_blank" rel="noopener" style="text-decoration:none">Open GitHub Actions</a></div>`);
}

// ---------------- results ----------------
function show(run) {
  RUN = run; enableNav(true);
  renderSnapshot(run); renderA1(run); renderA2(run);
  $('#answers').innerHTML = '';
  showView('snapshot'); refreshCount();
}
function trackSteps(h, p) {
  const shop = p && p.platform.name === 'Shopify';
  return [
    ['Plan check', p ? (shop ? 'Confirm Shopify plan' : 'Confirm platform') : 'Needs a person', 'review'],
    ['Catalogue', h ? `${num(h.coverage.skus)} SKUs ready` : 'Not harvested', h ? 'done' : 'review'],
    ['Integrate', p ? (shop ? 'Product and cart widget' : 'Scope with developers') : 'Pending', 'next'],
    ['Test', 'Test policy and refund in staging', ''],
    ['Go live', 'Watches first', ''],
  ];
}
function renderSnapshot(run) {
  const h = run.result.harvester, p = run.result.profiler, rows = h ? h.rows : [];
  const inStock = rows.filter(r => r.availability === 'in_stock').length, priced = rows.filter(r => r.price).map(r => +r.price);
  const inPlan = rows.filter(r => r.phase && r.phase !== 'Not in launch plan').length, med = median(priced), maxP = Math.max(1, ...priced);
  const phaseCols = [C.emerald, C.gold, C.sapphire, C.line];
  const phases = h ? [...h.phases.map(x => x.name), 'Not in launch plan'].map((n, i) => ({label: n.replace(' · ', ', '), value: rows.filter(r => r.phase === n).length, color: phaseCols[i]})) : [];
  const avail = [['in_stock', 'In stock', C.emerald], ['out_of_stock', 'Out of stock', C.ruby], ['preorder', 'Pre-order', C.amber], ['unknown', 'Unknown', C.line]].map(([k, l, c]) => ({label: l, value: rows.filter(r => r.availability === k).length, color: c}));
  $('#v-snapshot').innerHTML = `
   <div class="partner"><h1>${esc(run.slug)}</h1>${p ? `<span class="chip"><b>${esc(p.platform.name)}</b></span>` : ''}${sourceChip(run, 'harvester')}<span class="chip">Both agents in <b>${(run.meta || {}).seconds ?? '–'}s</b></span></div>
   <div class="grid g-snap">
     <div class="dialpanel" id="dial-ready">${ib('ready')}<h3>Integration readiness</h3>${p ? bezel(p.readiness.score) + `<div class="band">${esc(p.readiness.band)}</div><div class="eff">${esc(p.readiness.effort)}</div>` : '<p>No profile for this run</p>'}</div>
     <div>
       <div class="subdials" id="subdials">
         ${[[h ? num(h.coverage.skus) : '–', 1, C.dial, 'SKUs harvested'], [rows.length ? Math.round(100 * inStock / rows.length) + '%' : '–', inStock / Math.max(1, rows.length), C.emerald, 'In stock'],
            [rows.length ? Math.round(100 * inPlan / rows.length) + '%' : '–', inPlan / Math.max(1, rows.length), C.gold, 'In launch plan'], [med ? gbp(med) : '–', med ? med / maxP : 0, C.sapphire, 'Median ticket']]
           .map(([t, f, c, l]) => `<div class="subdial">${subdial(String(t), f, c)}<div class="lab">${l}</div></div>`).join('')}
       </div>
       <div class="panel mt" id="track">${head('Onboarding track', 'track')}
         <div class="track">${trackSteps(h, p).map(([t, s, st], i) => `<div class="tstep ${st}"><div class="n">${st === 'done' ? '✓' : i + 1}</div><b>${t}</b><small>${esc(s)}</small></div>`).join('')}</div></div>
     </div>
   </div>
   <div class="grid g3 mt" id="snap-charts">
     <div class="panel" id="snap-stock">${head('Stock position', 'stock')}${donut(avail, rows.length ? Math.round(100 * inStock / rows.length) + '%' : '–', 'in stock')}</div>
     <div class="panel" id="snap-phases">${head('Launch phases', 'phases')}${donut(phases, num(inPlan), 'SKUs in plan')}</div>
     <div class="nextstep" id="nextstep"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="${C.gold}" stroke-width="2" style="flex:none"><circle cx="12" cy="12" r="9"/><path d="M10 8l4 4-4 4"/></svg>
       <div><h3 style="color:#fff">Recommended next step</h3><p>${p ? esc(p.recommendation.approach) : 'Run Agent 2 to get a recommendation.'}</p></div></div>
   </div>`;
}
function renderA1(run) {
  const h = run.result.harvester;
  if (!h) { $('#v-a1').innerHTML = '<div class="panel"><h2>Agent 1 returned no catalogue for this site</h2><p class="lead">See the Problems log for the reason and the fix.</p></div>'; return; }
  const c = h.coverage, rows = h.rows, priced = rows.filter(r => r.price).map(r => +r.price);
  const cols = [C.emerald, C.gold, C.sapphire, C.line];
  const phases = [...h.phases.map(p => p.name), 'Not in launch plan'].map((name, k) => { const pr = rows.filter(r => r.phase === name), pp = pr.filter(r => r.price).map(r => +r.price);
    return {name, skus: pr.length, stock: pr.filter(r => r.availability === 'in_stock').length, med: median(pp), col: cols[k], why: (h.phases[k] || {why: 'Outside the brief: confirm scope'}).why}; });
  const bands = [[0, 1000], [1000, 5000], [5000, 10000], [10000, 25000], [25000, 1e12]].map(([a, b]) => [b > 1e11 ? '£25k+' : `£${a / 1000}k–${b / 1000}k`, priced.filter(p => p >= a && p < b).length]);
  const topBand = Math.max(1, ...bands.map(b => b[1]));
  $('#v-a1').innerHTML = `
   <div class="partner"><h1>Agent 1 · SKU Harvester</h1>${sourceChip(run, 'harvester')}</div>
   <div class="panel" id="a1-proof">${head('How the catalogue was gathered', 'a1proof', `<button class="chip" data-dl="csv">Download catalogue.csv</button><button class="chip" data-dl="cov">coverage.json</button>`)}
     <span class="chip">Route <b>${esc(c.strategy.replaceAll('_', ' '))}</b></span><span class="chip"><b>${c.requests_made}</b> requests</span><span class="chip"><b>${c.duration_seconds}s</b></span>
     <span class="chip"><b>${c.delay_seconds}s</b> between requests</span><span class="chip">robots.txt <b>${c.robots_found ? 'honoured' : 'not found'}</b></span>${c.quick_scan_limit ? `<span class="chip">Quick scan <b>${c.quick_scan_limit}</b> pages</span>` : ''}</div>
   <div class="panel mt" id="phasemap">${head('Launch Phase Map', 'phasemap', '<span class="tag">Own initiative</span>')}
     <div class="stack">${phases.map(p => `<div style="width:${100 * p.skus / Math.max(1, rows.length)}%;background:${p.col}" title="${esc(p.name)}: ${p.skus}"></div>`).join('')}</div>
     <div class="phasecards">${phases.map(p => `<div class="phasecard" style="border-top-color:${p.col}"><small>${esc(p.name)}</small><div class="num">${num(p.skus)}</div><small>${num(p.stock)} in stock, median ${gbp(p.med)}</small><small><i>${esc(p.why)}</i></small></div>`).join('')}</div></div>
   <div class="grid g2 mt">
     <div class="panel" id="brands">${head('Brands', 'brands')}${hbars(countBy(rows, r => r.brand), C.dial)}</div>
     <div class="panel" id="prices">${head('Price bands', 'prices')}<div class="hist">${bands.map(([l, v]) => `<div><div class="v">${num(v)}</div><div class="col" style="height:0" data-h="${Math.max(3, 110 * v / topBand)}px"></div>${l}</div>`).join('')}</div></div>
     <div class="panel">${head('Categories', 'brands')}${hbars(countBy(rows, r => (r.category_path || '').split(' > ')[0]), C.plum)}</div>
     <div class="panel" id="quality">${head('Data quality', 'quality')}<div class="quality">${[['Duplicates removed', c.duplicates_removed], ['Missing SKU', c.missing_sku], ['Price on application', c.price_on_application], ['Need a JavaScript render', c.needs_render], ['Failed pages', c.failed_pages], ['Skipped by robots.txt', c.blocked_by_robots]].map(([k, v]) => `<div><div class="num" style="color:${v ? C.amber : C.emerald}">${v}</div><small>${k}</small></div>`).join('')}</div></div>
   </div>
   <div class="panel mt" id="calc">${head('Cover Opportunity Calculator', 'calc', '<span class="tag">Own initiative</span>')}
     <div class="grid g2"><div class="calc">
       <select id="scope" aria-label="Scope">${['All SKUs', ...phases.filter(p => p.skus).map(p => p.name)].map(s => `<option>${esc(s)}</option>`).join('')}</select>
       <label>Orders per month <b id="ov"></b></label><input id="orders" type="range" min="10" max="2000" step="10" value="100">
       <label>Attach rate <b id="av"></b></label><input id="attach" type="range" min="1" max="40" value="10">
       <label>Premium, % of item value <b id="pv"></b></label><input id="prem" type="range" min="1" max="15" step="0.5" value="5">
       <p class="note">Only the ticket size is live data. Orders and premium rate are inputs; IPT at the 12% standard rate.</p></div>
       <div class="calcout" id="calcout"></div></div></div>
   <div class="panel mt" id="catalogue">${head('Full catalogue', 'catalogue')}<input class="search" id="csearch" placeholder="Search name, brand, category or SKU">
     <div class="tw"><table><thead><tr><th>Name</th><th>Brand</th><th>Category</th><th>Price</th><th>Stock</th><th>Phase</th></tr></thead><tbody id="ctb"></tbody></table></div><p class="note" id="ctn"></p></div>`;
  const draw = q => { q = q.toLowerCase(); const m = rows.filter(r => !q || [r.name, r.brand, r.category_path, r.sku].join(' ').toLowerCase().includes(q));
    $('#ctb').innerHTML = m.slice(0, 250).map(r => `<tr><td><a href="${esc(r.product_url)}" target="_blank" rel="noopener">${esc(r.name)}</a>${r.variant ? ` <small>${esc(r.variant)}</small>` : ''}</td><td>${esc(r.brand)}</td><td>${esc(r.category_path)}</td><td class="num">${r.price ? gbp(+r.price) : 'POA'}</td><td>${esc(r.availability.replaceAll('_', ' '))}</td><td>${esc(r.phase)}</td></tr>`).join('');
    $('#ctn').textContent = `${num(m.length)} SKUs${m.length > 250 ? ', first 250 shown' : ''}`; };
  $('#csearch').oninput = e => draw(e.target.value); draw('');
  const calc = () => { const s = $('#scope').value, o = +$('#orders').value, a = +$('#attach').value / 100, pr = +$('#prem').value / 100;
    $('#ov').textContent = num(o); $('#av').textContent = $('#attach').value + '%'; $('#pv').textContent = $('#prem').value + '%';
    const pool = (s === 'All SKUs' ? rows : rows.filter(r => r.phase === s)).filter(r => r.price).map(r => +r.price), tk = median(pool) || 0, pol = o * a, prm = tk * pr;
    $('#calcout').innerHTML = [['Median ticket, live', gbp(tk)], ['Premium per policy', gbp(prm)], ['Policies per month', num(Math.round(pol))], ['Customer pays incl. IPT', gbp(prm * 1.12)], ['Premium per month', gbp(pol * prm)], ['First 90 days', gbp(pol * prm * 3)]]
      .map(([k, v]) => `<div><div class="num">${v}</div><small>${k}</small></div>`).join(''); };
  ['scope', 'orders', 'attach', 'prem'].forEach(id => $('#' + id).oninput = calc); calc();
}
function renderA2(run) {
  const p = run.result.profiler;
  if (!p) { $('#v-a2').innerHTML = '<div class="panel"><h2>Agent 2 returned no profile for this site</h2><p class="lead">See the Problems log for the reason and the fix.</p></div>'; return; }
  const w = p.widgets, c = p.checkout, r = p.readiness, items = [...p.risk_flags, ...p.human_review];
  const conf = p.platform.confidence, confCol = conf >= .8 ? C.emerald : conf >= .6 ? C.gold : C.ruby;
  const cap = x => x.charAt(0).toUpperCase() + x.slice(1);
  const ded = r.deductions.map(d => { const m = /^-(\d+)\s+(.*)$/.exec(d); return m ? [+m[1], cap(m[2])] : [0, cap(d)]; });
  const SRC = {header: C.emerald, html: C.plum, probe: C.sapphire, inferred: C.amber};
  const fams = [['BNPL and finance', w.bnpl, 'warn'], ['Rival protection', w.protection.filter(x => x !== 'Loxa'), 'risk'], ['Reviews and trust', w.trust, 'ok'], ['Payments', w.payments, 'ok'], ['Cookie consent', w.consent, 'ok'], ['Analytics', w.analytics, 'ok']];
  let at = 100;
  const wfRows = ded.map(([n, t]) => { const row = `<div class="r"><span>${esc(t)}</span><div class="bar"><div style="left:${at - n}%;width:${n}%;background:${C.ruby}"></div></div><span class="num" style="color:${C.ruby}">−${n}</span></div>`; at -= n; return row; }).join('');
  $('#v-a2').innerHTML = `
   <div class="partner"><h1>Agent 2 · Integration Profiler</h1>${sourceChip(run, 'profiler')}<span class="chip"><b>Read-only</b>, no cart actions</span></div>
   <div class="grid g-snap">
     <div class="panel" id="a2-platform">${head('Platform', 'platform', '<button class="chip" data-dl="brief">Download brief.md</button>')}
       <div class="platform">${subdial(Math.round(conf * 100) + '%', conf, confCol, 110)}<div><div class="num" style="font-size:30px">${esc(p.platform.name)}</div>
         <div>${p.platform.evidence.map(e => `<span class="chip">${esc(e.signal)}</span>`).join('')}</div></div></div>
       <div class="quality mt">${[['Checkout', c.type], ['Steps', c.steps], ['GTM', p.gtm_containers.join(', ') || 'Not found'], ['GA4', p.ga4_ids.join(', ') || 'Not found'], ['Requests', p.requests_made], ['Time', p.duration_seconds + 's']]
         .map(([k, v]) => `<div><small>${k}</small><div style="font-weight:600;font-size:14px">${esc(v)}</div></div>`).join('')}</div></div>
     <div class="panel" id="waterfall">${head('Where the readiness score comes from', 'waterfall', '<span class="tag">Own initiative</span>')}
       <div class="wf"><div class="r"><span>Starting score</span><div class="bar"><div style="left:0;width:100%;background:${C.dial}"></div></div><span class="num">100</span></div>${wfRows}
       <div class="r"><b>Readiness</b><div class="bar"><div style="left:0;width:${r.score}%;background:${r.score >= 80 ? C.emerald : r.score >= 60 ? C.gold : C.ruby}"></div></div><b class="num">${r.score}</b></div></div>
       <p class="note">${esc(r.band)}. ${esc(r.effort)}.</p></div>
   </div>
   <div class="panel mt" id="widgets">${head('Already on the site', 'widgets')}<div class="widgets">
     ${fams.map(([t, xs, kind]) => { const found = xs && xs.length, col = !found ? C.line : kind === 'risk' ? C.ruby : kind === 'warn' ? C.amber : C.emerald;
       return `<div class="wtile"><div class="hd"><span class="st" style="background:${col}">${found ? (kind === 'ok' ? '✓' : '!') : '–'}</span>${t}</div>${found ? xs.map(x => `<span class="chip">${esc(x)}</span>`).join('') : '<small class="lead">None found</small>'}</div>`; }).join('')}</div></div>
   <div class="grid g2 mt">
     <div class="panel check" id="checklist">${head('Engineer checklist', 'checklist')}<div class="prog"><div id="pg" style="width:0"></div></div><small class="lead" id="pl"></small>
       ${items.map(x => `<label><input type="checkbox">${esc(x)}</label>`).join('')}</div>
     <div class="panel" id="signals">${head('Signal reliability', 'signals')}<table class="sig"><thead><tr><th>Finding</th><th>Source</th><th>Confidence</th></tr></thead><tbody>
       ${p.signals.map(s => `<tr><td>${esc(s.finding)}<br><small class="lead">${esc(s.evidence)}</small></td><td><span class="dot" style="background:${SRC[s.source] || C.line}"></span>${esc(s.source)}</td><td><span class="cbar"><div style="width:${s.confidence * 100}%;background:${s.confidence >= .8 ? C.emerald : s.confidence >= .6 ? C.gold : C.amber}"></div></span>${Math.round(s.confidence * 100)}%</td></tr>`).join('')}</tbody></table></div>
   </div>
   <div class="nextstep mt"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="${C.gold}" stroke-width="2" style="flex:none"><circle cx="12" cy="12" r="9"/><path d="M10 8l4 4-4 4"/></svg>
     <div><h3 style="color:#fff">Recommended Loxa approach</h3><p>${esc(p.recommendation.approach)}</p><p>${esc(p.recommendation.reasoning)}</p></div></div>`;
  const boxes = $$('#checklist input'), upd = () => { const n = boxes.filter(b => b.checked).length; $('#pg').style.width = (100 * n / Math.max(1, boxes.length)) + '%'; $('#pl').textContent = `${n} of ${boxes.length} done`; };
  boxes.forEach(b => b.onchange = upd); upd();
}

// ---------------- ask ----------------
function fmtAnswer(text) {
  return text.split(/\n\n/).map(block => { const out = []; let list = [];
    block.split('\n').forEach(l => { if (/^\s*-\s+/.test(l)) list.push(`<li>${esc(l.replace(/^\s*-\s+/, ''))}</li>`); else { if (list.length) { out.push(`<ul>${list.join('')}</ul>`); list = []; } if (l.trim()) out.push(`<p>${esc(l)}</p>`); } });
    if (list.length) out.push(`<ul>${list.join('')}</ul>`); return out.join(''); }).join('');
}
async function ask(q) {
  q = q.trim(); if (!q || !RUN) return;
  const box = document.createElement('div'); box.className = 'ans'; box.innerHTML = `<div class="q">${esc(q)}</div><p class="lead">Asking the agents</p>`;
  $('#answers').prepend(box);
  let r = null;
  if (MODE === 'local') { try { r = await api('api/ask', {run_id: RUN.id, question: q}); } catch { r = null; } }
  if (!r) r = LoxaAnswer.builtin(q, RUN.result.harvester, RUN.result.profiler);
  box.innerHTML = `<div class="q">${esc(q)}</div>${fmtAnswer(r.answer)}<div class="meta">${r.sources.map(s => `<span class="chip">${esc(s)}</span>`).join('')}<span class="chip">${esc(r.method)}</span></div>`;
}

// ---------------- problems log ----------------
const SEV = [['error', 'Errors', C.ruby, '!'], ['warning', 'Warnings', C.amber, '!'], ['review', 'Needs a person', C.sapphire, '?'], ['info', 'Info', C.muted, 'i']];
async function getIssues(scope) {
  if (MODE === 'local') { try { return await api(scope === 'run' && RUN ? `api/issues?run=${RUN.id}` : 'api/issues'); } catch { return []; } }
  if (scope === 'run' && RUN) return RUN.issues || [];
  const all = await Promise.all(SITE.runs.map(r => api(`data/${r.slug}.json`).catch(() => ({issues: []}))));
  return all.flatMap(r => r.issues || []);
}
async function refreshCount() {
  const list = await getIssues(RUN ? 'run' : 'all'), n = list.filter(i => i.severity === 'error' || i.severity === 'warning').length;
  $('#pcount').textContent = n; $('#pcount').className = 'count' + (n ? '' : ' zero');
}
async function renderProblems() {
  const list = await getIssues(RUN ? ISSUE_SCOPE : 'all');
  const shown = ISSUE_FILTER ? list.filter(i => i.severity === ISSUE_FILTER) : list;
  $('#v-problems').innerHTML = `<div class="panel-h"><h2>Problems log</h2><span class="sp"></span>
     ${RUN ? `<div class="seg"><button data-scope="run" class="${ISSUE_SCOPE === 'run' ? 'on' : ''}">This run</button><button data-scope="all" class="${ISSUE_SCOPE === 'all' ? 'on' : ''}">All runs</button></div>` : ''}${ib('problems')}</div>
   <div class="sev mt" id="sevtiles">${SEV.map(([k, l, col]) => `<button class="sevtile ${ISSUE_FILTER === k ? 'on' : ''}" data-sev="${k}" style="border-top-color:${col}"><div class="num">${list.filter(i => i.severity === k).length}</div><small>${l}</small></button>`).join('')}</div>
   <div class="panel mt">${shown.length ? shown.map(i => { const s = SEV.find(x => x[0] === i.severity) || SEV[3];
     return `<div class="issue"><span class="ic" style="background:${s[2]}">${s[3]}</span><div><div class="t">${esc(i.title)}</div><div class="f">Fix: ${esc(i.fix)}</div></div><div class="m">${esc(i.agent)}, ${esc(i.kind)}<br>${esc(i.target)}<br>${esc(i.at)}</div></div>`; }).join('')
     : '<p class="lead">No problems logged for this selection.</p>'}</div>`;
}

// ---------------- recent runs menu, info pop-ups, modal ----------------
async function runsMenu(btn) {
  closeFloat();
  const list = MODE === 'local' ? await api('api/history').catch(() => []) : SITE.runs.map(r => ({id: r.slug, target: r.target, started: r.started}));
  const m = document.createElement('div'); m.className = 'menu float';
  m.innerHTML = list.length ? list.map(r => `<button data-open="${esc(r.id)}">${esc(r.target)}<br><small>${esc(r.started)}</small></button>`).join('') : '<p class="lead" style="padding:8px">No runs yet</p>';
  document.body.appendChild(m); const b = btn.getBoundingClientRect();
  m.style.left = (b.right + 8) + 'px'; m.style.top = Math.max(8, b.bottom - m.offsetHeight) + window.scrollY + 'px';
}
function infoPop(btn) {
  closeFloat();
  const [t, what, why] = INFO[btn.dataset.info], p = document.createElement('div'); p.className = 'pop float';
  p.innerHTML = `<h4>${t}</h4><p>${what}</p><p class="why">Why it matters: ${why}</p>`;
  document.body.appendChild(p); const b = btn.getBoundingClientRect();
  p.style.left = Math.max(8, Math.min(innerWidth - p.offsetWidth - 8, b.right - p.offsetWidth)) + 'px'; p.style.top = (b.bottom + 8 + window.scrollY) + 'px';
}
const closeFloat = () => $$('.float').forEach(f => f.remove());
function modal(html) {
  closeTour(); const v = document.createElement('div'); v.className = 'tour-veil'; v.style.background = 'rgba(15,27,51,.62)';
  const c = document.createElement('div'); c.className = 'tour-card tour-welcome'; c.innerHTML = html;
  document.body.append(v, c); v.onclick = closeTour;
}

// ---------------- Start here: guided tour ----------------
const TOUR = [
  {sel: '.runbar', key: 'runbar', view: null},
  {sel: '#dial-ready', key: 'ready', view: 'snapshot'},
  {sel: '#subdials', key: 'subdials', view: 'snapshot'},
  {sel: '#track', key: 'track', view: 'snapshot'},
  {sel: '#snap-phases', key: 'phases', view: 'snapshot'},
  {sel: '#nextstep', key: 'nextstep', view: 'snapshot'},
  {sel: '#a1-proof', key: 'a1proof', view: 'a1'},
  {sel: '#phasemap', key: 'phasemap', view: 'a1'},
  {sel: '#calc', key: 'calc', view: 'a1'},
  {sel: '#a2-platform', key: 'platform', view: 'a2'},
  {sel: '#waterfall', key: 'waterfall', view: 'a2'},
  {sel: '#widgets', key: 'widgets', view: 'a2'},
  {sel: '#signals', key: 'signals', view: 'a2'},
  {sel: '.askbar', key: 'ask', view: 'ask'},
  {sel: '#sevtiles', key: 'problems', view: 'problems'},
  {sel: '#crmbtn', key: 'crm', view: null},
];
function closeTour() { $$('.tour-veil,.tour-spot,.tour-card').forEach(e => e.remove()); }
function startTour() {
  closeFloat();
  modal(`<h4>Welcome to the onboarding console</h4>
    <p class="what">This tool onboards a new retail partner from just its website. Two agents read the site side by side and build a snapshot for the team.</p>
    <p class="why">The tour has ${TOUR.length} short stops. Each one shows what you are looking at and why it matters.</p>
    <div class="ctrl"><span class="dots"></span><button class="btn ghost" data-close>Not now</button><button class="btn gold" data-tour="0">Start the tour</button></div>`);
}
async function tourStep(i) {
  if (i >= TOUR.length) return tourEnd();
  const st = TOUR[i];
  if (st.view && !RUN) {  // the rest of the tour needs a partner on screen
    modal(`<h4>First, run a partner</h4><p class="what">The rest of the tour explains real results. Run the demo partner, ${esc(SITE.default_url)}, and the tour carries on automatically.</p>
      <div class="ctrl"><span class="dots"></span><button class="btn ghost" data-close>Cancel</button><button class="btn gold" data-tourrun="${i}">Run ${esc(SITE.default_url)}</button></div>`);
    return;
  }
  closeTour();
  if (st.view) showView(st.view); else if (RUN && st.sel !== '#crmbtn') showView('snapshot');
  await new Promise(r => setTimeout(r, st.view === 'problems' ? 400 : 80));
  const el = $(st.sel); if (!el) return tourStep(i + 1);
  el.scrollIntoView({block: 'center', behavior: 'auto'});  // instant, so the spotlight measures the final position
  await new Promise(r => setTimeout(r, 80));
  const raw = el.getBoundingClientRect(), pad = 6;
  const b = {left: raw.left, right: raw.right, top: Math.max(70, raw.top), bottom: Math.min(innerHeight - 8, raw.bottom)};
  b.width = b.right - b.left; b.height = b.bottom - b.top;
  const veil = document.createElement('div'); veil.className = 'tour-veil';
  const spot = document.createElement('div'); spot.className = 'tour-spot';
  Object.assign(spot.style, {left: b.left - pad + 'px', top: b.top - pad + 'px', width: b.width + pad * 2 + 'px', height: b.height + pad * 2 + 'px'});
  const [t, what, why] = INFO[st.key], card = document.createElement('div'); card.className = 'tour-card';
  card.innerHTML = `<h4>${t}</h4><p class="what">${what}</p><p class="why">Why it matters: ${why}</p>
    <div class="ctrl"><span class="dots">${TOUR.map((_, k) => `<i class="${k === i ? 'on' : ''}"></i>`).join('')}</span>
    ${i ? `<button class="btn ghost" data-tour="${i - 1}">Back</button>` : ''}<button class="btn gold" data-tour="${i + 1}">${i === TOUR.length - 1 ? 'Finish' : 'Next'}</button></div>`;
  document.body.append(veil, spot, card);
  const cw = 360, ch = card.offsetHeight;
  let left = Math.min(innerWidth - cw - 12, Math.max(12, b.left)), top;
  if (b.bottom + 14 + ch < innerHeight - 12) top = b.bottom + 14;            // below
  else if (b.top - ch - 14 > 70) top = b.top - ch - 14;                      // above
  else if (b.right + 14 + cw < innerWidth) { left = b.right + 14; top = Math.max(80, b.top); }  // right
  else { left = innerWidth - cw - 24; top = innerHeight - ch - 24; }         // tall panel: bottom-right corner
  Object.assign(card.style, {left: left + 'px', top: top + 'px'});
  veil.onclick = closeTour;
}
function tourEnd() {
  modal(`<h4>That's the tour</h4><p class="what">Try another partner's website in the bar at the top, or ask the agents a question.</p>
    <div class="ctrl"><span class="dots"></span><button class="btn gold" data-close>Done</button></div>`);
}

// ---------------- events ----------------
document.addEventListener('click', async e => {
  const t = e.target.closest('button,a'); if (!t) { if (!e.target.closest('.float')) closeFloat(); return; }
  if (t.dataset.info) { e.stopPropagation(); return infoPop(t); }
  if (!t.closest('.float')) closeFloat();
  if (t.dataset.view) return showView(t.dataset.view);
  if (t.id === 'runsbtn') { e.stopPropagation(); return runsMenu(t); }
  if (t.dataset.open) { closeFloat(); return MODE === 'local' ? show(await api('api/job/' + t.dataset.open)) : openRun(t.dataset.open, false); }
  if (t.id === 'startbtn') return startTour();
  if (t.dataset.tour) return tourStep(+t.dataset.tour);
  if (t.dataset.tourrun) { const resume = +t.dataset.tourrun, prev = RUN; closeTour();
    startRun(SITE.default_url); const wait = setInterval(() => { if (RUN && RUN !== prev) { clearInterval(wait); setTimeout(() => tourStep(resume), 600); } }, 300); return; }
  if (t.hasAttribute('data-close')) return closeTour();
  if (t.dataset.scope) { ISSUE_SCOPE = t.dataset.scope; return renderProblems(); }
  if (t.dataset.sev) { ISSUE_FILTER = ISSUE_FILTER === t.dataset.sev ? null : t.dataset.sev; return renderProblems(); }
  if (t.dataset.dl && RUN) {
    const h = RUN.result.harvester, p = RUN.result.profiler;
    if (t.dataset.dl === 'csv' && h) return download(`${RUN.slug}_catalogue.csv`, toCSV(h.rows), 'text/csv');
    if (t.dataset.dl === 'cov' && h) return download(`${RUN.slug}_coverage.json`, JSON.stringify(h.coverage, null, 2), 'application/json');
    if (t.dataset.dl === 'brief' && p) return download(`${RUN.slug}_brief.md`, p.brief_md || '', 'text/markdown');
  }
  if (t.classList.contains('ex')) return ask(t.textContent);
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeTour(); closeFloat(); } });
$('#runform').onsubmit = e => { e.preventDefault(); startRun($('#target').value); };
$('#askform').onsubmit = e => { e.preventDefault(); const q = $('#question').value; $('#question').value = ''; ask(q); };
init();
