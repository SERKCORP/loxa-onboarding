#!/usr/bin/env python3
"""End-to-end test of the console: real server, real agents, two local partner sites, the
three example questions, downloads and run history. No internet needed.
Usage: python tests/run_tests.py"""
import json
import os
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("LOXA_DELAY", "0")
import tempfile  # noqa: E402
os.environ["LOXA_RUNS_DIR"] = tempfile.mkdtemp(prefix="loxa-test-runs-")  # keep test runs out of Run history
os.environ.pop("ANTHROPIC_API_KEY", None)  # test the built-in answer engine
import serve  # noqa: E402
import console as app  # noqa: E402  (console.py)
from http.server import ThreadingHTTPServer  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  ({str(detail)[:160]})" if detail and not cond else ""))


def call(base, path, body=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if r.headers.get_content_type() == "application/json" else raw


def run_job(base, target):
    jid = call(base, "/api/run", {"target": target})["id"]
    t0 = time.time()
    while True:
        v = call(base, f"/api/job/{jid}")
        if v["done"] or time.time() - t0 > 90:
            return v, time.time() - t0
        time.sleep(0.3)


def main():
    t0 = time.time()
    fixture = serve.start()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        print("Console start-up")
        info = call(base, "/api/info")
        check("both agents found", all(v in ("ready", "cloned") for v in info["agents"].values()), info["agents"])
        check("three example questions configured", len(info["examples"]) == 3)
        page = call(base, "/")
        check("website served", b"Run both agents" in page)
        st = call(base, "/api/selftest")
        check("agents' own test suites pass", all(v["ok"] for v in st.values()), st)

        print("Shopify-style partner")
        v, secs = run_job(base, f"http://127.0.0.1:{serve.PORT}/store")
        h, p = v["result"]["harvester"], v["result"]["profiler"]
        check("both agents finished", v["state"] == {"harvester": "done", "profiler": "done"}, v["state"])
        check("finished in a few seconds", secs < 20, f"{secs:.1f}s")
        check("live log streamed from both agents", {l["agent"] for l in v["log"]} == {"harvester", "profiler"})
        check("Agent 1: SKUs harvested via Shopify feed", h and h["coverage"]["strategy"] == "shopify_feed" and h["coverage"]["skus"] >= 20,
              h and h["coverage"])
        check("Agent 1: rows mapped to launch phases", h and {"Phase 1 · Month 1", "Phase 2 · Month 2"} <= {r["phase"] for r in h["rows"]})
        check("Agent 2: Shopify detected", p and p["platform"]["name"] == "Shopify", p and p["platform"])
        check("Agent 2: GTM and BNPL found", p and p["gtm_containers"] == ["GTM-TESTGTM1"] and "Klarna" in p["widgets"]["bnpl"])
        rid = v["id"]
        examples = info["examples"]
        a1 = call(base, "/api/ask", {"run_id": rid, "question": examples[0]})
        check("Q1 (platform and integration) answered", "Shopify" in a1["answer"] and "approach" in a1["answer"].lower(), a1["answer"])
        a2 = call(base, "/api/ask", {"run_id": rid, "question": examples[1]})
        check("Q2 (Rolex in stock and median) answered", "Rolex" in a2["answer"] and "Median" in a2["answer"], a2["answer"])
        a3 = call(base, "/api/ask", {"run_id": rid, "question": examples[2]})
        check("Q3 (competing protection and BNPL) answered", "Klarna" in a3["answer"] and "protection" in a3["answer"].lower(), a3["answer"])
        a4 = call(base, "/api/ask", {"run_id": rid, "question": "What's the commercial opportunity?"})
        check("commercial question answered with clearly labelled inputs", "Illustrative" in a4["answer"] and "£" in a4["answer"], a4["answer"])
        a5 = call(base, "/api/ask", {"run_id": rid, "question": "Which phase should we launch first?"})
        check("launch phase question answered", "Phase 1" in a5["answer"], a5["answer"])
        check("every answer names its source", all(x["sources"] for x in (a1, a2, a3, a4, a5)))
        csv_bytes = call(base, f"/files/{rid}/harvester/catalogue.csv")
        check("catalogue.csv downloadable", csv_bytes.startswith(b"name,brand,category_path"))
        brief = call(base, f"/files/{rid}/profiler/brief.md")
        check("brief.md downloadable", b"# Integration brief" in brief)
        run_dir = os.path.join(os.environ["LOXA_RUNS_DIR"], rid)
        check("run logged to its own folder", all(os.path.exists(os.path.join(run_dir, f)) for f in ("run_log.json", "qa_log.jsonl")))

        print("Second partner (not Shopify): proves reuse")
        v2, secs2 = run_job(base, f"http://127.0.0.1:{serve.PORT}/jeweller")
        h2, p2 = v2["result"]["harvester"], v2["result"]["profiler"]
        check("Agent 1 falls back to the sitemap", h2 and h2["coverage"]["strategy"] == "sitemap" and h2["coverage"]["skus"] == 2, h2 and h2["coverage"])
        check("Agent 2 detects Magento", p2 and p2["platform"]["name"] == "Magento", p2 and p2["platform"])
        hist = call(base, "/api/history")
        check("both runs listed in history", {rid, v2["id"]} <= {r["id"] for r in hist})
        reload = call(base, f"/api/job/{rid}")
        check("past run reloads", reload.get("done") and reload["result"]["harvester"])
        print("GitHub dashboard export")
        import shutil
        import subprocess
        pub = os.path.join(os.environ["LOXA_RUNS_DIR"], "published")
        site = os.path.join(os.environ["LOXA_RUNS_DIR"], "site")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "console.py"), "--run", f"http://127.0.0.1:{serve.PORT}/store",
                            "--publish", pub], capture_output=True, text=True, env=dict(os.environ))
        idx = json.load(open(os.path.join(pub, "index.json"), encoding="utf-8")) if os.path.exists(os.path.join(pub, "index.json")) else []
        check("run published for the GitHub dashboard", idx and idx[0]["skus"] >= 20 and idx[0]["platform"] == "Shopify", r.stdout[-300:])
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_site.py"), "--runs", pub, "--out", site],
                           capture_output=True, text=True)
        built = all(os.path.exists(os.path.join(site, f)) for f in ("index.html", "app.js", "answer.js", "crm.html", "data/site.json"))
        check("static GitHub site builds with the published run", built and os.path.exists(os.path.join(site, "data", idx[0]["slug"] + ".json")), r.stdout)
        run_json = json.load(open(os.path.join(pub, idx[0]["slug"] + ".json"), encoding="utf-8"))
        from core.answer import builtin
        qs = examples + ["What's the commercial opportunity?", "Which phase should we launch first?", "How many Rolex in stock?",
                         "What's the checkout like?", "Any risks?", "How long to integrate?", "How did the agents work?",
                         "Show me Speedmaster", "What tracking do they use?", "OMEGA prices", "something unrelated"]
        cases = []
        for q in qs:
            ans, srcs = builtin(q, run_json["result"]["harvester"], run_json["result"]["profiler"])
            cases.append({"run": run_json, "question": q, "expected": {"answer": ans, "sources": srcs}})
        cpath = os.path.join(os.environ["LOXA_RUNS_DIR"], "cases.json")
        json.dump(cases, open(cpath, "w", encoding="utf-8"))
        if shutil.which("node"):
            r = subprocess.run(["node", os.path.join(ROOT, "tests", "answer_parity.js"), cpath], capture_output=True, text=True)
            check("browser answers match the Python engine exactly", r.returncode == 0, r.stdout[-800:])
        else:
            print("  SKIP  browser answer parity (Node.js not installed)")
    finally:
        srv.shutdown()
        fixture.shutdown()
    passed = sum(ok for _, ok in results)
    print(f"\n{passed}/{len(results)} checks passed in {time.time() - t0:.1f}s")
    json.dump({"passed": passed, "total": len(results), "checks": results, "run_at": time.strftime("%Y-%m-%d %H:%M")},
              open(os.path.join(ROOT, "tests", "last_result.json"), "w"), indent=2)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
