# Architecture

```mermaid
flowchart LR
  U[You type a URL] --> C[Console website<br/>localhost]
  C -->|starts in parallel| A1[Agent 1<br/>SKU Harvester]
  C -->|starts in parallel| A2[Agent 2<br/>Integration Profiler]
  A1 -->|robots.txt, Shopify feed, sitemap, crawl| S[(Partner website)]
  A2 -->|read-only: home, product, collection, headers| S
  A1 --> R1[catalogue.csv<br/>coverage.json]
  A2 --> R2[profile.json<br/>brief.md]
  R1 & R2 --> L[runs/&lt;id&gt;/ run_log.json]
  L --> C
  C --> Q[Ask the agents<br/>answers from run data]
  Q --> QL[qa_log.jsonl]
  G[GitHub Actions] -->|tests, runs agents, publishes| P[published_runs/*.json]
  P --> W[GitHub Pages dashboard]
```

- **Agents** are ordinary command-line programs. The console runs them as separate processes, so the demo proves the real CLI works.
- **Each run** gets its own folder: the outputs, the full log, timings, and every question asked.
- **Fallback**: if a live run returns nothing, the console loads the agent's saved snapshot and labels it on screen.
- **GitHub mode**: Pages can only host static files, so GitHub Actions runs the agents (on push, daily, or on demand with a URL), saves the results to `published_runs/`, and redeploys the dashboard. The browser answers questions with a port of the same logic, tested for identical output.
- **Laptop mode**: the same dashboard served by `console.py` runs the agents directly, in seconds.
