# Integration brief: michaelspiers.co.uk
_Generated 2026-10-20 21:06 from visible signals only. No items were added to any cart._

**Readiness: 85/100 · Ready** · Indicative: 1–3 days for a product and cart widget

## Platform
- **Shopify** (confidence 80%)
- Evidence (html): cdn.shopify.com assets
- Evidence (html): Shopify JavaScript object

## Checkout
- Type: Shopify hosted checkout
- Steps: 1 (one-page, Shopify default) or 3 (three-page, if switched) (source: Shopify Help Center: one-page checkout is the default; merchants can switch to three-page)
- Checkout customisation: Only on Shopify Plus (checkout extensibility). Plan is not visible from outside.
- Account prompt on cart: unknown (cart not read)

## Tags and widgets
- Google Tag Manager: GTM-KRDB3S8L, GTM-PQFZ6J6
- GA4: G-KRCN67Z9TQ
- BNPL: none found
- Trust badges and reviews: Yotpo
- Competing protection: none found
- Payments: Apple Pay, PayPal, Shop Pay
- Cookie consent: none found
- Analytics: Google Analytics 4, Klaviyo, Meta Pixel

## Recommended Loxa approach
- Loxa widget on product and cart pages first (theme app extension). Add a checkout step only if the store is on Shopify Plus.
- Why: Product and cart placement works on every Shopify plan. Checkout customisation is limited to Plus, and the plan cannot be seen from outside the site.

## Risk flags
- None found from visible signals.

## Human review required
- [ ] Confirm the Shopify plan. Checkout customisation needs Shopify Plus.
- [ ] Confirm checkout steps with a test order in staging.
- [ ] Post-payment and logged-in flows cannot be read from outside. Confirm with the partner.
- [ ] https://michaelspiers.co.uk/cart is disallowed by robots.txt, so it was not read (respected).

## How the readiness score was reached
_Loxa onboarding heuristic (own initiative). Starts at 100 and deducts for each risk found._
- -5 no cookie consent tool detected, so tracking consent needs checking
- -5 Shopify plan (Plus or not) must be confirmed
- -5 checkout steps inferred, not observed
