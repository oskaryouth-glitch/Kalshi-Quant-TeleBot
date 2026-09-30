# lockerlab: storage-unit auction research (PAPER ONLY)

A research system to answer one question with evidence:

> Can Oskar repeatedly acquire storage units at prices sufficiently below
> realistic liquidation value to earn attractive **net** profit after auction
> premiums, transport, disposal, selling fees, storage, unsold inventory, and
> the value of his time?

**It never bids, buys, lists, posts or messages anyone.** It records auctions,
underwrites them, logs *paper* decisions, and scores those decisions against
real outcomes without look-ahead bias.

> This directory is independent of the Kalshi bot in the rest of this
> repository. It shares nothing with it.

## Status

| Phase | State |
|---|---|
| 0 Research | Done. See [docs/PHASE0_RESEARCH.md](docs/PHASE0_RESEARCH.md) |
| 1 Database + ingestion | Done: manual capture (the major platforms prohibit scraping) |
| 4–5 Underwriting + paper bidding core | Done: `manual_v1` human-baseline strategy |
| 2–3 Image analysis, valuation | Designed ([docs/VALUATION_METHODOLOGY.md](docs/VALUATION_METHODOLOGY.md)); start after ~50 captured auctions |
| 6 Evidence review | Needs 8–12 weeks of forward data |
| 7–9 Resale OS / listings / real mode | Only if Phase 6 justifies it |

## Setup (your laptop)

```bash
cd lockerlab
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                     # 145 tests
lockerlab --home . init       # creates data/lockerlab.sqlite3 (git-ignored)
```

Run commands from `lockerlab/`, or set `LOCKERLAB_HOME` to it.

## Weekly workflow

1. **Capture.** Browse Colorado Springs auctions as you normally would. For
   each one, add a row to a capture CSV (`lockerlab template capture --out
   week1.csv` gives the columns plus an example). Always include the **URL**,
   so you can check the outcome later.
   - Percentages are written as `18`, not `0.18`.
   - Times are local facility time.
   - List any fields you weren't sure of in `uncertain_fields`.
   - **Never record occupant names.**

   ```bash
   lockerlab --home . import week1.csv --market colorado_springs --by oskar
   lockerlab --home . photos storagetreasures 123456 --observed-at "2026-10-01 19:30" ~/Downloads/unit123456/*.jpg
   ```

   Re-capturing the same auction later adds a new snapshot; nothing is
   overwritten.
2. **Decide (before the auction ends).** For units you'd consider, copy
   `lockerlab template estimate` into a YAML, fill in your read of the photos,
   then:

   ```bash
   lockerlab --home . underwrite est_123456.yaml   # dry run, records nothing
   lockerlab --home . decide     est_123456.yaml   # records a FORWARD paper decision
   ```
3. **Record outcomes.** After close, add a row with `status` = `sold` (with
   `final_price`), `cancelled`, or `unsold`, then run `lockerlab --home .
   settle`.
4. **Review:**

   ```bash
   lockerlab --home . report market       # what units actually clear at, by size (OBSERVED)
   lockerlab --home . report paper        # simulated wins/losses; ESTIMATED profit
   lockerlab --home . report coverage     # missing outcomes, single snapshots
   lockerlab --home . report assumptions  # every non-verified number the model uses
   lockerlab --home . breakeven --avg-sale 100   # hurdle gross by size and bid
   ```

## Example underwriting output

A test fixture: a half-full 5x10 whose owner estimates $2,000 base-case
resale.

```
CURRENT BID [OBSERVED]: $45.00
MAXIMUM RECOMMENDED PAPER BID: $150.00
  (limited by: max_low_case_loss)
FIGURES BELOW ARE AT BID $150.00; all ESTIMATED:
EXPECTED GROSS REVENUE: $1,700.00 (low $510.00, high $3,400.00; after 85% haircut)
EXPECTED ALL-IN COST (incl. labor): $1,013.11
EXPECTED NET PROFIT: $686.89 (low -$259.56, high $2,039.19)
EXPECTED ROI: 135%
CASH REQUIRED UP FRONT: $600.21
EXPECTED LABOR: 12.2 hours
EXPECTED PROFIT/HOUR (before valuing labor): $76.44
VALUE DENSITY: MEDIUM ($17.00/kept cuft, net $6.87/kept cuft)
DISPOSAL: MEDIUM ($253.00, 1 dump visit(s), 40 cuft trash)
TRANSPORT: 2 trip(s) by homedepot_cargo_van ($55.60)
CONFIDENCE: 60%
DECISION: PAPER_BID  paper bid $150.00
UNVERIFIED ASSUMPTIONS IN PLAY: 76 (see: lockerlab report assumptions)
```

Even with $1,700 expected gross after the haircut, the max bid is only $150.
The pessimistic case (hidden contents are junk) has to absorb the $253
Colorado Springs dump minimum, transport, and fees. That's why verifying the
dump minimum is the top priority.

## Integrity guarantees

- Evidence tables are **append-only**; SQLite triggers reject UPDATE/DELETE.
- Raw capture files and photos are stored **content-addressed and read-only**,
  and re-hashed on read.
- Every observation keeps raw strings, parsed values, label + confidence per
  field, and the parser version.
- Every figure is labelled **OBSERVED / INFERRED / ESTIMATED / SIMULATED /
  REALIZED**.
- Paper decisions can't be backdated or made after an auction ends. Human
  estimates can't be backtested. Every decision stores its full inputs and
  the model version (code + config hash) that produced it.
- Automated collection is blocked for every source until
  `config/sources.yaml` records written permission (`collectors/base.py`).

## Docs

- [PHASE0_RESEARCH.md](docs/PHASE0_RESEARCH.md): sources, terms, APIs, costs, blockers
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): stack, schema (current + planned), integrity
- [PAPER_TRADING.md](docs/PAPER_TRADING.md): look-ahead guards, settlement rule, what paper can't prove
- [UNIT_ECONOMICS.md](docs/UNIT_ECONOMICS.md): formulas, max-bid rules, first breakeven results
- [VALUATION_METHODOLOGY.md](docs/VALUATION_METHODOLOGY.md): image analysis, comps, hidden-content model, calibration
- [ASSUMPTIONS_AND_RISKS.md](docs/ASSUMPTIONS_AND_RISKS.md): assumptions to validate, failure analysis, safety/privacy procedures
- [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md): phases, exit and kill criteria, next steps
- [PERMISSION_REQUESTS.md](docs/PERMISSION_REQUESTS.md): draft emails to platforms (not sent)
