# Loxa Partner Onboarding Console


The dashboard for [Loxa Partner Onboarding](../README.md). The same web app runs in two places:

- **GitHub Pages:** shows runs that GitHub Actions performed and published. New partners run through **Actions → dashboard → Run workflow**.
- **A laptop:** `python console/console.py` runs both agents live on any website in seconds.

| Command (from the repo root) | What it does |
|---|---|
| `python console/console.py` | Start the dashboard locally |
| `python console/console.py --run michaelspiers.co.uk` | Run both agents in the terminal and print a summary |
| `python console/console.py --run <site> --publish published_runs` | Run and export the result for the GitHub dashboard |
| `python console/tools/build_site.py` | Build the GitHub Pages site from published runs |
| `python console/tests/run_tests.py` | End-to-end tests, including browser and Python answer parity |

## What's on the page

| View | Shows |
|---|---|
| **Snapshot** | The partner at a glance: readiness dial, catalogue sub-dials, onboarding track, stock and launch-phase charts |
| **Agent 1 · Catalogue** | Crawl proof, Launch Phase Map, brands, price bands, Cover Opportunity Calculator, searchable catalogue |
| **Agent 2 · Integration** | Platform and confidence, readiness breakdown, engineer checklist, widgets found, signal reliability |
| **Ask** | Questions answered from the run's data, each with its source |
| **Problems log** | Every error, warning and review item across runs, with a suggested fix |
| **CRM sync** | Placeholder for pushing the snapshot into the CRM in a later phase |

Press **Start here** for a guided tour. The ⓘ buttons explain what each view shows and why it matters.

## Ask the agents: two modes

- **Default:** built-in logic over the run's own files. It works offline, is free and repeatable, and never invents an answer.
- **Optional:** set `ANTHROPIC_API_KEY` before starting, and Claude phrases the answers, grounded only in the same data. The model is set in `config.json`. The answer card shows which mode was used.

## Documentation

- [Brief mapping](docs/BRIEF_MAPPING.md): every requirement in the brief and how it's met
- [Decisions](docs/DECISIONS.md): what was decided and why
- [Architecture](docs/ARCHITECTURE.md): how the pieces fit together

## Settings (`config.json`)

- Request delay per agent (default 0.5 seconds).
- Quick-scan cap for non-Shopify sites (default 150 pages).
- The default URL.
- The three example questions.
- The optional AI model.
