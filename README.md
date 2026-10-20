# Loxa Partner Onboarding

![dashboard](https://github.com/SERKCORP/loxa-onboarding/actions/workflows/dashboard.yml/badge.svg)

## Live dashboard: **https://SERKCORP.github.io/loxa-onboarding/**

Two AI agents, built in Claude Code, that turn a retailer's website into an onboarding snapshot, and one dashboard that shows them working.

| | What it does |
|---|---|
| **Agent 1 · SKU Harvester** ([`loxa-sku-harvester/`](loxa-sku-harvester)) | Builds the partner's full SKU catalogue: name, brand, category path, price, stock, URL |
| **Agent 2 · Integration Profiler** ([`loxa-integration-profiler/`](loxa-integration-profiler)) | Writes the technical integration brief: platform, checkout, tags, widgets, recommendation, risks |
| **Dashboard** ([`console/`](console)) | Runs both agents and shows the snapshot, both agents' results, a question box, and a problems log |

## Try it

- **On GitHub (no install):** open the live dashboard above and press **Start here** for a guided tour. To run a new partner, open **Actions → dashboard → Run workflow** and enter a website address. GitHub runs both agents and republishes the dashboard in about two minutes.
- **On a laptop (any site in seconds):**
  ```bash
  git clone https://github.com/SERKCORP/loxa-onboarding && cd loxa-onboarding
  pip install -r console/requirements.txt
  python console/console.py
  ```

## How it stays honest
- **Tests:** every push runs 67 automated checks on offline test stores before anything is published.
- **Respectful crawling:** both agents honour robots.txt and rate-limit. Agent 2 never adds anything to a cart.
- **Problems log:** every error, warning and item needing a person is listed with a suggested fix.
- **Prompts:** each folder's `prompts_log.md` shows how Claude Code was directed, including what broke and how it was fixed.

Docs: [Brief mapping](console/docs/BRIEF_MAPPING.md) · [Decisions](console/docs/DECISIONS.md) · [Architecture](console/docs/ARCHITECTURE.md)
