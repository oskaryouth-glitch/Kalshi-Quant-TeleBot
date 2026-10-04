/**
 * Prints early-access signups by ?ref= source tag and platform. Aggregates only — no emails.
 *
 * Usage:
 *   DATABASE_URL=postgres://... npm run waitlist:report
 *   DATABASE_URL=... npm run waitlist:report -- --prefix=amb_ --since=2026-11-01
 *
 * Ambassador codes should share a prefix (e.g. amb_<campus>_<initials>) so a cohort can be
 * filtered with --prefix. See docs/EXPERIMENTS.md E008.
 */
import postgres from "postgres";
import { waitlistBySource } from "../src/lib/waitlist/report.ts";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL is not set.");
  process.exit(1);
}

const arg = (name: string) =>
  process.argv.find((a) => a.startsWith(`--${name}=`))?.slice(name.length + 3);

const sinceArg = arg("since");
const since = sinceArg ? new Date(`${sinceArg}T00:00:00Z`) : undefined;
if (since && Number.isNaN(since.getTime())) {
  console.error("--since must be YYYY-MM-DD");
  process.exit(1);
}

const sql = postgres(url, { max: 1, onnotice: () => {} });
try {
  const rows = await waitlistBySource(sql, { since, sourcePrefix: arg("prefix") });
  const pct = (n: number, d: number) => (d === 0 ? "—" : `${Math.round((n / d) * 100)}%`);
  console.table(
    rows.map((r) => ({
      source: r.source,
      total: r.total,
      android: r.android,
      iphone: r.iphone,
      other: r.other,
      "android %": pct(r.android, r.total),
      first: r.firstSignup.toISOString().slice(0, 10),
      last: r.lastSignup.toISOString().slice(0, 10),
    })),
  );
  const total = rows.reduce((s, r) => s + r.total, 0);
  console.log(`${total} signup(s) across ${rows.length} source(s).`);
  console.log("Counts are upper bounds until double opt-in exists (DECISIONS D-008).");
} finally {
  await sql.end();
}
