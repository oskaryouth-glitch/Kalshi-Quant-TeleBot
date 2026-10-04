import type postgres from "postgres";

/**
 * Aggregate-only waitlist report for acquisition experiments (E004, E008).
 * Returns counts by source tag and platform. It never selects email addresses or notes,
 * so its output is safe to share with ambassadors or paste into experiment write-ups.
 * Kept free of path aliases so scripts/waitlist-report.ts can import it directly.
 */
export interface SourceRow {
  source: string;
  android: number;
  iphone: number;
  other: number;
  total: number;
  firstSignup: Date;
  lastSignup: Date;
}

export const NO_SOURCE = "(no ref tag)";

export async function waitlistBySource(
  sql: postgres.Sql,
  opts: { since?: Date; sourcePrefix?: string } = {},
): Promise<SourceRow[]> {
  const since = opts.since ?? new Date(0);
  const prefix = opts.sourcePrefix ?? null;
  const rows = await sql<
    {
      source: string;
      android: number;
      iphone: number;
      other: number;
      total: number;
      first_signup: Date;
      last_signup: Date;
    }[]
  >`
    select coalesce(source, ${NO_SOURCE})                        as source,
           count(*) filter (where platform = 'android')::int     as android,
           count(*) filter (where platform = 'iphone')::int      as iphone,
           count(*) filter (where platform = 'other')::int       as other,
           count(*)::int                                         as total,
           min(created_at)                                       as first_signup,
           max(created_at)                                       as last_signup
    from waitlist_signups
    where created_at >= ${since}
      and (${prefix}::text is null or source like ${prefix} || '%')
    group by 1
    order by total desc, source asc
  `;
  return rows.map((r) => ({
    source: r.source,
    android: r.android,
    iphone: r.iphone,
    other: r.other,
    total: r.total,
    firstSignup: r.first_signup,
    lastSignup: r.last_signup,
  }));
}
