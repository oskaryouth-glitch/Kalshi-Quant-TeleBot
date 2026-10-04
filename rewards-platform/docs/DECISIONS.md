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

- **Date:** 2026-10-04 · **Status:** PROPOSED (_needs founder sign-off_)
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

- **Date:** 2026-10-04 · **Status:** PROPOSED (_needs founder sign-off_)
- **Decision:** A real-sounding working name so the site can be evaluated. It is defined once in
  `src/lib/site-config.ts` with `nameStatus: "working"`, and `npm run check:launch` fails until it is
  set to `"cleared"`.
- **Evidence:** One web search (2026-10-04) found only an older Spanish academic research project
  called "WorthPlay" (games for older adults). **This is not trademark clearance.** USPTO/state
  searches and domain/handle availability have not been checked.
- **Revisit when:** The founders choose a name, or before any public launch or publisher application.

## D-005 — Visual direction "Scorecard"

- **Date:** 2026-10-04 · **Status:** ADOPTED
- See DESIGN_SYSTEM.md for the three directions considered and how they scored.

## D-006 — No outcome-based numbers until measured; Offer Facts fixture is illustrative-only by type

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

- **Date:** 2026-10-04 · **Status:** PROPOSED (_needs founder sign-off_)
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

- **Date:** 2026-10-04 · **Status:** ADOPTED (_needs founder sign-off_)
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
