# H042: Kalshi Social Prospective Tailing. Social-data access audit

**Status: H042 BLOCKED / NOT STARTED.**
- No post has been captured, no account used, no order or quote requested, and no access control bypassed.
- Prerequisite set by the owner: **legitimate + mechanical + complete** Social capture.
- **No method available today meets it.** The only route that could is **prior written authorization from Kalshi** (§3, method E).

Audit date: 2026-10-01.

## 1. Hypothesis ID check

- **Owner's statement:** H040 is reserved (H039 → execution path) and H041 is closed. This experiment is provisionally **H042**.

**Searched for any prior use of H042** (none found):

| source | result |
|---|---|
| This repository, all refs (`main`, `claude/kalshi-pricing-scanner-wbdav0`, `claude/kind-carson-3dra5i`) | Working-tree grep and full history (`git log --all -G` / `--grep`): **no H041, H042 or H043**. The only H04x is this workstream's own withdrawn provisional label "H040" in commit `dda0948` |
| GitHub issues and PRs of `oskaryouth-glitch/Kalshi-Quant-TeleBot` | no match |
| Connected Dropbox | Search for "H042" and for a Kalshi hypothesis registry: only unrelated tokenised filename/content matches (personal and real-estate files, none opened). No registry found |
| Connected Wispr Flow notes and meetings | no match |

**Limitation.** The project's H-registry (where H038–H041 live) is **not reachable from this environment**, so the search cannot prove H042 is free there. Following the owner's instruction, H042 is used.

- The earlier `FEASIBILITY_AUDIT.md` label "H040" is withdrawn and relabelled H042. Commit `dda0948`'s message keeps the old label, and history is not rewritten.
- H038, H039, H040, H041, M6 and structural_arb are untouched.

## 2. Governing terms (primary sources, from Kalshi's public regulatory bucket)

| document | URL | sha256 | Last-Modified |
|---|---|---|---|
| Kalshi Developer Agreement v1.1 | `kalshi-public-docs.s3.amazonaws.com/Kalshi-Developer-Agreement.pdf` | `9d3e33685c0f0a88d23895685107975b0745283aac96f8bf7d202f5ae4dc1fa6` | 2023-11-09 |
| Kalshi Data Terms of Use | `kalshi-public-docs.s3.amazonaws.com/kalshi-data-terms-of-service.pdf` | `d19a0f94ffd65aa51eccb80cc8c9a06fb842478c5bf4cbd5a31ec51dd0a3966f` | 2024-09-11 |
| KalshiEX Member Agreement | `…/regulatory/agreement/kalshi_member_agreement.pdf` | `fba2210f…` | (no relevant clause) |

The API docs state: "By continuing to use or access Kalshi's API, you are agreeing to be bound to our Developer Agreement" (that link is `kalshi.com/developer-agreement`). kalshi.com is behind a bot checkpoint, so it **cannot be confirmed** that the bucket copies are the current versions.

**Verbatim clauses that decide this audit:**

- **Data Terms, §II (Prohibited uses):**
  - "Unless Kalshi gives you prior written permission, use of any Web browsers (other than generally available third-party browsers), engines, scripts, software, spiders, robots, avatars, agents, tools or other devices or mechanisms (such as crawlers, browser plug-ins and add-ons, or other technology) to navigate, access, copy in bulk, retrieve, harvest, index, search or analyze any portion of the Website is strictly prohibited."
  - Also prohibited without prior written authorization: "collecting, copying, … electronically extracting or scrubbing, scraping, compiling (including … systematic retrieval to create collections, compilations, databases or directories) or conducting 'text and data mining' … in relation to any Kalshi Data and other Kalshi intellectual property you access via the Website".
  - "use of any Kalshi Data (including associated metadata) in any manner for any machine learning and/or artificial intelligence, … or otherwise for the purposes of using or in connection with the use of such technologies, tools, or models to generate any information, material, data, derived works, content, or output is expressly prohibited."
- **Data Terms, §I (Permitted uses):** "You may access content only for your personal use for non-commercial purposes."
- **Developer Agreement, §3 (Prohibitions):**
  - "Use of Kalshi APIs is expressly limited to facilitating a members own trading on the Exchange; all other usages are disallowed".
  - §3.1 prohibits "Collecting, caching, aggregating, or storing data or content accessed via the API except for purposes of facilitating your own trading on Kalshi".
  - §3.5 prohibits access "for any other benchmarking or competitive purposes".
  - §3.6 prohibits "Attempting to access data belonging to other members".

## 3. Candidate methods, assessed against the owner's 12 questions

| # | method | verdict |
|---|---|---|
| A | Documented Kalshi Trade API (REST v2 and WebSocket) | **No Social data exists in it.** The current full docs (`llms-full.txt`, 524 KB, fetched 2026-10-01) have no social, post, feed, profile, follow or leaderboard endpoint. WebSocket channels: ticker, orderbook deltas, public trades, market and multivariate lifecycle, market positions, user orders/fills, order groups, communications (RFQ/block trades), CF Benchmarks/Pyth |
| B | Automated access to kalshi.com or app Social pages, or their undocumented internal endpoints (scripts, headless browsers) | **Not legitimate without written permission** (Data Terms §II), and the site sits behind a bot challenge that would have to be circumvented. **Rejected** |
| C | Third-party scrapers or data vendors (e.g. Apify "Kalshi trader/social profile" actors) | They obtain the data by the same website automation, so the same prohibition applies; provenance and completeness are unverifiable. **Rejected** |
| D | Mechanically processing the owner's own Kalshi push or email notifications for followed accounts | Not verifiable from here, and unlikely to qualify (see table below). **Not acceptable as specified** |
| E | **Prior written authorization from Kalshi**, or an official Social data feed or API granted to the owner | **The only route that can satisfy the prerequisite.** Its answers depend on what Kalshi grants |

**The 12 questions for D and E** (A has no Social data; B and C are prohibited):

| question | D: own notifications | E: Kalshi-authorized access |
|---|---|---|
| 1. method | Follow the frozen accounts; mechanically parse every notification delivered to the owner | Whatever Kalshi authorizes: an official feed or endpoint, or permission for a specified read-only capture method |
| 2. captures every post mechanically? | **Unknown, probably not.** Notifications are advertised for when followed traders "move" (trades), not necessarily every post. Delivery is best-effort; content may be truncated | Possible, if the grant covers complete per-account post listings |
| 3. timestamp precision | Notification receive time only. The post time may be absent | Depends on the feed (exact post time ideally) |
| 4. position/ticker information | Probably partial (a market name in the text, not a ticker) | Depends |
| 5. entry price and size | Probably not | Depends. Entry price is needed only for the slippage diagnostic, never for the fill |
| 6. edits and deletions | No | Only if the feed exposes them, or allows re-polling |
| 7. expected detection latency | Seconds to minutes; push delivery is not guaranteed | Depends on push vs polling cadence |
| 8. authentication | The owner's account and device or email | As granted |
| 9. rate limits | none (passive) | As granted |
| 10. terms and access concerns | Compiling notification content into a research database, and AI-assisted analysis, fall under the Data Terms §II collection/compilation and AI/ML clauses. Notifications also depend on the owner's personal account. **Needs Kalshi's written OK anyway** | None, if the authorization explicitly covers (a) automated read-only capture, (b) storage and analysis for research, including AI-assisted analysis, and (c) no redistribution |
| 11. unattended on the host | Only with a device or mailbox integration; fragile | Likely, if API-based |
| 12. historical or only new posts | New only | Depends. Historical posts are for discovery only, never evidence |

**Conclusion.** No legitimate, mechanical and complete capture method exists today.
- A has no Social data.
- B and C are prohibited.
- D is incomplete, and still needs written permission.
- **H042 remains BLOCKED / NOT STARTED.** The methodology is not weakened (no manual or selective capture).

## 4. Recommended next step (owner)

Request **written authorization** from Kalshi; the API docs and Developer Agreement give no specific address, so use Kalshi support or developer relations. The request should cover:
1. Automated read-only capture of public Kalshi Social posts and profile statistics, for a frozen list of roughly 25–50 public accounts. Ask for an official endpoint or feed if one exists or is planned.
2. Storage of that content, plus contemporaneous public market data, in a private research database. **No redistribution.**
3. AI-assisted analysis of it.
4. Clarification of whether the same research use of **public market data** (order books, trades, settlements) is permitted under Developer Agreement §3/§3.1/§3.5, which limits API use to "facilitating a member's own trading".

## 5. Compliance flag beyond H042 (for the owner; nothing changed)

The same clauses bear on the existing UltraCode research collectors, M6 and structural_arb. Neither is running. Both are designed to collect, store and aggregate public API market data for research and paper evaluation, with AI-assisted analysis.

- Whether that counts as "facilitating [the owner's] own trading" (Developer Agreement §3/§3.1), and how the Data Terms' AI/ML clause applies, is a **legal and terms interpretation I cannot make**.
- I have **not** changed or stopped anything.
- I recommend resolving it, ideally within the same written request to Kalshi, **before any START** of M6 or structural_arb, and before any H042 collection.
- H038/H039 were not inspected.
