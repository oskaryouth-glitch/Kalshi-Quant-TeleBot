import { describe, expect, it, vi } from "vitest";
import { POLICY_VERSIONS } from "@/lib/site-config";
import { FixedWindowRateLimiter } from "./rate-limit";
import { HONEYPOT_FIELD, submitWaitlist } from "./service";
import { MemoryWaitlistStore, type WaitlistStore } from "./store";

function form(fields: Record<string, string>): FormData {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.set(k, v);
  return fd;
}

const valid = { email: "  Player@Example.com ", platform: "android", ageConfirmed: "yes" };

function ctx(overrides: Partial<Parameters<typeof submitWaitlist>[1]> = {}) {
  return {
    store: new MemoryWaitlistStore() as WaitlistStore | null,
    limiter: new FixedWindowRateLimiter(100, 60_000),
    clientKey: "203.0.113.7",
    ...overrides,
  };
}

describe("submitWaitlist", () => {
  it("stores a valid signup with normalized email and consent version", async () => {
    const store = new MemoryWaitlistStore();
    const add = vi.spyOn(store, "add");
    const res = await submitWaitlist(form({ ...valid, note: "  hi  " }), ctx({ store }));
    expect(res).toEqual({ status: "success" });
    expect(add).toHaveBeenCalledWith({
      email: "Player@Example.com",
      emailNormalized: "player@example.com",
      platform: "android",
      note: "hi",
      source: null,
      privacyPolicyVersion: POLICY_VERSIONS.privacy,
      ageConfirmed: true,
    });
  });

  it("returns the same response for a duplicate email (no membership disclosure)", async () => {
    const store = new MemoryWaitlistStore();
    const c = ctx({ store });
    const first = await submitWaitlist(form(valid), c);
    const second = await submitWaitlist(form({ ...valid, email: "PLAYER@example.com" }), c);
    expect(first).toEqual(second);
    expect(store.size).toBe(1);
  });

  it("reports field errors and echoes safe values back", async () => {
    const res = await submitWaitlist(form({ email: "not-an-email", platform: "nokia" }), ctx());
    expect(res.status).toBe("invalid");
    if (res.status !== "invalid") throw new Error("unreachable");
    expect(res.errors.email).toMatch(/valid email/i);
    expect(res.errors.platform).toBeDefined();
    expect(res.errors.ageConfirmed).toMatch(/18/);
    expect(res.values.email).toBe("not-an-email");
  });

  it("requires the 18+ confirmation", async () => {
    const res = await submitWaitlist(form({ email: "a@b.co", platform: "iphone" }), ctx());
    expect(res.status).toBe("invalid");
  });

  it("rejects overly long notes", async () => {
    const res = await submitWaitlist(form({ ...valid, note: "x".repeat(501) }), ctx());
    expect(res.status).toBe("invalid");
  });

  it("drops malformed source tags instead of storing them", async () => {
    const store = new MemoryWaitlistStore();
    const add = vi.spyOn(store, "add");
    await submitWaitlist(form({ ...valid, source: "<script>" }), ctx({ store }));
    expect(add.mock.calls[0][0].source).toBeNull();
    await submitWaitlist(
      form({ ...valid, email: "other@example.com", source: "TikTok_Bio" }),
      ctx({ store }),
    );
    expect(add.mock.calls[1][0].source).toBe("tiktok_bio");
  });

  it("silently discards honeypot submissions without storing", async () => {
    const store = new MemoryWaitlistStore();
    const res = await submitWaitlist(form({ ...valid, [HONEYPOT_FIELD]: "x" }), ctx({ store }));
    expect(res).toEqual({ status: "success" });
    expect(store.size).toBe(0);
  });

  it("rate limits repeated submissions from one client", async () => {
    const c = ctx({ limiter: new FixedWindowRateLimiter(2, 60_000) });
    await submitWaitlist(form(valid), c);
    await submitWaitlist(form(valid), c);
    expect(await submitWaitlist(form(valid), c)).toEqual({ status: "rate-limited" });
  });

  it("says the list is unavailable when no store is configured", async () => {
    expect(await submitWaitlist(form(valid), ctx({ store: null }))).toEqual({
      status: "unavailable",
    });
  });

  it("reports a store failure honestly and never logs personal data", async () => {
    const log = vi.fn();
    const store: WaitlistStore = {
      kind: "broken",
      add: async () => {
        throw new Error("connection refused");
      },
    };
    const res = await submitWaitlist(form({ ...valid, note: "secret" }), ctx({ store, log }));
    expect(res).toEqual({ status: "error" });
    const logged = JSON.stringify(log.mock.calls);
    expect(logged).not.toContain("example.com");
    expect(logged).not.toContain("secret");
  });
});
