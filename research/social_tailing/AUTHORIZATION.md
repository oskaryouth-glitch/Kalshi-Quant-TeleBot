# H042: authorization required to unblock collection, and a DRAFT permission request (NOT SENT)

**Status:** H042 is BLOCKED / NOT STARTED.
- Nothing has been sent to Kalshi.
- The draft below is for the owner to review, edit and send, or not, at their discretion.
- The basis is `ACCESS_AUDIT.md`: Kalshi Data Terms of Use §I–II and Developer Agreement v1.1 §3, from Kalshi's public regulatory bucket. The sha256 of each document is recorded there.

## G. What authorization H042 needs (all of it, in writing)

| # | need | why (governing clause) | minimum capability for a valid test |
|---|---|---|---|
| 1 | Automated, read-only capture of public Kalshi Social posts and profile information, for a fixed research sample (about 30–50 accounts), **or** an official Social API/feed | Data Terms §II prohibit scripts, robots and "other devices or mechanisms" to access or retrieve the Website without prior written permission; the documented API has no Social data | Every public post of each listed account (complete, not sampled). Platform post id and exact post timestamp. Structured position fields (ticker, side; ideally the trader's average price, entry time and size). The ability to re-fetch a post to detect edits and deletions. A poll or push latency of seconds to a few minutes |
| 2 | Private storage of the captured dataset (append-only, research only, no redistribution) | Data Terms §II (collecting, copying, compiling into databases); Developer Agreement §3.1 (collecting, caching, aggregating, storing) | Retention for the study and its audit trail |
| 3 | Quantitative analysis, **including AI-assisted analysis**, of the captured data | Data Terms §II expressly prohibit use of Kalshi Data in connection with AI/ML "to generate any information" | Statistical analysis and reporting by the owner, assisted by an AI coding/analysis tool |
| 4 | Use and storage of public market data (order books, market/event/series objects, trades, fee schedules, settlements) from the Trade API for **non-commercial private research**, in addition to the owner's own trading | Developer Agreement §3 ("expressly limited to facilitating a member's own trading"), §3.1 (storage), §3.5 ("benchmarking or competitive purposes") | Order-book snapshots at detection time, plus settlement, for paper-fill evaluation |
| 5 | Whether an official Social API or feed exists or can be provided, and its rate limits | Determines the capture design (§4 of the spec) | — |

**If Kalshi grants only part of this:**
- Without (1) or (5), H042 stays **BLOCKED**.
- Without (2), (3) or (4), H042 stays **BLOCKED**: the study cannot be run or analysed.
- If the granted feed lacks exact post times or structured positions, the spec's timing classification (§6) and capture procedure (§4) must be amended **before** freeze. If structured positions are unavailable, a valid primary test may be impossible.

---

## H. Draft permission request (NOT SENT, owner to review)

> **Subject:** Request for written authorization: non-commercial research on Kalshi Social posts and public market data
>
> Hello Kalshi team,
>
> I am a Kalshi member *[account email / member ID]*. I would like to run a small, **non-commercial, private research study**. It measures whether publicly posted Kalshi Social positions could have been followed at realistic prices: a follower entering only after a post becomes visible, at the then-available order book, paying fees, holding to settlement.
>
> The study is paper-only. It places no orders or quotes, uses no other members' private data, and redistributes nothing. Your Data Terms of Use and Developer Agreement restrict automated access, storage and AI-assisted analysis without prior written permission, so I am asking whether you can authorize the following:
>
> 1. **Read-only automated capture of public Kalshi Social posts and profile information** for a fixed research sample of roughly 30–50 public accounts, at a rate you specify. If an official Social API or feed exists or could be provided, I would much prefer to use it.
> 2. **Private storage** of that research dataset (append-only, retained for the study and its audit trail, not shared or published in raw form).
> 3. **Quantitative analysis of the captured data, including with AI-assisted analysis tools**, for the study only.
> 4. **Use and storage of public market data** from the Trade API (order books, market/event/series data, trades, fee schedules, settlement results) for this non-commercial private research, in addition to my own trading.
> 5. **Whether an official Social API or feed exists** (or is planned), what it returns (post ids, exact post timestamps, structured position details) and any rate limits.
>
> I will follow any conditions you set: rate limits, scope, retention, attribution, or a review before any public statement, as Developer Agreement §6.4 requires. If this request should go to a different team, I would appreciate a pointer.
>
> Thank you,
> *[name]*
> *[contact email / phone]*

**Notes for the owner before sending:**
- Insert your member details.
- Decide whether to mention the other UltraCode market-data research (M6 and structural_arb) explicitly. Item 4 covers it generically.
- Keep Kalshi's written reply with this repository's H042 records, as the authorization evidence for the freeze.
