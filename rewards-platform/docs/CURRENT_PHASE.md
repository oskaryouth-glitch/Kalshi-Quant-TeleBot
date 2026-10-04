# Current phase: pre-approval company shell

**Updated:** 2026-10-04

## Goal

A credible, honest public presence that offer-network partnership teams can evaluate (supporting
E001 applications), plus an early-access list.

## Built

- Pages: Home, How it works, Trust & transparency, For partners, About, Early access, Contact,
  Privacy (draft), Terms (draft), 404. Sitemap, robots, OG image, icon.
- Early-access waitlist (Postgres; works without JS; fails closed without a DB).
- Guardrails: copy guard, launch-readiness check, security headers, contrast tests.
- Tests: unit (Vitest), Postgres integration, e2e (Playwright + axe) at mobile and desktop.
- Docs: this folder.

## Launch blockers: founder actions (no engineering needed)

`npm run check:launch` lists these until resolved:

1. **Choose and clear the brand name.** Trademark search plus domain and social handles (D-004).
   Then set `nameStatus: "cleared"` in `src/lib/site-config.ts` (and change `name` if needed).
2. **Form the legal entity**, then set `NEXT_PUBLIC_LEGAL_ENTITY` and `NEXT_PUBLIC_ENTITY_JURISDICTION`.
3. **Mailing address** (registered agent or virtual office): `NEXT_PUBLIC_MAILING_ADDRESS`. Also
   required by CAN-SPAM before sending any email.
4. **Domain plus business email** for partners@, support@ and privacy@ (or one inbox with aliases),
   then set the env vars.
5. **Hosting and Postgres** accounts, then `DATABASE_URL`, run `npm run db:migrate`, and set
   `NEXT_PUBLIC_SITE_URL`.
6. **Legal review** of `/privacy` and `/terms`, then replace the `-draft` versions in
   `POLICY_VERSIONS`.

Partner applications can begin once 1–5 are done. Networks commonly look for a real domain,
business email, privacy policy, terms and contact details.

## Recommended (founder choice, not a blocker)

- **Show real people on the About page** (names, roles, optionally LinkedIn). Partner managers and
  skeptical users both look for who is accountable. Nothing about the team is shown today because
  nothing may be invented.
- **Fill in the partner page's missing CTA.** The "Email partnerships" button only renders once
  `NEXT_PUBLIC_PARTNERS_EMAIL` is set.

## Decisions awaiting founder sign-off

Added 2026-10-04: D-022 (discovery categories, "Biggest" not "Best"), D-023 (exclude social casino),
D-025 (campus program guardrails).

D-004 (name), D-015 (time = elapsed days), D-017 (disclosing multi-network
intent on the partner page). See DECISIONS.md.

## Research areas opened (2026-10-04)

- Game desirability: `docs/research/GAME_DESIRABILITY.md` (feeds E002; hypotheses H-GD1–5).
- Referral and campus ambassadors: `docs/research/REFERRAL_AND_AMBASSADORS.md` (E008 can run
  pre-launch with `npm run waitlist:report`; E009 is post-launch and gated).

## Next phase candidates (in order)

1. **E001 execution:** archive Tier A provider terms (PROVIDER_REGISTRY "next research step"),
   then apply.
2. Double opt-in for the waitlist once an email provider exists (D-008).
3. On credentials: the raw-payload store plus the first real adapter (ARCHITECTURE Part 2), and
   E002 analysis notebooks over real snapshots.
