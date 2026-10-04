import { describe, expect, it } from "vitest";
import { formatUsdCents, sumCents } from "./format";

describe("formatUsdCents", () => {
  it.each([
    [0, "$0.00"],
    [5, "$0.05"],
    [40, "$0.40"],
    [100, "$1.00"],
    [2100, "$21.00"],
    [123456789, "$1,234,567.89"],
    [-250, "-$2.50"],
  ])("formats %i cents as %s", (cents, expected) => {
    expect(formatUsdCents(cents)).toBe(expected);
  });

  it("rejects fractional cents instead of rounding", () => {
    expect(() => formatUsdCents(10.5)).toThrow(TypeError);
    expect(() => formatUsdCents(Number.NaN)).toThrow(TypeError);
  });
});

describe("sumCents", () => {
  it("adds integer cents exactly where floats would drift", () => {
    // 0.1 + 0.2 !== 0.3 in binary floating point; in cents it is exact.
    expect(sumCents([10, 20])).toBe(30);
    expect(sumCents([])).toBe(0);
  });

  it("rejects non-integer inputs", () => {
    expect(() => sumCents([10, 0.5])).toThrow(TypeError);
  });
});
