# Decision log

| # | Decision | Why | Trade-off |
|---|---|---|---|
| 1 | One repo: two agent folders plus the dashboard | One link, one dashboard, one CI run; each agent still runs and tests on its own | Agents share a release cycle |
| 2 | Shopify feed first, then sitemap, then crawl | The cheapest complete source first: about 250 products per request | Only covers publicly listed products |
| 3 | Structured data (JSON-LD) before scraping HTML | Stable across themes; gives SKU, price and stock directly | Sites without it need `--render` |
| 4 | Playwright optional, not default | Heavy to install, slow, and not needed for most stores | JavaScript-only sites need one extra flag |
| 5 | Profiler is read-only and never touches a cart | No side effects on a partner's live store; safe to run on anyone | Checkout steps are inferred, not observed |
| 6 | Own Wappalyzer-style rules in JSON | Loxa's format, confidence scores, one-line additions | We maintain the rules |
| 7 | Every finding labelled with its source and confidence | Answers the brief's "reliable vs human review" question | More output to read |
| 8 | GitHub Pages dashboard fed by GitHub Actions, plus a laptop mode | Pages can't run Python and browsers can't read other sites (CORS), so Actions runs the agents and publishes results; the laptop runs them in seconds | New partners take about two minutes on GitHub |
| 9 | Built-in Q&A by default, Claude optional | Repeatable, free, offline and never invents an answer | Less flexible phrasing without a key |
| 10 | Snapshot fallback | The demo survives bad wifi or a site outage | Snapshot data can be stale; it's labelled on screen |
| 11 | Calculator inputs labelled illustrative | Only the ticket size is real data; the rest are clearly labelled inputs | Less dramatic headline |
| 12 | Quick-scan cap (150 pages) in the console for non-Shopify sites | Keeps live runs within seconds | Full crawl runs from the command line |
| 13 | Question answering ported to the browser | The GitHub dashboard answers questions with no server | Two implementations, kept identical by a parity test |
