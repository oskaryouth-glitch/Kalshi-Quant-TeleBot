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

// Kept in this file so it runs sequentially with the store tests (they share one table).
describe.skipIf(!url)("waitlistBySource report (integration)", () => {
  let sql: postgres.Sql;
  let store: PostgresWaitlistStore;

  const add = (email: string, platform: "android" | "iphone" | "other", source: string | null) =>
    store.add({
      email,
      emailNormalized: email,
      platform,
      note: "private note",
      source,
      privacyPolicyVersion: "test",
      ageConfirmed: true,
    });

  beforeAll(async () => {
    sql = postgres(url!, { max: 1, onnotice: () => {} });
    await sql`truncate waitlist_signups`;
    store = new PostgresWaitlistStore(url!, { onnotice: () => {} });
    await add("a@example.com", "android", "amb_state_jd");
    await add("b@example.com", "android", "amb_state_jd");
    await add("c@example.com", "iphone", "amb_state_jd");
    await add("d@example.com", "android", "amb_tech_kl");
    await add("e@example.com", "other", null);
  });

  afterAll(async () => {
    await store?.close();
    await sql?.end();
  });

  it("aggregates by source and platform without exposing personal data", async () => {
    const { waitlistBySource, NO_SOURCE } = await import("./report");
    const rows = await waitlistBySource(sql);
    expect(rows.map((r) => [r.source, r.total, r.android, r.iphone, r.other])).toEqual([
      ["amb_state_jd", 3, 2, 1, 0],
      ["(no ref tag)", 1, 0, 0, 1],
      ["amb_tech_kl", 1, 1, 0, 0],
    ]);
    expect(NO_SOURCE).toBe("(no ref tag)");
    const serialized = JSON.stringify(rows);
    expect(serialized).not.toContain("@example.com");
    expect(serialized).not.toContain("private note");
  });

  it("filters by source prefix and date", async () => {
    const { waitlistBySource } = await import("./report");
    const amb = await waitlistBySource(sql, { sourcePrefix: "amb_" });
    expect(amb.map((r) => r.source)).toEqual(["amb_state_jd", "amb_tech_kl"]);
    const future = await waitlistBySource(sql, { since: new Date(Date.now() + 86_400_000) });
    expect(future).toEqual([]);
  });
});
