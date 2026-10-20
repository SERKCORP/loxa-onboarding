#!/usr/bin/env python3
"""
SKU Harvester: builds a complete, SKU-level product catalogue for any retailer domain.

Discovery, cheapest and most complete first:
  1. Shopify product feed (/products.json, paginated, 250 per page) if the store exposes it
  2. sitemap.xml (follows sitemap indexes)
  3. bounded category crawl (follows collection pages and pagination)

Every request honours robots.txt, is rate-limited, retries with back-off on 429/503,
and is counted. Runs are resumable: feed pages are cached and product pages are checkpointed.

Usage:
  python -m harvester.harvest --domain michaelspiers.co.uk
  python -m harvester.harvest --domain partner.co.uk --delay 1.5 --render
"""
import argparse
import csv
import json
import os
import re
import statistics
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .polite import PoliteFetcher, absolute, same_host

HERE = os.path.dirname(os.path.abspath(__file__))
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PRODUCT_RE = r"/(products?|product|p)/[^/?#]+"
FIELDS = ["name", "brand", "category_path", "variant", "sku", "price", "currency",
          "price_on_application", "availability", "product_url", "source"]


# ---------- taxonomy cleanup ----------
def load_taxonomy(path=None):
    with open(path or os.path.join(HERE, "taxonomy.json"), encoding="utf-8") as f:
        return json.load(f)


def clean_text(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def clean_brand(raw, tax):
    b = clean_text(raw)
    return tax["brand_casing"].get(b.lower(), b.title() if b.isupper() or b.islower() else b)


def clean_category(raw, tax):
    c = clean_text(raw)
    if not c:
        return ""
    return tax["category_synonyms"].get(c.lower(), c.title() if (c.isupper() or c.islower()) else c)


def clean_path(segments, tax):
    out = []
    for seg in segments:
        seg = clean_text(seg)
        if not seg or seg.lower() in ("home", "shop", "all", "all products"):
            continue
        seg = tax["category_synonyms"].get(seg.lower(), seg)
        seg = tax["brand_casing"].get(seg.lower(), seg)
        if not out or out[-1].lower() != seg.lower():
            out.append(seg)
    return " > ".join(out)


def assign_phase(row, phases):
    brand = (row.get("brand") or "").lower()
    cat = (row.get("category_path") or "").lower()
    for ph in phases:
        if ph["rule"] == "brand" and any(m in brand or cat.endswith(m) for m in ph["match"]):
            return ph["name"]
        if ph["rule"] == "category" and any(cat.startswith(m) for m in ph["match"]):
            return ph["name"]
    return "Not in launch plan"


def availability(value):
    v = str(value or "").lower()
    if v in ("true", "1") or "instock" in v or "in stock" in v:
        return "in_stock"
    if v in ("false", "0") or "outofstock" in v or "soldout" in v or "out of stock" in v:
        return "out_of_stock"
    if "preorder" in v or "backorder" in v:
        return "preorder"
    return "unknown"


def price_fields(raw):
    try:
        p = float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return "", True
    return (f"{p:.2f}", False) if p > 0 else ("", True)


# ---------- strategy 1: Shopify product feed ----------
def shopify_feed(fetcher, base, cache_dir, fresh, max_pages=200):
    """Return list of Shopify product dicts, or None if the feed is unavailable."""
    os.makedirs(cache_dir, exist_ok=True)
    products, seen = [], set()
    for page in range(1, max_pages + 1):
        cache = os.path.join(cache_dir, f"products_page_{page}.json")
        if os.path.exists(cache) and not fresh:
            with open(cache, encoding="utf-8") as f:
                data = json.load(f)
        else:
            status, text, _ = fetcher.get(f"{base}/products.json?limit=250&page={page}")
            if status != 200 or not text:
                return products or None if page == 1 else products
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return None if page == 1 else products
            if "products" not in data:
                return None if page == 1 else products
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(data, f)
        batch = [p for p in data.get("products", []) if p.get("id") not in seen]
        if not batch:
            break
        for p in batch:
            seen.add(p.get("id"))
        products.extend(batch)
        print(f"      feed page {page}: {len(batch)} products (total {len(products)})")
    return products


def rows_from_shopify(products, base, tax, currency):
    rows = []
    for p in products:
        brand = clean_brand(p.get("vendor"), tax)
        top = clean_category(p.get("product_type"), tax)
        path = " > ".join(x for x in (top, brand) if x)
        url = f"{base}/products/{p.get('handle', '')}"
        variants = p.get("variants") or [{}]
        for v in variants:
            price, poa = price_fields(v.get("price"))
            vt = clean_text(v.get("title"))
            rows.append({
                "name": clean_text(p.get("title")), "brand": brand, "category_path": path,
                "variant": "" if vt.lower() in ("default title", "") else vt,
                "sku": clean_text(v.get("sku")) or (f"variant-{v['id']}" if v.get("id") else ""),
                "price": price, "currency": currency, "price_on_application": poa,
                "availability": availability(v.get("available")),
                "product_url": url + (f"?variant={v['id']}" if v.get("id") and len(variants) > 1 else ""),
                "source": "shopify_feed"})
    return rows


# ---------- strategy 2 and 3: sitemap, then crawl ----------
def sitemap_urls(fetcher, url, seen=None, depth=0):
    seen = seen if seen is not None else set()
    if url in seen or depth > 3:
        return []
    seen.add(url)
    status, text, _ = fetcher.get(url)
    if status != 200 or not text:
        return []
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError:
        return []
    out = []
    for loc in root.iter(SITEMAP_NS + "loc"):
        u = (loc.text or "").strip()
        if root.tag == SITEMAP_NS + "sitemapindex" or u.endswith(".xml"):
            out.extend(sitemap_urls(fetcher, u, seen, depth + 1))
        else:
            out.append(u)
    return out


def category_crawl(fetcher, start, product_re, max_depth=2, max_pages=400):
    found, queue, visited = set(), [(start, 0)], set()
    while queue and len(visited) < max_pages:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        status, html, _ = fetcher.get(url)
        if status != 200 or not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            link = absolute(a["href"], url).split("#")[0]
            if not same_host(link, start):
                continue
            path = urlparse(link).path
            if re.search(product_re, path):
                found.add(link.split("?")[0])
            elif depth < max_depth and (re.search(r"/(collections?|categories|category|shop)/", path)
                                        or "page=" in link):
                queue.append((link, depth + 1))
        nxt = soup.find("link", rel="next") or soup.find("a", rel="next")
        if nxt and nxt.get("href"):
            queue.append((absolute(nxt["href"], url), depth))
    return sorted(found)


def _ld_items(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for item in (data if isinstance(data, list) else data.get("@graph", [data])):
            if isinstance(item, dict):
                yield item


def _types(item):
    t = item.get("@type")
    return set(t) if isinstance(t, list) else {t}


def extract_page(html, url, source, tax):
    """Return a list of rows (one per variant) from a product page, or [] if none found."""
    soup = BeautifulSoup(html, "lxml")
    crumbs = []
    for item in _ld_items(soup):
        if "BreadcrumbList" in _types(item):
            crumbs = [(i.get("name") or (i.get("item") or {}).get("name", "")) for i in item.get("itemListElement", [])]
    path = clean_path(crumbs[:-1], tax) if len(crumbs) > 1 else ""
    rows = []
    for item in _ld_items(soup):
        types = _types(item)
        if not ({"Product", "ProductGroup"} & types):
            continue
        brand_raw = item.get("brand")
        brand = clean_brand(brand_raw.get("name") if isinstance(brand_raw, dict) else brand_raw, tax)
        variants = item.get("hasVariant") or [item]
        for v in variants:
            offers = v.get("offers", {})
            offers = offers[0] if isinstance(offers, list) and offers else offers
            if not isinstance(offers, dict):
                offers = {}
            price, poa = price_fields(offers.get("price") or (offers.get("priceSpecification") or {}).get("price"))
            rows.append({"name": clean_text(item.get("name") or v.get("name")), "brand": brand,
                         "category_path": path or brand, "variant": clean_text(v.get("name")) if v is not item else "",
                         "sku": clean_text(v.get("sku") or v.get("mpn") or ""), "price": price,
                         "currency": offers.get("priceCurrency", ""), "price_on_application": poa,
                         "availability": availability(offers.get("availability")), "product_url": url, "source": source})
        if rows:
            return rows
    title = soup.find("meta", property="og:title")
    amount = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
    if title and amount:
        cur = soup.find("meta", property="product:price:currency") or soup.find("meta", property="og:price:currency")
        price, poa = price_fields(amount.get("content"))
        return [{"name": clean_text(title.get("content")), "brand": "", "category_path": path, "variant": "",
                 "sku": "", "price": price, "currency": cur.get("content", "") if cur else "",
                 "price_on_application": poa, "availability": "unknown", "product_url": url, "source": source}]
    return []


def render(url):
    """Optional Playwright render with scrolling, for JavaScript and lazy-loaded pages."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(url, wait_until="networkidle", timeout=30000)
        for _ in range(5):
            pg.mouse.wheel(0, 4000)
            pg.wait_for_timeout(400)
        html = pg.content()
        b.close()
        return html


def page_mode(fetcher, urls, source, out, tax, do_render):
    ckpt_path = os.path.join(out, "checkpoint.jsonl")
    done = {}
    if os.path.exists(ckpt_path):
        with open(ckpt_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    done[rec["url"]] = rec
    with open(ckpt_path, "a", encoding="utf-8") as ck:
        for i, url in enumerate(urls, 1):
            if url in done:
                continue
            status, html, _ = fetcher.get(url)
            rec = {"url": url, "status": f"failed:{status}", "rows": []}
            if status == 200 and html:
                rows = extract_page(html, url, source, tax)
                if not rows and do_render:
                    rendered = render(url)
                    rows = extract_page(rendered, url, source + "+render", tax) if rendered else []
                rec = {"url": url, "status": "ok" if rows else "needs_render", "rows": rows}
            ck.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ck.flush()
            done[url] = rec
            if i % 25 == 0:
                print(f"      {i}/{len(urls)} pages")
    rows = [r for rec in done.values() for r in rec["rows"]]
    stats = {"failed": sum(1 for r in done.values() if r["status"].startswith("failed")),
             "needs_render": sum(1 for r in done.values() if r["status"] == "needs_render")}
    return rows, stats


def detect_currency(fetcher, base, product_url):
    status, html, _ = fetcher.get(product_url)
    if status == 200 and html:
        m = re.search(r'"priceCurrency"\s*:\s*"([A-Z]{3})"', html)
        if m:
            return m.group(1)
        m = re.search(r'product:price:currency"\s+content="([A-Z]{3})"', html)
        if m:
            return m.group(1)
    return ""


def dedupe(rows):
    out, seen_sku, seen_key, removed = [], set(), set(), 0
    for r in rows:
        key = (r["product_url"], r["variant"])
        if key in seen_key or (r["sku"] and r["sku"] in seen_sku):
            removed += 1
            continue
        seen_key.add(key)
        if r["sku"]:
            seen_sku.add(r["sku"])
        out.append(r)
    return out, removed


def run(domain, base=None, out=None, delay=1.0, render_pages=False, max_products=0, fresh=False,
        product_pattern=PRODUCT_RE, taxonomy=None, page_limit=0):
    t0 = time.time()
    base = (base or f"https://{domain}").rstrip("/")
    out = out or os.path.join("outputs", domain)
    os.makedirs(out, exist_ok=True)
    tax = load_taxonomy(taxonomy)
    fetcher = PoliteFetcher(base, delay=delay)
    print(f"[1/4] Discovery on {base}  (robots.txt {'found' if fetcher.robots_found else 'not found'})")

    stats = {"failed": 0, "needs_render": 0}
    sitemap_count = None
    products = shopify_feed(fetcher, base, os.path.join(out, "cache"), fresh)
    if products:
        strategy = "shopify_feed"
        if max_products:
            products = products[:max_products]
        first = f"{base}/products/{products[0].get('handle', '')}"
        currency = detect_currency(fetcher, base, first)
        print(f"[2/4] Shopify feed: {len(products)} products")
        rows = rows_from_shopify(products, base, tax, currency)
    else:
        sm = []
        for s in (fetcher.sitemaps or [base + "/sitemap.xml"]):
            sm.extend(sitemap_urls(fetcher, s))
        urls = sorted({u.split("?")[0] for u in sm if re.search(product_pattern, urlparse(u).path)})
        sitemap_count = len(urls)
        strategy = "sitemap"
        if not urls:
            print("      no sitemap products, falling back to category crawl")
            urls, strategy = category_crawl(fetcher, base + "/", product_pattern), "crawl"
        if max_products:
            urls = urls[:max_products]
        found = len(urls)
        if page_limit and len(urls) > page_limit:
            urls = urls[:page_limit]
            print(f"      quick scan: reading the first {page_limit} of {found} product pages")
        print(f"[2/4] {strategy}: {len(urls)} product pages to read")
        rows, stats = page_mode(fetcher, urls, strategy, out, tax, render_pages)

    rows, removed = dedupe(rows)
    with open(os.path.join(out, "catalogue.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    prices = [float(r["price"]) for r in rows if r["price"]]
    coverage = {
        "domain": domain, "base_url": base, "run_at": time.strftime("%Y-%m-%d %H:%M"),
        "strategy": strategy, "robots_found": fetcher.robots_found,
        "requests_made": fetcher.requests_made, "blocked_by_robots": fetcher.blocked,
        "delay_seconds": delay, "duration_seconds": round(time.time() - t0, 1),
        "products": len({r["product_url"].split("?")[0] for r in rows}), "skus": len(rows),
        "sitemap_product_urls": sitemap_count, "duplicates_removed": removed,
        "quick_scan_limit": page_limit if strategy != "shopify_feed" and page_limit else None,
        "failed_pages": stats["failed"], "needs_render": stats["needs_render"],
        "missing_sku": sum(1 for r in rows if not r["sku"]),
        "price_on_application": sum(1 for r in rows if r["price_on_application"]),
        "median_price": round(statistics.median(prices), 2) if prices else None,
    }
    with open(os.path.join(out, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(coverage, f, indent=2)
    print(f"[3/4] Exported {len(rows)} SKUs from {coverage['products']} products -> {out}/catalogue.csv")
    print(f"[4/4] {coverage['requests_made']} requests in {coverage['duration_seconds']}s; "
          f"{removed} duplicates removed; {coverage['needs_render']} need rendering")
    return coverage


def main():
    ap = argparse.ArgumentParser(description="Harvest a retailer's full SKU catalogue.")
    ap.add_argument("--domain", required=True)
    ap.add_argument("--base", help="Override base URL (local testing)")
    ap.add_argument("--out")
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--render", action="store_true", help="Playwright for JavaScript-only pages")
    ap.add_argument("--max-products", type=int, default=0)
    ap.add_argument("--fresh", action="store_true", help="Ignore cache and checkpoint")
    ap.add_argument("--product-pattern", default=PRODUCT_RE)
    ap.add_argument("--page-limit", type=int, default=0, help="Quick scan: cap product pages read (page mode only)")
    a = ap.parse_args()
    if a.fresh and a.out and os.path.exists(os.path.join(a.out, "checkpoint.jsonl")):
        os.remove(os.path.join(a.out, "checkpoint.jsonl"))
    run(a.domain, a.base, a.out, a.delay, a.render, a.max_products, a.fresh, a.product_pattern, page_limit=a.page_limit)


if __name__ == "__main__":
    main()
