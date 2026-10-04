# Unit economics and the full incentive stack

**Status:** canonical definitions and constraints (2026-10-04). Contains **no real economics**:
every number below is an illustration and is labeled as such. Real inputs come from E002 and later
experiments.

## 1. Definitions (do not blur these)

All amounts are integer minor units (cents). Definitions match EXPERIMENTS.md.

| Term                              | Definition                                                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Gross publisher revenue (GPR)** | Network payouts for conversions approved in the period.                                                                                     |
| **Reversals**                     | Network payouts clawed back.                                                                                                                |
| **Net publisher revenue (NPR)**   | GPR − reversals. _Use NPR or GPR minus expected reversals, never both_ (see §3).                                                            |
| **User offer rewards**            | Rewards credited to users for offer milestones, net of user rewards reversed.                                                               |
| **Gross spread**                  | NPR − user offer rewards. A property of the offer and the reward policy only.                                                               |
| **Acquisition cost (CAC)**        | Paid media; referral rewards; referred-user welcome bonuses; ambassador pay and stipends. Attributed by `acquisition_channel`.              |
| **Engagement incentives**         | Clan/group bonuses; progression, quest or streak bonuses; lifetime/loyalty milestone bonuses; any other non-offer reward to existing users. |
| **Variable costs**                | Payment processing and payout fees; fraud loss (rewards paid out that are later unrecoverable); variable support; working-capital cost.     |
| **Contribution**                  | Gross spread − CAC − engagement incentives − variable costs.                                                                                |
| **Contribution margin**           | Contribution ÷ NPR. Always report absolute dollars and n next to it.                                                                        |
| **Net profit**                    | Contribution − fixed costs. Not an experiment metric.                                                                                       |

**Gross revenue ≠ gross spread ≠ contribution ≠ net profit.** A document or dashboard that labels
gross spread as "profit" or "margin" is wrong and should be corrected.

## 2. The full incentive stack

A single approved conversion can trigger several payouts:

- the user's **offer reward**;
- a **referral or ambassador reward** (if the user was referred and this is the qualifying activity);
- a contribution to a **clan bonus**;
- progress toward a **progression bonus**.

All layers must be evaluated together:

```
  Gross publisher revenue
− Reversals
= Net publisher revenue (NPR)
− User offer rewards
= GROSS SPREAD
− Acquisition cost:       referral / ambassador / welcome bonus / paid media (allocated)
− Engagement incentives:  clan bonus / progression bonus / other
− Variable costs:         payment + payout fees, fraud loss, variable support, working-capital cost
= CONTRIBUTION
− Fixed costs
= NET PROFIT
```

### Per-conversion incentive budget (D-034)

For every qualifying conversion _c_, the sum of all incentives it can trigger must respect a budget
set by policy:

```
offer_reward(c) + referral_share(c) + clan_share(c) + progression_share(c)
    ≤ NPR(c) − expected_variable_costs(c) − minimum_contribution(c)
```

- `*_share(c)` is the portion of a pooled bonus attributable to _c_ (e.g. a clan pool divided by the
  qualifying dollars that unlocked it).
- This is enforced at **policy design time** (no layer's parameters may be set without checking
  the combined worst case) and **monitored** at the conversion and cohort level from the ledger
  (every ledger entry carries `incentive_type` and a cause reference; ARCHITECTURE 2.11).
- If a conversion would exceed the budget, layers are reduced in a declared priority order, never
  silently. The default order is engagement incentives first, then acquisition rewards. Offer
  rewards are never reduced after the user started (route-lock terms).

## 3. Two common accounting errors to avoid

1. **Double-counting reversals.** If revenue is measured as NPR (already net of reversals), do not
   also subtract "expected reversal loss". Subtract _fraud loss_ only for rewards we paid out and
   cannot recover; that is a different quantity from provider reversals.
2. **Treating acquisition cost as a reduction in spread.** Referral rewards are CAC (D-024). The
   founders' illustration ($50 revenue, $38 reward, $2 referral) has a gross spread of **$12**, and
   contribution is at most $10 before other costs.

## 4. Funding incentives from incrementality, and the double-counting trap

The right question for any engagement incentive is "how much additional profitable behavior did it
cause?", not "what sounds exciting?"

```
incremental_contribution = (activity_with − activity_without) × contribution_per_unit_before_this_incentive
affordable_incentive     < incremental_contribution × (1 − safety_share)
```

**Founders' illustration (numbers invented, not assumptions):** 50 users at 1.2 → 1.8 qualifying
completions per user per week means 30 incremental completions; at $5 each that is $150, so a clan
reward materially below $150 could leave both users and the company better off.

**The trap: attribution double-counting.** If each layer is justified by its _own_ incrementality
analysis, they can all claim the same extra conversion:

- referral: "this user exists because of the referral" (all of their contribution);
- clan: "these extra completions are because of the clan";
- progression: "this second offer is because of progression".

Each analysis looks profitable on its own while the combined payout exceeds the true combined lift.
Mitigations:

1. Evaluate incentives **jointly**: factorial experiments where volume allows, or at minimum
   measure the full stack against a control receiving none of the engagement layers.
2. Compute `contribution_per_unit_before_this_incentive` **after** the other layers already paid on
   that unit.
3. Enforce the per-conversion budget (§2) regardless of what any single analysis says.

## 5. Statistical reality check

Incrementality needs randomized comparisons with enough units (EXPERIMENTS "Power notes"). With
small early cohorts, lift will be **unmeasurable** for a long time. Decisions about cash incentives
should not be made on noise. That is why non-monetary variants are tested first (D-035).

## 6. Working capital interaction

Every incentive paid before the network settles enlarges the working-capital gap
(EXPERIMENTS "Working-capital model"). Bonuses should be paid **after** the qualifying conversions'
hold, which also aligns with reversal windows.

## 7. Inventory depth: a hard ceiling on activity

Most offers are for new players only, once per game. Activity per user is bounded by the supply of
eligible, desirable offers, not by motivation alone. Incentives that push volume beyond desirable
inventory push users into grinds they dislike, which lowers completion and advertiser quality
signals. E002 measures inventory depth and refresh rate (offers available per eligible user over
time) before any engagement incentive is designed.

## 8. Additions from the second founder round (2026-10-04)

- **D-034 strongly approved by founders.** Referral, clan, progression and loyalty incentives may
  never independently claim the same incremental conversion. There is one combined budget,
  constrained by real contribution economics, with consistent gross/net revenue definitions (§3).
- **Per verified person (D-041).** Budgets, caps and eligibility resolve to a verified person, not
  an account. Otherwise self-referral and account clusters let one human collect acquisition and
  engagement incentives that no incremental person justified.
- **Non-incremental referrals are a cost, not fraud.** Paying $2 for a user who would have joined
  organically did not acquire that user for $2; it gave away $2. Referral incrementality is measured
  with holdouts where volume allows (EXPERIMENTS "Channel cohort comparison").
- **Provider-side quality is an economic term.** Incentive designs that inflate shallow
  completions can lower future payouts and inventory. Those effects belong in long-run
  contribution, not just in fraud monitoring (EXPERIMENTS E002 "Provider-side user quality").
