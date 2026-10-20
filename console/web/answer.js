// "Ask the agents" in the browser: a line-for-line port of core/answer.py builtin(),
// so the GitHub dashboard answers exactly like the local console. Parity is tested in CI.
(function (root) {
  const fmt = n => Math.round(n).toLocaleString('en-GB');
  const gbp = v => v == null ? 'n/a' : '£' + fmt(v);
  const sku = n => `${n.toLocaleString('en-GB')} SKU${n === 1 ? '' : 's'}`;
  const esc = w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const has = (q, ...words) => words.some(w => new RegExp('\\b' + esc(w)).test(q));
  const median = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const price = r => r.price ? parseFloat(r.price) : null;
  const pyf = x => (typeof x === 'number' && Number.isInteger(x)) ? x.toFixed(1) : String(x);  // Python float style: 0.0

  function entities(q, rows) {
    const brands = [...new Set(rows.map(r => r.brand).filter(Boolean))].sort((a, b) => b.length - a.length);
    const cats = [...new Set(rows.filter(r => r.category_path).map(r => r.category_path.split(' > ')[0]))].sort((a, b) => b.length - a.length);
    return [brands.filter(b => q.includes(b.toLowerCase())), cats.filter(c => q.includes(c.toLowerCase().replace(/s+$/, '')))];
  }

  function catalogueAnswer(q, h) {
    const rows = h.rows, [b, c] = entities(q, rows);
    const sel = rows.filter(r => (!b.length || b.includes(r.brand)) && (!c.length || c.some(x => r.category_path.startsWith(x))));
    const label = [...b, ...c].join(' and ') || 'all';
    const stock = sel.filter(r => r.availability === 'in_stock');
    const useStock = has(q, 'in stock', 'available', 'stock'), focus = useStock ? stock : sel;
    const prices = focus.filter(r => r.price).map(price);
    const lines = [`${label === 'all' ? 'All products' : label}: ${sku(sel.length)}, of which ${stock.length.toLocaleString('en-GB')} ${stock.length === 1 ? 'is' : 'are'} in stock.`];
    if (prices.length) {
      let lo = focus[0], hi = focus[0];
      focus.forEach(r => { if ((r.price ? price(r) : 9e9) < (lo.price ? price(lo) : 9e9)) lo = r; if ((r.price ? price(r) : 0) > (hi.price ? price(hi) : 0)) hi = r; });
      lines.push(`- Median price${useStock ? ' (in stock)' : ''}: ${gbp(median(prices))}`);
      lines.push(`- Range${useStock ? ' (in stock)' : ''}: ${gbp(price(lo))} (${lo.name}) to ${gbp(price(hi))} (${hi.name})`);
    }
    const poa = sel.filter(r => String(r.price_on_application) === 'True').length;
    if (poa) lines.push(`- ${sku(poa)} ${poa === 1 ? 'is' : 'are'} price on application, so excluded from price figures`);
    return [lines.join('\n'), ['Agent 1 · catalogue.csv']];
  }

  function phaseAnswer(h) {
    const rows = h.rows, first = (h.phases || [])[0], casing = h.brand_casing || {};
    const titled = m => m.replace(/\b\w/g, ch => ch.toUpperCase());
    const out = first ? [`Start with ${first.name} (${first.match.map(m => casing[m] || titled(m)).join(', ')}): ${first.why.toLowerCase()}. Here is how the live catalogue splits across the plan:`]
                      : ['Catalogue mapped to the launch plan phases:'];
    [...(h.phases || []).map(p => p.name), 'Not in launch plan'].forEach(n => {
      const pr = rows.filter(r => r.phase === n), pp = pr.filter(r => r.price).map(price);
      if (pr.length) out.push(`- ${n}: ${sku(pr.length)}, ${pr.filter(r => r.availability === 'in_stock').length.toLocaleString('en-GB')} in stock, median ${gbp(pp.length ? median(pp) : null)}`);
    });
    return [out.join('\n'), ['Agent 1 · catalogue.csv', 'harvester/taxonomy.json (phases from the deck, slide 6)']];
  }

  function opportunityAnswer(h) {
    const prices = h.rows.filter(r => r.price && r.availability === 'in_stock').map(price);
    if (!prices.length) return ['There are no priced in-stock SKUs to estimate from.', ['Agent 1 · catalogue.csv']];
    const med = median(prices), prem = med * 0.05;
    return ['Illustrative only: the inputs below are assumptions, not data.\n' +
      `- Median in-stock ticket: ${gbp(med)} (from the live catalogue)\n` +
      `- At an illustrative 5% premium, that is ${gbp(prem)} per policy before IPT, or ${gbp(prem * 1.12)} with 12% IPT\n` +
      `- At 100 orders a month and the deck's 10% attach target: 10 policies, ${gbp(prem * 10)} a month, ${gbp(prem * 30)} over 90 days\n` +
      "- Replace the order volume with Michael Spiers' data and the rate with Loxa's rate card. Use the calculator to change both.",
      ['Agent 1 · catalogue.csv', 'Cover Opportunity Calculator']];
  }

  function profileAnswers(q, p) {
    const out = [], w = p.widgets, c = p.checkout, rec = p.recommendation, rd = p.readiness;
    const j = xs => xs && xs.length ? xs.join(', ') : 'none found';
    if (has(q, 'platform', 'stack', 'tech', 'shopify', 'magento', 'built on', 'integrat', 'how should', 'approach')) {
      out.push(`Platform: ${p.platform.name} (${Math.round(p.platform.confidence * 100)}% confidence; evidence: ` + p.platform.evidence.map(e => e.signal).join('; ') + ').');
      out.push(`- Recommended approach: ${rec.approach}`);
      out.push(`- Why: ${rec.reasoning}`);
    }
    if (has(q, 'checkout', 'steps')) out.push(`Checkout: ${c.type}; steps: ${c.steps}. Source: ${c.steps_reference} (inferred, so we confirm it in staging).`);
    if (has(q, 'compet', 'protection', 'warranty', 'extend', 'clash', 'conflict', 'rival')) {
      const rivals = w.protection.filter(x => x !== 'Loxa');
      out.push(`Competing protection: ${j(rivals)}.` + (rivals.length ? ' Check for an exclusivity clause before launch.' : ' Nothing visible, so there is a clear run at the offer.'));
    }
    if (has(q, 'bnpl', 'klarna', 'clearpay', 'finance', 'clash', 'pay later'))
      out.push(`BNPL and finance: ${j(w.bnpl)}.` + (w.bnpl.length ? " Place the cover offer so it doesn't compete with finance at the same moment." : ''));
    if (has(q, 'track', 'gtm', 'tag manager', 'analytics', 'pixel', 'measure'))
      out.push(`Tracking: GTM ${j(p.gtm_containers)}; GA4 ${j(p.ga4_ids)}; other tools: ${j(w.analytics)}.`);
    if (has(q, 'consent', 'cookie', 'gdpr', 'privacy')) out.push(`Cookie consent tool: ${j(w.consent)}.`);
    if (has(q, 'payment', 'apple pay', 'paypal')) out.push(`Payment methods visible: ${j(w.payments)}.`);
    if (has(q, 'risk', 'concern', 'flag', 'worr', 'blocker', 'issue', 'problem')) {
      out.push('Risk flags:\n' + (p.risk_flags.map(x => `- ${x}`).join('\n') || '- none from visible signals'));
      out.push('Needs a human:\n' + p.human_review.slice(0, 4).map(x => `- ${x}`).join('\n'));
    }
    if (has(q, 'ready', 'readiness', 'effort', 'how long', 'time to', 'when can', 'days', 'weeks', 'score'))
      out.push(`Readiness: ${rd.score}/100 (${rd.band}). ${rd.effort}.\n` + rd.deductions.map(x => `- ${x}`).join('\n'));
    return [out, ['Agent 2 · profile.json']];
  }

  function methodAnswer(h, p) {
    const lines = ['How the agents got this:'];
    if (h) { const cv = h.coverage;
      lines.push(`- Agent 1 used the ${cv.strategy.replaceAll('_', ' ')} route: ${cv.requests_made} requests in ${pyf(cv.duration_seconds)}s at a ${pyf(cv.delay_seconds)}s delay, robots.txt ${cv.robots_found ? 'honoured' : 'not found'}, ${cv.duplicates_removed} duplicates removed`); }
    if (p) lines.push(`- Agent 2 read ${Object.values(p.pages_read).filter(v => v === 200).length} pages read-only in ${p.requests_made} requests, and never added anything to a cart`);
    return [lines.join('\n'), ['coverage.json', 'profile.json']];
  }

  function builtin(q, h, p) {
    const ql = q.toLowerCase(), parts = [], sources = [];
    const add = ([text, src]) => { parts.push(text); sources.push(...src); };
    if (p) { const [txts, src] = profileAnswers(ql, p); if (txts.length) add([txts.join('\n'), src]); }
    if (h) {
      if (has(ql, 'phase', 'launch', 'roll', 'start with', 'first')) add(phaseAnswer(h));
      if (has(ql, 'revenue', 'opportunit', 'gwp', 'premium', 'worth', 'money', 'commercial', 'upside')) add(opportunityAnswer(h));
      if (has(ql, 'how many', 'count', 'sku', 'product', 'catalog', 'stock', 'price', 'median', 'cheapest', 'expensive', 'average', 'brand', 'range')
          || (!parts.length && entities(ql, h.rows)[0].length)) add(catalogueAnswer(ql, h));
    }
    if (has(ql, 'how did', 'how does', 'how do', 'method', 'robots', 'respect', 'crawl', 'work')) add(methodAnswer(h, p));
    if (!parts.length && h) {
      const stop = new Set(['what', 'which', 'show', 'have', 'they', 'the', 'and', 'for', 'any']);
      const terms = (ql.match(/[a-z0-9]{3,}/g) || []).filter(t => !stop.has(t));
      const hits = h.rows.filter(r => terms.every(t => (r.name + ' ' + r.brand + ' ' + r.category_path).toLowerCase().includes(t))).slice(0, 5);
      if (hits.length) add(['Matching products:\n' + hits.map(r => `- ${r.name} (${r.brand}): ${r.price ? '£' + fmt(price(r)) : 'POA'}, ${r.availability.replaceAll('_', ' ')}`).join('\n'), ['Agent 1 · catalogue.csv']]);
    }
    if (!parts.length) parts.push("I couldn't match that to the agents' data. Try asking about the platform, checkout, risks, readiness, launch phases, a brand (for example 'Rolex in stock'), prices, or the commercial opportunity.");
    return { answer: parts.join('\n\n'), sources: [...new Set(sources)].sort(), method: 'built-in agent logic (runs in your browser)' };
  }

  root.LoxaAnswer = { builtin };
  if (typeof module !== 'undefined') module.exports = { builtin };
})(typeof window !== 'undefined' ? window : globalThis);
