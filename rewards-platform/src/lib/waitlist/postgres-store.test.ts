import { execFileSync } from "node:child_process";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import postgres from "postgres";
import { PostgresWaitlistStore } from "./postgres-store";
import type { WaitlistRecord } from "./store";

/**
 * Integration test against a real Postgres. Runs only when TEST_DATABASE_URL is set
 * (CI provides a service container). The database is migrated with the real migration
 * script, then the table is truncated.
 */
const url = process.env.TEST_DATABASE_URL;

describe.skipIf(!url)("PostgresWaitlistStore (integration)", () => {
  let store: PostgresWaitlistStore;
  let sql: postgres.Sql;

  const record: WaitlistRecord = {
    email: "Player@Example.com",
    emailNormalized: "player@example.com",
    platform: "android",
    note: null,
    source: "test",
    privacyPolicyVersion: "test-version",
    ageConfirmed: true,
  };

  beforeAll(async () => {
    execFileSync("node", ["scripts/db-migrate.ts"], {
      env: { ...process.env, DATABASE_URL: url },
      stdio: "pipe",
    });
    sql = postgres(url!, { max: 1, onnotice: () => {} });
    await sql`truncate waitlist_signups`;
    store = new PostgresWaitlistStore(url!, { onnotice: () => {} });
  });

  afterAll(async () => {
    await store?.close();
    await sql?.end();
  });

  it("inserts a new signup", async () => {
    expect(await store.add(record)).toBe("created");
    const rows = await sql`select email, platform, source, age_confirmed from waitlist_signups`;
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ email: "Player@Example.com", platform: "android" });
  });

  it("is idempotent on normalized email, including under concurrency", async () => {
    const results = await Promise.all([store.add(record), store.add(record), store.add(record)]);
    expect(results.every((r) => r === "already-exists")).toBe(true);
    const [{ count }] = await sql`select count(*)::int as count from waitlist_signups`;
    expect(count).toBe(1);
  });

  it("enforces column constraints in the database itself", async () => {
    await expect(
      store.add({ ...record, emailNormalized: "x@y.co", platform: "nokia" as never }),
    ).rejects.toThrow();
  });
});
