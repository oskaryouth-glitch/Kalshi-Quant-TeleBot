# Daily workflow: the LockerLab desk

Target: 10–20 minutes a day. Paper only. LockerLab never bids, buys, lists
or messages anyone.

## One-time setup (about 15 minutes)

```bash
git clone https://github.com/oskaryouth-glitch/Kalshi-Quant-TeleBot.git   # or git pull
cd Kalshi-Quant-TeleBot/lockerlab
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[app]"
lockerlab --home . init
lockerlab --home . serve          # open http://127.0.0.1:8765
```

Optional: `export ANTHROPIC_API_KEY=...` (or `ant auth login`). This only
matters for platforms where screenshot reading is allowed (see Sources). For
StorageTreasures and Lockerfox it's off until they give written permission.
Cost is a few cents per capture with screenshots.

Keep `lockerlab/data/` backed up (copy the folder). It's your dataset, and
it's deliberately not in git.

## Tomorrow: your first 10 forward auctions (about 15–20 minutes)

1. **Open two windows:** the StorageTreasures app or site (search Colorado
   Springs, sort by ending soonest), and the desk at http://127.0.0.1:8765.
2. **For each of the next 10 small units (5x5 / 5x10), capture all of them,
   not just the good-looking ones.** Market prices are only honest if the
   sample isn't picked by taste.
   1. Copy the listing URL.
   2. Desk → **+ Capture auction** → paste the URL → **Continue to review**.
      StorageTreasures is detected and marked *manual only*.
   3. Type the six top fields from the listing:
      - unit size (`5x10`)
      - current bid (`85`)
      - number of bids
      - end time (`2026-10-08 14:00`, local time)
      - facility name
      - city
   4. Buyer premium and deposit are optional; leave them blank if not
      shown, since blanks are never filled with guesses.
   5. **Confirm snapshot.** About 40–60 seconds per auction.
3. **Estimate the 3–5 most promising** (the confirm step lands you on the
   auction page). Keep the listing's photos open in the other window.
   1. Visible items would sell for $ (realistic *sold* prices).
   2. Hidden value low/high for boxes, bags and out-of-frame areas. Be
      pessimistic: most boxes are $0–5.
   3. Disposal: negligible / light / medium / heavy.
   4. Vehicle needed: car/SUV, pickup/van, or truck.
   5. Confidence %, plus category tags.

   Then **Calculate**, read the numbers, and press **Paper bid**, **Watch**
   or **Pass** (with reasons). About 1–2 minutes each.
4. **For the rest, if they're obviously not for you** (huge, couch
   mountain), use *Pass or watch without estimating* and tick a reason
   (10 seconds). The reason is data too.
5. **Look at the desk.** Top cards show the most interesting open lockers
   and exactly why. "Ending soon" and "Needs estimate" tell you what's left.

## Every day after

| Minutes | What |
|---|---|
| 5 | Capture new small-unit listings (all of them, down to ~10) |
| 5–8 | Estimate and decide the 2–3 best before they end |
| 2–3 | **Awaiting result**: open each ended listing, record Sold $X / Cancelled / No bids / Unknown |
| 1 | Glance at the health strip: closed small units / 100 |

Weekly (20–30 min):

- **Readiness page:** log one timed sale of your own stuff; record any
  first-hand check (phone calls, a friend's car).
- **Assumptions page:** when you verify something (e.g. Woodmen's prices),
  enter it and mark it *Verified first-hand* with how you know. This affects
  future decisions only.
- **Calibration page:** look, but don't conclude anything under 10 auctions
  per group.

## What the numbers mean

- **Max paper bid**: the highest bid at which every underwriting rule holds:
  - cash profit ≥ $150
  - cash ROI ≥ 50%
  - **cash profit ≥ $25 per hour of work**
  - pessimistic case loses ≤ $75 cash
  - fits the $1,000 bankroll

  The $25/h rule usually binds, because selling labor dominates. It's your
  setting (Assumptions → "Minimum cash profit per hour").
- **Cash profit at current bid**: money left if you paid today's bid.
- **Economic profit @ $25/h**: cash profit minus your hours × $25. At the
  max bid it's ≈ $0 by construction, because that's what the max bid solves
  for.
- **Opportunity score (0–100)**: orders your attention. Every point is
  listed under "Why this score". It never changes a max bid or a rule.
- **Results**:
  - WON / LOST / VOID are SIMULATED under the rule in PAPER_TRADING.md.
    Winning needs your paper bid ≥ winning price + one bid increment.
  - Profit shown after a WON is ESTIMATED from your own estimate. Nobody
    has seen the contents.

## What's still manual

- Finding auctions (browsing the platforms yourself).
- Typing the listing fields for StorageTreasures, Lockerfox, and any source
  whose terms you haven't reviewed. The screenshot path turns on per source
  from the Sources page, with a recorded reason.
- Looking at photos for manual-only sources (on the site, not stored).
- Your estimates, by design: they are the human baseline the AI must beat
  later.
- Recording results (revisit each ended listing).
- Verifying assumptions (phone calls, friends' cars, timed sales).
