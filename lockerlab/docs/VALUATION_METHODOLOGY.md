# Valuation methodology (Phases 2–3 design; not yet implemented)

Principle: estimate **realistic liquidation proceeds** that are *checkable
later*, never MSRP. Every number keeps its evidence and its label.

## 1. Visible items (Phase 2: image analysis)

For each auction photo, a vision model returns structured JSON (validated
against a schema; invalid output is stored raw and flagged, never coerced):

```
{category, possible_brand, possible_model, identification_confidence,
 est_age, visible_condition, quantity, bbox, container_type,
 evidence: "yellow/black drill body with DeWalt-style battery, top shelf left"}
```

Rules:

- Brand/model are *possible* with a confidence ("possible DeWalt drill,
  0.82"). Below a threshold, the item stays at category level. No inventing
  model numbers.
- The raw model response, prompt version, model name and cost are stored
  (`image_analyses`). Re-running with a new model creates new rows.
- **Double counting:** the same item often appears in several photos. Phase 2
  de-duplicates across images of one unit (same category + position cues).
  Each merge is recorded.
- Validation: for your first ~50 auctions, compare the AI's item list with
  your own manual reading (the `manual_v1` estimate files are that record).

## 2. Item value (Phase 3)

For each identified item or category:

1. **Comps.** Search sold comps manually or through an allowed API (eBay sold
   search manually, PriceCharting, Reverb Price Guide, KEH/MPB buy quotes as a
   quick-sale floor). Store each comp with source, URL, date, condition, and
   **SOLD vs ASKING**.
2. **Weighting.** Sold comps carry full weight. Asking prices are used only as
   a ceiling, with a heavy haircut (initially ×0.6, learned later). Stale
   comps (> 12 months) are down-weighted.
3. **Condition adjustment** from the visible condition. Unknown condition is
   assumed to be "used, fair".
4. **Outputs:** low / expected / high **liquidation** value, quick-sale value
   (~7 days, local), slow-sale value (eBay, ~30+ days), expected
   days-to-sale, recommended channel, shipping difficulty, footprint (cuft),
   disposal risk.
5. **Sell-through.** Expected proceeds = value × P(sells within the holding
   window). P is a category prior (GUESS initially), learned from Phase-7
   sales.
6. **Category fallback.** Unidentifiable items get a per-category prior
   (e.g. "box of kitchenware: $0–15, mostly donate").

## 3. Hidden contents (uncertainty model)

Storage types seen in photos:

- transparent container
- opaque tote
- cardboard box
- bag
- drawer/cabinet
- completely hidden area

Each type gets a **prior distribution** of liquidation value per unit, e.g. a
lognormal with a high mass at ~$0.

- **Initial priors are deliberately pessimistic** (GUESS): median opaque tote
  $3, cardboard box $2, bag $1, 90th percentile ~$40. A black trash bag
  defaults to disposal volume, not value.
- They're stored in a versioned `hidden_content_priors` table and **only move
  on REALIZED data** (units actually opened). Paper data can't update them,
  because paper never sees inside the boxes.
- Unit total = Σ visible items + Σ hidden containers. Low/base/high = the
  10th/50th/90th percentile of a **Monte Carlo** over item and container
  distributions (with correlation: a unit that looks "organized household"
  shifts all container priors together). Implemented only once the priors
  have data behind them. Until then the three-point estimate stands.

## 4. Calibration: how we find out whether valuation is any good

| Check | Data needed | Available when |
|---|---|---|
| AI item list vs your manual read | photos + your estimates | Phase 2 |
| Estimate ÷ observed winning price, per size and category | forward captures + outcomes | Phase 5–6 |
| Predicted vs **realized** proceeds per item and per unit | real acquisitions | Phase 7+ |
| Interval coverage: do ~80% of realized unit totals fall inside low–high? | real acquisitions | Phase 7+ |
| Bias: mean(realized ÷ predicted); the valuation haircut is set to this | real acquisitions | Phase 7+ |

Until realized data exists, every valuation is labelled ESTIMATED, the
haircut stays at 0.85 or lower, and the reports say so.

## 5. Known failure modes to test for

- **Asking-price inflation:** marketplace asks exceed sold prices, often by
  30–100% for used household goods.
- **Photo selection bias:** facilities photograph the front of the unit. The
  back is often worse.
- **Brand halo:** a visible premium brand is taken as a sign that everything
  is premium.
- **Bulk illusion:** many items × small value, where labor dominates.
- **Condition optimism:** photos hide wear, missing parts, dead batteries.
