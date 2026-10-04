/**
 * Money is represented as integer minor units (US cents) everywhere in this codebase.
 * This formatter uses integer arithmetic only, so no binary floating-point is involved
 * even for display. See docs/ARCHITECTURE.md "Money".
 */
export function formatUsdCents(cents: number): string {
  if (!Number.isSafeInteger(cents)) {
    throw new TypeError(`formatUsdCents expects a safe integer number of cents, got ${cents}`);
  }
  const negative = cents < 0;
  const abs = Math.abs(cents);
  const dollars = Math.trunc(abs / 100);
  const remainder = abs % 100;
  const grouped = dollars.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}$${grouped}.${remainder.toString().padStart(2, "0")}`;
}

/** Sums integer cent amounts, refusing non-integers rather than silently rounding. */
export function sumCents(amounts: readonly number[]): number {
  let total = 0;
  for (const amount of amounts) {
    if (!Number.isSafeInteger(amount)) {
      throw new TypeError(`sumCents expects safe integers, got ${amount}`);
    }
    total += amount;
  }
  if (!Number.isSafeInteger(total)) throw new RangeError("sumCents overflowed safe integer range");
  return total;
}
