# Prompts log: Integration Profiler

| # | Prompt | Result | What broke and the fix |
|---|---|---|---|
| 1 | Build a read-only agent that turns a domain into an integration brief: platform, checkout, tags, widgets, recommendation, risks | `profiler/profile.py`, 19-check test runner | — |
| 2 | Keep detection rules editable, Wappalyzer-style, and label every finding as direct or inferred | `profiler/rules.json`, signal table | An empty product feed counted as Shopify evidence (false positive); the probe now needs real products |
| 3 | Base checkout steps on Shopify's documentation and mark them inferred | Checkout section | — |
| 4 | Add an explainable readiness score | Readiness score with every deduction shown | — |
