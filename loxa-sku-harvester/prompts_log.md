# Prompts log: SKU Harvester

| # | Prompt | Result | What broke and the fix |
|---|---|---|---|
| 1 | Build a reusable agent that harvests a retailer's full SKU catalogue from its domain: polite crawling, resumable, tested offline | `harvester/harvest.py`, three fixture stores, 21-check test runner | Coverage counts were wrong after a resumed run; now read from the checkpoint |
| 2 | Use the cheapest complete source first: Shopify's product feed, then sitemap, then category crawl | Feed, sitemap index and paginated crawl | A gap figure was shown for crawl runs where it means nothing; now only for sitemap runs |
| 3 | Clean brands and categories without code changes | `harvester/taxonomy.json` | — |
| 4 | Add a one-command demo with an offline fallback | `demo.py`, snapshots | Missing `importlib.util` import found by running the demo; fixed |
