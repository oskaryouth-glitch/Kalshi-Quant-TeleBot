# Current phase: evidence (E001 · LEGAL-001 · E002)

**Updated:** 2026-10-04 · **Scope freeze in effect (D-037).**

The pre-approval company shell is built. Product scope is frozen until real-world evidence exists.
The three things that matter now:

| Track         | Question                                                                   | Status                                                                                                                                   | Doc                                         |
| ------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **E001**      | Can we obtain legitimate supply under terms that permit our model?         | Not started. Readiness audit done: **not ready to apply** until the founder actions below are complete.                                  | docs/E001_APPLICATION_READINESS.md          |
| **LEGAL-001** | Can the reward/referral/payout/gamification structure operate compliantly? | OPEN. 28 items, nothing cleared.                                                                                                         | docs/LEGAL-001.md                           |
| **E002**      | What do real inventory and terms say about economics?                      | Blocked on E001 credentials. Plan includes desirability, social-casino segmentation, inventory depth, concentration and working capital. | docs/EXPERIMENTS.md, docs/UNIT_ECONOMICS.md |

## Founder actions, in order (unblock E001)

1. **Choose and clear the brand name, then buy the domain** (D-004). Do this before applying:
   rebranding after approval means re-approval with every network.
2. **Form the legal entity; get an EIN; set a mailing address** (needed for tax forms, contracts,
   CAN-SPAM). Set `NEXT_PUBLIC_LEGAL_ENTITY`, `NEXT_PUBLIC_ENTITY_JURISDICTION`,
   `NEXT_PUBLIC_MAILING_ADDRESS`.
3. **Business email(s) and a phone number.** Set `NEXT_PUBLIC_PARTNERS_EMAIL`, `_SUPPORT_EMAIL`,
   `_PRIVACY_EMAIL`. The partner page's email button appears automatically.
4. **Hosting + Postgres**, `npm run db:migrate`, set `NEXT_PUBLIC_SITE_URL`, deploy.
5. **Founder names and roles on About** (real facts only).
6. **Engage counsel for LEGAL-001.** Priority items: L8–L9 (provider terms), L17–L18 (payout and
   wallet), L10–L11 (referral and ambassador pay), L21 (age), L22 (tax), L23 (terms).
7. **Apply in waves** (E001 readiness §H): BitLabs, Offerwall.GG, RevU first.
8. **Repository migration** before any credentials or production database (docs/REPO_MIGRATION.md).

`npm run check:launch` lists the remaining site blockers.

## Engineering work allowed during the freeze

- Site changes needed for applications (facts via env, founder names, processor list in privacy).
- Repository migration.
- Once credentials exist: raw-payload capture and catalog snapshots, then E002 analysis. No consumer
  features.
- The pre-launch ambassador reach test (E008) using the existing `npm run waitlist:report`.

## Built so far (shell)

Pages: Home (earning-led, illustrative marketplace preview + offer detail dialog), How it works,
Trust & transparency, For partners, About, Early access, Contact, Privacy (draft), Terms (draft), 404.
Waitlist on Postgres (works without JS; fails closed without a DB). Guardrails: copy guard
(including no cash or payout-method claims until confirmed), launch check, CSP, contrast tests.
Tests: unit, Postgres integration, Playwright + axe e2e at 320/390/desktop.

## Decisions recorded this round

D-022 (re-confirmed; "Recommended" ranking only with data), D-027 (social casino segmented), D-028
(conversion-based ambassador pay; organization per-member payouts stay prohibited for now), D-029,
D-030, D-031, and new D-032 (college is a wedge, not the product), D-033 (leaderboards gated, no cash
for rank), D-034 (per-conversion incentive budget), D-035 (clans/progression: hypotheses with design
changes), D-036 (LEGAL-001), D-037 (scope freeze).

Still awaiting founder input: D-004 (name), D-015 (time = elapsed days), D-017 (multi-network
disclosure on the partner page).

## Research areas (documented; no build)

- Game desirability: `docs/research/GAME_DESIRABILITY.md`
- Referral and ambassadors: `docs/research/REFERRAL_AND_AMBASSADORS.md`
- Clans, progression, leaderboards: `docs/research/SOCIAL_AND_PROGRESSION.md`
- Competitors: `docs/research/COMPETITORS-2026-10.md`
