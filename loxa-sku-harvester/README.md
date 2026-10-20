# Loxa SKU Harvester


Agent 1 of the Loxa partner-onboarding toolkit. Give it a retailer's domain and it returns the full catalogue at SKU level: name, brand, category path, variant, SKU, price, currency, availability and product URL. It works on any partner domain. The only input is the domain.

## Run it

From the repo root (the dashboard runs it for you; this is the agent on its own):

```bash
cd loxa-sku-harvester
python -m harvester.harvest --domain michaelspiers.co.uk
python tests/run_tests.py   # 21 checks on offline test stores
```

Outputs go to `outputs/<domain>/`. Part of [Loxa Partner Onboarding](../README.md): the dashboard runs this agent alongside the other.

## How it solves the brief

| Brief asks | How the agent handles it |
|---|---|
| Sitemap vs category crawling | Tries the cheapest complete source first: Shopify's public product feed (`/products.json`, up to 250 products per request), then `sitemap.xml` (follows sitemap indexes), then a bounded category crawl |
| Pagination and lazy-loading | Pages through the feed until it is empty; follows `rel="next"` and `?page=` links; `--render` scrolls JavaScript pages with Playwright |
| Rate limiting, respectful crawling | Honours `robots.txt`, waits between requests (default 1s), backs off on 429/503, identifies itself with a contact address, and counts every request |
| JavaScript-rendered pages | Reads structured data first. Pages with none are reported as `needs_render`, never silently dropped. `--render` uses Playwright for those pages only |
| Deduplication and taxonomy cleanup | Deduplicates by SKU, then URL and variant. Cleans categories and brand names using `harvester/taxonomy.json` (for example "ROLEX" becomes "Rolex", "Mens Watches" becomes "Watches") |
| Error handling and resumability | Feed pages are cached and product pages checkpointed, so an interrupted run resumes. Failures are logged, not fatal |

## Own initiative (shown in the dashboard)

- **Launch Phase Map.** Maps every SKU to the roll-out phases in the launch plan, with SKU count, stock and listed value per phase. Edit the phases in `taxonomy.json`.
- **Cover Opportunity Calculator.** Uses the median ticket from the live catalogue. Adjust orders, attach rate and premium rate to see premium per month and over 90 days, with IPT at the 12% standard rate. Orders and premium rate are inputs, not data.
- **Data quality panel.** Shows duplicates removed, missing SKUs, price-on-application items, and pages needing rendering.

## Point it at a new partner

Run the dashboard on the new address, or `python -m harvester.harvest --domain newpartner.co.uk`. If the partner uses unusual URLs or category names, edit `harvester/taxonomy.json` or pass `--product-pattern`. No code changes needed.

## Known limits

- Prices hidden as "price on application" are flagged, not guessed.
- The Shopify feed shows publicly listed products only.
- Playwright is optional and not installed by default.
