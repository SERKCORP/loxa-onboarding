"""Finds, updates, runs and reads the two agents. Each agent runs as its own process,
exactly as it does from the command line, so the console proves the real CLI works."""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
RUNS = os.environ.get("LOXA_RUNS_DIR") or os.path.join(ROOT, "runs")  # tests use a temp folder


def agent_dir(name):
    """Agent folder: env override, else a sibling folder of console/ in the repo."""
    cfg = CONFIG["agents"][name]
    env = os.environ.get(f"LOXA_{name.upper()}_DIR")
    return env or os.path.join(os.path.dirname(ROOT), cfg["folder"])


def ensure_agents(log=print):
    """Both agents live in the same repo, next to this console folder."""
    return {name: ("ready" if os.path.isdir(agent_dir(name)) else "missing") for name in CONFIG["agents"]}


def parse_target(text):
    """'michaelspiers.co.uk', 'https://www.x.com/shop' or 'http://127.0.0.1:8799/store' -> (slug, base)."""
    t = text.strip()
    if not re.match(r"^https?://", t):
        t = "https://" + t
    u = urlparse(t)
    host = u.netloc.lower()
    path = u.path.rstrip("/")
    base = f"{u.scheme}://{u.netloc}{path}"
    slug = re.sub(r"[^a-z0-9.\-]+", "-", (host + path).replace("www.", "", 1)).strip("-")
    return slug, base


def run_agent(name, slug, base, out, on_line):
    cfg = CONFIG["agents"][name]
    cmd = [sys.executable, "-u", "-m", cfg["module"], "--domain", slug, "--base", base,
           "--out", out, "--delay", os.environ.get("LOXA_DELAY", str(cfg["delay"]))]
    if name == "harvester" and cfg.get("page_limit"):
        cmd += ["--page-limit", str(cfg["page_limit"])]
    t0 = time.time()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")  # same output on Windows and Mac
    p = subprocess.Popen(cmd, cwd=agent_dir(name), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", env=env)
    for line in p.stdout:
        on_line(line.rstrip())
    p.wait()
    return {"exit_code": p.returncode, "seconds": round(time.time() - t0, 1), "command": " ".join(cmd[1:])}


def read_harvest(out):
    cov_p, cat_p = os.path.join(out, "coverage.json"), os.path.join(out, "catalogue.csv")
    if not (os.path.exists(cov_p) and os.path.exists(cat_p)):
        return None
    cov = json.load(open(cov_p, encoding="utf-8"))
    rows = list(csv.DictReader(open(cat_p, encoding="utf-8")))
    sys.path.insert(0, agent_dir("harvester"))
    try:
        from harvester.harvest import assign_phase, load_taxonomy
        tax = load_taxonomy()
        phases = tax["phases"]
        casing = tax.get("brand_casing", {})
        for r in rows:
            r["phase"] = assign_phase(r, phases)
    except Exception:
        phases, casing = [], {}
    return {"coverage": cov, "rows": rows, "phases": phases, "brand_casing": casing} if cov.get("skus", len(rows)) else None


def read_profile(out):
    p = os.path.join(out, "profile.json")
    if not os.path.exists(p):
        return None
    prof = json.load(open(p, encoding="utf-8"))
    bp = os.path.join(out, "brief.md")
    prof["brief_md"] = open(bp, encoding="utf-8").read() if os.path.exists(bp) else ""
    return prof if any(v == 200 for v in prof.get("pages_read", {}).values()) else None


def snapshot(name, slug):
    d = os.path.join(agent_dir(name), "snapshots", slug)
    return d if os.path.isdir(d) else None


class Job:
    def __init__(self, target):
        self.slug, self.base = parse_target(target)
        self.id = time.strftime("%Y%m%d-%H%M%S") + "_" + self.slug.replace("/", "-")
        self.dir = os.path.join(RUNS, self.id)
        os.makedirs(self.dir, exist_ok=True)
        self.log = []
        self.state = {"harvester": "queued", "profiler": "queued"}
        self.result = {"harvester": None, "profiler": None}
        self.meta = {"id": self.id, "target": target, "slug": self.slug, "base": self.base,
                     "started": time.strftime("%Y-%m-%d %H:%M:%S"), "agents": {}}
        self.done = False
        self.t0 = time.time()

    def add(self, agent, line):
        if line:
            self.log.append({"t": round(time.time() - self.t0, 1), "agent": agent, "line": line})

    def _one(self, name, reader):
        self.state[name] = "running"
        out = os.path.join(self.dir, name)
        info = run_agent(name, self.slug, self.base, out, lambda l: self.add(name, l))
        data, source = reader(out), "live"
        if data is None:
            snap = snapshot(name, self.slug)
            if snap:
                data, source = reader(snap), "snapshot"
                shutil.copytree(snap, out, dirs_exist_ok=True)
                self.add(name, f"Live run returned no data. Using saved snapshot from {snap}.")
            else:
                self.add(name, "Live run returned no data and there is no saved snapshot for this site.")
        info["source"] = source if data else "none"
        self.meta["agents"][name] = info
        self.result[name] = data
        self.state[name] = "done" if data else "failed"

    def start(self):
        threads = [threading.Thread(target=self._one, args=("harvester", read_harvest)),
                   threading.Thread(target=self._one, args=("profiler", read_profile))]
        for t in threads:
            t.start()

        def finish():
            for t in threads:
                t.join()
            self.meta["seconds"] = round(time.time() - self.t0, 1)
            self.meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
            json.dump({**self.meta, "log": self.log}, open(os.path.join(self.dir, "run_log.json"), "w"), indent=2)
            self.done = True
        threading.Thread(target=finish, daemon=True).start()
        return self

    def view(self, since=0):
        return {"id": self.id, "slug": self.slug, "base": self.base, "state": self.state, "done": self.done,
                "elapsed": round(time.time() - self.t0, 1), "log": self.log[since:], "log_len": len(self.log),
                "meta": self.meta, "result": self.result if self.done else None}


def load_run(run_id):
    d = os.path.join(RUNS, run_id)
    if not os.path.isdir(d):
        return None
    meta = json.load(open(os.path.join(d, "run_log.json"))) if os.path.exists(os.path.join(d, "run_log.json")) else {}
    return {"id": run_id, "slug": meta.get("slug", run_id), "base": meta.get("base", ""), "done": True,
            "state": {k: "done" for k in ("harvester", "profiler")}, "meta": meta, "log": meta.get("log", []),
            "result": {"harvester": read_harvest(os.path.join(d, "harvester")),
                       "profiler": read_profile(os.path.join(d, "profiler"))}}


def history():
    out = []
    for rid in sorted(os.listdir(RUNS), reverse=True):
        p = os.path.join(RUNS, rid, "run_log.json")
        if os.path.exists(p):
            m = json.load(open(p))
            out.append({"id": rid, "target": m.get("target"), "started": m.get("started"), "seconds": m.get("seconds"),
                        "sources": {k: v.get("source") for k, v in m.get("agents", {}).items()}})
    return out[:30]


def self_test():
    res = {}
    for name in CONFIG["agents"]:
        d = agent_dir(name)
        if not os.path.isdir(d):
            res[name] = {"passed": 0, "total": 0, "ok": False}
            continue
        p = subprocess.run([sys.executable, "tests/run_tests.py"], cwd=d, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1"))
        m = re.search(r"(\d+)/(\d+) checks passed", p.stdout)
        res[name] = {"passed": int(m.group(1)) if m else 0, "total": int(m.group(2)) if m else 0, "ok": p.returncode == 0}
    return res
