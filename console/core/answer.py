"""'Ask the agents': answers questions from the agents' own outputs.

Default: built-in, deterministic logic over catalogue.csv and profile.json (offline, no API key, repeatable).
Optional: set ANTHROPIC_API_KEY to let Claude phrase answers, grounded only in the same data.
Every answer names the agent and the file it came from, and is logged to the run folder."""
import json
import os
import re
import statistics
import time
import urllib.request

from .agents import CONFIG, RUNS


def gbp(v):
    return "n/a" if v is None else f"£{v:,.0f}"


def sku(n):
    return f"{n:,} SKU" + ("" if n == 1 else "s")


def has(q, *words):
    return any(re.search(r"\b" + w, q) for w in words)


def entities(q, rows):
    brands = sorted({r["brand"] for r in rows if r.get("brand")}, key=len, reverse=True)
    cats = sorted({r["category_path"].split(" > ")[0] for r in rows if r.get("category_path")}, key=len, reverse=True)
    found_b = [b for b in brands if b.lower() in q]
    found_c = [c for c in cats if c.lower().rstrip("s") in q]
    return found_b, found_c


def catalogue_answer(q, h):
    rows = h["rows"]
    b, c = entities(q, rows)
    sel = [r for r in rows if (not b or r["brand"] in b) and (not c or r["category_path"].startswith(tuple(c)))]
    label = " and ".join(b + c) or "all"
    stock = [r for r in sel if r["availability"] == "in_stock"]
    focus = stock if has(q, "in stock", "available", "stock") else sel
    prices = [float(r["price"]) for r in focus if r["price"]]
    lines = [f"{'All products' if label == 'all' else label}: {sku(len(sel))}, of which {len(stock):,} "
             f"{'is' if len(stock) == 1 else 'are'} in stock."]
    if prices:
        lo = min(focus, key=lambda r: float(r["price"]) if r["price"] else 9e9)
        hi = max(focus, key=lambda r: float(r["price"]) if r["price"] else 0)
        lines.append(f"- Median price{' (in stock)' if focus is stock else ''}: {gbp(statistics.median(prices))}")
        lines.append(f"- Range{' (in stock)' if focus is stock else ''}: {gbp(float(lo['price']))} ({lo['name']}) "
                     f"to {gbp(float(hi['price']))} ({hi['name']})")
    poa = sum(1 for r in sel if r["price_on_application"] == "True")
    if poa:
        lines.append(f"- {sku(poa)} {'is' if poa == 1 else 'are'} price on application, so excluded from price figures")
    return "\n".join(lines), ["Agent 1 · catalogue.csv"]


def phase_answer(h):
    rows = h["rows"]
    first = h["phases"][0] if h["phases"] else None
    out = ([f"Start with {first['name']} ({', '.join(h.get('brand_casing', {}).get(m, m.title()) for m in first['match'])}): "
            f"{first['why'].lower()}. Here is how the live catalogue splits across the plan:"] if first
           else ["Catalogue mapped to the launch plan phases:"])
    names = [p["name"] for p in h["phases"]] + ["Not in launch plan"]
    for n in names:
        pr = [r for r in rows if r.get("phase") == n]
        pp = [float(r["price"]) for r in pr if r["price"]]
        if pr:
            out.append(f"- {n}: {sku(len(pr))}, {sum(r['availability'] == 'in_stock' for r in pr):,} in stock, "
                       f"median {gbp(statistics.median(pp) if pp else None)}")
    return "\n".join(out), ["Agent 1 · catalogue.csv", "harvester/taxonomy.json (phases from the deck, slide 6)"]


def opportunity_answer(h):
    prices = [float(r["price"]) for r in h["rows"] if r["price"] and r["availability"] == "in_stock"]
    if not prices:
        return "There are no priced in-stock SKUs to estimate from.", ["Agent 1 · catalogue.csv"]
    med = statistics.median(prices)
    prem = med * 0.05
    return ("Illustrative only: the inputs below are assumptions, not data.\n"
            f"- Median in-stock ticket: {gbp(med)} (from the live catalogue)\n"
            f"- At an illustrative 5% premium, that is {gbp(prem)} per policy before IPT, or {gbp(prem * 1.12)} with 12% IPT\n"
            f"- At 100 orders a month and the deck's 10% attach target: 10 policies, {gbp(prem * 10)} a month, {gbp(prem * 30)} over 90 days\n"
            "- Replace the order volume with Michael Spiers' data and the rate with Loxa's rate card. Use the calculator to change both."), \
           ["Agent 1 · catalogue.csv", "Cover Opportunity Calculator"]


def profile_answers(q, p):
    out, src = [], ["Agent 2 · profile.json"]
    w, c, rec, rd = p["widgets"], p["checkout"], p["recommendation"], p["readiness"]
    j = lambda xs: ", ".join(xs) if xs else "none found"
    if has(q, "platform", "stack", "tech", "shopify", "magento", "built on", "integrat", "how should", "approach"):
        out.append(f"Platform: {p['platform']['name']} ({p['platform']['confidence']:.0%} confidence; evidence: "
                   + "; ".join(e["signal"] for e in p["platform"]["evidence"]) + ").")
        out.append(f"- Recommended approach: {rec['approach']}")
        out.append(f"- Why: {rec['reasoning']}")
    if has(q, "checkout", "steps"):
        out.append(f"Checkout: {c['type']}; steps: {c['steps']}. Source: {c['steps_reference']} (inferred, so we confirm it in staging).")
    if has(q, "compet", "protection", "warranty", "extend", "clash", "conflict", "rival"):
        rivals = [x for x in w["protection"] if x != "Loxa"]
        out.append(f"Competing protection: {j(rivals)}."
                   + (" Check for an exclusivity clause before launch." if rivals else " Nothing visible, so there is a clear run at the offer."))
    if has(q, "bnpl", "klarna", "clearpay", "finance", "clash", "pay later"):
        out.append(f"BNPL and finance: {j(w['bnpl'])}." + (" Place the cover offer so it doesn't compete with finance at the same moment." if w["bnpl"] else ""))
    if has(q, "track", "gtm", "tag manager", "analytics", "pixel", "measure"):
        out.append(f"Tracking: GTM {j(p['gtm_containers'])}; GA4 {j(p['ga4_ids'])}; other tools: {j(w['analytics'])}.")
    if has(q, "consent", "cookie", "gdpr", "privacy"):
        out.append(f"Cookie consent tool: {j(w['consent'])}.")
    if has(q, "payment", "apple pay", "paypal"):
        out.append(f"Payment methods visible: {j(w['payments'])}.")
    if has(q, "risk", "concern", "flag", "worr", "blocker", "issue", "problem"):
        out.append("Risk flags:\n" + ("\n".join(f"- {x}" for x in p["risk_flags"]) or "- none from visible signals"))
        out.append("Needs a human:\n" + "\n".join(f"- {x}" for x in p["human_review"][:4]))
    if has(q, "ready", "readiness", "effort", "how long", "time to", "when can", "days", "weeks", "score"):
        out.append(f"Readiness: {rd['score']}/100 ({rd['band']}). {rd['effort']}.\n" + "\n".join(f"- {x}" for x in rd["deductions"]))
    return out, src


def method_answer(h, p):
    lines = ["How the agents got this:"]
    if h:
        cv = h["coverage"]
        lines.append(f"- Agent 1 used the {cv['strategy'].replace('_', ' ')} route: {cv['requests_made']} requests in {cv['duration_seconds']}s "
                     f"at a {cv['delay_seconds']}s delay, robots.txt {'honoured' if cv['robots_found'] else 'not found'}, "
                     f"{cv['duplicates_removed']} duplicates removed")
    if p:
        lines.append(f"- Agent 2 read {sum(v == 200 for v in p['pages_read'].values())} pages read-only in {p['requests_made']} requests, "
                     "and never added anything to a cart")
    return "\n".join(lines), ["coverage.json", "profile.json"]


def builtin(q, h, p):
    ql = q.lower()
    parts, sources = [], []

    def add(text, src):
        parts.append(text)
        sources.extend(src)

    if p:
        txts, src = profile_answers(ql, p)
        if txts:
            add("\n".join(txts), src)
    if h:
        if has(ql, "phase", "launch", "roll", "start with", "first"):
            add(*phase_answer(h))
        if has(ql, "revenue", "opportunit", "gwp", "premium", "worth", "money", "commercial", "upside"):
            add(*opportunity_answer(h))
        if has(ql, "how many", "count", "sku", "product", "catalog", "stock", "price", "median", "cheapest",
               "expensive", "average", "brand", "range") or (not parts and entities(ql, h["rows"])[0]):
            add(*catalogue_answer(ql, h))
    if has(ql, "how did", "how does", "how do", "method", "robots", "respect", "crawl", "work"):
        add(*method_answer(h, p))
    if not parts and h:
        terms = [t for t in re.findall(r"[a-z0-9]{3,}", ql) if t not in {"what", "which", "show", "have", "they", "the", "and", "for", "any"}]
        hits = [r for r in h["rows"] if all(t in (r["name"] + " " + r["brand"] + " " + r["category_path"]).lower() for t in terms)][:5]
        if hits:
            add("Matching products:\n" + "\n".join(f"- {r['name']} ({r['brand']}): {'£' + format(float(r['price']), ',.0f') if r['price'] else 'POA'}, {r['availability'].replace('_', ' ')}" for r in hits),
                ["Agent 1 · catalogue.csv"])
    if not parts:
        parts.append("I couldn't match that to the agents' data. Try asking about the platform, checkout, risks, readiness, "
                     "launch phases, a brand (for example 'Rolex in stock'), prices, or the commercial opportunity.")
    return "\n\n".join(parts), sorted(set(sources))


def ask_claude(q, h, p):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    rows = h["rows"] if h else []
    terms = re.findall(r"[a-z0-9]{3,}", q.lower())
    rel = [r for r in rows if any(t in (r["name"] + r["brand"]).lower() for t in terms)][:40]
    ctx = {"agent1_coverage": h and h["coverage"], "agent1_top_brands": _counts(rows, "brand"),
           "agent1_phases": phase_answer(h)[0] if h else None, "agent1_matching_rows": rel,
           "agent2_profile": p and {k: v for k, v in p.items() if k != "signals"}}
    body = {"model": CONFIG.get("ai_model", "claude-haiku-5-5"), "max_tokens": 400,
            "system": "You answer questions about a retail partner for Loxa, a product-protection insurer. Use ONLY the JSON data provided. "
                      "If the data does not answer the question, say so. Name the source (Agent 1 catalogue or Agent 2 profile). "
                      "At most 120 words, plain English, short bullet points. Label anything inferred as inferred.",
            "messages": [{"role": "user", "content": f"Data:\n{json.dumps(ctx, default=str)[:60000]}\n\nQuestion: {q}"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return "".join(b.get("text", "") for b in data.get("content", []))
    except Exception:
        return None


def _counts(rows, key):
    m = {}
    for r in rows:
        m[r.get(key) or "(blank)"] = m.get(r.get(key) or "(blank)", 0) + 1
    return sorted(m.items(), key=lambda x: -x[1])[:10]


def answer(q, run, mode="auto"):
    h, p = (run.get("result") or {}).get("harvester"), (run.get("result") or {}).get("profiler")
    text, method = None, "built-in agent logic (offline, deterministic)"
    if mode in ("auto", "ai") and os.environ.get("ANTHROPIC_API_KEY"):
        text = ask_claude(q, h, p)
        if text:
            method = f"Claude ({CONFIG.get('ai_model')}), grounded only in this run's agent data"
    srcs = None
    if not text:
        text, srcs = builtin(q, h, p)
    if srcs is None:
        srcs = ["Agent 1 · catalogue.csv", "Agent 2 · profile.json"]
    rec = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "run": run.get("id"), "question": q, "answer": text,
           "method": method, "sources": srcs}
    for path in (os.path.join(RUNS, run.get("id", ""), "qa_log.jsonl"), os.path.join(RUNS, "qa_log.jsonl")):
        if os.path.isdir(os.path.dirname(path)):
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
