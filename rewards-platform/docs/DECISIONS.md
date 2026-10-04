# Decision log

Append-only. Each entry: date, decision, alternatives, reason, evidence, revisit condition, status.
Status is one of **ADOPTED** (in effect), **PROPOSED** (needs founder sign-off; built in a way that is
easy to reverse), or **SUPERSEDED** (link to replacement).

Entries marked _needs founder sign-off_ touch positioning, business model or partner relations and
were made only to the degree required to ship the pre-approval shell.

---

## D-001 — Build the shell in an isolated `rewards-platform/` directory of the current repo

- **Date:** 2026-10-04 · **Status:** ADOPTED (temporary)
- **Decision:** The assigned repository (`Kalshi-Quant-TeleBot`) contains an unrelated Kalshi
  trading Telegram bot. The rewards shell lives entirely in `rewards-platform/`, with no changes to
  existing files.
- **Alternatives:** (a) delete the bot code and take over the repo root, which is destructive and
  needs explicit approval; (b) create a new repository, which needs an external account action.
- **Reason:** Non-destructive, and it unblocks work on the assigned branch.
- **Evidence:** `git log` shows only Kalshi bot history; root `.gitignore` contains Python rules
  (including `lib/`, which had to be re-included in `rewards-platform/.gitignore`).
- **Revisit when:** The founders create a dedicated repo. Move with history via
  `git subtree split --prefix=rewards-platform -b rewards-platform-only`, then push that branch.

## D-002 — Stack: Next.js 16 (App Router) + TypeScript + Tailwind CSS v4

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Alternatives:** Astro (excellent for static marketing, weaker fit for the later authenticated
  app, postback endpoints and ledger); Remix/React Router (good, but no advantage here); plain
  HTML (no path to the platform).
- **Reason:** Every page here is static, but the next phases need server endpoints (postbacks,
  catalog jobs) and an authenticated app in the same codebase and type system. Server Actions give
  a no-JS-capable form with built-in CSRF origin checks. Tailwind v4 keeps design tokens in CSS and
  adds no runtime.
- **Dependencies (each justified):** `zod` (input validation, to be reused for postback and catalog
  parsing), `postgres` (small, dependency-free driver; Postgres is the likely ledger DB anyway).
  Dev: `vitest`, `@playwright/test`, `@axe-core/playwright`, `prettier`. Nothing else.
- **Revisit when:** Never for the shell. Re-evaluate hosting/runtime when building postback
  ingestion (needs durable queues, not just serverless functions).

## D-003 — Lead positioning: "Know what a game reward takes before you start."

- **Date:** 2026-10-04 · **Status:** SUPERSEDED by D-019 (founder direction correction, 2026-10-04)
- **Alternatives considered:** "Find the games actually worth playing for money." (brief);
  "Know which rewards are actually worth your time." (brief).
- **Reason:** Both brief options promise a judgment of _worth_ that requires outcome data we will
  not have at launch, and possibly not for months (EXPERIMENTS E003+). Standardized up-front
  disclosure is something we can honestly deliver on day one with provider data alone. The
  headline promises what is true now; "worth it" becomes the promise once data supports it.
- **Evidence:** No outcome data exists. Provider catalog fields (milestones, deadlines, purchase
  flags) are reportedly available from several networks (founder research; unverified, see
  PROVIDER_REGISTRY.md).
- **Revisit when:** Outcome-based estimates pass their display thresholds for a meaningful share
  of the catalog.

## D-004 — Working brand name "Worthplay"

- **Date:** 2026-10-04 · **Status:** OPEN (founders, 2026-10-04: do not lock "Worthplay" because it is in the implementation; run the naming process in docs/NAMING_PROCESS.md)
- **Decision:** A real-sounding working name so the site can be evaluated. It is defined once in
  `src/lib/site-config.ts` with `nameStatus: "working"`, and `npm run check:launch` fails until it is
  set to `"cleared"`.
- **Evidence:** One web search (2026-10-04) found only an older Spanish academic research project
  called "WorthPlay" (games for older adults). **This is not trademark clearance.** USPTO/state
  searches and domain/handle availability have not been checked.
- **Revisit when:** The founders choose a name, or before any public launch or publisher application.

## D-005 — Visual direction "Scorecard"

- **Date:** 2026-10-04 · **Status:** ADOPTED, amended by D-019 (tokens and type kept; the Offer Facts label is no longer the hero motif)
- See DESIGN_SYSTEM.md for the three directions considered and how they scored.

## D-006 — No outcome-based numbers until measured; fixtures are illustrative-only by type

> Amended by D-019: the fixture now lives in `src/lib/fixtures/illustrative-offers.ts`, and outcome
> fields are hidden rather than shown as "Not enough data yet".

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Decision:** The only offer data in the codebase is `src/lib/fixtures/illustrative-offer.ts`. Its
  type has `provenance: "illustrative"` and no "live" variant exists, so the label always renders
  a visible "Illustrative example · Fictional game · not a real offer" banner. All outcome fields
  are `insufficient-data`. The `estimate` variant requires `sampleSize` and `estimatorVersion`.
- **Reason:** Founder rule. Also, fabricated precision is the fastest way to lose the trust thesis.
- **Revisit when:** Real catalog data exists. Add a `provider` provenance with snapshot ID and
  retrieval time; outcome estimates need the thresholds in EXPERIMENTS.md.

## D-007 — No placeholder company or contact facts; env-driven with a launch gate

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Decision:** Legal entity, jurisdiction, address and contact emails come from env vars. When
  missing, the UI says "not yet published" rather than showing a plausible fake (e.g.
  `hello@example.com`). `scripts/launch-check.ts` lists every blocker.
- **Revisit when:** Never. Wire `npm run check:launch` into the production deploy.

## D-008 — Waitlist: minimal fields, Postgres, fail closed

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Decision:** Collect email, phone platform, optional note, 18+ confirmation, optional `?ref=`
  source, plus privacy-policy version and timestamp. Postgres is selected when `DATABASE_URL` is
  set. In development without a DB, an in-memory store is used. **In production without a DB, the
  page says sign-ups are not open yet** instead of accepting data it cannot keep.
- **Alternatives:** Third-party form/list tools (send PII to another processor, need an account,
  and fewer controls); collecting a name (not needed).
- **Not done (deliberately):** Double opt-in email confirmation, which needs an email provider (an
  external account). Until then the list may contain mistyped or unverified addresses; treat
  counts as upper bounds in E004.
- **Revisit when:** An email provider is chosen. Add double opt-in, then update the privacy policy
  with the processor's name.

## D-009 — Light theme only for the shell

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Reason:** Halves visual QA for a marketing site. The trust aesthetic is built on warm paper.
- **Revisit when:** Building the logged-in app, where dark mode is a reasonable expectation.

## D-010 — CSP without nonces (`'unsafe-inline'` scripts)

- **Date:** 2026-10-04 · **Status:** ADOPTED (temporary)
- **Reason:** Nonce CSP forces dynamic rendering of every page in Next.js. SRI support is
  experimental. The shell has no user-generated content, no third-party scripts and no auth, so
  the XSS surface is minimal. `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'` and
  `form-action 'self'` are enforced.
- **Revisit when:** Before adding accounts, balances or any authenticated surface. Move to nonces
  (via `proxy.ts`) or SRI.

## D-011 — No analytics in the shell

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Reason:** It's the strongest privacy position, keeps the privacy policy simple, and lets the
  site say "no tracking cookies" truthfully (verified by e2e). The waitlist `?ref=` tag and
  platform split give the first E004 signal.
- **Revisit when:** E004 needs landing-page conversion rates. Use cookieless first-party analytics
  and update the privacy policy _before_ shipping it.

## D-012 — Partner contact via `mailto:`, not a form

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Reason:** A form without notification infrastructure lets partner leads rot silently. Partner
  managers expect email anyway.

## D-013 — Never name offer networks or competitors on public pages

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Reason:** Naming a network, even neutrally, can imply a relationship (founder public-claim
  rules). It is enforced by the copy guard (`src/lib/copy-guard.ts`) on source and rendered text.
  Internal docs may name them.

## D-014 — Tooling pins

- **Date:** 2026-10-04 · **Status:** ADOPTED
- `vitest` 3.2.x: npm 10.9's resolver crashes on vitest 4.x's peer set (`Cannot read properties of
null (reading 'edgesOut')`). `prettier-plugin-tailwindcss` was dropped for the same reason.
- `@playwright/test` 1.56.1 with `overrides.playwright-core` to match the preinstalled Chromium in
  the build sandbox. CI can use any matching browser download.
- `npm audit`: production dependencies report 0 vulnerabilities. The 5 "high" advisories are in the
  ESLint toolchain (`braces` via `eslint-config-next`) and do not ship.
- **Revisit when:** Upgrading npm (≥11) or the toolchain.

## D-015 — Define "time" metrics as elapsed calendar time, not play time

- **Date:** 2026-10-04 · **Status:** RESOLVED by D-042 (founder direction: elapsed days must not substitute for play effort or time)
- **Problem:** The brief's "$/hour" and "estimated effort: 5.2 hours" assume we can measure active
  play time. A web product cannot. Games run in separate apps. We observe click-out time and
  provider-reported milestone timestamps only.
- **Options:** (a) elapsed calendar time to each milestone (observable, honest, labeled "days");
  (b) self-reported play time (biased, low response); (c) a native Android companion app using
  UsageStats (accurate, but heavy permissions, Play Store policy exposure, and it abandons
  web-first); (d) provider-supplied time estimates, if any exist (unknown).
- **Recommendation:** (a) as the primary public metric, (b) as an optional secondary survey with
  its sample size shown, and evaluate (c) as a later experiment. The public site already describes
  time this way (Trust page, "How our numbers will work").
- **Revisit when:** Founders decide on a native companion app, or a provider exposes reliable time data.

## D-016 — Missing-credit disputes are a separate `Claim` entity

- **Date:** 2026-10-04 · **Status:** PROPOSED
- **Reason:** "DISPUTED" cannot be a state of a conversion record that does not exist. The most
  common dispute is _no postback arrived_. See ARCHITECTURE.md "Reward lifecycle".

## D-017 — Partner page discloses multi-network intent and the attribution lock

- **Date:** 2026-10-04 · **Status:** SUPERSEDED by D-043 (founder modification: public copy stays general; routing questions go private)
- **Decision:** The partner page says "If we work with more than one network, each user's attempt
  at an offer is attributed to exactly one network, chosen before they start."
- **Alternatives:** Say nothing about multi-network routing.
- **Reason:** Networks will discover it anyway (approval question 5–7). Framing it as attribution
  integrity is accurate and addresses their real concern (double attribution). Concealing it risks
  termination later.
- **Risk:** Some networks may decline publishers that route between competitors. That is exactly
  what E001 needs to learn early.
- **Revisit when:** Partner conversations show this framing hurts approvals.

## D-018 — Locked routes are locked at first click-out, not at install

- **Date:** 2026-10-04 · **Status:** PROPOSED
- **Reason:** We cannot observe installs. Once a user clicks a provider's tracking link, that
  provider may attribute the install for its whole attribution window. Locking at click-out is the
  only safe point. An attempt may be manually unlocked only after that provider's attribution
  window expires with no conversion, and the unlock is recorded.

## D-019 — Homepage leads with earning; disclosure moves to the offer detail (progressive disclosure)

- **Date:** 2026-10-04 · **Status:** ADOPTED (founder direction, with the refinements below)
- **Context:** Founders judged that the hero had overcorrected toward disclosure. The Offer Facts
  table read like a financial disclosure and made the product feel like work before it was
  appealing. New hierarchy: attraction → selection → transparency → tracking. Target feel:
  about 75% financial-product trust and 25% gaming/rewards energy.
- **Decision:**
  1. Hero headline "Play new games. Get paid as you progress." Alternatives considered: "Play
     games. Earn real money." (strongest pull, but the cash claim is unverified: every provider is
     `cash_reward_allowed: UNKNOWN`); "Find games worth playing." (differentiated but ambiguous,
     weak pull); "Get paid to play new games." (clear but generic); "New games. Real rewards. No
     surprises." (punchy, but the promise is broad). The chosen line states the value and the
     mechanism (milestones) truthfully.
  2. The hero preview is a marketplace: a featured offer card plus compact rows, with original genre
     artwork and the reward amount as the most prominent element.
  3. **Card headline rule** (`src/lib/offers/summary.ts`, unit-tested): measured expected earnings
     lead once displayable (n ≥ `MIN_DISPLAY_SAMPLE`, estimator version present), with the maximum
     secondary. Until then, the lead is the **total available without purchases**, and totals with
     purchases are secondary. Milestones gated behind a required purchase are excluded from the
     no-purchase total.
  4. Cards show the purchase badge, milestone count and time limit (small). A time limit decides
     whether the headline is reachable, so hiding it would be a material surprise.
  5. Clicking an offer opens the full detail (native modal dialog, with a no-JS fallback to the
     inline example): the milestone ladder with each reward, time limit, purchase rules,
     eligibility, and verification and reversal caveats, all before "Start offer".
  6. Outcome placeholder rows ("typical earnings", "typical days", "tracking record") are removed
     from consumer UI. They return only as measured, displayable estimates.
  7. Trust moves deeper (later homepage sections, /trust) but stays present on every surface.
- **Refinements to the founder direction (and why):** maximum available as the pre-data headline
  would recreate the "up to $X" pattern, so the no-purchase total leads instead. "Real money"
  wording is avoided until cash payouts are confirmed (enforced by the copy guard; see D-020). Real
  game titles and artwork are not used: that would mean trademark use, implied relationships and
  fabricated offers.
- **Evidence:** Competitor review (docs/research/COMPETITORS-2026-10.md), founder review of the
  previous hero.
- **Revisit when:** Real catalog data and artwork permissions exist; expected-earnings estimates
  become displayable; cash payouts are confirmed.

## D-020 — Copy guard blocks unconfirmed payout and cash claims

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Decision:** "real money", "real cash", PayPal, Venmo and Cash App are banned in public copy
  (source and rendered).
- **Reason:** No provider has confirmed cash-equivalent rewards in writing, and payout rails are
  not chosen. Competitors lead with these phrases, and we cannot yet say them truthfully.
- **Revisit when:** A provider is `cash_reward_allowed: YES` with stored evidence **and** a payout
  method is contracted. Then remove the pattern in `src/lib/copy-guard.ts`.

## D-021 — Game desirability is measured from raw, sourced signals; no composite "fun score"

- **Date:** 2026-10-04 · **Status:** ADOPTED, amended by D-029 (enjoyment kept conceptually separate from expected earnings)
- **Decision:** Desirability is a first-class research dimension for E002 onward
  (docs/research/GAME_DESIRABILITY.md). Signals are stored individually with source, scale, sample
  size, retrieval date and license. Any combining model is internal, versioned and validated
  against outcomes before it affects ranking. In ranking, desirability is expressed through
  **measured completion probabilities**, i.e. expected earnings. A $30 offer on a well-liked game
  outranks a $50 grind only when completion data shows users actually earn more on it.
- **Alternatives:** an editorial or algorithmic fun score (rejected: unfalsifiable, invites
  fabricated precision); ignoring the game (rejected: likely the main driver of completion).
- **Revisit when:** Enough completion data exists to test H-GD1 and H-GD4.

## D-022 — Discovery categories are defined filters with data gates

- **Date:** 2026-10-04 · **Status:** ADOPTED (reviewer approved 2026-10-04 and re-confirmed: "Biggest rewards", not "Best", until outcome data supports a quality or recommendation ranking; a personalized "Recommended" default ranking may come later, only once justified by real data)
- **Decision:** "No purchase needed" can ship at launch. "Popular games that pay" needs a licensed,
  named popularity source. "Quick wins" needs measured time-to-first-reward (the only pre-data
  variant is the structural "First reward at install or tutorial"). The founders' "Best rewards"
  becomes **"Biggest rewards (without purchases)"**, an opt-in sort that is never the default.
- **Reason:** "Best" implies a quality judgment we cannot support. A default max-reward sort would
  contradict the Trust page. If the opt-in sort ships, the Trust page copy must be updated to
  describe it.

## D-023 — Exclude simulated-gambling (social casino) games from the consumer catalog

- **Date:** 2026-10-04 · **Status:** SUPERSEDED by D-027 (reviewer modified: segment in E002 and decide later)
- **Reason:** Our public positioning says "not gambling", and competitors' casino offers are part
  of what makes the category look scammy. Many CPE offers are social casino games (INFERENCE), so
  exclusion has a supply cost that E002 must measure (share of catalog and of payout volume).
- **Revisit when:** E002 shows the exclusion makes supply inadequate.

## D-024 — Referral rewards: single-level, conversion-qualified, policy-versioned, counted as CAC

- **Date:** 2026-10-04 · **Status:** ADOPTED (as design constraints; nothing built)
- **Decision:** A referrer earns only when a directly referred user produces a provider-approved
  qualifying conversion that clears the reversal window. One level. No buy-in. No rewards for
  recruiting recruiters. Amounts come from a versioned `referral_policy` frozen at link time,
  capped per referrer. Referral rewards and welcome bonuses are acquisition cost in contribution
  margin. Correction to the founders' illustration: gross spread is $12 and the $2 referral reward
  is CAC (docs/research/REFERRAL_AND_AMBASSADORS.md §2).
- **Gate:** no referral feature before launch, written provider permission (Q27–29) and counsel
  review. Offers from providers that disallow referral traffic are hidden from referral-acquired
  users (`acquisition_channel` × `allowed_traffic_sources`).

## D-025 — Campus ambassadors: voluntary individuals only; no organization payouts; never paid per signup pre-launch

- **Date:** 2026-10-04 · **Status:** SUPERSEDED by D-028 (reviewer approved the anti-coercion guardrails and allowed conversion-based compensation)
- **Decision:** Ambassadors participate as individuals (18+, written terms, code of conduct, FTC
  disclosure). We do not pay fraternities, sororities, clubs, teams or dorms based on member
  participation. No quotas, leaderboards or group competitions. Pre-launch ambassadors are unpaid
  or receive a flat stipend for time, never a per-signup bounty. They link only to our site.
- **Reason:** Organization-level incentives create pressure on members (coercion and hazing
  adjacency). Per-signup pay rewards non-economic activity and junk signups. Direct provider links
  risk sub-publisher violations.
- **Test:** EXPERIMENTS E008.

## D-026 — "Already downloading this game?" acquisition is gated per campaign

- **Date:** 2026-10-04 · **Status:** ADOPTED, amended by D-030 (channel-dependent, not globally blocked; general channel matrix)
- **Decision:** No branded or search-intent acquisition (per-game pages or ads naming the game)
  except on campaigns whose terms explicitly permit it in writing (Q11, Q31). The schema carries
  per-campaign `allowed_traffic_sources`. Per-game pages must be data-driven and say immediately
  when an offer has ended.
- **Reason:** Advertisers pay for incremental players. Intercepting users who would install anyway
  is commonly restricted (INFERENCE), and violations risk rejected conversions and account loss.

## D-027 — Social-casino games are an E002 segmentation question, not an exclusion (supersedes D-023)

- **Date:** 2026-10-04 · **Status:** ADOPTED (reviewer decision)
- **Decision:** Do not exclude social-casino games yet. Classify every game (standard / social
  casino / sweepstakes-style casino / real-money gambling) and quantify the social-casino segment
  separately in E002: inventory share, payouts, purchase requirements, and later completion and
  economics. **Real-money gambling stays out of scope** and is never listed. Inclusion or exclusion
  is decided after evidence plus legal and provider review.
- **Engineering recommendation (not yet a decision):** treat sweepstakes-style casinos (redeemable
  prizes) as out of scope until counsel clears them, since their legal status varies by state.
- **Follow-ons if included:** re-review the "Is this gambling?" FAQ and Trust copy. Add a reviewed
  rule for provider-supplied titles to the copy guard, which currently bans gambling language in all
  public text.

## D-028 — Campus ambassadors: anti-coercion guardrails plus conversion-based compensation (supersedes D-025)

- **Date:** 2026-10-04 · **Status:** ADOPTED (reviewer decision; gated on provider permission and legal review)
- **Decision:** Performance-based compensation is **allowed and is the intended model**. A referrer
  or ambassador is paid only after a **directly referred** user produces an eligible,
  provider-approved economic conversion that clears the reversal window. There is no compensation
  for recruiting recruiters, no downstream commissions, and no mandatory participation, pledging or
  initiation requirements. Voluntary, individual participation, code of conduct, 18+, FTC
  disclosure and the no-quota/no-leaderboard rules remain.
- **Retained and confirmed by founders (2026-10-04, "for now"):** no per-member performance
  payments to _organizations_ (fraternities, sororities, clubs, teams, dorms). Leadership authority over members
  makes this a coercion vector. Changing it needs an explicit founder decision and legal review.
- **Pre-launch:** no conversions exist, so E008 ambassadors are unpaid or receive a flat stipend for
  time, never per waitlist signup.
- **Gate:** written provider permission (Q27–29, Q33), legal review, then E009. No referral
  infrastructure is built before E001, legal review, provider permission and real offer economics
  (D-031).

## D-029 — Enjoyment is separate from expected earnings

- **Date:** 2026-10-04 · **Status:** ADOPTED (reviewer direction)
- **Decision:** Expected earnings come only from observed completion behavior and answer "How much
  will I likely earn?" Voluntary enjoyment ratings, from players who started through us and are
  never incentivized, answer "Will I actually enjoy playing this?" They are displayed separately
  with n, never blended into expected earnings, and high completion is never labeled "fun".

## D-030 — Acquisition channels are enabled per provider and campaign (amends D-026)

- **Date:** 2026-10-04 · **Status:** ADOPTED (design; nothing built)
- **Decision:** "Already thinking about downloading this game? Get paid to start" is
  channel-dependent, not globally blocked. A general **channel permission matrix** (ARCHITECTURE
  2.9) enables each acquisition channel (organic, SEO, game-intent pages and search, referral,
  ambassador, paid social, paid search, influencer) only where provider and campaign terms permit it.
  Resolution: explicit campaign rule > provider default > **deny**. Every allow carries written
  evidence and effective dates. Eligibility checks both the user's sticky acquisition channel and
  the attempt's entry channel.

## D-031 — Sequencing: evidence before referral infrastructure

- **Date:** 2026-10-04 · **Status:** ADOPTED (reviewer direction)
- **Decision:** No substantial referral infrastructure until E001 passes, legal review is done,
  providers grant referral permission in writing, and real offer economics exist (E002). Until then,
  referral work is limited to documentation, metric definitions and the existing aggregate
  `waitlist:report` used by E008.
- **Metric added:** Referral Contribution Margin, compared directly with paid and organic cohorts
  on retention and second-offer rate (EXPERIMENTS "Channel cohort comparison").

## D-032 — College is a distribution wedge, not the product

- **Date:** 2026-10-04 · **Status:** ADOPTED (founder direction)
- **Decision:** The founder's college networks (friends, teams, fraternities, roommates and their
  extended networks) are an initial, low-cost acquisition experiment. **No campus identity in product
  architecture, branding, progression or the long-term thesis.** Referral, ambassador and group
  mechanics must work for any eligible social network.
- **Consequence:** E008 is renamed to an ambassador reach test in founder social networks. Codes use
  `amb_<community>_<id>`. No campus-vs-campus mechanics.

## D-033 — Leaderboards: blanket ban withdrawn; gated research

- **Date:** 2026-10-04 · **Status:** ADOPTED (founder direction, with engineering conditions)
- **Decision:** Replace the "no leaderboards" rule (D-025/D-028 text) with: leaderboards may be
  researched in friend, clan, individual or seasonal scopes. No campus-specific boards. **No cash
  prizes for rank** (contest law and a fraud magnet; LEGAL L14). Rank only on approved qualifying
  dollars. Tested only as variants inside E010/E011.
- **Note:** The live site makes no public promise about leaderboards. The Trust page's "no
  pressure tactics" items (countdowns, fake activity, spins) remain true.

## D-034 — Per-conversion incentive budget across all stacked incentives

- **Date:** 2026-10-04 · **Status:** ADOPTED (design constraint; **strongly approved by founders**, second round 2026-10-04)
- **Decision:** Offer reward + referral share + clan share + progression share ≤ NPR − expected
  variable costs − minimum contribution, enforced at policy-design time and monitored from the
  ledger (`incentive_type` on every entry). Incentives are evaluated jointly, not one layer at a
  time, to avoid attribution double-counting (docs/UNIT_ECONOMICS.md §2–4).
- **Also fixed:** "provider revenue − … − expected reversal loss" double-counts if revenue is
  already NPR. Use NPR and subtract only fraud loss on unrecoverable paid-out rewards.

## D-035 — Clans/groups and progression are hypotheses with required design changes

- **Date:** 2026-10-04 · **Status:** ADOPTED as research direction; **nothing built** (D-031). Amended 2026-10-04: progress unit left **open** (events / reward dollars / weighted activity / E002-derived unit); dollar-based is the lead hypothesis only; required-purchase exclusion approved as default; 3–10 is an initial test hypothesis, not a limit; marginal tiers are a candidate.
- **Clan assessment: MODIFY.** Targets in approved, non-purchase **qualifying dollars**, not
  completion counts. **Purchase milestones excluded** from group progress. Approval-date
  accounting over monthly or rolling four-week periods (weekly visibility), paid after the hold.
  **Social-only arm before cash.** Rewards as **marginal-tier rate × qualifying dollars**, so cost
  scales with value at any size. Targets sublinear in verified active members at the start of the
  period (hypothesis), pending counsel review (L12: recruitment-linked reward risk). Initial size
  hypothesis 3 to about 10. Allocation hypothesis: eligibility + equal share, membership locked per
  period, per-member clawback.
- **Progression:** non-monetary first. Avoid loss-framed streaks and expiring rewards.
- **Experiments:** E010 (clans, cluster-randomized), E011 (progression). Both are post-scale per the
  power notes.
- **Docs:** docs/research/SOCIAL_AND_PROGRESSION.md.

## D-036 — LEGAL-001 established as a formal gate

- **Date:** 2026-10-04 · **Status:** ADOPTED
- **Decision:** docs/LEGAL-001.md is the canonical legal issue register (28 items), with status
  labels CONFIRMED / INFERENCE / HYPOTHESIS / UNKNOWN / COUNSEL REQUIRED. **No real consumer money
  moves** until launch-relevant COUNSEL REQUIRED items are resolved in writing. Only a recorded
  counsel resolution may mark an item cleared. No agent or document may.

## D-037 — Scope freeze: the evidence phase begins

- **Date:** 2026-10-04 · **Status:** ADOPTED (founder direction; engineering concurs)
- **Decision:** No new product scope until E001, LEGAL-001 and E002 produce evidence. Engineering
  work is limited to: launch-readiness items founders request, application support, the repository
  migration, and (once credentials exist) raw-payload capture and catalog analysis for E002.
- **Revisit when:** E001 passes and E002 reports real unit economics.

## D-038 — Referral compensation follows quality, not a declining volume schedule

- **Date:** 2026-10-04 · **Status:** ADOPTED as direction (founder); nothing designed or built
- **Decision:** No permanently declining per-referral rate. Direction: standard rate → measured
  quality → trusted/performance tiers → higher sustainable pay for economically valuable
  acquisition. Signup never qualifies. The qualifying event is chosen after E002, with "cumulative
  approved value within a window, after the hold" as the lead hypothesis and a time-bounded spread
  share as the follow-on candidate. Upgrades use mature, credibility-weighted cohorts. Suspicious
  traffic gets holds and review, not silent cuts. **No personal-play requirement.** High-volume
  referrers move to an affiliate track (contract, tax, disclosure, provider sub-publisher check).
  An internal referrer-quality model may be built later with **no arbitrary weights**, inputs
  validated on real cohorts, and is never shown publicly as a score.
- **Docs:** docs/research/REFERRAL_AND_AMBASSADORS.md §9–13. **Legal:** L29, L30.

## D-039 — Lifetime and seasonal progression are separate hypotheses

- **Date:** 2026-10-04 · **Status:** HYPOTHESIS (founder); nothing built
- **Decision:** Lifetime progression never resets and rewards maintaining one legitimate account.
  Seasonal progression may reset and carries quests and battle-pass-style mechanics. Both are
  tested in E011, use the D-034 budget, and count only provider-approved, post-hold activity.
- **Engineering assessment:** the anti-abuse effect is modest. It deters restarting (ban evasion,
  bonus cycling), not parallel accounts, and monetary milestones can raise farm payoffs. Lean on
  status and perks; identity-gate any cash milestone. Never represented as fraud prevention.

## D-040 — Principle: one legitimate account should become more valuable over time, without lock-in

- **Date:** 2026-10-04 · **Status:** ADOPTED as principle (founder)
- **Decision:** Accumulated value through progression, trust and reputation, tracking history,
  personalization, social ties, referral history and status. **No punitive lock-in:** users can leave
  and withdraw available balances under published terms. Forfeiture only for fraud or terms
  violations, with process and appeal (LEGAL L31).

## D-041 — Incentives are accounted per verified person, not per account

- **Date:** 2026-10-04 · **Status:** ADOPTED (design constraint, when monetary incentives exist)
- **Decision:** Referral eligibility, incentive caps, lifetime milestones and clan membership
  counts resolve to a verified-person entity linking that person's accounts (ARCHITECTURE 2.10).
  Two accounts resolving to one person cannot refer each other. Signals (device, phone, payout
  destination, network, behavior, graph, provider reversals) are combined; no single signal proves
  fraud. Privacy and legal constraints apply (L20, L32, L33).
- **Reason:** the "A refers B" self-referral and the "self-contained household" across
  referrals, clans and lifetime progression both exploit per-account incentives.

## D-042 — Time metrics: no effort or play-time implication from elapsed days (resolves D-015)

- **Date:** 2026-10-04 · **Status:** ADOPTED (founder direction)
- **Decision:** We do not present elapsed calendar days as a measure of effort or play time, and we
  show no play-time estimates or earnings per hour unless play time can be measured defensibly.
  Elapsed time may be used internally (analytics, deadline feasibility). Any consumer display needs a
  separate decision with wording that cannot be read as effort.
- **Applied:** the Trust page row "Typical days to reach a milestone" was replaced with "Time and
  effort: we will not show play-time estimates or earnings per hour unless we can measure play time
  reliably." The "Quick wins" category (D-022) stays gated: its name implies low effort, so it needs
  a play-time measure or a non-effort definition and name.

## D-043 — Public routing disclosure stays general; specifics go private (supersedes D-017)

- **Date:** 2026-10-04 · **Status:** ADOPTED (founder modification)
- **Decision:** Don't misrepresent how the product works, but the public site doesn't advertise our
  competitive or routing strategy. Partner page: "We integrate approved rewarded inventory through
  API-driven publisher partnerships"; the attribution promise is kept ("each attempt is attributed to
  exactly one network, never switched after the user begins") without describing network selection.
  The Trust page now says each offer is tracked through one network recorded at start. Questions on
  multiple providers, ranking, routing, duplicate campaigns and route selection are asked privately
  and answered in writing (Q4–7; application packet note).
