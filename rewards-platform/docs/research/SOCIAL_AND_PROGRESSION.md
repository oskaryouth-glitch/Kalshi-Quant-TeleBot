# Research area: clans/groups, progression and leaderboards

**Status:** HYPOTHESES ONLY (2026-10-04). Nothing is built (D-031, D-035, D-037). All numbers are
illustrations. **Decision refs:** D-033, D-034, D-035. **Economics:** docs/UNIT_ECONOMICS.md.
**Legal:** LEGAL-001 items L12–L14.

## 1. Clan / group hypothesis (founder proposal, reviewed)

Users voluntarily create or join a group of friends. Three incentives overlap: **play** (normal
offer rewards), **refer** (conversion-qualified referral rewards, D-028) and **clan** (collective
qualifying activity unlocks additional group rewards). The hoped-for effects are acquisition,
retention, social accountability and organic distribution. **Unproven.**

Groups must not be campus-specific. The mechanic is for any friend group, roommates, Discord
communities, coworkers or online communities (D-032).

### Founder review (2026-10-04, second round): what is approved vs open

| Item                                                                     | Status                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MODIFY assessment                                                        | Agreed                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Progress unit                                                            | **Open.** Candidates: qualifying approved events, approved reward dollars, weighted qualifying activity, or another normalized unit from E002. Criteria: understandable to users; correlates with legitimate advertiser and company value; resists farming; doesn't pressure purchases; works across very different milestone structures. The dollar-based recommendation below is the engineering _lead hypothesis_, not a decision. |
| Required-purchase milestones excluded from clan **monetary** progression | **Approved as the default hypothesis**                                                                                                                                                                                                                                                                                                                                                                                                |
| Weekly **visible/social** progress with delayed **financial** settlement | Preserved                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Social/non-cash clan before cash                                         | **Approved**, conditional on enough scale for a meaningful experiment                                                                                                                                                                                                                                                                                                                                                                 |
| Size 3–10                                                                | **Initial test hypothesis**, not a product limit                                                                                                                                                                                                                                                                                                                                                                                      |
| Marginal-tier rewards                                                    | **Candidate**, not final                                                                                                                                                                                                                                                                                                                                                                                                              |

### Assessment: MODIFY

Worth testing, with these structural changes:

| Founder framing                | Change                                                                                                                    | Reason                                                                                                                                                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Targets in **completions**     | Targets in **qualifying dollars**: the clan's combined approved, non-purchase offer rewards                               | Completions differ by about 40× in value (a $0.40 install vs a $15 deep milestone). Counts reward farming shallow milestones, which also hurts advertiser quality signals. Dollars track our economics and are numbers users already see. |
| All qualifying activity counts | **Exclude purchase milestones** (and purchase-gated steps) from clan progress                                             | Prevents friends pressuring friends to spend money (consumer harm; LEGAL L6, L12).                                                                                                                                                        |
| Weekly quests                  | **Count approvals by approval date** over a monthly or rolling four-week period; show progress weekly; pay after the hold | Provider approvals lag and reversals arrive later. A weekly quest settles either on unapproved data (fraud and reversal exposure) or on approvals that land after the week ends (frustration).                                            |
| Cash bonus from day one        | **Test a social-only clan first** (shared goal and progress, no cash), then add cash in a separate arm                    | If social features alone produce the lift, a cash bonus is pure cost.                                                                                                                                                                     |

## 2. Target scaling (stepped / sublinear)

Let _n_ = verified active members at the start of the period, _T(n)_ = target, _t(n) = T(n)/n_ =
per-member target.

- **Recruiting incentive exists** only if adding an active member lowers the per-member burden:
  _t(n+1) < t(n)_, i.e. _T_ grows sublinearly.
- **Economic safety does not come from targets. It comes from the reward function.**

Using the founders' illustrative brackets (not adopted):

| Bracket | T   | t (per member, at bracket max) |
| ------- | --- | ------------------------------ |
| 3–5     | 10  | 2.00                           |
| 6–10    | 20  | 2.00                           |
| 11–20   | 35  | 1.75                           |
| 21–35   | 50  | 1.43                           |
| 36–50   | 65  | 1.30                           |

If every eligible member received the **same fixed bonus** at the target, cost per required unit
would be about **1.54× higher at 50 members than at 5** (2.00 ÷ 1.30). Large clans would be the
most expensive per unit of activity, which is exactly the farming problem.

**Recommendation (hypothesis):**

1. **Reward = rate × qualifying dollars, in marginal tiers** (like tax brackets: the Tier II rate
   applies only to activity inside the Tier II band). Cost scales with value at any clan size, and
   there are no retroactive cliffs at tier edges.
2. **Targets sublinear in verified active members**, either a smooth curve (e.g. _T = a·n^β_ with
   β < 1, to be fitted from data) or many small steps. Large discrete brackets create edge games
   ("stay at 5, don't add a 6th").
3. **Why sublinear is also economically right:** social psychology documents declining per-person
   effort in larger groups (social loafing; the established effect is general, and its applicability
   here is UNKNOWN). Incremental activity per member therefore probably falls with size. Targets that
   fall per member track that; they are not just a growth gimmick.
4. **Too aggressive vs too slow** becomes a calibration problem with measurable inputs (incremental
   activity per member by clan size, from randomized data), not a guess.
5. **Legal flag (L12):** any design where membership size lowers the bar to monetary rewards
   resembles the recruitment-reward language in FTC MLM guidance (BurnLounge). Counsel must review
   before any monetary clan reward. A safer variant to evaluate: targets that do **not** depend on
   size, with recruiting valuable only through the activity new members generate.

## 3. Clan size (hypothesis)

**Initial: minimum 3, maximum around 8–10.** Close friend groups are small; accountability is
strongest when members know each other; the fraud and moderation surface is smaller; and
experiments need many clans (§8), which favors small ones. Test a larger cap (around 20) only after
small clans show lift.

## 4. Reward allocation

| Option                           | Incentive effect                                                                 | Abuse cases                                                                    |
| -------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| A. Equal split among all members | Strong cooperation; heavy free-riding                                            | Inactive members collect; incentive to pad with low-effort members             |
| B. Proportional to contribution  | No free-riding; weak cooperation (just a bonus rate); in-clan status competition | Large contributors dominate; little social glue                                |
| C. Eligibility + equal share     | Requires participation, keeps the team feel                                      | Minimal-effort "eligibility farming"; pressure on weaker members; late joiners |

**Recommendation (hypothesis): C, with:**

- an eligibility threshold of a **modest** amount of the member's own approved, non-purchase
  qualifying dollars in the period (dollar-weighted so it can't be met by the cheapest action
  repeated);
- pool = marginal-tier rate × clan qualifying dollars, split equally among eligible members;
- **membership locked during the period**: joiners count from the next period (prevents tier
  sniping and clan-hopping);
- per-member clawback if a member's qualifying activity is reversed (no collective punishment).

## 5. Cadence

| Cadence  | Likely behavior                                                     | Problems                                               |
| -------- | ------------------------------------------------------------------- | ------------------------------------------------------ |
| Weekly   | Habit, frequent check-ins                                           | Approval lag; pushes users to shallow offers; pressure |
| Monthly  | Aligns with approval lag and settlement; deeper milestones possible | Less frequent engagement; mid-period drop-off          |
| Seasonal | Long goals, deep milestones, status                                 | Weak short-term pull; harder to test quickly           |

**Hypothesis:** monthly or rolling four-week settlement, with weekly progress visibility.

## 6. Abuse and fraud: the biggest risk

**Clans give fraud rings an organizing unit and a payoff multiplier.** Farmed accounts or device
farms form a clan, hit tiers, and collect offer rewards, clan bonuses and referral rewards on the
same fake activity. Clans can also hide individual fraud behind group activity.

Controls (when built): count only provider-approved activity; pay only after the hold; count only
verified unique people; analyze links between clan members (shared devices, payout accounts,
timing); cap clan size and tiers; clawbacks per member; manual review of any clan crossing high
tiers early in the program.

Other risks: social pressure and harassment (no chat initially; report and leave tools); privacy
(members see only aggregate clan progress unless each member opts in to show their contribution);
offensive clan names (moderation).

## 7. Progression (separate from clans)

Possible mechanics: XP, levels, tiers, milestone bonuses, streaks, quests, seasons, badges,
achievements. **None should be assumed.**

- **Economic hypothesis:** progression causes extra profitable second and subsequent offers, and
  part of that incremental contribution funds the rewards (UNIT_ECONOMICS §4).
- **Test order:** non-monetary progression first (levels, badges, progress visualization, cost ≈
  0), then monetary variants only if non-monetary shows lift or a clear ceiling.
- **Streaks and expiring rewards** carry dark-pattern risk (FTC staff report, LEGAL L13). Prefer
  designs without loss framing: unlockable, non-expiring milestones over "don't break your streak".
- **Inventory ceiling** (UNIT_ECONOMICS §7) limits how much extra activity progression can cause.

## 8. Leaderboards (D-033)

The blanket "no leaderboards" rule is withdrawn and replaced by gates.

- **Potential benefits:** social comparison motivates some users; friend and clan scopes add
  relevance. (INFERENCE from gamification research generally: effects are mixed, motivating top
  ranks and demotivating lower ranks.)
- **Risks:** fraud to climb ranks; harassment; pressure; privacy.
- **Design hypotheses:** friend-, clan- and opt-in-scoped boards; ranking by qualifying dollars
  after approval; **no cash prizes for rank** (contest law and a fraud magnet; status only); no
  campus-specific boards.

## 9. Experiments (backlog; all blocked on launch, LEGAL-001 and E002)

- **E010: Clan pilot.** Cluster-randomized by clan. Arms: control (no clan feature) / social-only
  clan / clan + marginal-tier cash bonus. Measures: qualifying dollars per member, second-offer
  rate, retention, offers per user, incentive cost, fraud, reversals, network rejection,
  contribution per member. Decision via UNIT_ECONOMICS §4 with the per-conversion budget.
- **E011: Progression.** User-randomized. Arms: control / non-monetary progression / monetary
  progression (only if non-monetary is promising). Same measures.
- Leaderboards are tested as a variant inside E010/E011, never standalone.

### Power notes (assumption-laden back-of-envelope)

Assume weekly qualifying completions per user have SD ≈ 1.5 (ASSUMPTION). Detecting a lift of 0.3
per user per week at α = 0.05 and 80% power needs n ≈ 2 × (1.96 + 0.84)² × 1.5² ÷ 0.3² ≈ **390
users per arm**. Clan randomization inflates variance by the design effect 1 + (m − 1)·ρ. With
m = 8 members and ρ = 0.2 (ASSUMPTION), that is 2.4, so about **940 users (about 118 clans) per
arm**. Conclusion: clan and monetary-progression experiments are **post-scale**. The first cohort
can only produce qualitative signals.

## 10. Lifetime account progression (hypothesis; D-039)

Concept only: qualifying-offer counts (e.g. 10 / 25 / 50 / 100) unlock lifetime milestones that
**never reset**. A milestone might grant status, an account level, a perk, or possibly a monetary
bonus. No numbers or rewards are approved.

**Purpose A, retention:** a user approaching a milestone may return for another profitable offer.
Testable inside E011 (lifetime milestone arm vs control).

**Purpose B, account stickiness / anti-abuse: likely overestimated.**

- It deters **restarting**: ban evasion and cycling new accounts to re-farm welcome bonuses, since
  progress would be lost.
- It does **not** deter **parallel** accounts. In the "A refers B" attack both accounts are kept
  and both accumulate.
- **Monetary** lifetime bonuses can _increase_ the payoff of account farms: every account earns its
  own milestones.
- So: lean on status and perks; gate any cash milestone behind identity verification; key milestone
  eligibility to the verified person (D-041). **Never described as fraud prevention.**

**Counting rule (hypothesis):** count provider-approved, post-hold qualifying offers, so milestones
can't be reached with reversed or shallow activity. Whether purchase milestones count follows the
same purchase-pressure reasoning as clans.

## 11. Lifetime vs seasonal progression (kept separate)

|           | Lifetime                                     | Seasonal                                                            |
| --------- | -------------------------------------------- | ------------------------------------------------------------------- |
| Resets    | Never                                        | Yes, per season                                                     |
| Rewards   | Maintaining one legitimate account over time | Recurring goals within a period                                     |
| Supports  | Status, trust, loyalty                       | Quests, progression, battle-pass-style mechanics                    |
| Main risk | Monetary milestones multiply farm payoffs    | Dark-pattern exposure (deadlines, streaks, loss framing; LEGAL L13) |

A user could eventually have both. Neither is built. Both draw on the same per-conversion incentive
budget (D-034).

## 12. Principle: one account should become more valuable over time (D-040)

Using one legitimate account should generally beat starting over, through **positive** accumulated
value: lifetime progression, reputation and trust (e.g. faster payout holds for accounts with a
clean history, if risk data supports it), historical tracking record and evidence for claims,
personalized recommendations, clan and social relationships, referral history, earned status.

**No punitive lock-in.** Users can leave at any time, close their account and withdraw available
balances under the published terms. Forfeiture of accrued value only for fraud or terms violations,
with a stated process and appeal (LEGAL L31). No artificial switching barriers.

## 13. Combined fraud vector: referrals + lifetime progression + clans

**The "self-contained household".** One person or a small ring runs a referrer account plus several
alternate accounts, referred into the referrer's own clan. Referral rewards pay per referred
account; clan targets that ease with size reward padding; lifetime milestones pay per account.
Every layer multiplies with the account count, so the combination is worse than the sum of its
parts.

**Required mitigations before any of these layers carries money:**

1. Incentives, caps and milestone eligibility keyed to a **verified person**, not an account
   (D-041).
2. One relationship graph across referrer, referee, clan co-membership, devices, phones and payout
   destinations.
3. Only provider-approved, post-hold activity counts for anything.
4. Identity verification before monetary incentives above small thresholds.
5. Clan size and target rules evaluated against padding (size-independent targets as the safer
   variant; LEGAL L12).

## 14. The flywheel (hypothesis, not a moat)

desirable games + good rewards → users join → users earn → progression encourages another offer →
users refer friends → friends join groups → group incentives create more activity → more legitimate
conversions → more revenue → some incremental revenue funds incentives → retention and organic
acquisition.

Every arrow is a hypothesis with an experiment attached. The **potential** moat, if this works, is
the combination of multi-provider supply, routing, trustworthy tracking, proprietary completion and
desirability data, expected earnings, referral distribution, group retention loops and provider
reliability data. None of it is proven.
