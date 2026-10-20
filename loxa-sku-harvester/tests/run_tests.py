#!/usr/bin/env python3
"""Runs the harvester against three local fixture stores and checks every brief requirement.
No internet needed. Usage: python tests/run_tests.py"""
import csv
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from harvester.harvest import run  # noqa: E402
import serve  # noqa: E402

BASE = f"http://127.0.0.1:{serve.PORT}"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))


def rows(out):
    with open(os.path.join(out, "catalogue.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    t0 = time.time()
    srv = serve.start()
    tmp = tempfile.mkdtemp()
    import io, contextlib
    quiet = contextlib.redirect_stdout(io.StringIO())
    try:
        print("Shopify feed store")
        out = os.path.join(tmp, "shop")
        with quiet:
            cov = run("shop", f"{BASE}/shop", out, delay=0)
        r = rows(out)
        check("uses the Shopify feed first", cov["strategy"] == "shopify_feed", cov["strategy"])
        check("paginates across feed pages", any(x["name"] == "Tudor Black Bay 54" for x in r))
        check("one row per variant (SKU level)", sum(1 for x in r if x["name"].startswith("Diamond")) == 2)
        check("removes duplicate SKUs", cov["duplicates_removed"] == 1, cov["duplicates_removed"])
        check("required fields present", set(["name", "category_path", "price", "product_url", "availability"]) <= set(r[0]))
        check("taxonomy cleaned (ROLEX -> Rolex, watches -> Watches)",
              any(x["category_path"] == "Watches > Rolex" for x in r))
        check("brand casing (Omega -> OMEGA)", any(x["brand"] == "OMEGA" for x in r))
        check("price on application flagged", any(x["price_on_application"] == "True" for x in r))
        check("currency detected", all(x["currency"] == "GBP" for x in r), r[0]["currency"])
        check("requests counted", cov["requests_made"] > 0)
        with quiet:
            run("shop", f"{BASE}/shop", out, delay=0)
        check("resumes from cache on rerun", rows(out) == r)

        print("Sitemap store")
        out = os.path.join(tmp, "sitemapsite")
        with quiet:
            cov = run("sitemapsite", f"{BASE}/sitemapsite", out, delay=0)
        r = rows(out)
        check("falls back to sitemap", cov["strategy"] == "sitemap", cov["strategy"])
        check("follows sitemap index; strips duplicate query URLs", cov["sitemap_product_urls"] == 5, cov["sitemap_product_urls"])
        check("reads JSON-LD with breadcrumb path", any(x["category_path"] == "Watches > Tudor" for x in r))
        check("reads meta-tag fallback", any(x["name"] == "OMEGA Constellation" for x in r))
        check("reads ProductGroup variants", sum(1 for x in r if x["sku"].startswith("DR-")) == 2)
        check("JavaScript-only page reported, not hidden", cov["needs_render"] == 1, cov["needs_render"])
        check("broken page reported as failed", cov["failed_pages"] == 1, cov["failed_pages"])
        before = cov["requests_made"]
        with quiet:
            cov2 = run("sitemapsite", f"{BASE}/sitemapsite", out, delay=0)
        check("checkpoint: rerun skips finished pages", cov2["requests_made"] < before,
              f"{cov2['requests_made']} vs {before}")

        print("Store with no sitemap")
        out = os.path.join(tmp, "nositemap")
        with quiet:
            cov = run("nositemap", f"{BASE}/nositemap", out, delay=0)
        r = rows(out)
        check("falls back to category crawl", cov["strategy"] == "crawl", cov["strategy"])
        check("follows pagination (rel=next)", any(x["brand"] == "TAG Heuer" for x in r))
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} checks passed in {time.time() - t0:.1f}s")
    with open(os.path.join(ROOT, "tests", "last_result.json"), "w") as f:
        json.dump({"passed": passed, "total": len(results), "checks": results,
                   "seconds": round(time.time() - t0, 1), "run_at": time.strftime("%Y-%m-%d %H:%M")}, f, indent=2)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
