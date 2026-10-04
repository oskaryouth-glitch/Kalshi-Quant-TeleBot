# Architecture

Part 1 describes what exists (the pre-approval shell). Part 2 is a **proposal** for the platform
after provider credentials exist. Nothing in Part 2 is built. Do not build fake integrations ahead
of real credentials.

---

## Part 1 — The pre-approval shell (built)

```
rewards-platform/
├── src/app/                 Next.js App Router pages (all statically generated)
│   ├── early-access/        page + Server Action (the only server-side write path)
│   ├── privacy/, terms/     draft legal pages
│   ├── sitemap.ts, robots.ts, opengraph-image.tsx, icon.svg
├── src/components/          UI: header/footer, Offer Facts label, balance states, form, primitives
├── src/lib/
│   ├── site-config.ts       brand/company/contact facts (env-driven) + launch blockers
│   ├── copy-guard.ts        public-claim rules as code
│   ├── money/format.ts      integer-cent formatting
│   ├── fixtures/            ILLUSTRATIVE offer only (typed so it cannot pose as real)
│   └── waitlist/            schema (zod), service (pure), stores, rate limiter, config
├── db/migrations/           SQL migrations (applied by scripts/db-migrate.ts)
├── scripts/                 launch-check.ts, db-migrate.ts (run with Node type-stripping)
├── e2e/                     Playwright: pages, a11y, links, copy, headers, form flows
└── docs/                    project memory (this folder)
```

**Request flow (waitlist):** `<form action={joinWaitlist}>` → Server Action (Origin-checked by
Next.js) → `submitWaitlist(formData, ctx)` (pure: honeypot → rate limit → zod validation → store) →
`WaitlistStore.add` → Postgres `INSERT … ON CONFLICT (email_normalized) DO NOTHING`. The form works
without JavaScript (e2e-tested).

**Store selection:** `DATABASE_URL` → Postgres; otherwise in-memory in development; otherwise
(production without a DB) the page and action report "not open yet". Signups are never silently
dropped.

**Security posture:** CSP and hardening headers in `next.config.ts` (D-010 trade-off documented);
no cookies; no third-party origins; `poweredByHeader` off; HSTS when the site URL is HTTPS. Rate
limiting is per instance and **not** a security control (`rate-limit.ts` header comment).

**Money:** integer cents everywhere. `formatUsdCents` and `sumCents` reject non-integers rather
than rounding.

**Email normalization:** lowercasing the whole address is a pragmatic uniqueness choice (local parts
are technically case-sensitive, but nearly all providers treat them case-insensitively). We do not
strip dots or `+tags`. Those are legitimate distinct addresses, and stripping them is a
fraud-control question for later, not a waitlist concern.

**Deploy (not done; needs accounts):** any Node host works. On Vercel: root directory
`rewards-platform`, set env vars from `.env.example`, run `npm run db:migrate` against the
production DB, and add `npm run check:launch` as a required step before promoting to production.

---

## Part 2 — Platform proposal (not built)

### 2.1 Principles

1. **Raw first, normalize second.** Every provider response and callback is stored byte-for-byte
   (with headers, source IP and retrieval time) _before_ parsing. Normalization is a pure, versioned
   function that can be re-run over history.
2. **Provider logic stays in adapters.** Core domain code never branches on provider name.
3. **Immutable facts, derived state.** Ledger entries and raw records are append-only; balances and
   statuses are projections.
4. **Idempotency everywhere** on natural keys from the provider.

### 2.2 Provider adapter interface (refines the brief's sketch)

The brief proposed `fetchOffers / normalizeOffer / verifyPostback / normalizeConversion /
normalizeReversal / fetchReporting`. The refinement separates I/O from pure transforms and makes
capabilities explicit, so missing features are data, not runtime surprises:

```ts
interface ProviderAdapter {
  readonly id: ProviderId;
  readonly capabilities: {
    milestonePayouts: boolean;
    storeIds: boolean;
    reversalPostback: boolean;
    reportingApi: boolean;
    signedCallbacks: "hmac" | "secret" | "ip-allowlist" | "none";
  };
  readonly normalizerVersion: string; // bump on any mapping change

  // I/O only — returns raw pages; caller persists them before anything else happens.
  fetchCatalog(ctx: FetchContext): AsyncIterable<RawPayload>;
  fetchReporting?(range: DateRange): AsyncIterable<RawPayload>;

  // Pure transforms over stored raw data.
  normalizeCatalog(raw: StoredRawPayload): NormalizationResult<OfferSnapshotDraft[]>;
  buildTrackingUrl(input: { offer: OfferSnapshot; subId: OpaqueUserId; clickId: ClickId }): URL;
  verifyCallback(req: StoredRawRequest, secrets: ProviderSecrets): Verified | Rejected;
  parseCallback(verified: Verified): ConversionEvent | ReversalEvent;
}

type NormalizationResult<T> = { value: T; warnings: string[]; unmappedFields: string[] };
```

`unmappedFields` and `warnings` are persisted, so lossy mappings are visible in review.

### 2.3 Canonical schema (improves the brief's field list)

The brief's single flat offer row mixes four different things: the game, the provider's offer
version, its milestones, and our pricing decision. Split them:

- **`app`**: the canonical game. `platform`, `store_id` (package name), `title`.
- **`provider_offer_app_map`**: provider offer → app, with `match_method` (store_id / manual /
  fuzzy) and `confidence`. Overlap and dispersion analysis depend on this being explicit.
- **`raw_payload`**: `id`, `provider`, `kind` (catalog/report/callback), `retrieved_at`, `sha256`,
  `body` (jsonb or object-storage key), `request_meta`. Immutable.
- **`offer_snapshot`** (one provider offer version): `provider`, `provider_offer_id`,
  `provider_campaign_id`, `app_id`, `targeting` (countries[], platforms[], min_os, device
  requirements), `new_users_only`, `attribution_window`, `offer_expires_at`, `provider_status`,
  `terms_text`, `provider_claimed_epc`, `provider_claimed_cr` (with `as_of`, never displayed as
  ours), `raw_payload_id`, `normalizer_version`, `content_hash`, `first_seen_at`, `last_seen_at`.
  A material change creates a new snapshot.
- **`offer_goal`**: `snapshot_id`, `provider_goal_id`, `sequence`, `description`, `goal_type`
  (level / event / purchase / deposit / time), `purchase_requirement` (none / optional / required),
  `publisher_payout_minor` + `currency`, `payout_type` (fixed / revenue-share), `completion_window`,
  and `provider_suggested_user_reward` (raw value plus unit, since some providers express it in
  virtual currency).
- **`reward_quote`**: _our_ user reward for a goal = f(snapshot goal, `pricing_policy_version`).
  Not a provider field. This is where gross-spread policy lives.

### 2.4 Route lock

- **`offer_attempt`**: `user_id`, `app_id`, `provider`, `snapshot_id` (the exact terms shown),
  `quoted_rewards` (frozen copy), `click_id`, `clicked_at`, `locked_at`, `eligibility_evidence`
  (geo/platform/new-user checks at click), `session_ref`, `status`.
- **Locked at first click-out** (D-018): we cannot observe installs, and the clicked provider may
  attribute for its whole window. Enforce with a partial unique index: one non-terminal attempt per
  (user, app).
- An unlock is allowed only after the provider's attribution window passes with no conversion, and
  it is recorded as an event, never as an update.

### 2.5 Reward lifecycle (improves the brief's single state machine)

The brief's chain `TRACKED → PENDING → PROVIDER APPROVED → FRAUD HOLD → AVAILABLE → WITHDRAWN` mixes
provider-side facts with our own decisions, and has no home for missing conversions. The proposal
uses three separate lifecycles.

**A. Conversion (what the provider says)**
`RECEIVED → VERIFIED | REJECTED_SIGNATURE` → `PENDING_PROVIDER → APPROVED | REJECTED_BY_PROVIDER`
→ (`REVERSED` at any later time).
Idempotency key: `(provider, provider_txn_id, event_type)`.

**B. User reward (what we decide)**
`PENDING` (provider pending) → `CONFIRMED_HOLD` (provider approved; time hold ≥ provider reversal
window policy) → `AVAILABLE` → `WITHDRAWAL_REQUESTED` → `PAID`.
Side states: `RISK_HOLD` / `MANUAL_REVIEW` (any time before PAID; blocks withdrawal),
`REVERSED_BEFORE_PAYOUT`, `REVERSED_AFTER_PAYOUT` (creates a user receivable; policy needed).

**C. Claim (missing credit — the most common dispute)**
`OPEN → EVIDENCE_ATTACHED → SUBMITTED_TO_PROVIDER → GRANTED | DENIED | EXPIRED`.
The evidence pack is generated from `offer_attempt` (terms snapshot, click ID, timestamps) plus
user-supplied screenshots.

**D. Settlement (what the provider actually pays us) — for working capital**
`ACCRUED → INVOICED → PAID | SHORT_PAID | WRITTEN_OFF`, reconciled against provider reports.

### 2.6 Ledger

Double-entry, append-only, integer minor units, every entry referencing its cause (conversion event,
claim, withdrawal, adjustment with operator ID). Per-user accounts: `pending`, `held`,
`available`, `paid_out`, `receivable`. Company accounts: `provider_receivable:{provider}`,
`rewards_expense`, `fees`, `fraud_loss`. Balances are sums, never stored mutable fields. Invariant
tests: every transaction balances to zero, and no user account goes negative except `receivable`.

### 2.7 Estimates

Table `estimate`: `app_id`, `provider?`, `snapshot_id?`, `metric`, `value`, `interval_low/high`,
`n_started`, `n_event`, `cohort_definition`, `window_start/end`, `estimator_version`,
`computed_at`, `display_eligible` (threshold check). Methodology rules are in EXPERIMENTS.md.

### 2.8 Ingestion runtime

Postback ingestion should not depend on a single serverless invocation succeeding. Accept → persist
raw → 200 quickly, then process from a durable queue with idempotent workers and a dead-letter
queue. Catalog polling runs as scheduled jobs that respect provider rate limits.
