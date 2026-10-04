import { createHash, randomBytes } from "node:crypto";

/**
 * Fixed-window, in-process rate limiter.
 *
 * HONEST LIMITATION: state lives in one server instance's memory. On serverless or
 * multi-instance hosting each instance counts separately and state resets on cold start,
 * so this only slows casual abuse. It is not a security control. Replace with a shared
 * store (e.g. Postgres or Redis) before anything valuable sits behind it. See ARCHITECTURE.md.
 *
 * Client keys (IP addresses) are hashed with a per-process random salt, so raw IPs are
 * never retained, even in memory.
 */
export class FixedWindowRateLimiter {
  private readonly hits = new Map<string, { count: number; windowStart: number }>();
  private readonly salt = randomBytes(16).toString("hex");

  constructor(
    private readonly limit: number,
    private readonly windowMs: number,
    private readonly maxKeys = 10_000,
  ) {}

  /** Returns true if the request is allowed. */
  check(clientKey: string, now: number = Date.now()): boolean {
    const key = createHash("sha256").update(this.salt).update(clientKey).digest("hex");
    const entry = this.hits.get(key);
    if (!entry || now - entry.windowStart >= this.windowMs) {
      if (this.hits.size >= this.maxKeys) this.evictExpired(now);
      this.hits.set(key, { count: 1, windowStart: now });
      return true;
    }
    entry.count += 1;
    return entry.count <= this.limit;
  }

  private evictExpired(now: number) {
    for (const [k, v] of this.hits) {
      if (now - v.windowStart >= this.windowMs) this.hits.delete(k);
    }
    // If everything is still active, drop the oldest entries to bound memory.
    while (this.hits.size >= this.maxKeys) {
      const oldest = this.hits.keys().next().value;
      if (oldest === undefined) break;
      this.hits.delete(oldest);
    }
  }
}
