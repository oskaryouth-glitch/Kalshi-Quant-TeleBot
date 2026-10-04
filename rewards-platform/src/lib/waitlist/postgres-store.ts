import postgres from "postgres";
import type { AddResult, WaitlistRecord, WaitlistStore } from "./store";

/**
 * Postgres-backed store. Schema: db/migrations/001_waitlist.sql.
 * Uniqueness is enforced by the database (email_normalized UNIQUE), not by a read-then-write,
 * so concurrent duplicate submissions cannot create two rows.
 */
export class PostgresWaitlistStore implements WaitlistStore {
  readonly kind = "postgres";
  private readonly sql: postgres.Sql;

  constructor(databaseUrl: string, options: postgres.Options<Record<string, never>> = {}) {
    this.sql = postgres(databaseUrl, { max: 3, idle_timeout: 20, connect_timeout: 10, ...options });
  }

  async add(r: WaitlistRecord): Promise<AddResult> {
    const rows = await this.sql`
      insert into waitlist_signups
        (email, email_normalized, platform, note, source, privacy_policy_version, age_confirmed)
      values
        (${r.email}, ${r.emailNormalized}, ${r.platform}, ${r.note}, ${r.source},
         ${r.privacyPolicyVersion}, ${r.ageConfirmed})
      on conflict (email_normalized) do nothing
      returning id
    `;
    return rows.length === 1 ? "created" : "already-exists";
  }

  async close(): Promise<void> {
    await this.sql.end({ timeout: 5 });
  }
}
