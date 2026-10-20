# Brief mapping: Task 2


## Agent 1: SKU Harvester
| Brief asks | How it's met | Show it |
|---|---|---|
| Working Python script in a Claude Code session | `harvester/harvest.py`, built and published with Claude Code; prompts in `prompts_log.md` | GitHub repo |
| Full SKU export: name, category path, price, URL, availability | `catalogue.csv`, one row per variant, plus brand, SKU, currency and a price-on-application flag | Agent 1 tab, catalogue search, CSV download |
| README for a new partner domain | README "Point it at a new partner"; `taxonomy.json` and `--product-pattern`, no code changes | README |
| Walkthrough or live demo | This console | Live run |
| Sitemap.xml discovery vs category crawling | Shopify feed first (250 products per request), then sitemap index, then bounded category crawl | Agent 1 tab: "Route" pill |
| Pagination and lazy-loading | Feed paged until empty; `rel=next` and `?page=` followed; Playwright scroll with `--render` | Test suite checks |
| Rate limiting and respectful crawling | robots.txt, delay between requests, back-off on 429/503, bot identifies itself, requests counted | Agent 1 tab: proof pills |
| JS-rendered pages | Structured data first; empty pages reported as `needs_render`; Playwright only with `--render` | Data quality panel |
| Deduplication and taxonomy cleanup | By SKU, then URL and variant; brands and categories normalised | Data quality panel, category chart |
| Error handling and resumability | Feed cache and page checkpoint; failures logged; rerun resumes | Test suite: "resumes" checks |

## Agent 2: Technical Integration Profiler
| Brief asks | How it's met | Show it |
|---|---|---|
| Platform detection | Signature rules across HTML, headers and a read-only feed probe, giving a confidence score | Agent 2 tab, platform card |
| Checkout flow type and number of steps | Shopify: hosted checkout, 1 step by default or 3 if switched (Shopify Help Center). Labelled inferred | Checkout card, signal table |
| Tag manager (GTM ID) | All `GTM-` IDs, plus GA4 and pixels | GTM card |
| Existing widgets (BNPL, trust badges, competing protection) | Six widget families; clashes flagged | "What's on the site" |
| Recommended approach with reasoning | Plain-English approach and why | Recommendation box |
| Risk flags and human-review items | Lists, plus a clickable engineer checklist | Readiness section |
| Wappalyzer-style vs own detection | Own rules in Wappalyzer style (`rules.json`), so the output fits Loxa's format | `rules.json` |
| Checkout without an active cart | Never adds to cart; cart read only if robots.txt allows; checkout inferred from platform | Signal table, "inferred" labels |
| Reliable signals vs human review | Every finding labelled header, html, probe or inferred, with a confidence score | Signal reliability table |
| Structured for the integration engineer | `brief.md` with sections, checklist and readiness score | brief.md download |

## How to approach it
| Brief asks | How it's met |
|---|---|
| Reusable, not one-off | Any URL in the console; tested on 3 fixture stores per agent plus 2 in the console; separate repos with CI |
| Show your prompts | `prompts_log.md` in each repo, including what broke and the fix |
| Demo, don't describe | Live run in the console; offline snapshot fallback |

## Own initiative ("+ More")
1. **Launch Phase Map** (Agent 1): catalogue mapped to the deck's roll-out phases (slide 6)
2. **Cover Opportunity Calculator** (Agent 1): live median ticket, plus inputs for orders, attach rate and premium rate, with IPT at 12%
3. **Integration Readiness Score** (Agent 2): explainable 0 to 100 score, effort range and checklist
4. **Ask the agents** (console): questions answered from the run's data, with sources, and logged
5. **Problems log** (console): every error, warning and review item across runs, with a suggested fix
6. **Guided tour** (console): a Start here walkthrough explaining what each view shows and why it matters
7. **CRM sync** (console): placeholder for pushing the partner snapshot into the CRM in a later phase
