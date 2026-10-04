# rewards-platform

Pre-approval company shell for a US consumer product that makes rewarded mobile-game offers easier
to evaluate: standardized up-front disclosure now, measured outcomes once real data exists.

> **Working name:** "Worthplay" (not trademark-cleared; see `docs/DECISIONS.md` D-004).
> **Status:** pre-launch. No offers, balances or payouts exist. Nothing here integrates with any
> offer network yet.

This directory is self-contained and lives inside an unrelated repository for now (D-001).

## Start here

| If you want to…                                                         | Read                                 |
| ----------------------------------------------------------------------- | ------------------------------------ |
| Understand the business and thesis                                      | `docs/PRODUCT_VISION.md`             |
| Know the current priorities (evidence phase) and what's blocking launch | `docs/CURRENT_PHASE.md`              |
| See why things are the way they are                                     | `docs/DECISIONS.md`                  |
| Review risks                                                            | `docs/RISK_REGISTER.md`              |
| Review experiment design and metric definitions                         | `docs/EXPERIMENTS.md`                |
| Check provider status (all UNKNOWN today)                               | `docs/PROVIDER_REGISTRY.md`          |
| Check claim rules and legal open questions                              | `docs/COMPLIANCE_NOTES.md`           |
| Understand the code and the future platform design                      | `docs/ARCHITECTURE.md`               |
| Work on UI or copy                                                      | `docs/DESIGN_SYSTEM.md`              |
| Read research areas (competitors, game desirability, referrals)         | `docs/research/`                     |
| Unit economics and the full incentive stack                             | `docs/UNIT_ECONOMICS.md`             |
| Legal issue register (nothing cleared)                                  | `docs/LEGAL-001.md`                  |
| Provider application readiness                                          | `docs/E001_APPLICATION_READINESS.md` |
| Moving to a standalone repository                                       | `docs/REPO_MIGRATION.md`             |

## Develop

Requires Node ≥ 22.18 (scripts use native TypeScript type-stripping; the Next app itself needs ≥ 20.9).

```bash
npm ci
cp .env.example .env.local      # optional; the dev server works with nothing set
npm run dev                     # http://localhost:3000 (waitlist uses an in-memory store in dev)
```

## Checks

```bash
npm run verify          # format check, lint, typecheck, unit tests, production build
npm run check:launch    # fails until launch blockers are resolved (expected to fail today)
DATABASE_URL=… npm run waitlist:report -- --prefix=amb_   # signups by ref code and platform (no PII)

# Postgres integration test
TEST_DATABASE_URL=postgres://… npm test

# End-to-end (production build + real Postgres)
DATABASE_URL=postgres://… npm run db:migrate
DATABASE_URL=postgres://… npm run build
E2E_DATABASE_URL=postgres://… npm run test:e2e
# In sandboxes with a preinstalled Chromium:
#   PLAYWRIGHT_CHROMIUM_PATH=/path/to/chrome PLAYWRIGHT_NO_PROXY=1 npm run test:e2e
```

## Rules that the build enforces

- **No fake claims.** `src/lib/copy-guard.ts` fails the build on hype, implied partnerships,
  network or competitor names, user counts, payout totals, hourly rates and ratings.
- **No fabricated offer data.** The only offer data is a typed, visibly labeled illustration.
- **No placeholder company facts.** Missing facts render as "not yet published"; `check:launch` blocks.
- **Money is integer cents.**
- **WCAG AA contrast** for design tokens; axe runs on every page in e2e.
