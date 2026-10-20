# Loxa Integration Profiler


Agent 2 of the Loxa partner-onboarding toolkit. Give it a retailer's domain and it writes the technical onboarding brief an integration engineer would otherwise spend a week assembling. It is read-only and never adds items to a cart or submits a form.

## Run it

From the repo root (the dashboard runs it for you; this is the agent on its own):

```bash
cd loxa-integration-profiler
python -m profiler.profile --domain michaelspiers.co.uk
python tests/run_tests.py   # 19 checks on offline test stores
```

Outputs go to `outputs/<domain>/`. Part of [Loxa Partner Onboarding](../README.md): the dashboard runs this agent alongside the other.

## How it solves the brief

| Brief asks | How the agent handles it |
|---|---|
| Platform detection | Wappalyzer-style signatures in `profiler/rules.json` (Shopify, Magento, BigCommerce, WooCommerce, Salesforce Commerce Cloud, Wix). Evidence from HTML, headers and a read-only feed probe adds up to a confidence score |
| Checkout flow type and steps | Shopify: hosted checkout, 1 step (one-page is Shopify's default) or 3 if the merchant switched, per Shopify's Help Center. Marked as *inferred* and sent to human review |
| Tag manager | Every `GTM-` container ID in the page source, plus GA4 IDs |
| Existing widgets | BNPL, trust badges and reviews, competing protection, payment methods, cookie consent, and analytics pixels |
| Recommended approach | Plain-English recommendation with reasoning (for Shopify: product and cart widget first; checkout only on Plus) |
| Risk flags and human review | Competing protection, BNPL placement, missing tracking, account prompts, an unconfirmed plan, and anything inferred |
| Reliable signals vs human review | Every finding is labelled header, html, probe or inferred, with a confidence score |
| Inspect checkout without a cart | Reads the cart page only if `robots.txt` allows it. Checkout behaviour is inferred from the platform, never by placing items in a cart |

## Own initiative (shown in the dashboard)

- **Integration Readiness Score.** A 0 to 100 score that starts at 100 and deducts for each risk, with every deduction shown. It also gives an indicative effort range. The scoring is our heuristic, not an industry standard.
- **Engineer checklist.** Every risk flag and review item becomes a clickable checklist with a progress bar.
- **Signal reliability table.** Shows what was seen directly and what was inferred.

## Add a new detection

Add one line to `profiler/rules.json`. No code changes needed.

## Known limits

- It reads up to 7 pages, so a widget that appears only deep in the site can be missed.
- The Shopify plan (Plus or not), post-payment flows and logged-in flows cannot be seen from outside the site. They are always listed for human review.
