# Paper-trading methodology

Goal: record what we *would* have done, using only what we knew at the time,
and score it honestly against what actually happened.

## 1. Timeline of one auction

```
discover ──► capture #1 ──► (capture #2 ~24h before end) ──► DECIDE ──► auction ends ──► capture outcome ──► settle
             observation     observation                      paper      sold / cancelled   observation      paper
                                                              decision   / unsold                            settlement
```

Every box that writes data appends a row. Nothing is ever updated or deleted:
SQLite triggers abort any UPDATE/DELETE on evidence tables.

## 2. Two clocks

Every observation has:

- `observed_at`: when the information was on the auction page.
- `recorded_at`: when it entered the database (the system clock at import).

The DB enforces `observed_at <= recorded_at`.

A decision at time *T* may use an observation only if **both** its
`observed_at <= T` and its `recorded_at <= T`. The second condition is the
important one. If you type in on Friday a bid you "saw on Tuesday", a
Wednesday decision cannot use it, because on Wednesday the system didn't have
it. This is enforced in `pit.snapshot_as_of`, the only function decision code
uses to read auction data.

## 3. Look-ahead guards (each is tested in tests/test_paper.py)

| Guard | Enforced by |
|---|---|
| Strategies see only a frozen point-in-time `Snapshot`, never the DB | `strategies.py` signature; `paper.decide` builds the snapshot |
| Outcome fields (final price) aren't in the Snapshot type at all | `pit.Snapshot` |
| FORWARD decisions can't be backdated: `decided_at == recorded_at` | DB CHECK constraint |
| No decision at or after the auction's known end time | DB CHECK + `paper.decide` |
| No decision once any terminal observation (sold/cancelled/unsold) is known, even before the scheduled end (tenant paid) | `paper.decide` |
| A human-judgement strategy (`manual_v1`) can **never** run in BACKTEST mode, because the human may know or be able to look up the outcome | `paper.decide` refuses |
| An outcome typed in late but observed *before* the decision voids the decision rather than scoring it | `paper.settle_all` |
| Decisions store their full inputs (snapshot, estimate, policy, scenarios, config, unverified-assumption list), an inputs hash, and a `model_versions` row keyed by code hash + config hash | `paper_decisions`, `model_versions` |
| Changing the model or config creates a new model version. Old decisions still point at the version that made them | `ensure_model_version` |
| Settlement uses a named rule (`settle_v1`). A new rule adds rows; old settlements are never rewritten | `UNIQUE(decision_id, rule_version)` |

The operative decision per (auction, strategy) is the **latest one made
before the auction ended**. Earlier decisions stay on record and are available
for "did updating help?" analysis.

## 4. Settlement rule `settle_v1`

Let *M* be our paper bid (a proxy max), *P* the observed winning price, and
*inc(P)* the bid increment at *P*.

| Observed outcome | Our decision | Result | Simulated acquisition price |
|---|---|---|---|
| cancelled (tenant paid / pulled) | any | **VOID**: no capital used | n/a |
| unsold (no bids) | PAPER_BID with M ≥ opening bid | **WON** | opening bid |
| unsold | PAPER_BID with M < opening, or opening unknown | LOST / VOID | n/a |
| sold at P | PAPER_BID and M ≥ P + inc(P) | **WON** | *conservative:* **M** (the winner's hidden max could have pushed us all the way); *neutral:* P + inc(P) |
| sold at P | PAPER_BID and M < P + inc(P) (ties lose) | **LOST** | n/a |
| sold at P | WATCH / PASS | **NOT_BID** (P kept for missed-deal analysis) | n/a |
| closed, price unknown | any | not settled; counted in `report coverage` | n/a |

Portfolio figures use the **conservative** price by default and show neutral
alongside. The truth lies between them, and nearer to *M* the harder the
auction was contested.

## 5. What paper trading can and cannot tell us

**It CAN measure (OBSERVED/SIMULATED):**

- What lockers of each size actually clear at in each market, including
  cancellation rates (many lien auctions are cancelled when the tenant pays).
- How often our max bids would have won, i.e. whether our discipline leaves us
  *any* deal flow at all.
- How our estimates compare with market prices (estimate ÷ price). If we
  "win" only where our estimate is far above everyone else's, that's the
  **winner's curse** signature. Our win set is adversely selected.
- The time commitment of the research process itself.

**It CANNOT measure:**

- What the lockers actually contained or what the contents actually sell for.
  Every paper profit is **ESTIMATED by the same model being tested**. A paper
  portfolio that looks profitable proves only that the model is internally
  consistent, not that it is right.
- Real labor, disposal weight, transport trips, or sell-through time.

**Implication (a decision for you, not something the software will do):**
validating the value side eventually requires ground truth. That means a small
number of real, cheap, small units bought specifically to calibrate
(photos → contents → realized sales), treated as a research cost. Phase 6
defines when that's justified. Until then the system reports paper results
only with ESTIMATED/SIMULATED labels.

## 6. Strategies

`manual_v1` (implemented) underwrites from your own reading of the photos.
It's the **human baseline**. Later strategies (vision-model valuation,
size-only baselines, "low disposal", "high value density", etc.) must beat it
on the same forward auctions to justify their complexity.

Automatic strategies (no human input) may also run in BACKTEST mode over
stored snapshots, because they can't know outcomes. BACKTEST results are
reported separately from FORWARD results and are never mixed.

## 7. Planned statistics (Phase 6)

Per strategy and size bucket: win rate, capital deployed, estimated profit
(conservative/neutral), estimate÷price distribution, missed deals (NOT_BID
where P was far below our max), drawdown and capital turnover under a $1,000
bankroll with capital locked until estimated resale. Every figure carries its
label, and sample sizes are shown next to every rate. **No conclusion is
drawn from fewer than ~30 settled auctions per comparison.**
