import { PostgresWaitlistStore } from "./postgres-store";
import { FixedWindowRateLimiter } from "./rate-limit";
import { MemoryWaitlistStore, type WaitlistStore } from "./store";

/**
 * Store selection (DECISIONS D-008):
 * - DATABASE_URL set            → Postgres
 * - otherwise, not production   → in-memory (development only; data is lost on restart)
 * - otherwise (production)      → null: the form reports that early access is not open yet,
 *                                 rather than accepting signups it cannot keep.
 */
let cachedStore: WaitlistStore | null | undefined;

export function getWaitlistStore(): WaitlistStore | null {
  if (cachedStore !== undefined) return cachedStore;
  const url = process.env.DATABASE_URL;
  if (url) {
    cachedStore = new PostgresWaitlistStore(url);
  } else if (process.env.NODE_ENV !== "production") {
    cachedStore = new MemoryWaitlistStore();
  } else {
    cachedStore = null;
  }
  return cachedStore;
}

export function isWaitlistOpen(): boolean {
  return Boolean(process.env.DATABASE_URL) || process.env.NODE_ENV !== "production";
}

/** 5 submissions per client per 10 minutes, per server instance. See rate-limit.ts caveats. */
export const waitlistLimiter = new FixedWindowRateLimiter(5, 10 * 60 * 1000);
