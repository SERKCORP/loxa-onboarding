#!/usr/bin/env python3
"""
Integration Profiler: turns a retailer's domain into a technical onboarding brief.

Read-only. It never adds items to a cart and never submits a form. It reads:
  homepage, cart page (if robots.txt allows), up to 3 product pages, one collection page,
  response headers, and (for Shopify) the public /products.json feed.

Outputs (outputs/<domain>/):
  profile.json  every finding with its evidence, source (header / html / probe / inferred) and confidence
  brief.md      one-page brief: platform, checkout, tags, widgets, recommendation, risk flags,
                readiness score, indicative effort and an engineer checklist

Usage:
  python -m profiler.profile --domain michaelspiers.co.uk
"""
import argparse
import json
import os
import re
import time

from bs4 import BeautifulSoup

from .polite import PoliteFetcher, absolute, same_host

HERE = os.path.dirname(os.path.abspath(__file__))
SHOPIFY_CHECKOUT_SRC = "Shopify Help Center: one-page checkout is the default; merchants can switch to three-page"


def load_rules(path=None):
    with open(path or os.path.join(HERE, "rules.json"), encoding="utf-8") as f:
        return json.load(f)


def fetch_pages(fetcher, base):
    pages, notes = {}, []

    def grab(key, url):
        status, html, headers = fetcher.get(url)
        pages[key] = {"url": url, "status": status, "html": html or "", "headers": headers}
        if status == "blocked_by_robots":
            notes.append(f"{url} is disallowed by robots.txt, so it was not read (respected).")

    grab("home", base + "/")
    grab("cart", base + "/cart")
    soup = BeautifulSoup(pages["home"]["html"], "lxml") if pages["home"]["html"] else None
    product_links, collection = [], None
    if soup:
        for a in soup.find_all("a", href=True):
            link = absolute(a["href"], base + "/").split("#")[0].split("?")[0]
            if not same_host(link, base + "/"):
                continue
            if re.search(r"/(products?|product|p)/[^/]+", link) and link not in product_links:
                product_links.append(link)
            elif collection is None and re.search(r"/(collections?|categories|category)/[^/]+", link):
                collection = link
    # Shopify probe: public product feed (read-only)
    status, text, _ = fetcher.get(base + "/products.json?limit=3")
    feed = None
    if status == 200 and text:
        try:
            feed = json.loads(text)
        except json.JSONDecodeError:
            feed = None
    shopify_feed = bool(feed and isinstance(feed.get("products"), list)
                        and any(isinstance(x, dict) and x.get("handle") for x in feed["products"]))
    if shopify_feed and not product_links:
        product_links = [f"{base}/products/{p['handle']}" for p in feed["products"] if p.get("handle")]
    for i, link in enumerate(product_links[:3]):
        grab(f"product_{i + 1}", link)
    if collection:
        grab("collection", collection)
    return pages, notes, shopify_feed


def detect_platform(pages, rules, shopify_feed):
    combined = " ".join(p["html"] for p in pages.values())
    scores, evidence = {}, {}
    for r in rules["platforms"]:
        hit, source = False, None
        if r.get("html") and re.search(r["html"], combined, re.I):
            hit, source = True, "html"
        if r.get("header"):
            for p in pages.values():
                if any(re.fullmatch(r["header"], k, re.I) for k in p["headers"]):
                    hit, source = True, "header"
        if r.get("probe") == "shopify_feed" and shopify_feed:
            hit, source = True, "probe"
        if hit:
            scores[r["name"]] = min(1.0, round(scores.get(r["name"], 0) + r["weight"], 2))
            evidence.setdefault(r["name"], []).append({"signal": r["signal"], "source": source})
    if not scores:
        return {"name": "Custom or unknown", "confidence": 0.3,
                "evidence": [{"signal": "no known platform signature found", "source": "html"}]}
    best = max(scores, key=scores.get)
    return {"name": best, "confidence": scores[best], "evidence": evidence[best]}


def find(table, text):
    return sorted(k for k, pat in table.items() if re.search(pat, text, re.I))


def security_headers(pages):
    h = {k.lower(): v for k, v in pages["home"]["headers"].items()}
    return {"HSTS": "strict-transport-security" in h, "Content-Security-Policy": "content-security-policy" in h,
            "X-Frame-Options": "x-frame-options" in h, "CDN": "Cloudflare" if "cf-ray" in h else
            ("Fastly" if "x-served-by" in h else (h.get("server") or "unknown"))}


def checkout_profile(platform, pages, fetcher, base):
    cart = pages.get("cart", {})
    html = cart.get("html", "")
    account_prompt = bool(re.search(r"\b(log ?in|sign ?in|create (an )?account)\b", html, re.I)) if html else None
    checkout_blocked = not fetcher.allowed(base + "/checkout")
    if platform["name"] == "Shopify":
        return {"type": "Shopify hosted checkout", "steps": "1 (one-page, Shopify default) or 3 (three-page, if switched)",
                "steps_confidence": 0.6, "steps_source": "inferred", "steps_reference": SHOPIFY_CHECKOUT_SRC,
                "account_prompt_on_cart": account_prompt, "checkout_disallowed_in_robots": checkout_blocked,
                "customisable_checkout": "Only on Shopify Plus (checkout extensibility). Plan is not visible from outside."}
    return {"type": "Unknown; needs human review", "steps": "unknown", "steps_confidence": 0.3,
            "steps_source": "inferred", "steps_reference": "Checkout is not visible without an active cart",
            "account_prompt_on_cart": account_prompt, "checkout_disallowed_in_robots": checkout_blocked,
            "customisable_checkout": "Unknown"}


def recommend(platform):
    if platform["name"] == "Shopify":
        return {"approach": "Loxa widget on product and cart pages first (theme app extension). Add a checkout step only if the store is on Shopify Plus.",
                "reasoning": "Product and cart placement works on every Shopify plan. Checkout customisation is limited to Plus, and the plan cannot be seen from outside the site.",
                "confidence": 0.75}
    if platform["name"] in ("Magento", "BigCommerce", "WooCommerce", "Salesforce Commerce Cloud"):
        return {"approach": f"Product page widget plus a {platform['name']} cart integration via its standard extension points.",
                "reasoning": "A known platform with documented extension points, but the checkout build needs scoping with the partner's developers.",
                "confidence": 0.55}
    return {"approach": "Product page widget plus API-based cart integration, scoped with the partner's developers.",
            "reasoning": "No standard platform detected, so the integration path needs human scoping.",
            "confidence": 0.4}


def readiness(platform, gtm, widgets, checkout):
    """Own-initiative heuristic: 0-100 readiness, an indicative effort range, and why."""
    score, why = 100, []

    def minus(n, reason):
        nonlocal score
        score -= n
        why.append(f"-{n} {reason}")

    if platform["name"] == "Custom or unknown":
        minus(30, "platform not identified")
    elif platform["confidence"] < 0.6:
        minus(10, "platform confidence below 60%")
    if not gtm:
        minus(10, "no Google Tag Manager, so attach-rate tracking needs setting up")
    rivals = [w for w in widgets["protection"] if w != "Loxa"]
    if rivals:
        minus(20, f"competing protection present ({', '.join(rivals)})")
    if widgets["bnpl"]:
        minus(5, "BNPL competes for attention at the same decision point")
    if not widgets["consent"]:
        minus(5, "no cookie consent tool detected, so tracking consent needs checking")
    if platform["name"] == "Shopify":
        minus(5, "Shopify plan (Plus or not) must be confirmed")
    minus(5, "checkout steps inferred, not observed")
    score = max(0, score)
    band = "Ready" if score >= 80 else ("Ready with fixes" if score >= 60 else "Needs scoping")
    effort = ("Indicative: 1–3 days for a product and cart widget" if platform["name"] == "Shopify"
              else "Indicative: 1–2 weeks including scoping")
    return {"score": score, "band": band, "effort": effort, "deductions": why,
            "method": "Loxa onboarding heuristic (own initiative). Starts at 100 and deducts for each risk found."}


def build(domain, base=None, out=None, delay=1.0, rules_path=None):
    t0 = time.time()
    base = (base or f"https://{domain}").rstrip("/")
    out = out or os.path.join("outputs", domain)
    os.makedirs(out, exist_ok=True)
    rules = load_rules(rules_path)
    fetcher = PoliteFetcher(base, delay=delay)
    print(f"[1/4] Reading {base} (robots.txt {'found' if fetcher.robots_found else 'not found'}), read-only")
    pages, notes, shopify_feed = fetch_pages(fetcher, base)
    text = " ".join(p["html"] for p in pages.values())
    platform = detect_platform(pages, rules, shopify_feed)
    print(f"[2/4] Platform: {platform['name']} ({platform['confidence']:.0%})")
    gtm = sorted(set(re.findall(r"GTM-[A-Z0-9]{4,9}", text)))
    ga4 = sorted(set(re.findall(r"\bG-[A-Z0-9]{6,12}\b", text)))
    widgets = {k: find(v, text) for k, v in rules["widgets"].items()}
    checkout = checkout_profile(platform, pages, fetcher, base)
    rec = recommend(platform)
    ready = readiness(platform, gtm, widgets, checkout)
    print(f"[3/4] GTM {gtm or 'none'} · BNPL {widgets['bnpl'] or 'none'} · protection {widgets['protection'] or 'none'}")

    flags, review = [], []
    rivals = [w for w in widgets["protection"] if w != "Loxa"]
    if rivals:
        flags.append(f"Competing protection visible ({', '.join(rivals)}). Check for exclusivity before launch.")
    if "Loxa" in widgets["protection"]:
        flags.append("Loxa markup already present. Check whether an earlier integration is live.")
    if widgets["bnpl"]:
        flags.append(f"BNPL present ({', '.join(widgets['bnpl'])}). Place the cover offer so it does not compete with finance.")
    if not gtm:
        flags.append("No Google Tag Manager container found. Plan tracking for attach rate.")
    if checkout["account_prompt_on_cart"]:
        flags.append("Account prompt on the cart page. Confirm guest checkout behaviour.")
    if platform["confidence"] < 0.6:
        review.append("Platform confidence is low. Confirm the platform with the partner.")
    if platform["name"] == "Shopify":
        review.append("Confirm the Shopify plan. Checkout customisation needs Shopify Plus.")
    review += ["Confirm checkout steps with a test order in staging.",
               "Post-payment and logged-in flows cannot be read from outside. Confirm with the partner."] + notes

    signals = [{"finding": f"Platform: {platform['name']}", "evidence": e["signal"], "source": e["source"],
                "confidence": platform["confidence"]} for e in platform["evidence"]]
    signals += [{"finding": f"GTM container {g}", "evidence": "container ID in page source", "source": "html", "confidence": 0.95} for g in gtm]
    labels = {"bnpl": "BNPL", "trust": "Trust badge", "protection": "Protection"}
    signals += [{"finding": f"{labels[k]}: {w}", "evidence": "script or markup match", "source": "html", "confidence": 0.8}
                for k in ("bnpl", "trust", "protection") for w in widgets[k]]
    signals.append({"finding": f"Checkout steps: {checkout['steps']}", "evidence": checkout["steps_reference"],
                    "source": "inferred", "confidence": checkout["steps_confidence"]})

    profile = {"domain": domain, "base_url": base, "run_at": time.strftime("%Y-%m-%d %H:%M"),
               "duration_seconds": round(time.time() - t0, 1), "requests_made": fetcher.requests_made,
               "pages_read": {k: v["status"] for k, v in pages.items()}, "robots_found": fetcher.robots_found,
               "platform": platform, "gtm_containers": gtm, "ga4_ids": ga4, "widgets": widgets,
               "security": security_headers(pages), "checkout": checkout, "recommendation": rec,
               "readiness": ready, "risk_flags": flags, "human_review": review, "signals": signals}
    with open(os.path.join(out, "profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    write_brief(os.path.join(out, "brief.md"), profile)
    print(f"[4/4] Readiness {ready['score']}/100 ({ready['band']}) · {fetcher.requests_made} requests · brief at {out}/brief.md")
    return profile


def write_brief(path, p):
    w, c, r, rd = p["widgets"], p["checkout"], p["recommendation"], p["readiness"]
    j = lambda xs: ", ".join(xs) if xs else "none found"
    lines = [f"# Integration brief: {p['domain']}", f"_Generated {p['run_at']} from visible signals only. No items were added to any cart._", "",
             f"**Readiness: {rd['score']}/100 · {rd['band']}** · {rd['effort']}", "",
             "## Platform", f"- **{p['platform']['name']}** (confidence {p['platform']['confidence']:.0%})"]
    lines += [f"- Evidence ({e['source']}): {e['signal']}" for e in p["platform"]["evidence"]]
    lines += ["", "## Checkout", f"- Type: {c['type']}", f"- Steps: {c['steps']} (source: {c['steps_reference']})",
              f"- Checkout customisation: {c['customisable_checkout']}",
              f"- Account prompt on cart: {'unknown (cart not read)' if c['account_prompt_on_cart'] is None else ('yes' if c['account_prompt_on_cart'] else 'no')}",
              "", "## Tags and widgets", f"- Google Tag Manager: {j(p['gtm_containers'])}", f"- GA4: {j(p['ga4_ids'])}",
              f"- BNPL: {j(w['bnpl'])}", f"- Trust badges and reviews: {j(w['trust'])}", f"- Competing protection: {j(w['protection'])}",
              f"- Payments: {j(w['payments'])}", f"- Cookie consent: {j(w['consent'])}", f"- Analytics: {j(w['analytics'])}",
              "", "## Recommended Loxa approach", f"- {r['approach']}", f"- Why: {r['reasoning']}", "",
              "## Risk flags"] + ([f"- {x}" for x in p["risk_flags"]] or ["- None found from visible signals."])
    lines += ["", "## Human review required"] + [f"- [ ] {x}" for x in p["human_review"]]
    lines += ["", "## How the readiness score was reached", f"_{rd['method']}_"] + [f"- {x}" for x in rd["deductions"]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Profile a retailer's integration surface (read-only).")
    ap.add_argument("--domain", required=True)
    ap.add_argument("--base")
    ap.add_argument("--out")
    ap.add_argument("--delay", type=float, default=1.0)
    a = ap.parse_args()
    build(a.domain, a.base, a.out, a.delay)


if __name__ == "__main__":
    main()
