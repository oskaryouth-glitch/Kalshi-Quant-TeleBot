# Implementation plan

> **Revised Phase 1 plan: [AUDIT_2026-10.md](AUDIT_2026-10.md) §10.** The next-steps
> and kill criteria below are refined by the audit's §9 evidence threshold.

Each phase has an **exit criterion** (what must be true to move on) and a
**kill criterion** (evidence that should stop or redirect the project).
Phases 7–9 happen **only if** Phase 6 justifies them.

## Done in this change (Phase 0 + Phase 1 + paper-trading core)

- [x] Phase-0 research: sources, terms, APIs, resale data, legal, costs (PHASE0_RESEARCH.md)
- [x] Schema v1 with append-only enforcement, two-clock timestamps, raw evidence store
- [x] Manual capture ingestion (CSV + photos), validated, idempotent, all-or-nothing
- [x] Point-in-time reads + look-ahead guards + FORWARD/BACKTEST separation
- [x] Unit economics, transport, disposal, labor models + max-bid solver, tested before use
- [x] `manual_v1` human-baseline strategy; paper decisions; `settle_v1` settlement
- [x] Reports: market clearing prices by size, paper results, coverage, unverified assumptions
- [x] Breakeven/hurdle analysis
- [x] Collection gate (`PoliteClient`): no source is authorized, so no scraper exists
- [x] 145 tests

## Next two weeks (you)

1. **Phone calls (highest value per minute):**
   - Waste Connections CS transfer: does the 2-ton / $253 minimum apply to a
     van-load of household junk?
   - WM Colorado Springs Landfill: self-haul minimum?
   - One junk hauler: minimum-load price.
   - Update `config/markets.yaml` with status VERIFIED.
2. **Send the permission emails** (PERMISSION_REQUESTS.md). Nothing gets sent
   automatically; that's your call.
3. **Start capturing:** every Colorado Springs auction you can find, active
   and upcoming, on each platform (with a URL for every one). Record outcomes
   after close, including cancellations. Target ≥ 20 auctions per week.
4. **For auctions you'd consider:** fill in an estimate YAML and run
   `lockerlab decide` **before** they end.
5. **Time yourself** doing a capture and an estimate. That's the research
   process's labor cost.

## Phase 2: Image analysis (start after ~50 captured auctions with photos)

- Vision-model JSON extraction per image; schema validation; cost tracking;
  cross-image de-duplication.
- Evaluation vs your manual estimates. **Exit:** item-category recall ≥ 80%
  on 30 hand-checked auctions.
- Check current model pricing before starting; cache by (image hash, model
  version).

## Phase 3: Valuation engine

- Comps table with SOLD/ASKING provenance; category priors; hidden-content
  priors; three-point estimate. Later, Monte Carlo.
- New strategy `ai_v1` (automatic, so it's also backtestable over stored
  snapshots).

## Phase 4–5: Underwriting + paper bidding for AI strategies

- Run `ai_v1` next to `manual_v1` on every auction.
- Add strategy variants: small-unit only, high value density, low disposal,
  tools/outdoor focus, conservative.

## Phase 6: Evidence review (after ≥ 8–12 weeks, or ≥ 100 settled auctions)

Questions to answer with OBSERVED/SIMULATED data:

- What do units clear at, by size, in Colorado Springs?
- How often are auctions cancelled?
- Does any strategy's max bid win a meaningful share (≥ ~10%) of auctions it
  wants?
- Is our estimate ÷ price distribution showing a winner's-curse pattern?
- How many hours per week does the research process itself cost?

**Kill / redirect criteria** (any one is enough to stop and rethink):

- Median clearing price + fees for 5x5/5x10 exceeds the breakeven max bid for
  a typical unit profile (the market already prices away the edge).
- Our disciplined max bids win < 5% of desired auctions (no deal flow).
- Verified disposal + transport fixed costs exceed ~40% of typical small-unit
  gross.
- Manual research time exceeds ~1 hour per decided auction with no automation
  path (no permission).

If none trigger, the next step is a **deliberate, small calibration purchase
program** (e.g. 2–3 small units, capped spend) to get REALIZED data. That's
Phase 9 below, done early and small, and **only on your explicit decision**.

## Phase 7: Resale OS (only if Phase 6 passes)

- Real acquisitions; item photos, IDs and A/B/C/D classes; storage locations;
  labor and disposal logs.

## Phase 8: Listings

- Listing generator; listing queue with copy/paste for every platform.
- eBay Sell API with human approval of every listing.
- Markdown schedule learned from data; bundling engine.

## Phase 9: Real-acquisition mode

- Manual PAPER→REAL switch per auction (append-only event). The system still
  never places a bid itself.

## Dashboard

Only after Phases 2–3 produce data worth looking at. It will be a thin
FastAPI + server-rendered page over the same reports.
