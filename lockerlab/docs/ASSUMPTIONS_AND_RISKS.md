# Assumptions, failure analysis, and safety

## 1. Assumptions that need empirical validation

The authoritative list is generated from config:
`lockerlab report assumptions` (≈ 75 non-VERIFIED values today). Ranked by how
much they move the max bid:

| # | Assumption | Current | Status | How to validate |
|---|---|---|---|---|
| A1 | CS dump minimum per visit | $253 | SOURCED | Phone Waste Connections + WM + a junk hauler |
| A2 | Valuation haircut (our optimism) | 0.85 | GUESS | Realized ÷ predicted on real units only |
| A3 | Hidden-content value | pessimistic priors | GUESS | Realized contents of opened units |
| A4 | Labor minutes per listing / sale / cuft | 15 / 25 / 0.6 | GUESS | Time yourself on real tasks (even selling your own stuff) |
| A5 | Buyer premium when not shown | 18% | SOURCED | Read it off each auction |
| A6 | Sales tax paid (no resale certificate) | 8.25% CS / 9.25% Marin | UNVERIFIED | Check rate tables; decide whether to get a resale certificate |
| A7 | Vehicle capacities & packing efficiency | 25–402 cuft × 0.65 | GUESS/UNVERIFIED | Measure one real load |
| A8 | Friend-vehicle availability and cost | $20–30 + mileage | GUESS | Ask friends; it's a real constraint |
| A9 | Blended selling fee | 7% | GUESS | Mix of local (0%) vs eBay (13.6%+) sales |
| A10 | Cancellation rate of auctions | not modelled | Unknown | Observed directly from captures |
| A11 | Margin rules ($150 min, 50% ROI, −$75 low case, $25/h) | policy | GUESS | Your risk preference; revisit after Phase 6 |
| A12 | Bid increments | generic table | GUESS | Record from auction pages |

## 2. Failure analysis: ways this business might not work, and the test for each

| Hypothesis (business fails because…) | Test | Data source | Status |
|---|---|---|---|
| Auction prices eliminate the edge | Clearing price + fees vs breakeven max bid by size | Captures + `report market` + `breakeven` | Testable after ~4 weeks |
| Disposal eliminates the edge | Verified dump costs in the breakeven table; disposal share of gross | Phone calls; later receipts | **Early warning:** SOURCED $253 minimum makes small-unit hurdles ~$1,000+ gross |
| Transport eliminates the edge | Transport share of cost by size; vehicle availability | Model now; real trips later | Modelled |
| Labor makes returns unattractive | profit/hour before labor; hours per unit | Time logs (Phase 7) | GUESS-driven today |
| Valuable-looking lockers are efficiently priced | Winning price vs our base estimate, split by visible categories | Captures + estimates | Testable with forward data |
| Hidden contents are mostly junk | Realized hidden value vs priors | Real units only | Needs acquisitions |
| Small units underperform | Per-size comparison of all metrics | Paper (price side) + real (value side) | Testable (price side) |
| Selling takes too long | Days-to-sale; capital turnover | Real listings only | Needs Phase 7–8 |
| Marketplace asking prices mislead | Sold ÷ asking on identical items | Comps table (Phase 3) | Planned |
| Inventory storage becomes the bottleneck | Retained cuft vs available space over time | Phase 7 inventory | Planned |
| AI systematically overvalues visible goods | AI estimate ÷ manual estimate ÷ realized | Phases 2–7 | Planned |
| Deal flow too thin | Auctions/week in Colorado Springs; our win share | Captures | Testable immediately |
| Research time too high | Minutes per capture + estimate | Your timing | Testable immediately |

**Flaws already visible in the strategy (tell-it-straight list):**

1. **No legitimate bulk data.** Without permission, the system runs at human
   speed. The 50–200-auction ambition needs an authorized feed.
2. **Paper trading can't validate value.** Only real units can. A paper
   portfolio's profit is the model grading itself.
3. **Fixed costs hit small units hardest.** A dump minimum, a van rental and
   ~4 hours of fixed labor cost roughly the same for a 5x5 as for a 10x10.
   Small units win on cash required and transport but need very high value
   density.
4. **A $1,000 bankroll excludes large units.** Upfront cash (bid + 18% premium
   + tax + deposit + truck + dump) caps 10x10 bids near $390 and 10x20 bids
   near $110.
5. **Winner's curse.** If we win, it's disproportionately where we
   over-estimated. Track estimate ÷ price on every auction, not just wins.
6. **Cleanout deadline vs no car.** 24 hours (California statute) to 72 hours
   (typical terms) to clear the unit. A friend's car may not be available on
   the day.

## 3. Safety, privacy and sensitive items (procedures for real acquisitions)

*Not legal advice. Follow the facility's rules and current law; ask the
facility manager first.*

| Found | Do | Don't |
|---|---|---|
| IDs, passports, Social Security cards, financial/tax/legal documents, medical records | Put them in a sealed envelope and hand it to the facility manager the same day (in California the operator must return personal papers, photos and records on request, B&P 21712). Log "documents returned" without the contents | Photograph, read, list, sell, throw in the trash, or store in lockerlab |
| Personal photographs, family albums, keepsakes, ashes/urns | Return them via the facility | Sell or dump them |
| Hard drives, phones, computers, cameras with cards | Do not look at the data. Before resale, factory-reset or securely erase. If you can't, physically destroy the storage and sell the device as "no drive" | Browse, copy or recover data |
| Firearms / ammunition | Stop. Contact the facility and local police non-emergency for guidance. Colorado and California both regulate private transfers (Colorado requires background checks; California requires a licensed dealer) | Transport, sell or post online without verified compliance |
| Medications | Take-back program / pharmacy disposal | Sell or give away |
| Hazardous materials (fuel, paint, chemicals, propane, batteries) | County household-hazardous-waste program | Regular trash, or selling unlabeled containers |
| Possibly illegal items, anything suggesting a crime, remains | Stop, leave them, call police | Touch or move them |
| Vehicle/boat | Title process through the facility/DMV | Assume you own it |

System rules already in place:

- Capture files refuse occupant/tenant name columns.
- `data/` (photos, raw captures) is git-ignored.
- The `bid_events` schema holds only a hash of bidder aliases (no import path exists yet).
- Phase-7 item intake will have a mandatory "sensitive item?" review flag
  that blocks listing until a human clears it.
