# Unit economics and maximum bid

Code: `lockerlab/economics.py` (pure functions, integer cents, costs round
**up** and proceeds round **down**). Tests: `tests/test_economics.py`
(hand-computed cases + brute-force check of the max-bid solver).

## 1. Definitions

```
acquisition          = bid + buyer premium (max(rate*bid, minimum)) + sales tax (on bid + premium)
out_of_pocket        = acquisition + transport + disposal + storage + packing
                       + expected cleaning-deposit forfeit + other
selling_costs        = platform/payment fees + per-order fees + returns/refunds + risk reserve
profit_before_labor  = gross_proceeds − out_of_pocket − selling_costs
net_profit           = profit_before_labor − labor_hours × labor_rate
cash_invested        = acquisition + transport + disposal + storage + packing + other
ROI                  = net_profit / cash_invested
cash_required        = acquisition + refundable cleaning deposit + transport + disposal
profit/hour          = profit_before_labor / labor_hours
profit per cuft      = net_profit / retained (kept-for-sale) cubic feet
profit per trip      = net_profit / vehicle trips
```

`gross_proceeds` is the expected total sale price of what actually sells
(sell-through already applied), before fees. Unsold inventory is therefore in
the valuation, not a separate cost line.

## 2. Scenarios

Each auction is evaluated in **low / base / high** scenarios.

- The low case assumes hidden contents disappoint: half of the would-be
  donations become trash.
- A **valuation haircut** (config, 0.85) multiplies all three gross figures
  until calibration shows how biased the estimates are.

## 3. Maximum bid (margin of safety)

The max bid is the **largest whole-dollar bid at which all of these hold**:

| Rule | Default (GUESS) | Rationale |
|---|---|---|
| base net profit (after labor) ≥ minimum | $150 | Not worth the risk for less |
| base net profit ≥ target ROI × cash invested | 50% | Capital is scarce |
| low-case **cash** result (before labor) ≥ −max loss | −$75 | Limits real dollars lost; time is covered by the other rules |
| base profit before labor ≥ $/hour × hours | $25/h | Your time has value |
| cash required ≤ bankroll | $1,000 | Can't bid what you don't have |

Every rule gets strictly harder to satisfy as the bid rises, so a binary
search finds the exact boundary (verified against brute force). The output
names the **binding constraint**, i.e. why the max isn't higher.

Decision:

- **PASS** if no bid qualifies, or the current bid plus one increment already
  exceeds the max.
- **WATCH** if confidence is below the threshold (0.5).
- Otherwise **PAPER_BID** at the max (a proxy bid).

## 4. Transport model (`transport.py`)

- trips = ⌈(kept + donate + trash cuft) / (vehicle cuft × 0.65 packing
  efficiency)⌉
- Vehicles can be infeasible: unavailable, longest item too long, or more than
  4 trips.
- **The vehicle is chosen to minimize transport + disposal together**, because
  each dump visit pays the gate minimum. A bigger vehicle with fewer dump runs
  can be cheaper overall. (That was a bug caught by the breakeven analysis
  below. It now has a regression test.)

## 5. Disposal model (`disposal.py`)

- Each dump visit costs max(minimum, tons × rate).
- Items add per-item fees: mattresses, appliances, e-waste.
- An optional free household-trash allowance (default 0) diverts small amounts
  away from the dump.
- The displayed burden level is the worse of the volume/item score and the
  cost share of gross.

## 6. Labor model

```
hours = fixed (1.0) + trips × 1.0 + occupied cuft × 0.6 min
      + listings × 15 min + sales × 25 min
```

All of these are GUESS values. Time the first real tasks you do (even
photographing and listing your own stuff) to replace them.

## 7. First result: breakeven hurdles (SIMULATED, mostly GUESS inputs)

`lockerlab breakeven` computes, per unit size, the minimum **base-case gross
resale** (before haircut) a unit must hold before the rules allow a given bid.

Profile: 50% full, 30% kept, 40% trashed, low case = 33% of base.

**Colorado Springs, average sale $100:**

| Size | $0 bid | $50 | $100 | $200 | $400 |
|---|---|---|---|---|---|
| 5x5 | $1,010 | $1,230 | $1,500 | $2,040 | $3,130 |
| 5x10 | $1,080 | $1,310 | $1,580 | $2,120 | $3,200 |
| 10x10 | $1,460 | $1,690 | $1,950 | $2,500 | over bankroll |
| 10x15 | $2,840 | $3,070 | $3,340 | $3,880 | over bankroll |
| 10x20+ | $2,990 | $3,220 | $3,490 | over bankroll | over bankroll |

With an average sale of $40 (lots of cheap household goods), every hurdle
rises: a 5x5 goes from $1,010 to $1,600 just to justify a $0 bid, and a 10x20
from $2,990 to $4,460. Marin, with a *guessed* $80 dump minimum, has 5x5/5x10
hurdles about 30–37% lower ($640 / $740 at a $0 bid).

**How to read this:**

1. **Fixed costs per locker dominate small units.** The dump minimum (if
   $253 is real), transport, fixed labor and the deposit add up to roughly
   $350–400 before a single item sells. Even a free 5x5 must hold about $1,000
   of resale value (roughly $280 in the pessimistic case after haircut) to pass
   the downside rule.
2. **The binding rule for small units is the low-case cash loss.** That's
   driven by the dump minimum, so it's the most valuable number to verify.
   Call Waste Connections and WM; price a junk hauler; check free county
   events.
3. **Bankroll rules out large units.** With $1,000, cash required (bid + 18%
   premium + tax + $100 deposit + truck + dump) exceeds the bankroll for
   10x10s above about $390 and 10x20s above about $110, however valuable
   the contents.
4. **The small-unit hypothesis isn't supported or refuted by this.** Small
   units have the lowest *absolute* hurdles, but the hurdle *per square foot*
   is far higher, so a small unit needs much denser value. Whether small
   units actually contain $1,000+ of sellable goods is exactly what forward
   data must show.
5. **Sensitivity to the average sale price shows the value-density point.**
   Many small sales make labor eat the margin.

Rerun it any time: `lockerlab breakeven --avg-sale 100 --keep 0.5 --trash 0.2`.
