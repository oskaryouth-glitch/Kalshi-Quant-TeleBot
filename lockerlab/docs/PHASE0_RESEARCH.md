# Phase 0: Feasibility research

*Researched 2026-09-30. Method: web research through a search/answer service. The
development sandbox's network policy blocks the auction and marketplace sites
themselves, so **no page was loaded directly**. Treat every item as SOURCED
(cited, not first-hand verified) and re-read the key terms pages yourself in a
browser before relying on them.*

## 1. Headline findings

1. **The biggest auction platforms forbid automated collection.** You can't
   legitimately build the "continuously discover 50–200 auctions" crawler
   against them without written permission.
   - **StorageTreasures** terms: the license "expressly excludes … any data
     extraction or data mining whatsoever". Prohibited uses include "collecting
     auction dates or unit counts, by electronic **or other means**, for
     commercial or competitive purposes" and "any automated use of the
     system". The service is "for the personal use of Members only".
   - **Lockerfox** terms prohibit "robots, spiders, or other automatic or
     manual processes to monitor or copy" pages or data without express
     written permission.
   - **StorageAuctions.com** excludes "commercial use of the Site … (other
     than the buying and selling of items)". Its full automated-access clause
     wasn't verified.
   - **Bid13**: terms on automated access weren't verified. Bid13 *does*
     advertise an API for programmatic integrations. That makes it the best
     candidate for an authorized feed.
2. **No public data API exists** on any storage-auction platform found. The
   APIs that exist (StorageTreasures/OpenTech, SiteLink/Storable, Lockerfox's
   integrations) are operator-side tools for *creating* auctions.
3. **Historical sold prices aren't a searchable public dataset.**
   StorageTreasures sold auctions reportedly stay online at their URL but
   can't be searched (per a support reply quoted on Sitejabber; unverified).
   So there is **no legitimate way to backtest on historical outcomes**. The
   only honest path is forward collection: record the auction URL before it
   ends, then record the outcome after it ends.
4. **eBay sold-price data via API is effectively unavailable.**
   - The Finding API (including `findCompletedItems`) was decommissioned in
     February 2025.
   - The Browse API returns only *active* listings (asking prices).
   - Marketplace Insights (sold data) is a Limited Release API that is "not
     open to new users".
   - Terapeak in Seller Hub is a manual research tool, not a data API.
5. **No local marketplace offers a posting or data API to individuals.**
   Facebook Marketplace, Craigslist, OfferUp, Poshmark and Mercari all
   prohibit scraping. Depop has a permissioned partner API. eBay's Sell
   Inventory API *is* usable by a small seller to create listings, so eBay is
   the only realistic automated-listing target (Phase 8).
6. **Fees are higher than they look.**
   - StorageTreasures buyer premium: **18%** on the Basic tier (15% / 12% /
     9% on paid tiers), $10 minimum, plus a facility purchase deposit of
     0–10% and a cleaning deposit commonly ≥ $100.
   - Lockerfox buyer premium: 15%.
7. **Disposal may be the decisive cost in Colorado Springs.** The Waste
   Connections Colorado Springs Transfer Station lists $126.50/ton with a
   **2-ton minimum ($253)**. If that applies to a small household load, every
   locker that needs one dump run carries a $253 fixed cost. See
   UNIT_ECONOMICS.md for how much that matters. **Verify by phone first.**

## 2. Auction sources

| Source | Who uses it | Automated collection | Manual capture | Sold prices visible |
|---|---|---|---|---|
| StorageTreasures | Extra Space (exclusive online partner since 2019); absorbed SelfStorageAuction.com; claims 20,000+ facilities | **Prohibited** | Gray area: personal bidding research is the intended use, but "collecting … by other means for commercial purposes" is also prohibited | At the auction URL, not searchable (unverified) |
| Lockerfox | Unverified roster; integrates with SiteLink, storEDGE, SSM, Yardi | **Prohibited** without written permission | Viewing is fine; systematic monitoring needs permission | Unknown |
| StorageAuctions.com | Unverified | Prohibited (commercial-use exclusion) | Allowed for buying | Unknown |
| Bid13 | US + Canada; has a Colorado Springs listings page | Unknown; **API exists by arrangement** | Allowed | Winner gets full bid history by email; public visibility unknown |
| iBid4Storage | Participating facilities (US/Canada) | Unknown | Allowed | Unknown |
| Public lien-sale notices (newspapers, publicnoticecolorado.com, Marin IJ legals) | Required by law in some forms | Varies by publisher | Allowed | No prices. Useful to count the auction universe; they contain **occupant names, which must never be stored** |

Machine-readable version: `config/sources.yaml`. The collector gate reads it
and refuses any source not marked `authorized`.

### What this means for the plan

- **Phase-1 ingestion is manual capture.** Oskar views auctions he's
  considering and records them in a CSV (a few minutes per auction). The
  system stores the file as immutable evidence. This is slower than a crawler.
  A realistic volume is **20–40 auctions per week, not 50–200**.
- **Bid-evolution snapshots** (how bids move over time) need repeated
  captures. Manually, capture at most discovery, ~24 hours before close, and
  the outcome.
- **Ask for permission** (drafts in PERMISSION_REQUESTS.md). A yes from Bid13
  or StorageTreasures would unlock automated collection through the
  already-built `PoliteClient` gate.
- **Gray-area warning:** even manual recording of StorageTreasures data for a
  business could be read as violating "collecting … by other means for
  commercial purposes". Personal research to decide your own bids is the
  site's intended use. Building a broad market dataset is less clearly so.
  Getting written permission removes the ambiguity. **This is your call. I'm
  not a lawyer and this isn't legal advice.**

## 3. Resale price data (for Phase 3 valuation)

| Source | Access | Sold or asking? | Notes |
|---|---|---|---|
| eBay sold listings (website search, "Sold items" filter) | Manual browsing | **Sold** | Best general source; manual only. Scraping is against eBay's terms |
| eBay Browse API | Free developer account | Asking (active) | Useful as a ceiling, never as a value |
| eBay Marketplace Insights API | Limited Release, closed to new users | Sold | Not available |
| eBay Terapeak (Seller Hub) | Free with a seller account, manual | Sold | Manual research tool |
| PriceCharting API | Paid subscription | Guide values built from sales; its Marketplace API exposes sold offers | Video games and some collectibles |
| Reverb Price Guide | Website; API terms unclear | **Sold** (Reverb transactions) | Musical instruments |
| Discogs API | Free; marketplace stats are "Restricted Data" | Sales history (restricted) | Records/CDs |
| Bicycle Blue Book | Website | Value guide (asking-oriented) | Bikes |
| KEH / MPB trade-in quotes | Website | Dealer buy offers | A useful **quick-sale floor** for cameras and lenses |
| Facebook Marketplace / OfferUp / Craigslist | Browse manually | Asking only | No sold data exists publicly. Treat asking prices as ceilings |

**Consequence:** valuation (Phase 3) must be built on manual sold-comp
research plus a small number of paid/official APIs. Every comp is stored with
provenance and a SOLD/ASKING label, and asking prices get heavy haircuts. The
AI-proposed identification and value range is an ESTIMATE that comps must
confirm.

## 4. Marketplace integration (Phase 8, only if justified)

| Platform | Official route | Plan |
|---|---|---|
| eBay | Sell Inventory API (OAuth, individual sellers allowed) | Automatable, with a human approving each listing |
| Facebook Marketplace | No individual API | Listing queue + copy/paste workflow |
| Craigslist | No API (bulk posting only for certain paid categories) | Listing queue |
| OfferUp | No API; terms forbid third-party apps without consent | Listing queue |
| Poshmark | No API; scraping prohibited | Listing queue |
| Depop | Partner API by approval only | Listing queue; apply if clothing volume justifies it |
| Mercari | No official API found | Listing queue |

Seller fees (2026, secondary sources except eBay):

- eBay: 13.6% + $0.40 per order for most categories
- Facebook Marketplace: 0% for local sales, 10% shipped ($0.80 minimum)
- OfferUp: 0% local, ~12.9% shipped (unverified)
- Mercari: 10%
- Poshmark: 20% (≥ $15 sale)
- Depop US: 0% selling fee + 3.3% + $0.45 processing
- Craigslist: mostly free

## 5. Legal notes (not legal advice; verify with the facility and statutes)

- **Online lien auctions** are expressly permitted in both Colorado (C.R.S.
  38-21.5) and California (B&P 21700–21716).
- **California B&P 21710:** the buyer must remove the property **within 24
  hours** of the sale.
- **California B&P 21712:** the *operator* must return personal papers,
  personal photographs and personal records to the occupant on request. The
  buyer should hand such items to the facility promptly and not dispose of or
  sell them.
- **Colorado:** the researched sources did not confirm an equivalent
  personal-papers rule or a statutory buyer cleanout deadline. The auction
  terms govern. Ask the facility.
- **Vehicles/boats:** a unit sale does not by itself convey a vehicle title.
  There are separate title procedures.
- **Sales tax:** auction purchases are generally taxable retail sales. A
  **valid resale certificate** (not just a seller's permit) can exempt
  purchases for resale in California. For Colorado, confirm with CDOR. The
  model conservatively assumes tax is paid on bid + premium.

## 6. Operating costs found

| Item | Colorado Springs | Marin / Bay Area |
|---|---|---|
| Landfill / transfer | Waste Connections CS Transfer: $126.50/ton, **2-ton min ($253)**, mattress $86.25, freon-free appliance $7, **no freon appliances** (SOURCED, call to confirm) | Redwood Landfill: mattress $67.64, freon-free appliance $61.38 (Oct 2025 sheet). General self-haul rate not published: call MRRC 415-485-5647 |
| E-waste | El Paso County HHW: free for residents, ~5 devices/household/year | Marin HHW accepts e-waste |
| Free options | County cleanup events: one pickup load free (2025 flyer, seasonal) | Bye Bye Mattress program (check locations) |
| Home Depot Load 'N Go van/pickup | $19 for the first 75 min, unlimited miles, $150 deposit | Same chain pricing |
| U-Haul in-town | From $19.95 + per-mile (example: $0.89/mi van, $1.39/mi 10' truck; not Colorado Springs rates) | Same |

## 7. Blockers and open questions

| # | Blocker / question | Why it matters | How to resolve |
|---|---|---|---|
| B1 | Terms prohibit automated collection | No crawler; manual capture caps volume | Permission emails (drafted); Bid13 API |
| B2 | No historical outcome data | No backtest possible; the edge must be measured forward | Record every URL; capture outcomes after close |
| B3 | Sandbox network blocks auction sites | Collectors and parsers can't be developed or tested here | Run lockerlab on your laptop; widen the environment's network policy if you want me to inspect pages |
| B4 | Colorado Springs dump minimum | Could dominate small-unit economics | **Phone calls**: Waste Connections, WM Colorado Springs Landfill, a junk hauler |
| B5 | eBay sold data API closed | Valuation comps are manual | Manual comps + PriceCharting/Reverb where they apply |
| B6 | Paper trading can't observe real contents | The value side of the model can never be validated on paper | See PAPER_TRADING.md §5: eventually requires a few small real acquisitions, if you choose |
| B7 | Unknown number of Colorado Springs auctions per week | Determines how fast evidence accumulates | Count them in the first two weeks of capture |
