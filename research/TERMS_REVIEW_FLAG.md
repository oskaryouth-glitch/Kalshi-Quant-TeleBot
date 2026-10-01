# Terms-review flag (cross-workstream). For owner review; no legal conclusion

**Raised:** 2026-10-01, during the H042 access audit (`research/social_tailing/ACCESS_AUDIT.md`).

**What was found.** Kalshi's own terms documents, from its public regulatory bucket:

| document | sha256 | Last-Modified |
|---|---|---|
| Kalshi Developer Agreement v1.1 (`kalshi-public-docs.s3.amazonaws.com/Kalshi-Developer-Agreement.pdf`) | `9d3e33685c0f0a88d23895685107975b0745283aac96f8bf7d202f5ae4dc1fa6` | 2023-11-09 |
| Kalshi Data Terms of Use (`kalshi-public-docs.s3.amazonaws.com/kalshi-data-terms-of-service.pdf`) | `d19a0f94ffd65aa51eccb80cc8c9a06fb842478c5bf4cbd5a31ec51dd0a3966f` | 2024-09-11 |

The verbatim clauses are quoted in `research/social_tailing/ACCESS_AUDIT.md` §2:
- Developer Agreement §3, §3.1 and §3.5: API use limited to "facilitating a members own trading"; restrictions on collecting, caching, aggregating and storing; restrictions on "benchmarking or competitive purposes".
- Data Terms §I and §II: personal non-commercial use; prohibitions on automated access, compilation and text-and-data mining without prior written permission; prohibition of use of Kalshi Data in connection with AI/ML.

Whether the bucket copies are the current versions could not be confirmed: kalshi.com is behind a bot checkpoint.

**Why it is flagged.** Several UltraCode research designs collect, store and analyse public Kalshi market data with AI assistance for paper evaluation:
- M6 (frozen manifest `5dcb3af7…`, not started);
- structural_arb (manifest `456eafb5…`, not started);
- the edge_search price tests.

How these clauses apply to them, and to H038/H039 (not inspected), is a **legal and terms question I cannot decide**.

**What was NOT done.**
- No legal conclusion is drawn.
- No experiment was started, stopped, modified or invalidated on the basis of this flag.
- M6, structural_arb, H038, H039, H040 and H041 are untouched.

**Suggested handling (owner's decision).**
- Review the clauses, ideally with counsel.
- Consider asking Kalshi for written clarification. Item 4 of the H042 draft request (`research/social_tailing/AUTHORIZATION.md`) covers research use of public market data generically.
- Resolve this before any START decision you consider affected.
