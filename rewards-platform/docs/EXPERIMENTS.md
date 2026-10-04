# Experiments

Experiments are never advanced automatically. Each gate ends with an explicit recommendation:
**PASS**, **CONTINUE COLLECTING**, **FAIL** or **REDESIGN**, and the evidence behind it.

| ID   | Question                                                    | Status                                                      | Recommendation |
| ---- | ----------------------------------------------------------- | ----------------------------------------------------------- | -------------- |
| E001 | Can a pre-launch company obtain adequate legitimate supply? | Not started (shell built to support applications)           | —              |
| E002 | Do the unit economics work?                                 | Blocked on E001 credentials                                 | —              |
| E003 | How reliable is tracking, per network × game?               | Blocked                                                     | —              |
| E004 | Does acquisition / landing-page conversion work?            | Instrumented minimally (waitlist platform + `?ref=` source) | —              |
| E005 | First-offer contribution margin                             | Blocked                                                     | —              |
| E006 | Second offer / retention                                    | Blocked                                                     | —              |
| E007 | Scaling CAC                                                 | Blocked                                                     | —              |

---

## Metric definitions (use these exact terms)

All money is in integer minor units (US cents). "Period" means conversions _approved_ in the period
unless stated otherwise.

| Term                              | Definition                                                                                                                                                      |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Gross publisher revenue (GPR)** | Sum of network payouts for conversions approved in the period.                                                                                                  |
| **Reversals**                     | Network payouts clawed back in the period (by approval-period cohort when analyzing).                                                                           |
| **Net publisher revenue (NPR)**   | GPR − reversals.                                                                                                                                                |
| **User rewards cost**             | Rewards credited to users for those conversions, net of user rewards reversed.                                                                                  |
| **Gross spread**                  | NPR − user rewards cost. **Gross spread %** = gross spread ÷ NPR.                                                                                               |
| **Contribution profit**           | Gross spread − payout processing fees − fraud losses (rewards paid out and later unrecoverable) − variable support cost − allocated CAC − working-capital cost. |
| **Contribution margin %**         | Contribution profit ÷ NPR.                                                                                                                                      |
| **Net profit**                    | Contribution profit − fixed costs. Not an experiment metric.                                                                                                    |

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
