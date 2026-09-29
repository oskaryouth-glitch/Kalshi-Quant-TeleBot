# Review pass 1: rules and mechanics falsification (M2, M3, M5, M6, M7, M8)

Date: 2026-09-29.

**Scope.** Every test in this pass reads only rules, filings and settlement-state fields.
- No price, order book or trade was read. Nothing was computed about P&L, profitability or calibration. No parameter was fitted. Nothing was collected or implemented.
- Settlement-state frequencies were counted only where they are the pre-registered price-free step 1 of a mechanism (M5, M8). They are frequencies of rule-defined states, not returns.
- H038 and H039 were not touched.

**Sources.**
- Kalshi's public regulatory bucket (`kalshi-public-docs.s3.amazonaws.com`): filed Part 40 certifications, amendments, notices and rulebooks, plus the contract-terms PDFs Kalshi serves to users.
- Unauthenticated Kalshi API `GET` requests.
- Hashes are in `evidence/review1/outputs/filings_sha256.txt`. Reproduction: `evidence/review1/scripts/review1_mechanics.py`.

**Blocked sources.** The environment's network policy blocks `help.kalshi.com`, `www.cftc.gov`, `weather.com`, `forecast.weather.gov`, `tsa.gov`, `gasprices.aaa.com`, `ice.com` and `dashboard.ornnai.com`. Anything attributed to the help center below comes from a web-search excerpt and is labelled as such.

## Verdicts

| # | verdict after this pass |
|---|---|
| M2 | **Mostly killed.** <br>• Early YES-determination is already covered by M1, and Kalshi's rules close those markets by the next fixed time. <br>• Partial averages have no mechanical bound, so what remains there is statistical. <br>• **Survives only as a narrow sub-case:** already-determined contracts in templates that allow early closing only on a YES outcome. Kalshi's close times show these stay open for months (NBA win totals). Next is a price-free existence count. |
| M3 | **The discrepancy is resolved and is not an edge.** The contract-terms PDF Kalshi serves is stale, and the filed amendments put The Weather Company (TWC) first. The only open question is data-only: does TWC's value ever differ from NWS's? |
| M5 | **Survives as an expected-value hypothesis, not as a lock.** <br>• The payout identities are derived for five tie classes. <br>• Golf step 1 passes: in 38 settled events, top-10 payouts averaged N + 1.86. <br>• The NCAA conference class is excluded because its controlling rule is unresolved. |
| M6 | **Survives, with caveats.** <br>• The authoritative rules are now established, and a small direct member is eligible. <br>• What is new since the prior investigation: <br>&nbsp;&nbsp;– market makers with a Market Maker Agreement have been eligible since July 30, 2026; <br>&nbsp;&nbsp;– the program ends January 1, 2027 unless extended; <br>&nbsp;&nbsp;– pools in under-quoted markets are no longer paid out in full. |
| M7 | **KILLED as a duplicate** of structural-arb R2/R4/R5. |
| M8 | **Survives step 1 only for T20 cricket leagues.** <br>• In those leagues the fixed $0.50 state occurs in 6.9–25% of matches (≥5%), clearing the 2% kill threshold. <br>• Killed for ITF tennis, NFL and soccer. <br>• Its cross-contract constraints are just R1/R4. |

---

## M2: settlement statistics that become mechanically determined before trading ends

**Controlling rule/source**
- **Rulebook v1.29, Rule 7.2(c).** Expiration may be moved earlier "if an Expiration Value that is included in the Payout Criterion … occurs", which is a YES-type trigger.
- **Filed terms, each with its own early-close clause:**
  - RAINNYCM (Amendment 2, filed 2026-09-02);
  - AAAGASMINMAX;
  - WTIMINMAX;
  - TSAW;
  - GLOBALTEMPERATURESUSTAINED (Amendment 2, 2026-09-02);
  - INDEXVALUE;
  - PERIODMEDIACONSUMPTION;
  - ENTITYOUTCOME;
  - NCAAFWINS and WINTOTAL.
- **The two early-close patterns:**
  - Most templates are YES-only: expiry comes sooner "following the occurrence of an event encompassed by the Payout Criterion".
  - NCAAFWINS and WINTOTAL add "(or can no longer occur …) … may resolve to No early", a discretionary NO trigger.

**Concrete examples** (all non-crypto; no CF Benchmarks RTI series)

| series (template) | settlement formula (filed terms + market rules) | source | last trading | what is known when |
|---|---|---|---|---|
| KXRAINNYCM (RAINNYCM Am.2) | Sum of daily precipitation at Central Park for the month, from NWS Daily Climate Reports; initial non-preliminary values unless otherwise specified | NWS, then TWC | First 10:00 ET after the strike is crossed; otherwise 23:59 ET on the last day | The running total is known daily. YES is certain once crossed. "Above x" cannot be settled NO before month-end. |
| KXAAAGASMAXM / MINM / MAX (AAAGASMINMAX) | Set of AAA daily national average regular-gas prices from issuance to the date; YES if any value is > (or <) the strike | AAA | First 10:15, 11:00 or 15:00 ET after a crossing; otherwise 09:55 ET on the date | The running max/min is known daily. |
| KXWTIMAX / MIN (WTIMINMAX) | Set of ICE front-month WTI daily settles; YES if any settle is > (or <) the strike | ICE | First 10:00 ET after a crossing; otherwise 14:30 ET on the date | The running extreme is known after each settle. |
| KXTSAW (TSAW) | Weekly Average = sum of the published daily TSA checkpoint counts Mon–Sun ÷ number of days published | TSA | Sunday 23:59 | Daily counts are published with a lag. The exact schedule is unverified here because tsa.gov is blocked. At close, Sunday (and possibly Saturday) is unpublished. |
| KXDDR5MS (INDEXVALUE + market rules) | Arithmetic mean of daily Ornn values for the month, 2 dp | Ornn, then a fallback hierarchy | Expiry at 10:00 ET | The partial mean is known daily. **Terms are ambiguous**: the template says for "in <period>" "it is enough … to cross … once at any point", while the market rules define a single monthly mean. |
| KXAVGTKIAH (GLOBALTEMPERATURESUSTAINED Am.2) | At least k consecutive days (Sep 28–Oct 4) whose mean of TWC hourly temperatures at KIAH (local day, rounded) is > 90 °F; a day with fewer than 18 hourly values breaks a streak | TWC | Week-end | Each day's mean is known after the day. |
| KXNBAWINS (ENTITYOUTCOME), KXNFLWINS (WINTOTAL), KXNCAAFWINS (NCAAFWINS) | At least k regular-season wins; ties are not wins | League | Season end (early close possible) | YES is certain when wins reach k. NO is certain when wins plus remaining games is below k. |

**Observed close behaviour** (Kalshi `close_time` and `result` fields; `outputs/m2_close_timing.txt`):

| series | early closes | pattern | reading |
|---|---|---|---|
| KXWTIMAX | 74 markets closed more than 1 h before their event's final close | mostly 10:00–10:01 ET | consistent with close-on-crossing |
| KXRAINNYCM | 23 | 10:14–13:17 ET | consistent with close-on-crossing |
| KXYTVIEWSW | 591 | spread across the day | consistent with close-on-crossing |
| KXTSAW | 0 of 272 events | — | averages never close early |
| KXDDR5MS | 0 | — | averages never close early |
| KXNBAWINS | 2 of 270 markets | 268 closed with the season, including 126 NO and 142 YES | markets that were already determined stayed open to season end |
| KXNFLWINS | 31 NO and 31 YES early | — | early resolution used often |
| KXNCAAFWINS | 11 YES early; all 18 NO with the event | — | NO side never closed early here |

**Mathematical implication**
- **(a) Monotone accumulators** (running max/min, cumulative totals, "at any point").
  - YES becomes certain at the first crossing. The rules then move last trading to the next fixed time (10:00, 10:15, 11:00 or 15:00 ET).
  - So the window in which a YES-determined market stays open runs only from publication to the next fixed close, which is bounded by design. This is **M1's mechanism**, not a separate one.
- **(b) Averages.** V = (S_known + R)/n, where R is the unpublished remainder.
  - The rules put no bound on daily values beyond R ≥ 0.
  - For TSA, n itself depends on which days are published.
  - Result: no useful mechanical determination. Information arrives progressively, but pricing it is a statistical nowcast.
- **(c) NO by exhaustion.** NO becomes certain when the best outcome still achievable is below the strike:
  - for streaks: max(current run + remaining days, longest completed run) < k;
  - for win totals: wins + remaining games < k.

  Under templates whose early-close trigger is YES-only (ENTITYOUTCOME; GLOBALTEMPERATURESUSTAINED), nothing in the rules closes these markets early. The data confirm it: NBA win totals, including those determined long before the end, stayed open to season end.

**Relation to H038.** H038 is not in this repository and was not inspected, so no content comparison is possible. From the brief's exclusion of BTC/ETH, I infer that H038 concerns CF Benchmarks RTI settlement windows.
- Every RTI-settled series, of any coin, is therefore treated as H038 territory and excluded here, because it is the same mechanism.
- If H038 covers partial-window averaging in general, (b) duplicates it.
- (c) is a different mechanism unless H038 covers detecting determined states: it rests on combinatorial exhaustion plus an asymmetric early-close rule, not on timing an averaging window.

**Is it genuinely new?**
- (a): no, it is M1.
- (b): not mechanical.
- (c): yes, as a rule-level fact backed by close-time evidence.

**Fatal problems**
- (a) is designed out: markets close at the next fixed time.
- (b) has no mechanical bound. TSA publication timing is unverified, and KXDDR5MS is TERMS_AMBIGUOUS.
- (c) is capped by the price grid. On a 1¢ grid, a determined-NO market can only be harvested by selling YES into resting YES bids. If those bids sit at 1¢, the gain is at most about 1¢ minus fees, over a holding period of up to months. That is the M4 floor problem, and it may be fatal on linear-cent markets.
- **Win-total certainty is conditional on the schedule.** The terms say a shortened or lengthened season "will not affect the value of the Underlying" but do not say which games count if the schedule changes.
- **NCAA/NFL windows are discretionary.** Those templates *may* close NO early.

**Cheapest next test (if (c) survives), price-free**
- Enumerate the currently open markets in a rule-certain NO state, using only rules and public results. For example, KXNCAAFWINS wins and remaining regular-season games can be read from Kalshi's own settled and listed game markets.
- Record how long each stays open before its scheduled close.
- **Kill** if there are fewer than about 20 market-days per month across all series.
- Only then, and only with approval, look at whether resting YES bids above 1¢ plus fees exist on those markets.

---

## M3: settlement source versus rules summary (weather discrepancy)

**Controlling rule/source**
- **Rulebook v1.29.** "Contract Specifications" means "the rules … containing specifications for such Contract, as adopted, amended, supplemented or otherwise modified from time to time". Rule 7.2(a) lets Kalshi designate a new Source Agency.
- **The contract's filed terms** (header "Rulebook: GLOBALTEMPERATURE"), amended twice by Part 40.6 notices:
  - **2026-08-17**: "Added in an additional Source Agency".
  - **2026-09-02**: added a clarification for initially inaccurate readings.
- **Controlling Source Agency:** "in hierarchical order, The Weather Company (TWC), National Weather Service, the national weather service for <area>".
- The filing also states: "All instructions on how to access the Underlying are non-binding". The weather.com/kalshi link is therefore a convenience, not part of the terms.
- The market listing supplies the variables: area (CLINYC), count and time period.

This is my reading of the filed record, not a legal opinion.

**Concrete examples**
- **The served GLOBALTEMPERATURE PDF** (sha256 `160281…`, S3 date 2025-12-12) predates both amendments. A text diff against Amendment 2 shows five differences:
  1. TWC is inserted first in the Source Agency hierarchy.
  2. The station clause changed from "as designated by the National Weather Service" to "primary official weather measurement station(s)".
  3. "First official non-preliminary report … *unless otherwise explicitly specified by the Exchange*".
  4. Revisions are now excluded if they "do not remedy a material error" (previously, revisions "after Expiration Date").
  5. A material-error expiry-delay clause was added.

  The live KXHIGHNY rules ("according to The Weather Company") **agree with the controlling filed terms**. The PDF is the anomaly.
- **The same kind of staleness is confirmed for RATECUTS.**
  - The served PDF (2026-03-25) differs from Amendment 2 (2026-09-16):
    - tick size 0.001 → $0.01;
    - position accountability of 25,000 contracts → a position limit of $7,000,000;
    - the contingency rule reference changed.
  - The rules summary also disagrees with the filing:
    - the summary says "75bp cut is 3, **and so on**";
    - the filing says ">25bp is two cuts; >50bp is three cuts", which caps a single move at three.
- **FFSTATLEADER** — the summary says "settle at 1/N". The filed and served terms say "the number of remaining qualifying positions divided by the number of entities so tied", rounded down to the cent. The filed version controls.
- **Screen across all templates:** 102 of the 190 templates with amendment notices serve a PDF older than their latest amendment. This is a date heuristic: BTC and ETH are confirmed false positives, because their served text equals Amendment 2.

**Mathematical implication.** None for pricing. There are not two live rules, only a stale convenience copy. For NYC temperature: V = the TWC-reported maximum at the primary official station for the day, at full reported precision. NWS applies only if TWC is unavailable.

**Is it genuinely new?** No; the discrepancy is not an edge. One empirical question remains. Before August 17 the first-listed source was NWS, so traders may still anchor on NWS. Does TWC's daily maximum ever differ from the NWS daily climate report for the same station and day?

**Fatal problems**
- The claimed discrepancy is resolved.
- The residual proxy hypothesis needs TWC and NWS data, and both hosts are blocked here.
- The other M3 instances (FX "open price", mention markets) were not reviewed in this pass.

**Cheapest next test (price-free).** Compare `expiration_value` for every settled KXHIGHNY market since 2026-08-17 with the NWS climate-report maximum for Central Park on the same dates. **Kill** M3-weather if they agree on at least 98% of days.

---

## M5: tie rules

**Controlling rule/source**
- **GOLFFINISH** — the served PDF and the certification are both dated 2026-02-20; no amendments:
  - "Tie Handling … the tied position counts as the position itself";
  - "Boundary Ties … resolves to Yes";
  - withdrawal after tee-off → No; missed cut / MDF → No;
  - withdrawal before tee-off → last fair price;
  - shortened → official final leaderboard;
  - postponed more than 2 weeks, or cancelled → last fair price.
- **ACHIEVEMENTS** — served and certified: when "multiple participants are reported as the result", YES = $1/N rounded down to the cent, and NO = 1 − YES.
- **FFSTATLEADER** — served and certified: ties at the top-N cutoff pay YES = floor_cent(r/N_t), where r is the number of remaining qualifying positions and N_t the number tied.
- **ENTITYOUTCOME** — the served NCAAFREGULARSEASON PDF is textually identical to it, and the NCAAFREGULARSEASON certification in the bucket is byte-identical to ENTITYOUTCOME's:
  - "<sporting outcome> shall be interpreted according to the official rules … as determined by the governing body";
  - it contains **no placement-tie clause**;
  - the "all tied teams … achieved that position" rule exists only in the market rules text.

**Concrete examples** (active on 2026-09-29; regex counts, so upper bounds; `outputs/m5_tieclasses.txt`)

| class | rule | markets / series | `mutually_exclusive` |
|---|---|---|---|
| A | "top N (including ties)", full pay | 798 / 7 (KXPGATOP5/10/20, KXPGAR1TOP5, KXPGAR1/2/3TOP10) | false |
| B | "all tied teams resolve as having achieved that position" | 438 / 9 (NCAA football and men's basketball conference top-4/5) | false |
| C | dead heat, $1/N rounded down | 4,384 / 33 (round leaders, awards, NFL weekly high score, MVPs) | true |
| D | dead heat, r/N (fantasy top-N) | 865 / 2 (KXNFLFFLEADERTOP, KXNFLFFWEEKTOP) | false |
| E | official tiebreakers → unique ranks | 746 / 23 (FIDE, NFL division order, AI leaderboards) | mixed |

**Mathematical implication.** S is the sum of YES payouts over the complete field.

- **A (golf).**
  - S = #{i : rank_i ≤ N} under competition ranking. The N-th best finisher always has rank ≤ N, so **S ≥ N in every completed tournament**, with no upper bound tied to N.
  - Consequences:
    - buying YES on the whole field pays at least N, so Σ ask < N is a lock;
    - Σ bid > N is **not** an arbitrage, unlike in an exactly-N market.
  - The lock needs two conditions:
    - (i) every entrant is listed;
    - (ii) the tournament completes. In the cancellation and pre-tee withdrawal states the affected markets pay a discretionary fair price in [0, 1].
  - Per player, the payouts are nested: YES_win ≤ YES_top5 ≤ YES_top10 ≤ YES_top20. That is R2 under another name.
  - **Step 1 (settlement states only; `outputs/m5_field_coverage.txt`).** Across 38 settled events per series, the sum of payouts over listed markets was never below N.

    | series | mean excess over N | median sum |
    |---|---|---|
    | top 5 | +1.08 | — |
    | top 10 | +1.86 | 11.92 |
    | top 20 | +3.10 | — |
    | round-1 top 10 | +4.33 | — |
    | round-2 top 10 | +2.96 | — |
    | round-3 top 10 | +1.31 | — |

    Listed markets per event ranged from 30 to 165, so full-field listing is not guaranteed by any rule.
  - The pre-registered kill (E[S] − N < 0.25) is **not triggered**.
- **B (NCAA conference).**
  - If the market rule controls, the maths is the same as A (S ≥ N).
  - If the template's "official rules of the governing body" controls, tiebreakers apply and S = N exactly.
  - **This conflict is unresolved.**
- **C (dead heat, $1/N rounded down).** With N_t tied:
  - S = N_t·⌊100/N_t⌋/100 ≤ 1, with equality only for N_t ∈ {1, 2, 4, 5, 10, 20, 25, 50, 100};
  - examples: 3 tied → 0.99, 6 → 0.96, 13 → 0.91, 26 → 0.78; above 100 tied, S = 0.

  So buying YES on the whole field is not a lock: its worst case depends on the field size (0.78 for a 32-team field). The short side still holds: buying NO on everything pays at least n − 1, and a NO pair pays at least 1, because any tied YES is ≤ 0.5. This matches structural_arb's short-only MECNET treatment, so nothing changes there.
- **D (fantasy, r/N).**
  - S = (N − r) + N_t·⌊100r/N_t⌋/100 ≤ N, with equality iff N_t divides 100r.
  - This is a one-sided cap, the mirror image of A: Σ bid > N makes buying NO on everything a lock, while Σ ask < N does not.
- **E (tiebreakers).** S = N exactly. Ordinary.

**Is it genuinely new?**
- **As a lock, no.** A and D are linear sum constraints of R1's type, with a different constant and a single direction. A's lock additionally requires full-field listing and completion, so it can never be RULE_DEFINED_LOCK. C only *removes* R1-long.
- **As an expected-value mechanism, yes (new to this project).** In class A the fair sum over the field is about N + 1.9 for top 10. Any quoting normalised to N would underprice YES by roughly 19% of N in aggregate. Whether prices actually are normalised that way has not been looked at.

**Fatal problems**
- B: the controlling rule is in conflict → exclude.
- D: the summary ("1/N") contradicts the filed terms (r/N). The filed rule applies, and the disagreement is not an edge.
- A: thin books and wide spreads; the premium is spread across the whole field; fair prices for pre-tee withdrawals are discretionary; listing is partial, so a lock is impossible.

**Cheapest next test (the first look at prices; needs approval).**
- Take one read-only snapshot, at a pre-registered T−24 h, of every listed KXPGATOP10/TOP20 market in the next 4 tournaments.
- Compare Σ mid over the listed players with E[S_listed] from step 1.
- **Kill** if |Σ mid − E[S_listed]| ≤ Σ half-spreads in at least 3 of the 4 events.

---

## M6: liquidity-incentive rewards

**Controlling rule/source**
- **Liquidity Incentive Program terms, Appendix A**, filed 2026-07-15 and effective 2026-07-30, as modified by the 2026-07-30 filing. That modification added "this minimum and maximum shall be applied on a per-market basis".
- Kalshi Rule 3.13(f).
- API schema for `GET /incentive_programs`.
- The help-center page (dated 2026-09-25, web-search excerpt) matches the filing.

**Concrete terms (from the filing)**

- **Eligibility.** "all Kalshi members, except the following: Introducing Brokers, Futures Commission Merchants, and customers thereof when transacting via the IB or FCM." A direct small member is **eligible**.
  - The September 2025 and February 2026 versions also excluded (i) Kalshi affiliates and (ii) members with a Market Maker Agreement. Both exclusions were removed with effect from 2026-07-30.
- **Duration.** "until the earlier of January 1, 2027, or the date that Kalshi amends or terminates the Program."
- **Per-market schedule:**
  - each Time Period is at most 31 days;
  - Target Size is more than 100 and less than 20,000 contracts;
  - the Discount Factor is at most 1.00;
  - the Reward is at least $1 and at most $1,000 per calendar day, per market.
- **Snapshots.**
  - One per second, taken at a uniformly random time within the second.
  - A snapshot is **excluded** if the market is not open, or if resting orders do not meet the Target Size **on each side**.
- **Qualifying bids on each side.** A YES ask counts as a NO bid.
  - Walk down from the best bid, accumulating size.
  - The **Reference Price** is the first level where cumulative size reaches Target ÷ 5.
  - Stop once cumulative size reaches the Target. If it never does, that side has no qualifying bids.
- **Scoring:**
  - score(bid) = DF^(max(Ref − price, 0) in ticks) × size, normalised per side;
  - a user's snapshot score = Σ normalised YES + Σ normalised NO, at most 2;
  - period score = the user's summed snapshot scores ÷ the sum over all users.
- **Payout.** Period score × Reward × (non-excluded snapshots ÷ total snapshots). It is paid only if at least $1.00, rounded down to the cent.
- **Revocation.** The Chief Regulatory Officer may revoke a participant's status for abusive participation, and the Rulebook's Chapter 5 prohibitions apply.
- **API units:**
  - `period_reward`: integer centi-cents;
  - `discount_factor_bps`: 5000 means 0.50 per tick;
  - `target_size_fp`: contracts, 2 decimal places;
  - `max_reward_per_account`: centi-cents, optional.
- **Live snapshot** (previous pass): 4,139 programs worth $494,770 in total. 97% have a target of 1,000 contracts, all have DF = 0.50, and 2,015 are on markets with zero 24-hour volume.

**Mathematical implication**
- **Zero-volume markets can pay.**
  - Scoring uses resting depth, not volume. A sole provider meeting the Target on both sides (non-crossing) scores 2 per snapshot, i.e. a share of 1. They receive Reward × (fraction of snapshots with two-sided target depth).
  - Where nobody provides both sides, snapshots are excluded and the pool is **not paid**. The unpaid part is not redistributed.
- **Minimum quoting.**
  - To earn anything, the whole book's cumulative depth must reach the Target on both sides (e.g. 1,000 contracts each).
  - An order counts only if it lies in the qualifying range. One sitting behind a full Target's worth of better-priced size earns 0.
  - With DF = 0.5, an order k ticks below the Reference Price earns 0.5^k.
- **Capital.** A sole provider needs about 1,000 × (YES bid + NO bid) of collateral per market. Whether opposing resting orders are margined jointly is not established.

**Is it genuinely new?** The mechanism itself — taking part in a published subsidy — is not new.

Compared with the prior investigation (MECHANISMS.md M6 / EVIDENCE D7), which relied on the September 2025 filing and a search excerpt and left eligibility unverified, the authoritative facts added here are:
1. Market makers with a Market Maker Agreement, and Kalshi affiliates, are eligible from 2026-07-30. **Professional market makers can now compete** in exactly the neglected markets M6 targets.
2. Payouts are scaled by the share of non-excluded snapshots, so under-quoted pools go unpaid.
3. The Reference Price is now set by cumulative size reaching Target ÷ 5, so a small top-of-book order can no longer set it.
4. The minimum reward is now $1 per day.
5. The program ends **January 1, 2027**, about 3 months away, unless extended.

Any H0xx reward investigation outside this repository has to be compared by the reviewer.

**Fatal problems.** Nothing at the rules level. Practical ones:
- about 3 months of program life left;
- professional market makers eligible since July 30;
- about $1,000 of collateral per market to meet the target alone;
- adverse selection (M1 from the other side);
- the Chief Regulatory Officer's abuse clause.

**Cheapest next test (needs approval; a first look at order books).**
- Take one read-only book snapshot, no collection, of 30 randomly drawn live rewarded markets.
- For each market, record whether two-sided target depth already exists, and what share a hypothetical 1,000-lot at the Reference Price would get.
- **Kill** if, among the zero-volume markets, at least 80% already have others' two-sided target depth and the hypothetical share is below 20%.

---

## M7: compositions across series

**Controlling rule/source**
- **structural_arb DESIGN.md:** §B.1 (explicit state model, including product states) and §B.3 (R1–R5).
- **FEDDECISION terms:** a cancelled meeting → "No change" YES; last trading at 13:55 ET.
- **FED terms:** the upper bound "for <meeting>"; no data → No.
- **RATECUTS Amendment 2** (2026-09-16): a cut of 1–25 bp counts as 1, >25 bp as 2, >50 bp as 3, counted "between Issuance and <date>".

**Concrete examples.** KXFEDDECISION-26OCT/-26DEC (buckets per meeting, mutually exclusive); KXFED (upper-bound thresholds); KXRATECUTCOUNT-26DEC31 (cut-count buckets).

**Mathematical implication.** Let c₀ be the cuts already counted, g(Δ) the count for a single move, and I ≥ 0 the cuts between meetings. Then count = c₀ + g(Δ_Oct) + g(Δ_Dec) + I. The relationships:
- {cut in Oct} ⊆ {count ≥ c₀+1} is **R2**: nesting through a monotone map.
- {cut in Oct} ∧ {cut in Dec} ⊆ {count ≥ c₀+2} gives YES_count≥c₀+2 + NO_cutOct + NO_cutDec ≥ 1. That is **R5's lower Fréchet bound**.
- {Δ_Oct < −25 bp} ⊆ {count ≥ c₀+2} is R2.
- KXFED "upper bound < U₀" ⊇ {cut} is R2.
- The equality (R4) directions fail, because nothing in the rules bounds I or hikes.

Every relationship is an R2, R4 or R5 inequality that structural_arb's checker (`payoff.verify` over explicit, product states) already expresses.

**Is it genuinely new?** **No.** The only new ingredient is the semantic map between series. That is the terms-equivalence problem already met with AAA gas and SOL (TERMS_EQUIVALENCE_UNRESOLVED), and here it has known breaks:
- moves between meetings;
- hikes;
- cancelled meetings;
- the three-cut cap on a single move;
- the summary-versus-filing disagreement above 75 bp.

**Fatal problems.** Duplicate mathematics, plus unresolved mapping breaks.

**Cheapest next test.** None. **M7 is KILLED as a duplicate.** If it is ever revisited, it belongs inside structural_arb as a cross-series template under that project's terms-verification standard. It is not a separate mechanism, and nothing should be added while that protocol is frozen.

---

## M8: fixed-value and fallback payout states

**Controlling rule/source**
- CRICKETMATCHWIN (served 2026-09-10).
- **FOOTBALLGAMEWIN Amendment 3** (filed 2026-09-18, "Added new tie provisions").
- ACHIEVEMENTS (served and certified) plus the ITF market rules.
- SOCCERGAMEWIN (served 2026-09-15).
- FEDDECISION.
- GOLFFINISH.

**Concrete payoff tables**

T20 match (KXT20MATCH; markets A and B). There is no fair-price state in the filed terms:

| state | YES_A | YES_B | Σ |
|---|---|---|---|
| A declared winner (including DLS or super over) | 1 | 0 | 1 |
| B declared winner | 0 | 1 | 1 |
| tie with no super over; abandoned with no result; cancelled before start; forfeit before start; insufficient play | 0.50 | 0.50 | 1 |
| forfeit or disqualification after start, with an official winner | official result | | 1 |

NFL game (KXNFLGAME; two team markets, no Tie strike; FOOTBALLGAMEWIN Amendment 3):

| state | YES_A | YES_B | Σ |
|---|---|---|---|
| a team wins | 1/0 | 0/1 | 1 |
| tie | 0.50 | 0.50 | 1 |
| suspended before 55 minutes and not resumed within 48 h | each market at its own last fair price (unless already determined) | | not constrained by rule |
| suspended after 55 minutes, or declared final | settled on the score at that point | | 1 |

ITF match (two markets):
- Not started (walkover, injury, cancellation) → 0.50 / 0.50.
- Retirement after the first ball → the retiring player's market resolves NO; the opponent is the official winner.
- Postponed → the market stays open for up to 2 weeks. Beyond that the rules say nothing.

Soccer three-way (Home / Tie / Away):
- A regulation result gives exactly one YES.
- Cancellation, abandonment before start, rescheduling beyond 48 h, or an awarded result → **each market settles at its own "last fair price"**, so Σ is not constrained by rule.

FOMC: a cancelled meeting → "No change" YES and all other buckets NO, so Σ = 1.

Golf top-N: withdrawal before tee-off, or cancellation → last fair price.

Dead-heat classes: see M5, class C.

**Mathematical implication**
- **Events where every rule-specified state pays Σ = 1** (T20; NFL except the early-suspension state; ITF except long postponement; FOMC).
  - These events are exactly exhaustive, so both directions of R1 hold: Σ ask < 1 → buy every YES; Σ bid > 1 → buy every NO.
  - That is an **R1/R4 cover pair**. structural_arb's MECNET treatment allows only the short side. These fixed-value clauses are what would justify the long side too, but only as verified terms, and the registry is frozen, so nothing was changed.
- **Fair-price states** (soccer, golf, NFL early suspension). Σ is not rule-constrained.
  - R1-long is invalid, and even R1-short is not rule-guaranteed.
  - In practice all 9 soccer fair-price splits observed (USL/MLS), and the 6 non-0.50 T20 splits, summed to exactly 1.00. That is evidence of coherence, not a guarantee.
- **Single-contract implication** (the expected-value part of M8):
  - p_A = (1 − q)·P(A | decided) + 0.5·q.
  - Compared with a price anchored on a void (refund) convention, the gap is q·(0.5 − P(A | decided)): favourites are overpriced, underdogs underpriced, and Σ stays at 1.
  - This is a single-contract statement, not a cross-contract constraint.
- **Step 1 (settlement states only; pre-registered kill is q < 2% in every listed league; `outputs/m8_contingency_counts.txt`):**
  - **KXT20MATCH:** 194 of 1,494 events (13.0%) settled at a fixed 0.50. By league:

    | league | fixed 0.50 settlements | q |
    |---|---|---|
    | T20 (M) | 81 / 320 | 25.3% |
    | Odisha | 7 / 16 | 43.8% |
    | Topklasse | 9 / 49 | 18.4% |
    | Major Clubs | 8 / 55 | 14.5% |
    | European T20 PL | 3 / 31 | 9.7% |
    | T20 International | 9 / 131 | 6.9% |
    | T20 Blast | 2 / 112 | 1.8% |
    | Major League Cricket | 0 / 34 | 0% |

  - **Other series:**

    | series | fixed 0.50 settlements | q | decision |
    |---|---|---|---|
    | KXODIMATCH | 3 / 131 | 2.3% | — |
    | KXITFMATCH | 106 / 10,000 | 1.1% | killed |
    | KXITFWMATCH | 123 / 9,142 | 1.35% | killed |
    | KXNFLGAME | 6 / 430 | 1.4% (ties) | killed |

**Is it genuinely new?**
- **Cross-contract constraints: no.** The fixed-value clauses make exhaustiveness rule-established (R1/R4), while the fair-price clauses remove it.
- **The expected-value compression toward 0.50: new to this project.** It survives step 1 only for T20 leagues with q ≥ 5%. It is killed for ITF, NFL and soccer (where the fallback is a fair price, not a fixed value).

**Fatal problems**
- The void-anchoring hypothesis is unverified.
- Cricket books are thin or empty.
- The trade is directional on a single contract, since both sides move together.
- Some 0.50 events are pre-match cancellations in markets that may never have traded, so q among traded matches may be lower.

**Cheapest next test (price-free).**
- Recompute q using only matches whose markets actually traded (`volume_fp` > 0; volume is not a price), for the leagues with q ≥ 5%.
- **Kill** if that q is below 5% in every league.
- Only then (with approval) take read-only snapshots at T−1 h for the next 30 matches in the surviving leagues.

---

## Correction: interest on open positions does not remove capital lock-up

MECHANISMS.md (universe map, and M4's economic reason) said that capital lock-up "mostly disappears on Kalshi, because open positions earn the same variable APY as cash". **That overstated it.**

**What the sources say**
- **Kalshi Klear Rulebook 1.4, Rule 7.9(D)** (and DCM Rulebook v1.29, Rule 8.1(c)): "Klear **may** pay interest … at a **floating rate** to be determined by Klear on funds in Participant's accounts **in excess of an amount to be determined by Klear**." Interest is discretionary, variable and subject to a threshold.
- **Help center, "APY on Kalshi"** (dated 2026-03-17; web-search excerpt only):
  - 3.25%, variable;
  - US eligible users only;
  - balance of at least $250;
  - SSN required above $10 of interest a year;
  - accrues daily on net portfolio value at 12 am ET, i.e. cash plus positions **valued at last traded prices**;
  - paid monthly, within up to 10 business days.
- **Klear Rule 7.5:** positions in fully collateralised contracts "must, at all times, be fully collateralized". **Klear Rule 6.4:** withdrawals are processed by the next settlement-bank business day. Collateral securing an open position is not withdrawable cash.
- **Pending, not in force:** the Klear Event Contract Margin Framework (40.5(a) submission, 2026-09-22). It would introduce side-specific initial margin for eligible non-sports contracts, effective no earlier than 45 days after submission and subject to CFTC approval, with full collateralisation as expiry approaches.

**Corrected statement**
- For **eligible** accounts, interest accrues on the marked value of open positions as it does on cash. A position is therefore roughly *carry-neutral relative to idle cash on Kalshi*, at a rate that is variable and discretionary.
- That does **not** remove lock-up:
  - the purchase price is posted as full collateral and cannot be withdrawn or redeployed until the position is sold or settles;
  - selling requires a counterparty at an acceptable price, which is thin for tail contracts;
  - interest accrues on last-traded value, not on cost;
  - ineligible accounts, or balances under $250, earn nothing.
- M4 must still charge the opportunity cost of immobilised collateral and the risk of being unable to exit. Only the pure interest-carry component is roughly neutralised, and only for eligible accounts. MECHANISMS.md has been corrected to match.

## Separate finding: stale served terms PDFs (affects the frozen structural_arb registry; nothing changed)

- Kalshi serves `contract_terms/<NAME>.pdf` at each series' `contract_terms_url`. The controlling contract specifications are the filed Part 40 certification plus its amendments.
- On a date screen, 102 templates are flagged. Staleness is confirmed textually for GLOBALTEMPERATURE and RATECUTS. BTC and ETH are false positives: their served text equals the filed amendment.
- **structural_arb's `terms.REGISTRY` verifies the served PDF's hash.** Its GLOBALTEMPERATURE entry (sha `160281…`) is the pre-amendment document.
  - The clauses it cites are still in the filed terms: operators, full precision, no data → last fair price, and the first non-preliminary report.
  - But the Source Agency changed, and the first-report clause gained "unless otherwise explicitly specified by the Exchange" plus a material-error delay.
  - A hash check on the served PDF cannot detect filed amendments.
- This is flagged for whoever owns the frozen protocol. No code or registry was modified.
