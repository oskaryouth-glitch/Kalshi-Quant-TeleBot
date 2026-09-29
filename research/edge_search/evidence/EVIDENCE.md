# Evidence log — small-participant edge search (research only)

Every figure in `../MECHANISMS.md` comes from one of the sources below.

- **Kalshi data.** Unauthenticated public `GET` requests to `api.elections.kalshi.com/trade-api/v2`.
- **Official documents.**
  - `docs.kalshi.com`, including the `llms-full.txt` bundle.
  - Kalshi DCM Rulebook v1.29 (`../../structural_arb/sources/`; sha256 `3b6d4ffd…185240b`).
  - The contract-terms PDFs already hashed in `../../structural_arb/sources/SOURCES.md`.
  - The Kalshi help-center pages cited inline.

**No orders, no credentials, and no H038/H039 material.**

**No outcome-conditioned statistics.** No price-versus-result, P&L or calibration figure was computed. Every falsification test in `MECHANISMS.md` therefore remains untouched by what was seen here. Exactly two price-derived figures were computed, and both are *prevalence* counts, not test statistics:

- summary spread percentiles;
- counts of markets quoting at the 1¢ / 99¢ grid edge.

## Raw snapshots (not committed; too large; hashes for provenance)

| file | sha256 | fetched (UTC) | request |
|---|---|---|---|
| series_0929.json | b031bb4d20dff24c7852c3c30accb34722e86aecf5e2356709ca8a201269e427 | 2026-09-29T02:37Z | `GET /series` (all) |
| events_0929.json | 9b4ba16f3e205bae6c934b5d0464f6a249d18e9f495459e15291cff7eafea175 | 2026-09-29T02:39Z | `GET /events?status=open&with_nested_markets=true` (all pages) |
| incentives_all.json | 568ef6e121b01219ee6280a7d992d3ecc105d8530d366d23e8ce59ecd2305478 | 2026-09-29T02:41Z | `GET /incentive_programs` (21,000 rows) |
| settled_3d.json | 1cc5ca96329fbe86afdeb8e26a5f77ce3bf71b0c5cb0ea6965d109662660ff08 | 2026-09-29T02:42Z | `GET /markets?status=settled` (5,000 most recent; all turned out to be KXMVE combos) |
| settled_nonmve.json | 2d5e7339ece6837e085c162fef9ffe534a82f08ade395db1fb4c6215457712c6 | 2026-09-29T02:49Z | `GET /markets?status=settled&mve_filter=exclude&min_close_ts=now-3d` (12,000) |
| margin_markets.json | fa4ef1832e3d5c838bddb08051027d547297b46992f76ebaac10fd79d96e3b1c | 2026-09-29T02:49Z | `GET /margin/markets` |
| trades_recent.json | 8c874bf6171b3058b7f5a60135e00164931e7de01f4eee802180e49bc6046c22 | 2026-09-29T02:53Z | `GET /markets/trades?limit=1000` (a ~5 s window of the public tape) |

## Scripts (one-off, read-only mapping; no strategy, signal or backtest logic)

Run each script from the directory holding the raw snapshots above. `universe_map.py` takes that directory as its argument; `rules_census.py` and `rules_examples.py` read `events_0929.json` and `series_0929.json` from the working directory.

- **`scripts/universe_map.py`** (→ `outputs/universe_map.txt`) — covers:
  - categories, frequency, fee type/multiplier and price grid;
  - activity and summary spreads;
  - `can_close_early`, strike types, settlement sources and terms-PDF count.
- **`scripts/rules_census.py`** (→ `outputs/rules_census.txt`) — two parts:
  - a regex census of rules text for the clause types used by M2/M3/M5/M8;
  - tail-quote prevalence by price grid (M4).

  The regexes are deliberately broad, so the counts are *upper bounds* with false positives (e.g. "tie" as an outcome name). Treat them as prevalence indicators, not exact counts.
- **`scripts/rules_examples.py`** (→ `outputs/rules_examples.txt`) — verbatim rules text, sources, terms URL, fee type, times and summary quotes for the series quoted in `MECHANISMS.md`.
- **`scripts/fetch_settled_nonmve.py`** — fetches the settled-market snapshot. **`scripts/settled_timing.py`** (→ `outputs/settled_timing.txt`) summarises its settlement-mechanics fields only (no prices).
- **`scripts/incentive_stats.py`** (→ `outputs/incentive_stats.txt`) — live liquidity-incentive programs joined to market activity.
- **`outputs/perps.txt`, `outputs/combos.txt`** — margin-exchange universe, and combo settlement/tape shares.

## Official-document facts used (quoted or paraphrased, with location)

| # | fact | source |
|---|---|---|
| D1 | `close_time` "may be moved earlier if `can_close_early` is true"; the close-time update "can happen when a market is closed ahead of its scheduled close time, including before determination"; after close all order operations are rejected and resting orders cancelled | docs.kalshi.com market lifecycle page (in `llms-full.txt`) |
| D2 | Rule 5.11(c): trade review on request ≤15 min after execution; fair value ± $0.20 "No Cancellation Range"; outside it Kalshi "shall have the authority, but not the obligation, to cancel or adjust"; 5.11(b) trader-preventable errors are not "extraordinary circumstances" | Rulebook v1.29 |
| D3 | Rule 7.2(b)/(c): Kalshi may move Expiration later (rescheduling, delayed data) or earlier (outcome occurred before Expiration) | Rulebook v1.29 |
| D4 | Rule 6.3(c): where the Underlying cannot be measured and the contingency is not addressed, Kalshi determines payouts, e.g. from the last traded price | Rulebook v1.29 |
| D5 | Rule 5.3(b): the RFQ content is public to all Members; "Any other Member … may choose to respond to the RFQ with a Quote"; the quoter confirms after acceptance (30 s standard); 15 s execution timer; 5.3(b)(h) RFQs and quotes only for bona fide transactions | Rulebook v1.29 |
| D6 | All combo markets are High Volatility Markets: 3 s confirmation window, 1 s execution timer; the `communications` channel broadcasts every RFQ "public by design, so makers can quote them" | docs.kalshi.com RFQ page and changelog |
| D7 | Liquidity Incentive Program scoring. <br>• Order book snapshotted at a random moment within each second. <br>• Reference Price = first level, walking from the best bid, where cumulative size reaches 1/5 of Target Size. <br>• Order score = size × DiscountFactor^ticks, normalised per side. <br>• A snapshot counts only if *both* sides reach Target Size. <br>• Payout = share × pool × (non-excluded snapshots ÷ all snapshots), rounded down; below $1 not paid. <br>• Target 100–20,000; pool $10–$1,000 per day. <br>• Eligibility: "most regular U.S. Kalshi members". This eligibility wording comes from a web-search summary of the help-center page; the page itself was not read directly, so treat it as unverified | help.kalshi.com/en/articles/13823851 (dated 2026-09-25); CFTC filing "Liquidity Incentive Program – September 8, 2025" |
| D8 | Interest (APY, variable, stated as 3.25%) on cash **and open positions**, for balances ≥ $250. This is discretionary (Klear Rule 7.9(D): "may pay … floating rate … in excess of an amount to be determined") and does not release collateral (Klear Rule 7.5) | help.kalshi.com/en/articles/13823847 (dated 2026-03-17; web-search excerpt); Klear Rulebook 1.4 |
| D9 | GOLFFINISH terms: ties at the boundary resolve Yes; withdrawal after tee-off → No | `contract_terms_GOLFFINISH.pdf` (hash in structural_arb SOURCES.md) |
| D10 | GLOBALTEMPERATURE terms name the **National Weather Service** as Source Agency (hierarchical); "only the first official non-preliminary report" counts; Position Accountability Level $25,000 per strike. The live KXHIGHNY rules instead say "according to The Weather Company" (weather.com/kalshi) | `contract_terms_GLOBALTEMPERATURE.pdf`; `outputs/rules_examples.txt`; **superseded:** filed amendments of 2026-08-17 and 2026-09-02 list TWC first (see `../REVIEW_PASS_1.md`) |
| D11 | Margin exchange: 27 perps (23 crypto, 4 metals); funding endpoints; no RFQs | docs.kalshi.com margin pages; `outputs/perps.txt` |
| D12 | Rule 5.19: position limits are specified per contract, and Market Makers in a program are excluded from them | Rulebook v1.29 |

## Third-party material (context only; not relied on for any kill decision)

- **arXiv 2601.01706**, "Semantic Non-Fungibility and Violations of the Law of One Price":
  - about 2% of Kalshi markets have a cross-venue equivalent;
  - execution-aware deviations average 2–4%.
- **arXiv 2602.19520**, "Domain-Specific Calibration Dynamics in Prediction Markets":
  - covers 353M Kalshi and Polymarket trades;
  - reports domain-level calibration patterns. Relevant to *competition* for M4, not used as evidence of edge.
- **Polymarket US** is a CFTC-designated contract market (QCX LLC), open to US residents in most states, with a taker-only fee. Sources: CNBC 2026-02-14; actionnetwork.com / defirate.com pages dated 2026-09.
- **Public cross-venue scanners already exist** (e.g. predictionmarketspicks.com arb scanner), which is a competition signal for M9.
- **Settlement-rule divergence between Kalshi and Polymarket** (deadline and source) is documented at oddsshopper.com (2026-08-15).
