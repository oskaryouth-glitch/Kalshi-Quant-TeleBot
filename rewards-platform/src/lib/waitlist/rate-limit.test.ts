import { describe, expect, it } from "vitest";
import { FixedWindowRateLimiter } from "./rate-limit";

describe("FixedWindowRateLimiter", () => {
  it("allows up to the limit within a window, then blocks", () => {
    const rl = new FixedWindowRateLimiter(3, 1000);
    expect([1, 2, 3, 4].map(() => rl.check("a", 0))).toEqual([true, true, true, false]);
  });

  it("resets after the window elapses", () => {
    const rl = new FixedWindowRateLimiter(1, 1000);
    expect(rl.check("a", 0)).toBe(true);
    expect(rl.check("a", 999)).toBe(false);
    expect(rl.check("a", 1000)).toBe(true);
  });

  it("tracks clients independently", () => {
    const rl = new FixedWindowRateLimiter(1, 1000);
    expect(rl.check("a", 0)).toBe(true);
    expect(rl.check("b", 0)).toBe(true);
  });

  it("bounds memory by evicting entries", () => {
    const rl = new FixedWindowRateLimiter(1, 1000, 10);
    for (let i = 0; i < 50; i++) rl.check(`client-${i}`, 0);
    // @ts-expect-error inspecting private state in a test
    expect(rl.hits.size).toBeLessThanOrEqual(10);
  });
});
