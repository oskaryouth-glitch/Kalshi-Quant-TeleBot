/**
 * Launch-readiness gate. Run with `npm run check:launch` (Node >= 22.18 strips types natively).
 *
 * Fails (exit 1) while any fact the public site depends on is missing or still a
 * working placeholder. Wire this into the production deploy pipeline so the site
 * cannot go public with a working name, missing legal entity, or draft policies.
 * See docs/CURRENT_PHASE.md "Launch blockers".
 */
import { launchBlockers } from "../src/lib/site-config.ts";

const blockers = launchBlockers();

if (blockers.length > 0) {
  console.error(`Launch check FAILED — ${blockers.length} blocker(s):`);
  for (const b of blockers) console.error(`  • ${b}`);
  process.exit(1);
}

console.log("Launch check passed.");
