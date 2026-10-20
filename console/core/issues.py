"""Problems & errors log: every error, warning and review item found across runs, with a suggested fix."""
import json
import os

from .agents import RUNS


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def for_run(run_id):
    d = os.path.join(RUNS, run_id)
    meta = _load(os.path.join(d, "run_log.json")) or {}
    cov = _load(os.path.join(d, "harvester", "coverage.json"))
    prof = _load(os.path.join(d, "profiler", "profile.json"))
    at, target = meta.get("started", ""), meta.get("target", run_id)
    out = []

    def add(sev, agent, title, fix, kind="System"):
        out.append({"at": at, "run": run_id, "target": target, "agent": agent, "severity": sev,
                    "kind": kind, "title": title, "fix": fix})

    names = {"harvester": "Agent 1", "profiler": "Agent 2"}
    for key, info in (meta.get("agents") or {}).items():
        a = names.get(key, key)
        if info.get("source") == "none":
            add("error", a, "No data returned and no saved backup", "Check the address and connection, then run again")
        elif info.get("source") == "snapshot":
            add("warning", a, "Live site unreachable, so the saved backup was shown", "Run again when online to refresh it")
        if info.get("exit_code") not in (0, None):
            add("error", a, f"Agent stopped with exit code {info['exit_code']}", "Open run_log.json in this run's folder")
    if cov and cov.get("skus", 0):
        if cov.get("failed_pages"):
            add("warning", "Agent 1", f"{cov['failed_pages']} product pages failed to load", "Run again: only failed pages are retried")
        if cov.get("needs_render"):
            add("warning", "Agent 1", f"{cov['needs_render']} pages need a JavaScript render", "Run the harvester with --render")
        if cov.get("blocked_by_robots"):
            add("info", "Agent 1", f"{cov['blocked_by_robots']} pages skipped because robots.txt disallows them", "By design; ask the partner for a product feed if needed")
        if cov.get("quick_scan_limit"):
            add("info", "Agent 1", f"Quick scan read the first {cov['quick_scan_limit']} product pages", "Run a full crawl from the command line")
        if cov.get("price_on_application"):
            add("review", "Agent 1", f"{cov['price_on_application']} SKUs are price on application", "Get valuations from the partner before pricing cover", "Data")
        if cov.get("missing_sku"):
            add("info", "Agent 1", f"{cov['missing_sku']} SKUs have no SKU code", "Match on product URL instead", "Data")
        if cov.get("duplicates_removed"):
            add("info", "Agent 1", f"{cov['duplicates_removed']} duplicate listings removed", "Resolved automatically", "Data")
    if prof and any(v == 200 for v in prof.get("pages_read", {}).values()):
        if prof["platform"]["confidence"] < 0.6:
            add("warning", "Agent 2", f"Platform identified with only {prof['platform']['confidence']:.0%} confidence", "Confirm the platform with the partner")
        for f in prof.get("risk_flags", []):
            add("warning", "Agent 2", f, "Discuss with the partner before launch", "Partner risk")
        for r in prof.get("human_review", []):
            add("review", "Agent 2", r, "Confirm with the partner's developers", "Needs a person")
    return out


def all_runs(limit=30):
    if not os.path.isdir(RUNS):
        return []
    ids = sorted((d for d in os.listdir(RUNS) if os.path.isdir(os.path.join(RUNS, d))), reverse=True)[:limit]
    return [i for rid in ids for i in for_run(rid)]
