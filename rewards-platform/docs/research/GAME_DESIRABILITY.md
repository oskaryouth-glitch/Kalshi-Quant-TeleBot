# Research area: game desirability

**Status:** research design (2026-10-04). Nothing here is built or shown to users.
**Hypothesis owner:** founders. **Decision refs:** D-021, D-022, D-023.

## 1. Question

Does the attractiveness of the _underlying game_ change offer completion and user value enough that
we should optimize the **game + reward combination**, rather than the reward alone?

Founder intuition: a $30 reward on an excellent game may outperform a $50 reward on an unpleasant
grind.

## 2. Key insight: desirability is already inside expected value

The brief's expected payout is

```
E[payout] = Σ_k P(reach milestone k) × reward_k
```

If a game is enjoyable, more people keep playing, so P(reach k) is higher at every depth. So we do
**not** need a separate "fun score" to optimize the combination: once measured, expected earnings
already rank a well-liked $30 game above a grindy $50 game **if** the completion data says so. Our
revenue has the same shape (Σ P(reach k) × publisher_payout_k), so user value and our economics point
the same way.

Desirability adds two things on top:

1. **A cold-start prior.** Before we have completion data for a game, external signals may predict
   P(reach k). That is a testable hypothesis, not an assumption.
2. **Enjoyment itself.** Time spent in a game the user enjoys costs them less than time in one they
   dislike. Only users can tell us that (self-report), and it should be displayed as what it is
   ("players rated this game"), never folded into a dollar figure.

**Rule (D-021):** no composite "fun score". We store and, where legitimately allowed, display
individual signals with their source, scale, sample size and date. Any model that combines them is
internal, versioned and validated against outcomes before it influences ranking.

## 3. Candidate signals

Legend: **Avail.** = when we could have it. **Legit.** = legitimacy and licensing status.

### External (could exist before we have users)

| Signal                                              | Source options                                                                                                                                                                                                                                   | Avail.           | Legit. / caveats                                                                                                                                    |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Store rating + rating count (Android)               | No official Google API for apps you don't own (CONFIRMED via third-party summaries of the Play Developer API scope). Options: licensed data vendors (e.g. Appfigures, AppMagic, Sensor Tower, 42matters), or provider catalog fields if exposed. | E002 if licensed | Scraping Google Play is a ToS and legal risk; **do not scrape**. Vendor pricing and display rights are UNKNOWN.                                     |
| Store rating + count (iOS, as cross-platform proxy) | Apple iTunes Search/Lookup API: public, no key, returns `averageUserRating`, `userRatingCount`, `primaryGenreName`; about 20 calls/min (CONFIRMED via secondary sources)                                                                         | E002             | Need to review Apple's terms for this API before using it; iOS ratings are only a proxy for Android experience; needs cross-platform game matching. |
| Install range ("1M+")                               | Shown publicly on Play listings; vendors                                                                                                                                                                                                         | E002 if licensed | Coarse buckets; same no-scraping rule.                                                                                                              |
| Chart rank / popularity trend                       | Licensed vendors                                                                                                                                                                                                                                 | Post-E001        | Paid. Useful for "popular games that pay".                                                                                                          |
| Genre / category                                    | Provider catalog (if exposed), store category via vendor or iOS API                                                                                                                                                                              | E002             | Low risk.                                                                                                                                           |
| Publisher / studio                                  | Provider catalog, store listing                                                                                                                                                                                                                  | E002             | Low risk. Studio reputation is a weak prior.                                                                                                        |
| Release date, update recency                        | Vendor / iOS API (`currentVersionReleaseDate`)                                                                                                                                                                                                   | E002             | Abandoned games correlate with tracking problems (hypothesis).                                                                                      |
| Content rating; **simulated gambling** flag         | Store content rating (IARC), genre                                                                                                                                                                                                               | E002             | See D-023: social-casino games conflict with our positioning.                                                                                       |
| Provider-claimed EPC / conversion rate              | Provider catalog                                                                                                                                                                                                                                 | E002             | Provider-claimed, not ours; stored with as-of; never displayed as our data.                                                                         |

### Internal (only after launch)

| Signal                     | Definition                                                                                                                        | Notes                                                                       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Card → detail rate         | detail opens ÷ card impressions                                                                                                   | Interest; confounded by reward size and position. Log position.             |
| Detail → start rate        | click-outs ÷ detail opens                                                                                                         | Decision after seeing full terms. A drop here may signal off-putting terms. |
| Activation                 | P(first milestone \| started)                                                                                                     | Strongest early desirability signal; first milestones are usually easy.     |
| Milestone survival curve   | Kaplan–Meier P(reach k), per game × terms version                                                                                 | Core input to expected earnings.                                            |
| Elapsed days to milestones | Per D-015 (calendar days, not play time)                                                                                          |                                                                             |
| Abandonment point          | Last milestone reached before inactivity                                                                                          | Where the grind bites.                                                      |
| Post-offer feedback        | Two optional questions after a user stops or finishes: "Did you enjoy the game?" (1–5) and "Was the offer worth your time?" (1–5) | Response bias; show n; never incentivize ratings.                           |
| Missing-credit claim rate  | Claims ÷ starts                                                                                                                   | Tracking quality, not fun; keep it separate.                                |
| Repeat engagement          | Started another offer within 30 days                                                                                              | Product-level retention; partly attributable to game experience.            |

## 4. Methodology pitfalls (must be handled before any claim)

1. **Confounding by payout design.** Advertisers set payouts from their own LTV and funnel
   economics. Deep, hard milestones pay more. Popular games may pay _less_ per milestone because
   their organic installs are cheap (hypothesis H-GD3). A raw "payout vs completion" correlation
   therefore mixes desirability with difficulty. Compare at matched milestone depth (e.g.
   P(reach first milestone)), or model reward and depth explicitly.
2. **Self-selection.** Users pick games they already like, so completion is conditional on choice.
   That is fine for "what works for people who choose this", but not for causal claims.
3. **Position and presentation effects.** Card order changes clicks. Log positions and randomize
   order in a holdout before inferring desirability from clicks.
4. **Small samples per game.** Most games will have few starts. Use hierarchical (partial-pooling)
   estimates by genre if modeling, and keep display thresholds (`MIN_DISPLAY_SAMPLE`).
5. **Terms changes.** A game with new milestones is a new offer version (ARCHITECTURE 2.3).

## 5. Hypotheses

| ID    | Hypothesis                                                                                                                | First test                                                                                                                           | Data needed                                  |
| ----- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| H-GD1 | Among offers with similar first-milestone reward, games with higher store rating and rating volume have higher activation | Post-launch, within E003/E005                                                                                                        | Internal activation + external ratings       |
| H-GD2 | Users choose a lower reward on a better-liked game over a higher reward on a weaker game                                  | **Pre-launch stated-preference survey** of the waitlist (paired choices with fictional offers), then post-launch revealed preference | Survey responses; later click and start logs |
| H-GD3 | Popular games pay less per milestone than less popular games                                                              | **E002** (catalog + external signals)                                                                                                | Payout ladders + rating volume / installs    |
| H-GD4 | External signals predict P(reach k) well enough to be a cold-start prior                                                  | Post-launch, after ≥ N games have completion data                                                                                    | Survival curves vs signals                   |
| H-GD5 | Recently updated games have fewer missing-credit claims                                                                   | Post-launch                                                                                                                          | Claims + update recency                      |

## 6. Discovery categories: requirements and gates

Categories are **filters with explicit definitions**, not opaque rankings. None ships before its
gate. No category uses a composite score.

| Category                                       | Definition                                                                                                      | Data source                       | Gate before shipping                          | Notes                                                                                                                                                                                                                                                                |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **No purchase needed**                         | `purchase = none`                                                                                               | Provider catalog                  | Launch                                        | Pure filter. Safe.                                                                                                                                                                                                                                                   |
| **Biggest rewards** (founders' "Best rewards") | User-selected sort by total available **without purchases**, labeled as such                                    | Provider catalog                  | Founder decision + Trust page update          | ⚠ Tension: the Trust page says we will not rank by maximum possible total. Acceptable only as an opt-in sort (never the default) with an explicit label; the Trust copy must say so. "Best" implies a quality judgment we cannot support, so we recommend "Biggest". |
| **Popular games that pay**                     | Games above a disclosed popularity threshold (e.g. rating count or install range) from a named, licensed source | Licensed vendor or provider field | License permits display; source named in UI   | Never "popular on our site" until internal volume clears thresholds.                                                                                                                                                                                                 |
| **Quick wins**                                 | Measured: median elapsed time to first reward ≤ X, with n ≥ threshold                                           | Internal outcomes                 | Outcome data with display thresholds          | Before data, the only honest variant is structural, "First reward at install or tutorial" (from milestone 1 terms). It makes no speed claim.                                                                                                                         |
| **Highest expected earnings**                  | Sort by displayable expected earnings                                                                           | Internal                          | Estimates displayable for most of the catalog | This is the long-term default ranking.                                                                                                                                                                                                                               |

## 7. Acquisition concept: "Already thinking about downloading this game? Start through us and get paid."

**Idea:** capture high-intent users who are about to install a specific game, for example through
per-game landing pages ("Get paid to play {Game}") and search.

**Why it is attractive:** high intent means low CAC; it fits "popular games that pay"; it is
honest (the user wanted the game anyway).

**Material risks, possibly blocking:**

1. **Advertiser incrementality.** Advertisers pay CPI/CPE to acquire players they would _not_
   otherwise get. Intercepting users who were going to install anyway is exactly what many
   advertisers try to exclude. Campaign terms commonly restrict **brand-name keywords and branded
   traffic** (approval question 11). Violations can mean rejected conversions or account
   termination. **INFERENCE:** this is likely restricted on many campaigns. Requires written,
   per-campaign answers.
2. **Trademark use.** Using game names on our pages is likely nominative, but advertiser or
   provider terms may prohibit it regardless. Use no logos or artwork without permission.
3. **New-user eligibility.** People who have "already been thinking" may have installed before.
   They must be told up front that prior installs void the offer (already an eligibility item in
   the offer detail; a pre-start "installed before?" prompt is a planned product step).
4. **Catalog volatility.** Campaigns end. A page for a game whose offer ended must say so
   immediately and not imply availability (SEO pages must be data-driven, not static promises).

**Recommendation:** treat it as hypothesis H-ACQ1. Add per-campaign traffic permissions to the
schema (ARCHITECTURE 2.9) so branded or search traffic can be gated per campaign. Test only on
campaigns that explicitly permit it.

## 8. What E002 should add (no users required)

For every eligible game in the catalog snapshot:

1. Match to store ID (Android package) and, where possible, to an iOS app ID for cross-platform
   signals.
2. Record available external signals with source, retrieved_at and license reference (no
   scraping).
3. Report **coverage**: share of games with each signal.
4. Report the **payout vs popularity** relationship (H-GD3) at matched milestone depth.
5. Report the **share of catalog that is simulated gambling / social casino** (input to D-023's
   supply impact).
6. Draft and pilot the H-GD2 stated-preference survey (waitlist; requires the email provider and a
   privacy-policy update first).
