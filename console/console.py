#!/usr/bin/env python3
"""
Loxa Partner Onboarding Console: a local website that runs both agents on any partner URL.

  python console.py                 start the console and open it in your browser
  python console.py --run <url>     run both agents from the terminal and print a summary (no browser)
  python console.py --check         self-test both agents and exit

Only the Python standard library is used here. The agents need: requests, beautifulsoup4, lxml.
"""
import argparse
import json
import mimetypes
import os
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from core import agents  # noqa: E402
from core.answer import answer  # noqa: E402
from core import issues  # noqa: E402

JOBS = {}
_selftest = {"at": 0, "data": None}


def selftest_cached():
    if time.time() - _selftest["at"] > 300 or _selftest["data"] is None:
        _selftest["data"] = agents.self_test()
        _selftest["at"] = time.time()
    return _selftest["data"]


def get_run(rid):
    if rid in JOBS:
        j = JOBS[rid]
        return j.view() if hasattr(j, "view") else j
    loaded = agents.load_run(rid)
    if loaded:
        JOBS[rid] = loaded
    return loaded


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        data = body if isinstance(body, bytes) else (json.dumps(body, default=str) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "text" in ctype or "json" in ctype else ""))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        if u.path in ("/", "/index.html"):
            return self.static("index.html")
        if u.path == "/crm":
            return self.static("crm.html")
        if len(parts) == 1 and os.path.isfile(os.path.join(ROOT, "web", os.path.basename(parts[0]))):
            return self.static(os.path.basename(parts[0]))
        if u.path == "/api/issues":
            rid = parse_qs(u.query).get("run", [""])[0]
            return self.send(200, issues.for_run(rid) if rid else issues.all_runs())
        if u.path == "/api/info":
            return self.send(200, {"mode": "local", "examples": agents.CONFIG["example_questions"],
                                   "default_url": agents.CONFIG["default_url"], "agents": agents.ensure_agents(),
                                   "ai": bool(os.environ.get("ANTHROPIC_API_KEY")), "repo": agents.CONFIG.get("github_repo")})
        if u.path == "/api/selftest":
            return self.send(200, selftest_cached())
        if u.path == "/api/history":
            return self.send(200, agents.history())
        if len(parts) == 3 and parts[:2] == ["api", "job"]:
            j = get_run(parts[2])
            if not j:
                return self.send(404, {"error": "unknown run"})
            since = int(parse_qs(u.query).get("since", ["0"])[0])
            if hasattr(JOBS.get(parts[2]), "view"):
                return self.send(200, JOBS[parts[2]].view(since))
            return self.send(200, j)
        if len(parts) == 4 and parts[0] == "files":
            rid, agent, fname = parts[1], parts[2], parts[3]
            path = os.path.join(agents.RUNS, rid, agent, fname)
            if agent in ("harvester", "profiler") and os.path.isfile(path) and ".." not in u.path:
                ctype = mimetypes.guess_type(path)[0] or "text/plain"
                return self.send(200, open(path, "rb").read(), ctype,
                                 {"Content-Disposition": f'attachment; filename="{rid}_{fname}"'})
            return self.send(404, {"error": "not found"})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/run":
            target = (self.body().get("target") or "").strip()
            if not target:
                return self.send(400, {"error": "enter a website address"})
            job = agents.Job(target).start()
            JOBS[job.id] = job
            return self.send(200, {"id": job.id})
        if u.path == "/api/ask":
            b = self.body()
            run = get_run(b.get("run_id", ""))
            if not run or not run.get("done"):
                return self.send(400, {"error": "run the agents first"})
            return self.send(200, answer(b.get("question", ""), run, b.get("mode", "auto")))
        self.send(404, {"error": "not found"})

    def static(self, name):
        path = os.path.join(ROOT, "web", name)
        self.send(200, open(path, "rb").read(), mimetypes.guess_type(path)[0] or "text/html")


def free_port(start):
    for p in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


def cli_run(target):
    job = agents.Job(target).start()
    seen = 0
    while not job.done:
        v = job.view(seen)
        for l in v["log"]:
            print(f"  {l['t']:>5}s  [{l['agent']}] {l['line']}")
        seen = v["log_len"]
        time.sleep(0.3)
    h, p = job.result["harvester"], job.result["profiler"]
    print(f"\nRun {job.id} finished in {job.meta['seconds']}s  ->  runs/{job.id}/")
    if h:
        print(f"  Agent 1: {h['coverage']['skus']} SKUs via {h['coverage']['strategy']} ({job.meta['agents']['harvester']['source']})")
    if p:
        print(f"  Agent 2: {p['platform']['name']}, readiness {p['readiness']['score']}/100 ({job.meta['agents']['profiler']['source']})")
    return job


def save_snapshots(job):
    """Copy a live run's outputs into each agent's snapshots/ folder (the offline fallback)."""
    import shutil
    for name in ("harvester", "profiler"):
        info = job.meta["agents"].get(name, {})
        if job.result.get(name) and info.get("source") == "live":
            dst = os.path.join(agents.agent_dir(name), "snapshots", job.slug)
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(os.path.join(job.dir, name), dst, ignore=shutil.ignore_patterns("cache", "checkpoint.jsonl"))
            print(f"  Offline backup saved: {dst}")
        else:
            print(f"  {name}: no live data, offline backup not updated")


def publish(job, folder):
    """Export one run (results, log, problems) as JSON for the static GitHub dashboard."""
    os.makedirs(folder, exist_ok=True)
    if not any(job.result.values()):
        print("  Nothing to publish: no live data and no backup.")
        return
    payload = {**job.view(), "issues": issues.for_run(job.id)}
    with open(os.path.join(folder, f"{job.slug}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str)
    idx_path = os.path.join(folder, "index.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else []
    idx = [e for e in idx if e["slug"] != job.slug]
    h, p = job.result["harvester"], job.result["profiler"]
    idx.insert(0, {"slug": job.slug, "id": job.id, "target": job.meta["target"], "started": job.meta["started"],
                   "skus": h["coverage"]["skus"] if h else None, "platform": p["platform"]["name"] if p else None,
                   "readiness": p["readiness"]["score"] if p else None})
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)
    print(f"  Published for the GitHub dashboard: {folder}/{job.slug}.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--run", metavar="URL")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--save", action="store_true", help="with --run: save live results as each agent's offline snapshot")
    ap.add_argument("--publish", metavar="DIR", help="with --run: export the run for the GitHub dashboard into DIR")
    a = ap.parse_args()
    status = agents.ensure_agents()
    print("Agents:", status)
    if a.check:
        res = agents.self_test()
        print(json.dumps(res))
        sys.exit(0 if all(r["ok"] for r in res.values()) else 1)
    if a.run:
        job = cli_run(a.run)
        if a.save:
            save_snapshots(job)
        if a.publish:
            publish(job, a.publish)
        sys.exit(0 if any(job.result.values()) else 1)
    port = free_port(a.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"\n  Loxa Partner Onboarding Console running at {url}\n  Press Ctrl+C to stop.\n")
    threading.Thread(target=selftest_cached, daemon=True).start()
    if not a.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
