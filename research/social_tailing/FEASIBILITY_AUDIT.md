# H042, Kalshi Social Prospective Tailing: read-only feasibility audit (NOT STARTED)

- **Workstream:** Kalshi Social Tailing Audit. Is there a follower edge from copying public posts at post-detection prices?
- **ID: H042 (Kalshi Social Prospective Tailing).** Relabelled 2026-10-01: the owner reserved H040 elsewhere and H041 is closed. The ID check is in `ACCESS_AUDIT.md` §1.
- **Isolation:** fully separate from H022/H038/H039, M6 and structural_arb. Nothing was collected, no account was used, and no order or quote request was made.
- **Status:** feasibility only. No prospective collection, no candidate freeze. Your approval is needed before either.
- **Date:** 2026-10-01.

## Summary

**The market side is fully feasible. The social side is not reachable from this environment.**

| side | status |
|---|---|
| **Market data** for single markets | Public order books, the trade tape, candles, fees and settlement are all available, and already proven in M6 and structural_arb |
| **Kalshi Social data** (profiles, posts, post times, shared positions, edits/deletes) | Has **no documented API**. kalshi.com sits behind a Vercel bot checkpoint (every page, including robots.txt, returns HTTP 429 with a JavaScript challenge), and I will not circumvent it. The help centre, X and third-party scrapers are blocked by this environment's egress policy |
| **Combos/parlays** | Have **no public executable price**. Of 1,000 open combo markets, 14 displayed any ask and 1 had any volume. Combos are priced per user through an authenticated quote request, so a realistic follower fill **cannot be observed read-only** |

**A scientifically valid follower-ROI test therefore needs one of the social-access routes in §2.** Until then, nothing about the three accounts can be verified.

## 1. Hypothesis ID (superseded: now **H042**; see `ACCESS_AUDIT.md` §1)

- On every branch of this repository (`main`, `claude/kalshi-pricing-scanner-wbdav0`, `claude/kind-carson-3dra5i`), the only H-IDs referenced are H022, H024, H029, H031, H038 and H039.
- H040 and above appeared nowhere. *(Superseded: the owner reports H040 is reserved and H041 closed in the external registry.)*
- `edge_search/MECHANISMS.md` already notes that **the H0xx registry itself is not in this repository**.
- ~~Please confirm H040 is unused in the external registry~~. Resolved by the owner: use H042.

## 2. Kalshi Social information I can access

| source | access from here | notes |
|---|---|---|
| Kalshi Trade API v2 (`api.elections.kalshi.com`, documented) | ✅ | No social, profile, post or leaderboard endpoint. The current `docs.kalshi.com/llms.txt` (2026-10-01) adds only settlement bounds and a premium index since 2026-09-27 |
| kalshi.com web (profiles, feed) | ❌ | Vercel Security Checkpoint (HTTP 429 plus a JS challenge) on every path. Getting past it means automated bot-evasion, which I won't do |
| help.kalshi.com, x.com, apify.com, botforkalshi.com | ❌ | blocked by the session's egress policy |
| Web search index | ✅, but empty | No indexed content for `@wightsurfer10`, `@Hidden.Edge` or `@cwilltennis` |

**Public reporting (search snippets only) says Kalshi Social:**
- is mobile-first;
- gives every user a profile by default, with an opt-out to private;
- has posts of up to 800 characters that can "share positions";
- has a For You feed, follows with move notifications, Inner Circles (private sharing) and a leaderboard.

Third-party profile scrapers exist (Apify), which suggests profile data is machine-retrievable somewhere. Their access method and terms-of-service status are unknown and unreviewed, and I do not recommend them without that review.

**Legitimate access routes, for your decision:**

| route | what it involves | trade-off |
|---|---|---|
| **(A) Read-only capture by a person** | Through your app or browser session. Captures are recorded mechanically: every post from the frozen accounts as it appears or is notified, with screenshot and capture time | Valid but manual. Detection delay equals human latency. The capture protocol must stop selective recording |
| **(B) Written permission or a documented endpoint from Kalshi** | Kalshi permits automated read-only access to Social data, or provides an endpoint | Then an automated poller runs on a host whose egress allows it. Cleanest, if obtainable |
| **(C) A third-party data source** | e.g. a scraper | Only after a terms-of-service and provenance review. Its timestamps and completeness would themselves need validation |

## 3. Can post timestamps and positions be captured reliably?

**Not from here, so unverified.** Under route A or B the questions to settle in a short pilot are:
- whether posts show an exact creation time (or only "2h ago");
- whether a shared position carries the ticker, side, average entry price and size;
- whether shared positions update over time (P&L, exits).

Relative timestamps ("5m") only bound the time to a window, and that window must be carried as uncertainty. **The follower test does not depend on the post time anyway.** It uses *our detection time* and the market state after it. The post time matters only for diagnostics: delay and trader-to-follower slippage.

## 4. Can contemporaneous market prices and order books be captured? **Yes, for single markets**

- **Unauthenticated endpoints:**
  - `/markets/{t}/orderbook` (full depth);
  - `/markets/orderbooks?tickers=` (≤ 100 per call);
  - `/markets/{t}`;
  - `/markets/trades` (an anonymous global tape with `created_time`, price, size, taker side);
  - candlesticks;
  - `/series` and fee changes (fee ledger);
  - settlement result.
- **Detection-to-book latency** can be held to seconds. The 429 risk is known: 2.7% of requests were rate-limited in the 2026-09-30 cycle.
- **Combos:** order books are empty and quotes come through an authenticated quote request. **No realistic follower fill is observable** (§12).
- **Trader identity is not on the tape.** Trades are anonymous, so a trader's actual fills can never be matched to their posts from public data.

## 5. Can deleted or edited posts be detected?

Only by **repeated re-observation and diffing**. Every capture of a post stores a content hash; a later capture that differs, or a post missing from the profile, is logged as edited or deleted, bounded by the two capture times. A post created and deleted between two captures is invisible. Detection power therefore depends on capture cadence, which is weak under route A.

## 6. The three named accounts

**Nothing could be verified from this environment.** Profiles are behind the bot checkpoint, and web search returns nothing for any of the three handles.

- `@Hidden.Edge`: not to be confused with an unrelated Substack, "The Hidden Edge in Kalshi's Crypto Markets"; no link is established.
- The **"repeated references to @wightsurfer10"** cannot be seen from here. Checking the upstream-signal hypothesis needs the posts themselves, via route A or B.

What would be recorded per account at the freeze (snapshot plus capture time):
- displayed lifetime profit, volume and trade count;
- post count, and account and post history length;
- categories traded, and singles vs combos;
- posting frequency;
- whether losing positions are visible;
- whether posts precede resolution;
- typical liquidity of posted markets (computed from our own book captures).

## 7. How many more candidates can realistically be discovered

- **20–50 is realistic** under route A, in a few hours of read-only browsing, or under route B. **Zero** under the current egress.
- **Proposed discovery frame,** fixed before looking at any results and deliberately not profit-ranked:
  1. accounts credited, tagged or tailed by the three seed accounts (snowball; this also builds the relationship graph);
  2. leaderboard accounts across *volume* as well as profit, and across categories;
  3. a seeded random sample of active posters from the public feed during a fixed window.
- Each account's discovery source is recorded, so selection effects can be analysed.

## 8. Proposed prospective methodology (for approval; nothing frozen yet)

1. **Freeze** the candidate manifest (accounts, discovery source, profile snapshot), the parser, fill rules, control, analysis script and decision rule, all hashed as in M6.
2. **Capture**, append-only:
   - every new post by a frozen account, with its own capture time = *detection time*;
   - the raw payload or screenshot and its sha256;
   - the parsed legs.
3. **Market snapshot** immediately after detection: the full order book of every leg, the market object, and trades since the stated post time.
4. **Qualifying signal:** an explicit position (market + side) in a market that is open at detection. Commentary without a position is logged, not traded.
5. **Paper fill (primary).** A marketable taker buy of a **fixed stake** (e.g. 10 contracts; the stake is pre-specified) on the posted side:
   - priced from the first order book received ≥ L seconds after detection (L pre-specified, e.g. 5 s), walking depth;
   - taker fee from the time-versioned fee ledger;
   - **never the trader's price.**
   - **Not copyable** (recorded, not filled) if: no ask; depth below the stake; market closed or halted; or the ask exceeds a pre-specified ceiling (e.g. ≥ 99¢).
6. **Exit:** hold to settlement (primary). Mirroring the trader's posted exits is a secondary variant, only if exits are observable.
7. **Separate strata, never pooled:** singles; 2-leg; 3–4 leg; 5+ leg combos. Combos are logged and reported descriptively, with leg-implied proxy prices clearly labelled "not executable" (§12).
8. **Metrics:**
   - **Primary:** follower net P&L and net ROI on copyable singles, pooled over the frozen accounts.
   - **Also reported:**
     - counts, number copyable, wins and losses, gross P&L, fees, net P&L, ROI;
     - mean and median return per trade, win rate, maximum drawdown;
     - trader-to-follower slippage;
     - breakdowns by account, category and combo size.
9. **Inference:** cluster bootstrap by event (10,000 resamples, fixed seed), as in M6.
10. **Decision rule** (pre-specified):
    - **SURVIVE** only if the net-ROI lower 95% bound > 0 **and** the signal-minus-control difference has a lower 95% bound > 0, with n ≥ the pre-specified minimum.
    - Per-account results are secondary, Holm-adjusted.
11. **Fixed horizon** (e.g. 6–8 weeks), plus a fixed settlement cutoff. No interim peeking: monitoring covers counts and operations only.

**Power warning.** Binary contracts at mid-range prices have per-trade return SD ≈ 1. Detecting a +5% mean net ROI needs roughly 1,500 independent singles, and posts cluster by account and event. Unless the frozen accounts post very often, the most likely honest outcome is INSUFFICIENT_EVIDENCE.

## 9. Proposed control: **a matched-market, same-timestamp placebo entry**

- For each copyable single signal, the control is the same paper-fill rule, at the same detection timestamp, in a market drawn by seeded RNG from the open markets that match the signal on:
  - category or series family;
  - side;
  - entry-price bucket (±5¢);
  - time-to-close bucket.
- The primary contrast is the signal's return minus the control's.
- **Why it's the cleanest:** it is fully computable from public data, pre-registrable, and removes generic effects that would otherwise look like trader skill: the favourite-longshot bias, NO-side bias, category drift and fee level.
- **Rejected as primary:**
  - the market-implied zero-excess baseline: it is implicit in "net ROI > 0" and reported anyway;
  - random active posters: they need the same social access, add noise, and are reported as secondary if access allows.

## 10. Data and schema design (append-only JSONL, one stream per type, every row with provenance)

| stream | key fields |
|---|---|
| `accounts_manifest` (frozen) | handle, discovery source and seed link, profile snapshot (displayed profit, volume, trades, posts, join date), capture time, capture method, raw sha256 |
| `post_captures` (raw, immutable) | capture_id, captured_at_utc (detection), handle, post_id if visible, displayed post time (raw string and parsed bounds), text, shared-position fields as displayed (ticker(s), side, avg price, size), raw/screenshot sha256, capture method/operator, code version |
| `post_reobservations` | capture_id, post_id, seen/absent, content sha256 → edit/delete events with time bounds |
| `signals` (derived by the frozen parser) | signal_id, post refs, legs, combo size, category, qualifying flag and reason, duplicate-of (same position re-posted, or the same position across accounts) |
| `market_snapshots` | signal_id, leg ticker, orderbook body, market body, trades since post, send/receive times, HTTP status |
| `paper_fills` | signal_id or control_id, fill rule version, per-leg VWAP, size, fee and fee provenance, copyable flag and reason, trader displayed price, slippage |
| `controls` | control_id, signal_id, selection set hash, RNG seed/draw, chosen market |
| `settlements` | ticker, result, settled time, source body |
| `relationship_edges` | from, to, type (credit/tag/tail), post ref |

Raw rows are never rewritten. Later knowledge (an outcome, an edit) is added as new rows that reference the old ones.

## 11. Likely failure modes

1. **No legitimate automated social access**, the current state. A manual route A has human latency and possible selective capture.
2. Post times shown only as relative ("2h"), and missing or incomplete position details (no entry price or size).
3. **Combos not executable for followers**, while the seed accounts may be combo-heavy.
4. Survivorship and selection: deleted losers, winners posted after the fact, posts after big moves or near resolution, P&L from unposted activity, accounts chosen by displayed profit.
5. Duplicate and correlated signals: re-posts, accounts tailing each other, many posts on one event.
6. Illiquid markets: the trader's price cannot be reproduced, and depth is below the stake.
7. Rate limits (429s) at detection time delaying the book capture; mitigated by recording the actual receive time.
8. **Too few posts for power** (§8), and drift in account behaviour if they learn they are followed.

## 12. What would prevent a scientifically valid follower-ROI test

- **No legitimate, complete and timely access to posts** (§2). Without route A or B there is no test. A selectively captured route A is invalid too, so the capture protocol must be mechanical and complete for the frozen accounts.
- **Combos:** a follower fill cannot be observed without an authenticated quote request, which is out of scope (no orders or quotes). Combo follower ROI can only be a labelled proxy, never a primary result.
- **Detection time** must be our own measured capture time. If captures are batched (e.g. reviewed hours later), the test is of a slow follower, and must be described as such.
- **Sample size:** if the frozen accounts post fewer than a few hundred qualifying singles in the horizon, the pre-specified outcome is INSUFFICIENT_EVIDENCE, not a positive claim.
- **Historical data is never evidence of edge here.** Pre-freeze browsing is for discovery and behaviour only.

## Decisions needed from you before any build or freeze

1. The social-access route: (A) person-operated read-only capture, (B) seek Kalshi permission or an endpoint, or (C) a third party after terms-of-service review.
2. ~~Confirm H040 in the external registry~~ (resolved: H042).
3. Approve, or amend, the fill rule (stake, latency L, price ceiling), the control, the horizon/minimum n and the decision rule.
4. Combos: logged and reported descriptively only (recommended), or excluded entirely.

### Sources consulted (web search snippets only)

- Kalshi Social announcement: <https://x.com/KalshiTrade/status/2047721899430482398>
- Help centre: <https://help.kalshi.com/en/articles/15891130-how-do-i-post-comment-and-react-on-kalshi-social> (title only; blocked here)
- Third-party scrapers (not used): <https://apify.com/automation-lab/kalshi-trader-social-profile-scraper>, <https://apify.com/saswave/kalshi-profile-scraper>
- Unrelated "Hidden Edge" Substack: <https://henryzhang.substack.com/p/the-hidden-edge-in-kalshis-crypto>
