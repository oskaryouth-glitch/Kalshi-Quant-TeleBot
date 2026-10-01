# H042: candidate discovery notes (design evidence only; NOT data)

**Status:** H042 is BLOCKED / NOT STARTED.
- These notes come from the owner's **manual inspection** of public Kalshi Social profiles before any H042 access was authorized.
- They are **discovery and design evidence only**.
- **No post, position, price or outcome from that inspection is part of, or may ever be ingested into, the H042 prospective dataset.**

## Accounts identified as potential candidates

The order is arbitrary (as supplied). **This is not a profitability ranking, and no account is inferred to have a tail-able edge.**

1. `@wightsurfer10`
2. `@Hidden.Edge`
3. `@cwilltennis`
4. `@extended.gopher1494`
5. `@SirHenryLama`
6. `@PureVictoryPick`
7. `@ActionAdvisorsHQ`
8. `@tony.plush`
9. `@LostAcrossAmerica99`

In the draft account-selection procedure (`H042_SPEC_DRAFT.md` §5) they form stratum S0, "owner-nominated", which is tracked separately so that their selection effect can be analysed. Inclusion in the frozen manifest still requires the eligibility rules there, checked through authorized access at freeze time.

## Methodological lessons (each is a design requirement, not a claim about an account)

Statements attributed to commenters are **unverified** and are **not** recorded as facts about any account. They are noted only because they show a failure mode the design must handle objectively.

| observed in manual inspection | design requirement it motivates | where in the spec |
|---|---|---|
| A large displayed profit with relatively few trades; some visible positions *appeared* retrospective, and a commenter alleged that wins were sometimes posted after the fact (unverified) | Post timing must be **objectively classified** from timestamps and public price history only, never from the outcome | §6 timing classification; §11.7 Prospective Disclosure Rate |
| An account stated it remained negative lifetime and advised against blind tailing; comments asked why positions weren't posted earlier | **Trader performance ≠ follower-available performance**: the follower is evaluated only at post-detection prices | §9 fill; §11 estimands |
| Many posts and single-market sports positions; comments questioned whether picks are posted before winning (unverified) | The same objective timing classification; **no dropping of posts**; the PDR is reported per account | §6, §11.7 |
| Both wins and losses visible, but the same economic position appeared to be referenced in several posts; the account also points users to external pick services | **SOCIAL POST ≠ SIGNAL ≠ ECONOMIC POSITION**: posts must be clustered. **Only authorized Kalshi Social data** is evaluated; external channels are out of scope unless a future protocol freezes them | §7 IDs and clustering; §2 scope |
| A specialist pattern: weather/climate positions with contemporaneous-looking reasoning while markets were live | Discovery must not be a lifetime-profit leaderboard pick; there is a **specialist stratum** | §5 strata |
| Heavy focus on large combos ("lottery tickets"), with uncertainty openly acknowledged | Combos are **excluded from the primary follower-ROI test**, and descriptive only | §3 population |
