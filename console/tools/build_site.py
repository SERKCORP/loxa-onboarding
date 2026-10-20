#!/usr/bin/env python3
"""Builds the static GitHub Pages dashboard: the same web app plus every published run.
Usage: python console/tools/build_site.py [--runs published_runs] [--out site]"""
import argparse
import json
import os
import shutil

CONSOLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(CONSOLE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.join(REPO, "published_runs"))
    ap.add_argument("--out", default=os.path.join(REPO, "site"))
    a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True)
    shutil.copytree(os.path.join(CONSOLE, "web"), a.out)
    data = os.path.join(a.out, "data")
    os.makedirs(data, exist_ok=True)
    idx = []
    if os.path.isdir(a.runs):
        for f in os.listdir(a.runs):
            if f.endswith(".json"):
                shutil.copy(os.path.join(a.runs, f), data)
        ip = os.path.join(a.runs, "index.json")
        if os.path.exists(ip):
            idx = json.load(open(ip, encoding="utf-8"))
    tests = {}
    for name, folder in (("harvester", "loxa-sku-harvester"), ("profiler", "loxa-integration-profiler"), ("console", "console")):
        tp = os.path.join(REPO, folder, "tests", "last_result.json")
        if os.path.exists(tp):
            t = json.load(open(tp, encoding="utf-8"))
            tests[name] = {"passed": t["passed"], "total": t["total"], "ok": t["passed"] == t["total"], "run_at": t.get("run_at")}
    cfg = json.load(open(os.path.join(CONSOLE, "config.json"), encoding="utf-8"))
    site = {"mode": "static", "examples": cfg["example_questions"], "default_url": cfg["default_url"],
            "repo": os.environ.get("GITHUB_REPOSITORY") or cfg.get("github_repo"), "runs": idx, "tests": tests}
    with open(os.path.join(data, "site.json"), "w", encoding="utf-8") as f:
        json.dump(site, f, indent=2)
    idx_html = os.path.join(a.out, "index.html")  # mark as the GitHub copy so it never probes for a local server
    with open(idx_html, encoding="utf-8") as f:
        html = f.read().replace("<head>", '<head><meta name="loxa-mode" content="static">', 1)
    with open(idx_html, "w", encoding="utf-8") as f:
        f.write(html)
    open(os.path.join(a.out, ".nojekyll"), "w").close()
    print(f"Site built: {a.out} ({len(idx)} published partner run(s))")


if __name__ == "__main__":
    main()
