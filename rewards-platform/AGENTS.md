<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# Project rules for agents (rewards-platform)

Read `README.md` and `docs/CURRENT_PHASE.md` first. Record any architectural, product or
compliance-relevant decision in `docs/DECISIONS.md` (date, decision, alternatives, reason, evidence,
revisit condition). Do not let decisions live only in chat.

Non-negotiables (several are enforced by tests):

- Never invent public claims: partnerships, users, payouts, earnings, hourly rates, ratings,
  testimonials. Never name offer networks or competitors on public pages. (`src/lib/copy-guard.ts`)
- Never fabricate offer data. Fixtures must use `provenance: "illustrative"` and render the banner.
- Never add placeholder company or contact facts. Use `src/lib/site-config.ts` and env vars.
- Money is integer minor units. No floats in financial logic.
- Planned features are labeled as planned. Do not describe a control as live until it is.
- Raw provider data must be preserved before normalization (see `docs/ARCHITECTURE.md` Part 2).
- Distinguish CONFIRMED / INFERENCE / HYPOTHESIS / ASSUMPTION / UNKNOWN in docs.
- Any new data collection requires a privacy-policy update and `POLICY_VERSIONS` bump first.
- Run `npm run verify` before committing; run e2e for UI or form changes.
