# Provider registry

**Hard gate:** a provider enters the production cash marketplace only when
`cash_reward_allowed = YES`, backed by stored written evidence. `UNKNOWN` never ships.

Evidence levels used below:

- **CONFIRMED** — verified by us from a first-party source or written provider statement, with URL or
  file and date.
- **FOUNDER-REPORTED** — from the founders' prior research; source not yet attached here.
- **UNKNOWN** — not researched or not answered.

> **Update 2026-10-04 (E001 readiness research):** first-party publisher documentation was reviewed
> for eight providers (docs/E001_APPLICATION_READINESS.md). **One cash-permission entry is now
> CONFIRMED from public terms: BitLabs/Prodege.** It must still be re-verified against the current
> version (archived) and confirmed for our specific payout model before reliance. Everything else
> remains UNKNOWN. Nothing here is legal permission.

## Registry fields (per provider)

| Field                                              | Values / notes                                                                                                                   |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `cash_reward_allowed`                              | YES / NO / WRITTEN_APPROVAL_REQUIRED / UNKNOWN                                                                                   |
| `gift_card_allowed`                                | YES / NO / WRITTEN_APPROVAL_REQUIRED / UNKNOWN                                                                                   |
| `custom_ui_allowed`                                | Can we render their catalog in our own UI?                                                                                       |
| `independent_ranking_allowed`                      | Can we sort and rank offers ourselves?                                                                                           |
| `multi_network_allowed`                            | Can competing networks be integrated at the same time?                                                                           |
| `cross_provider_comparison_allowed`                | Can we compare duplicate offers internally?                                                                                      |
| `pre_start_routing_allowed`                        | Can we choose the provider for a new user before they start?                                                                     |
| `traffic_sources`                                  | organic social / paid social / SEO / brand bidding — each allowed, prohibited or conditional                                     |
| `reversal_policy`, `max_reversal_window_days`      | Text + number                                                                                                                    |
| `payment_terms`, `minimum_payout`, `reserve_terms` | e.g. Net-30, $50 min                                                                                                             |
| `api_rate_limits`                                  |                                                                                                                                  |
| `catalog_endpoint_complete`                        | Full catalog or paginated subset                                                                                                 |
| `exposes_milestone_payouts`                        | Per-goal publisher payout                                                                                                        |
| `exposes_store_ids`                                | Package name / App Store ID                                                                                                      |
| `exposes_epc_cr`                                   | Provider-claimed performance metrics                                                                                             |
| `exposes_expiration`, `exposes_attribution_window` |                                                                                                                                  |
| `signed_conversion_postback`                       | Scheme: HMAC / secret / IP allowlist                                                                                             |
| `reversal_postback`                                | Yes / report-only / no                                                                                                           |
| `accepts_prelaunch_publishers`                     | Q26                                                                                                                              |
| `allowed_traffic_sources`                          | Per provider and, where needed, per campaign: organic, SEO, branded/search, referral, ambassador, paid social (Q8–11, 27–28, 31) |
| `exposes_desirability_signals`                     | Ratings, installs, genre, publisher; display rights (Q30)                                                                        |
| `application_status`                               | not-applied / applied / approved / rejected (+dates)                                                                             |
| `evidence`                                         | List of {claim, source URL or file, retrieved/received date, quote ≤ 25 words}                                                   |

## Current candidates

| Provider                | Tier                | cash_reward_allowed               | Founder-reported notes (unverified)                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------- | ------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lootably                | A                   | UNKNOWN                           | CONFIRMED (docs): configurable user revenue split; Catalogue API (poll every 10–20 min) and User API; reporting API; approval requires contacting your Lootably contact. Cash permission not found publicly.                                                                                                                                                                                 |
| BitLabs / Prodege       | A                   | **YES (CONFIRMED, public terms)** | Terms of Use (dashboard.bitlabs.ai/termsOfService): monetary rewards permitted "provided you comply with Applicable Laws"; must prominently post all material conversion requirements; Net 30 from month end; $100 minimum; integration approval requested in the Dashboard; signup collects legal status and VAT. Re-verify the current version; confirm our model in writing.              |
| RevU                    | A                   | UNKNOWN                           | CONFIRMED (revu.co/docs): Get Offers API (full catalog, multi-step reward events, payouts, targeting, performance metrics); Get Progress API (per-step pending, credited, reversed); reversal postbacks on by default; IP allowlist; payment terms negotiated with an account manager; credentials via account manager.                                                                      |
| AdGem                   | A                   | UNKNOWN                           | CONFIRMED (docs.adgem.com): property review before approval; Offer API (beta; security token from their team) with goals and `attribution_window_days`; postback hashing; static postback IP; **Net 60** from month end; $100 minimum (ACH/PayPal); address, payment method and tax forms required before payout.                                                                            |
| ayeT Studios            | A                   | UNKNOWN                           | CONFIRMED (ayetstudios.com/openapi, docs): Offerwall API (server or client side), Static API (key approved by account manager), 60 requests/hour per key on some endpoints; reversal callbacks ("r-" prefix); IAP callbacks; callback retries 12×/hour; onboarding via account manager incl. traffic-quality review.                                                                         |
| Monlix                  | Strong              | UNKNOWN                           | CONFIRMED (docs.monlix.com): site approval ≤ 3 business days; JSON and Static APIs with CPE goals; Net 30, $20 minimum; payouts via Payeer, FaucetPay, AirTM or Bitcoin only (friction for a US company).                                                                                                                                                                                    |
| Adscend Media           | Strong              | UNKNOWN                           | CONFIRMED (adscendmedia.com): application asks phone, websites/apps, **daily active users**, traffic source, fraud prevention; review 1–3 business days; publisher 18+; traffic "primarily from organic sources"; must disclose incentivized offers; sub-publishers only with advance written notice; leads expire after 12 months; recommends titling the wall "Adscend Media" (LEGAL L27). |
| Offerwall.GG            | Strong              | UNKNOWN                           | CONFIRMED (offerwall.gg): "No minimum traffic"; payouts from $30; HMAC-signed postbacks plus reversal postbacks; stats API incl. EPC; advertiser balances pre-funded; operator AESHA Technology Services Limited (Seychelles), Seychelles law (LEGAL L28).                                                                                                                                   |
| Offerwall Ad            | Strong              | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| Adparagon               | Strong              | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| Wannads                 | Strong              | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| TapResearch             | Survey lane (later) | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| CPX Research            | Survey lane (later) | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| TheoremReach            | Survey lane (later) | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| inBrain                 | Survey lane (later) | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| Unity / Tapjoy          | Low priority        | UNKNOWN                           | SDK/app-centric; weaker web fit.                                                                                                                                                                                                                                                                                                                                                             |
| Digital Turbine / Fyber | Low priority        | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| adjoe Playtime          | Low priority        | UNKNOWN                           | Native-app (usage-time) model; relevant if a native companion is ever built (D-015).                                                                                                                                                                                                                                                                                                         |
| MyChips                 | Low priority        | UNKNOWN                           | —                                                                                                                                                                                                                                                                                                                                                                                            |
| CPAlead                 | Excluded            | **NO** (FOUNDER-REPORTED)         | Public rules reportedly prohibit compensating users with real money absent a separate arrangement. Attach source before relying on it.                                                                                                                                                                                                                                                       |

## Approval questions (ask in writing; never infer answers)

1. Real USD / PayPal / cash-equivalent consumer rewards permitted?
2. Gift-card rewards permitted?
3. Custom UI on your API permitted?
4. Independent sorting and ranking permitted?
5. Competing networks integrated simultaneously permitted?
6. Internal comparison of duplicate offers across networks permitted?
7. Routing a new user to whichever eligible network we select before start permitted?
8. Organic TikTok / Instagram / YouTube traffic permitted?
9. Paid TikTok / Meta / other paid social permitted?
10. SEO traffic permitted?
11. Brand-bidding rules?
12. Reversal / clawback rules?
13. Maximum reversal window?
14. Publisher payment schedule?
15. Minimum payout?
16. Reserve / holding periods?
17. API rate limits?
18. Complete catalog endpoint available?
19. Individual milestone payouts exposed?
20. Stable app/store identifiers exposed?
21. EPC / conversion-rate metrics exposed?
22. Offer expiration timestamps available?
23. Attribution windows available?
24. Signed conversion postback available?
25. Reversal postback available?
26. Will you approve a legitimate pre-launch US startup without significant existing traffic?
27. Are users acquired through a referral program (incentivized to sign up by a referral bonus) permitted traffic?
28. Are campus or brand-ambassador programs permitted, and would ambassadors be treated as sub-publishers? (Ambassadors would link only to our site, never to your tracking links.)
29. Are there restrictions on funding referral bonuses or welcome bonuses from your payouts?
30. Do you expose store ratings, rating counts, install ranges, genre or publisher in the catalog, and may we display them?
31. Which campaigns restrict branded or search traffic (e.g. pages or ads naming the game), and is that exposed per campaign?
32. Does the catalog identify casino-style games, and distinguish social casino, sweepstakes-style (redeemable prizes) and real-money gambling offers?
33. May we pay referrers or ambassadors a fixed amount after a directly referred user's conversion is approved by you (single level, no payment for signups or installs)?
34. Are additional bonus layers tied to offer completion permitted (e.g. group/clan bonuses, progression or quest bonuses), beyond the per-offer user reward?
35. Do you share post-install quality feedback (retention, ROAS, rejection reasons), and what quality thresholds trigger payout changes or campaign removal for a publisher?
36. How many new eligible US Android game campaigns appear per week, and what is a typical campaign lifetime?

## Suggested next research step

Retrieve and archive the current publisher terms for each Tier A provider (first-party URLs only),
record verbatim clauses on cash rewards and traffic sources with retrieval dates, and move each
`cash_reward_allowed` from UNKNOWN to a cited value. This was intentionally not done in the shell
phase. It deserves its own reviewed pass.
