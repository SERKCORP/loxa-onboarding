#!/usr/bin/env python3
"""Runs the profiler against three local fixture stores and checks every brief requirement.
No internet needed. Usage: python tests/run_tests.py"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from profiler.profile import build  # noqa: E402
import serve  # noqa: E402

BASE = f"http://127.0.0.1:{serve.PORT}"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))


def main():
    t0 = time.time()
    srv = serve.start()
    tmp = tempfile.mkdtemp()
    try:
        print("Shopify store")
        with contextlib.redirect_stdout(io.StringIO()):
            p = build("shop", f"{BASE}/shop", os.path.join(tmp, "shop"), delay=0)
        check("detects Shopify from HTML, header and feed", p["platform"]["name"] == "Shopify"
              and {e["source"] for e in p["platform"]["evidence"]} >= {"html", "header", "probe"}, p["platform"])
        check("high confidence when signals agree", p["platform"]["confidence"] >= 0.9, p["platform"]["confidence"])
        check("finds GTM container ID", p["gtm_containers"] == ["GTM-K7Q2ZX"], p["gtm_containers"])
        check("finds GA4 measurement ID", p["ga4_ids"] == ["G-AB12CD34EF"], p["ga4_ids"])
        check("finds BNPL on a product page", "Klarna" in p["widgets"]["bnpl"], p["widgets"]["bnpl"])
        check("finds trust badges", "Trustpilot" in p["widgets"]["trust"], p["widgets"]["trust"])
        check("finds competing protection", "Extend" in p["widgets"]["protection"], p["widgets"]["protection"])
        check("finds cookie consent tool", "OneTrust" in p["widgets"]["consent"], p["widgets"]["consent"])
        check("respects robots.txt (cart not read)", p["pages_read"]["cart"] == "blocked_by_robots", p["pages_read"])
        check("checkout steps from Shopify docs, marked inferred",
              p["checkout"]["steps"].startswith("1") and p["checkout"]["steps_source"] == "inferred")
        check("recommends product and cart widget first", p["recommendation"]["approach"].startswith("Loxa widget on product"))
        check("risk flag for competing protection", any("Competing protection" in f for f in p["risk_flags"]))
        check("human review: Shopify plan", any("Shopify plan" in x for x in p["human_review"]))
        check("readiness score with deductions", 0 <= p["readiness"]["score"] < 100 and p["readiness"]["deductions"])
        brief = open(os.path.join(tmp, "shop", "brief.md"), encoding="utf-8").read()
        check("brief written with all sections", all(s in brief for s in
              ["## Platform", "## Checkout", "## Tags and widgets", "## Recommended Loxa approach", "## Risk flags", "## Human review required"]))

        print("Magento store")
        with contextlib.redirect_stdout(io.StringIO()):
            p = build("magento", f"{BASE}/magento", os.path.join(tmp, "magento"), delay=0)
        check("detects Magento", p["platform"]["name"] == "Magento", p["platform"])
        check("finds Clearpay", "Clearpay" in p["widgets"]["bnpl"], p["widgets"]["bnpl"])

        print("Custom site")
        with contextlib.redirect_stdout(io.StringIO()):
            p = build("custom", f"{BASE}/custom", os.path.join(tmp, "custom"), delay=0)
        check("unknown platform gets low confidence", p["platform"]["name"] == "Custom or unknown" and p["platform"]["confidence"] < 0.5)
        check("low score sends it to scoping", p["readiness"]["band"] == "Needs scoping", p["readiness"])
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
