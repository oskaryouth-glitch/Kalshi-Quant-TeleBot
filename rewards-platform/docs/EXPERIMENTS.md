# Experiments

Experiments are never advanced automatically. Each gate ends with an explicit recommendation:
**PASS**, **CONTINUE COLLECTING**, **FAIL** or **REDESIGN**, and the evidence behind it.

| ID        | Question                                                                                                                                                                    | Status                                                                   | Recommendation |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------- |
| E001      | Can a pre-launch company obtain adequate legitimate supply?                                                                                                                 | Not started (shell built to support applications)                        | —              |
| E002      | Do the unit economics work?                                                                                                                                                 | Blocked on E001 credentials                                              | —              |
| E003      | How reliable is tracking, per network × game?                                                                                                                               | Blocked                                                                  | —              |
| E004      | Does acquisition / landing-page conversion work?                                                                                                                            | Instrumented minimally (waitlist platform + `?ref=` source)              | —              |
| E005      | First-offer contribution margin                                                                                                                                             | Blocked                                                                  | —              |
| E006      | Second offer / retention                                                                                                                                                    | Blocked                                                                  | —              |
| E007      | Scaling CAC                                                                                                                                                                 | Blocked                                                                  | —              |
| E008      | Can voluntary ambassadors in the founders' social networks reach qualified early-access users cheaply? (pre-launch; college networks are the initial wedge, not the market) | Ready to design; measurement exists (`npm run waitlist:report`)          | —              |
| E009      | Do conversion-qualified referrals beat other channels on CAC per qualified user, without worse fraud or reversals? (post-launch)                                            | Blocked: launch, provider permission (Q27–29), counsel                   | —              |
| E010      | Do clans/groups cause incremental profitable activity? (cluster-randomized; social-only arm before cash)                                                                    | Backlog. Blocked: launch, LEGAL-001 (L12), E002, scale (see power notes) | —              |
| E011      | Does progression cause incremental second/subsequent offers? (non-monetary before monetary)                                                                                 | Backlog. Blocked: launch, LEGAL-001 (L13), E002                          | —              |
| LEGAL-001 | Can the intended reward/referral/payout/gamification structure operate compliantly?                                                                                         | OPEN (docs/LEGAL-001.md)                                                 | —              |

---

## Metric definitions (use these exact terms)

All money is in integer minor units (US cents). "Period" means conversions _approved_ in the period
unless stated otherwise.

| Term                                   | Definition                                                                                                                                                                                                                                                                                                 |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Gross publisher revenue (GPR)**      | Sum of network payouts for conversions approved in the period.                                                                                                                                                                                                                                             |
| **Reversals**                          | Network payouts clawed back in the period (by approval-period cohort when analyzing).                                                                                                                                                                                                                      |
| **Net publisher revenue (NPR)**        | GPR − reversals.                                                                                                                                                                                                                                                                                           |
| **User rewards cost**                  | Rewards credited to users for those conversions, net of user rewards reversed.                                                                                                                                                                                                                             |
| **Gross spread**                       | NPR − user rewards cost. **Gross spread %** = gross spread ÷ NPR.                                                                                                                                                                                                                                          |
| **Contribution profit**                | Gross spread − payout processing fees − fraud losses (rewards paid out and later unrecoverable) − variable support cost − allocated CAC − working-capital cost. **CAC includes** paid media, referral rewards, referred-user welcome bonuses and ambassador stipends, attributed by `acquisition_channel`. |
| **Contribution margin %**              | Contribution profit ÷ NPR.                                                                                                                                                                                                                                                                                 |
| **Net profit**                         | Contribution profit − fixed costs. Not an experiment metric.                                                                                                                                                                                                                                               |
| **Channel contribution**               | For a signup cohort of one acquisition channel over horizon H: gross spread − variable costs − that channel's CAC. Definition in "Channel cohort comparison".                                                                                                                                              |
| **Referral Contribution Margin (RCM)** | Channel contribution ÷ NPR for the referral cohort (and separately for the ambassador cohort).                                                                                                                                                                                                             |

Never call gross spread "margin" or "profit". Never mix cohorts (approval month versus conversion
month) within one table.

---

## E001 — Supply feasibility

**Question:** Can a pre-launch US company obtain enough legitimate, cash-reward-compatible offer
supply to run E002?

**Founder-proposed PASS criteria** (kept), with **refinements** (proposed; each one tightens a
criterion so it measures what matters):

| #   | Criterion                                      | Refinement and reason                                                                                                                           |
| --- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | ≥3 approved providers                          | "Approved" = signed or accepted publisher terms **and** working credentials. An application in review does not count.                           |
| 2   | ≥1 explicitly permits cash-equivalent rewards  | **In writing** (email or terms clause), stored with date in PROVIDER_REGISTRY. `cash_reward_allowed = YES`.                                     |
| 3   | ≥1 usable custom catalog API                   | Must return milestone structure **and** a stable store identifier (package name). Without store IDs, overlap and estimates are unreliable.      |
| 4   | ≥25 combined eligible US Android gaming offers | Count **unique games by store ID** after deduplication across providers, not raw offer rows. Only from providers passing #2.                    |
| 5   | Verified conversion/postback infrastructure    | ≥1 provider with **signed** conversion postbacks **and** a reversal postback (or a documented reversal report), tested end to end in a sandbox. |
| 6   | Sufficient economics to begin E002             | Defined as: per-milestone publisher payouts are exposed for ≥50% of eligible games (otherwise E002 cannot model reward splits).                 |

**Also record, even though they are not pass criteria:** overlap rate (share of unique games on ≥2
providers); answers to all 26 approval questions per provider; time from application to approval;
rejection reasons.

**Decision rule:** all six met → PASS. Criteria 1, 2 or 4 unmet after contacting every Tier A and
"strong additional" candidate → REDESIGN (e.g. gift-card-only rewards, or surveys-first). Partial
with applications pending → CONTINUE COLLECTING.

---

## E002 — Unit economics (plan)

Run once E001 passes, on real catalog snapshots (raw payloads retained).

Measure:

1. Eligible US Android game count (unique by store ID), by provider.
2. Publisher payout per game: median, mean, P10/P90; per-milestone distribution.
3. Overlap and **payout dispersion for identical games** across providers (same store ID, comparable milestone).
4. Settlement terms, reserves and reversal windows per provider (from written answers).
5. Gross spread scenarios at 15%, 20% and 25% of NPR.
6. Sensitivity of contribution margin to reversal rate (0–15%), fraud loss and CAC.
7. Working-capital requirement (model below).

**Important:** E002 can model unit economics from catalog payouts, but **expected** revenue per user
depends on milestone completion rates, which only E003/E005 can measure. Report E002 results as
"per completed milestone", not "per user".

### Game desirability dimension (see docs/research/GAME_DESIRABILITY.md)

E002 also records, per eligible game: store ID (and iOS ID where matchable), genre, publisher,
release/update recency, content rating, a game-segment classification, and any **legitimately obtainable**
external popularity and rating signals (with source, retrieval date and license; no scraping).
Report signal coverage, the payout-vs-popularity relationship at matched milestone depth (H-GD3),
and the social-casino segment separately (below). **No composite "fun score".**

### Social-casino segmentation (D-027)

Classify every game: **standard**, **social casino** (casino-style mechanics, no cash-out),
**sweepstakes-style casino** (prizes redeemable for cash or equivalents), **real-money gambling**.
Real-money gambling is out of scope: it is recorded in raw data only and never listed.
Sweepstakes-style casinos are flagged for legal review; recommendation: treat as out of scope
until counsel clears them, because their legal status varies by state and is actively contested
(INFERENCE; needs counsel).

For **social casino vs standard**, report: share of eligible games and of total publisher payout;
payout per milestone at matched depth; share with purchase-required or purchase-optional
milestones and the purchase share of listed totals. Post-launch, add completion curves, reversal
rate, claim rate and channel contribution for each segment. Inclusion or exclusion is decided after
this evidence plus legal and provider review. If included, the "Is this gambling?" FAQ and Trust copy
must be re-reviewed, and the copy guard's gambling-language rule will need an explicit, reviewed
rule for provider-supplied game titles (it currently applies to all public text).

### Inventory depth and supply structure (added 2026-10-04)

Engagement is capped by eligible, desirable inventory (UNIT_ECONOMICS §7). For each provider and in
aggregate, report: eligible US Android game offers (unique store IDs); **new eligible offers per
week** (refresh rate); median offer lifetime; offers available to a single user over 4 and 12 weeks
after excluding games they have started; and **provider concentration** (share of eligible games and
of payout value from the top provider). These bound any later progression or clan design.

**User-level effective inventory (critical; founder emphasis 2026-10-04).** Total catalog size is
not the metric. Report what a typical eligible US Android user can actually do:

- unique eligible games per typical user (after geo, device and OS targeting)
- desirable eligible games (using legitimately obtained desirability signals; D-021)
- no-purchase eligible games
- social-casino share
- duplicate games across providers, and the **genuinely incremental unique supply** each additional
  provider adds (marginal unique store IDs, not offer rows)
- share of offers restricted to new players
- offer expiration and churn; catalog refresh rate
- realistic offers per user per month before inventory exhaustion (a simulation over the snapshot
  series that removes games a user has started)

These numbers bound retention, LTV, progression and clan design. If effective inventory is shallow,
engagement mechanics cannot fix it.

**Provider-side user quality.** Maximizing our conversion count is not the same as maximizing
advertiser value. Where data permits (Q35, Q38), track per provider: rejection and reversal reasons,
payout changes, campaign removals or caps applied to us, and any post-install quality feedback. Treat
deterioration as an economic cost (future inventory and payouts), not only a fraud signal.

For the social-casino segment (D-027), report separately: inventory share; publisher payouts;
user-reward potential at candidate reward policies; milestone structure (depth, time limits);
purchase requirements; provider concentration; and later completion, reversal rate and contribution.

### Working-capital model

Working capital is modeled separately from profitability.

```
capital_gap(t) = Σ cash paid to users up to t − Σ cash received from networks up to t
steady-state approximation:
  gap ≈ daily_user_payouts × (avg_network_settlement_lag_days − avg_user_payout_lag_days)
        + reserves_held_by_networks
```

**Hypothetical illustration (invented numbers, not a forecast):** if users can withdraw 14 days
after a milestone is confirmed, and a Net-60 network pays about 75 days after the conversion
(month-end plus 60), the lag difference is about 61 days. At $1,000/day of user payouts that ties up
about $61,000, and it scales linearly with growth.

### Expected collectible value (for provider comparison)

No weights are invented. This is an expected-value calculation over measurable factors:

```
ECV = payout × P(tracked) × (1 − reversal_rate) × P(collected) − payout × cost_of_capital × settlement_days / 365
```

Using the brief's illustrative providers and an **assumed** 12% annual cost of capital:

|     | Payout | P(tracked) | Reversal | Settlement | ECV (≈)                                            |
| --- | ------ | ---------- | -------- | ---------- | -------------------------------------------------- |
| A   | $52.00 | 0.93       | 5%       | 60 days    | 52 × 0.93 × 0.95 − 52 × 0.12 × 60/365 ≈ **$44.92** |
| B   | $49.00 | 0.99       | 1%       | 30 days    | 49 × 0.99 × 0.99 − 49 × 0.12 × 30/365 ≈ **$47.54** |

B wins despite the lower headline. Caveats: P(collected) is assumed to be 1 for both; tracking
failures also cost user trust and support time, which this formula does not capture; and every
input needs measured values with sample sizes before it drives routing.

---

## E004 — Acquisition (early instrumentation already live)

The waitlist records the phone platform and an optional `?ref=` source tag (no cookies, no
analytics; D-011). Use distinct `ref` values per channel (e.g. `?ref=tiktok_bio`). Signup counts are
upper bounds until double opt-in exists (D-008).

---

## E008 — Ambassador reach test in founder social networks (pre-launch)

> Initial wedge: the founder's college networks (friends, teams, fraternities, roommates and their
> extended networks). College is a distribution experiment, not the product category (D-032).

**Question:** Can a small number of voluntary ambassadors (initially students in the founder's networks) generate early-access signups from
our target audience (US, Android-heavy) at a lower cost per signup than other channels, without
harming trust?

**Design (no new infrastructure):**

- 5–10 ambassadors across 2–3 communities (initially campuses in the founder's network), recruited individually. All 18+, written
  terms, code of conduct, FTC disclosure training (docs/research/REFERRAL_AND_AMBASSADORS.md §7–8).
- Each gets a unique code with a shared prefix: `amb_<community>_<id>` (fits the waitlist's
  `[a-z0-9_-]{1,64}` rule). Measure with `npm run waitlist:report -- --prefix=amb_`.
- Compensation: none, or a **flat stipend for time**. **Never per waitlist signup** (that pays for
  non-economic activity and invites junk). Conversion-based ambassador pay is the intended
  post-launch model (D-028) and is tested in E009; ambassadors are told it is planned
  and still subject to provider permission and legal review.
- Run 3–4 weeks. Same landing page for everyone. No paid amplification.

**Measure:** signups per ambassador per week; Android share; cost per signup (stipends ÷ signups);
later, once launched: activation of the ambassador cohort (started an offer, first approved
conversion) versus other sources; complaint and conduct incidents.

**Decision:** thresholds must be set **before** the test starts, against a comparison channel (e.g.
an organic-social baseline from E004). Without a baseline the result is descriptive only:
CONTINUE COLLECTING rather than PASS. Any conduct or coercion incident → stop and REDESIGN.

## E009 — Conversion-qualified referral pilot (post-launch)

**Preconditions:** launched product; written provider permission for referral traffic (Q27–29) for
every provider whose offers referred users can see; counsel review; referral ledger and states
implemented (ARCHITECTURE 2.10).

**Design:** invite-only, capped number of referrers and per-referrer caps, manual review of every
referral payout for the first cohort, policy amount set from the affordability constraint in the
referral research doc (not hard-coded). Optionally A/B two reward levels.

**Arms:** friend referrals and ambassadors (both conversion-qualified, single-level),
compared against paid-acquisition and organic cohorts acquired over the same period.

**Measure** (see "Channel cohort comparison"): Referral Contribution Margin and channel contribution
per acquired and per activated user; CAC per qualified user; q (share of referred signups whose
reward is actually paid); 30/60/90-day retention; second-offer rate; reversal, void, claim and
provider-rejection rates. Each is reported for referral, ambassador, paid and organic.

**Compensation variants to compare (D-038; not designed yet):** fixed amount per qualifying event
(lead qualifying event: cumulative approved value within a window, after the hold) vs a
time-bounded gross-spread share. Quality-based upgrades are evaluated only on mature cohorts. No
declining-by-volume schedules.

**Decision rule:** PASS only if, at maturity, referral (or ambassador) channel contribution per
acquired user beats **paid acquisition**, **and** retention and second-offer rate are not materially
worse than organic, **and** reversal and fraud rates are not materially worse. Worse provider
rejection rates → FAIL regardless of margin (supply risk outweighs it). Too few mature users →
CONTINUE COLLECTING.

## Channel cohort comparison (referral vs ambassador vs paid vs organic)

**Cohort:** users whose immutable `acquisition_channel` is c and who signed up in period P,
observed for H days from signup (e.g. H = 90). Only **mature** cohorts are compared: H has elapsed
**and** the longest relevant reversal window has closed for conversions inside H. Immature figures
are labeled provisional.

```
NPR_c   = Σ net publisher revenue on cohort conversions approved within H (net of reversals)
GS_c    = NPR_c − user rewards cost_c
V_c     = payment fees + fraud losses + variable support + working-capital cost, attributed to cohort
CAC_c   = paid:        media + creative spend attributed to the cohort
          referral:    referral rewards paid or accrued (qualified, not voided) + welcome bonuses
          ambassador:  ambassador performance rewards + stipends + materials
          organic:     0 direct (content and SEO costs are fixed; reported separately)

Channel contribution             CC_c  = GS_c − V_c − CAC_c
Channel contribution margin      CCM_c = CC_c ÷ NPR_c         (RCM = CCM for referral; also ambassador)
Contribution per acquired user          = CC_c ÷ signups_c
Contribution per activated user         = CC_c ÷ users with ≥1 approved conversion within H
CAC per qualified user                  = CAC_c ÷ users with ≥1 approved conversion within H
Payback (paid)                          = first day cumulative (GS − V) ≥ CAC
```

**Behavior metrics (same cohorts):**

- **Retention:** share of the cohort with any offer activity (start or milestone) in days 31–60 and
  61–90.
- **Second-offer rate:** among users with ≥1 approved conversion within H, the share with an
  approved conversion on a second distinct offer within H. Second-offer _start_ rate is the leading
  indicator.
- **Quality:** reversal rate (reversed ÷ gross publisher revenue), provider rejection rate, void
  and fraud rate, missing-credit claim rate.

**Reporting rules:**

1. Always show absolute dollars per user next to percentages. A margin % on a tiny NPR is
   meaningless. Show n and bootstrap intervals.
2. Single attribution per user, immutable. No channel double-counts a user.
3. Organic has zero direct CAC by construction, so it will usually "win" on margin. The decision
   questions are whether referral or ambassador beats **paid** (the scalable alternative), and
   whether referred users are as valuable as organic ones.
4. **Incrementality:** a referral program can pay for friends who would have joined anyway. Where
   volume allows, use holdouts (e.g. delay referral rewards for a random subset of new referrers)
   or compare organic signup trends where referrals launch. Note the limitation otherwise.
5. Self-selection: early referrers and ambassadors are enthusiasts. Pilot results may overstate
   scaled performance.
6. Compare channels on the same offer mix where possible, or report segment mix alongside (e.g.
   social-casino share), since offer mix drives margin.

## E010 / E011: design notes

Designs, arms and power analysis live in docs/research/SOCIAL_AND_PROGRESSION.md §9. Key constraints:
cluster randomization for clans; non-monetary variants first; joint evaluation of stacked incentives
and the per-conversion budget (UNIT_ECONOMICS §2, §4). Back-of-envelope power (assumption-laden):
about 390 users per arm for user-randomized tests, and about 940 users (about 118 clans of 8) per
arm for clan tests. These are post-scale experiments.

## Hypothesis register (cross-experiment)

| ID      | Hypothesis                                                                                                                     | Where tested                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| H-GD1   | Better-rated, higher-volume games have higher activation at similar first-milestone reward                                     | E003/E005                                                     |
| H-GD2   | Users trade reward for game quality (lower reward + better game preferred)                                                     | Pre-launch stated-preference survey, then revealed preference |
| H-GD3   | Popular games pay less per milestone                                                                                           | E002                                                          |
| H-GD4   | External signals predict completion well enough as a cold-start prior                                                          | Post-launch                                                   |
| H-GD5   | Recently updated games have fewer missing-credit claims                                                                        | Post-launch                                                   |
| H-ACQ1  | High-intent "already downloading" traffic converts at low CAC **where campaigns permit it**                                    | Post-launch, permitted campaigns only                         |
| H-REF1  | Ambassadors in dense social networks (initially the founder's college networks) reach Android-heavy, high-intent users cheaply | E008                                                          |
| H-REF2  | Conversion-qualified referrals have lower CAC per qualified user than paid channels                                            | E009                                                          |
| H-CLAN1 | Social-only clans increase qualifying dollars per member vs control                                                            | E010                                                          |
| H-CLAN2 | A cash clan bonus adds lift beyond social-only clans, by more than its cost                                                    | E010                                                          |
| H-PROG1 | Non-monetary progression increases second-offer rate                                                                           | E011                                                          |
| H-PROG2 | Monetary progression adds lift beyond non-monetary, by more than its cost                                                      | E011                                                          |
| H-REF3  | Quality-based referral pay (upgrades on mature cohorts) yields higher contribution per referred user than a flat rate          | E009 extension                                                |
| H-LIFE1 | Users near a lifetime milestone are more likely to complete another profitable offer                                           | E011 (lifetime arm)                                           |
| H-LIFE2 | Lifetime progression reduces restart abuse (ban evasion, bonus cycling); it is not expected to reduce parallel-account abuse   | E011 + fraud review                                           |

## Methodology rules for any outcome estimate shown to users

1. **Cohort:** everyone who _started_ the offer through us (clicked out), not only finishers.
2. **Censoring:** users still in progress are censored observations. Use survival methods
   (Kaplan–Meier) for P(reach milestone k) and time-to-milestone, not naive averages.
3. **Version:** estimates are keyed to a terms snapshot. Break the series when milestones or payouts
   change materially.
4. **Display gate:** each figure stays hidden below a published minimum sample (to be set before
   launch, e.g. n ≥ 30 starters _and_ ≥ 10 reaching the milestone). Show n and the date range.
5. **Store:** value, uncertainty interval, n, cohort definition, window start/end,
   `estimator_version`, computed_at.
6. **Which statistic for "typical earnings" is open.** The brief's expected payout (mean) is right for
   ranking, but the median can be $0 for steep funnels and the mean is skewed by rare finishers.
   The proposal is to show a distribution statement ("half of starters earned at least $X; 1 in 5
   reached $Y") alongside the expected value. Public copy deliberately does not commit to a
   statistic yet.
7. **Optimal stopping** is presented descriptively ("most people who reach level 30 take N more days
   to reach level 45, for $X more"), not prescriptively, because each user's value of time is
   personal.
