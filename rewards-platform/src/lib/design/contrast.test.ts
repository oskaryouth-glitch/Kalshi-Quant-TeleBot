import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * Reads the color tokens straight from globals.css (the single source of truth)
 * and enforces WCAG 2.x contrast for every text/background pairing we use.
 */
const css = readFileSync(fileURLToPath(new URL("../../app/globals.css", import.meta.url)), "utf8");

function token(name: string): string {
  const match = css.match(new RegExp(`--color-${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`Token --color-${name} not found in globals.css`);
  return match[1];
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// [foreground, background, minimum ratio]. 4.5 = WCAG AA body text.
const pairs: Array<[string, string, number]> = [
  ["ink", "paper", 4.5],
  ["ink-2", "paper", 4.5],
  ["ink-3", "paper", 4.5],
  ["ink-3", "surface", 4.5],
  ["ink-3", "paper-deep", 4.5],
  ["accent", "paper", 4.5],
  ["accent", "surface", 4.5],
  ["accent", "accent-soft", 4.5],
  ["accent-ink", "accent", 4.5],
  ["pending", "pending-soft", 4.5],
  ["ok", "ok-soft", 4.5],
  ["bad", "bad-soft", 4.5],
  ["surface", "ink", 4.5],
];

describe("design token contrast", () => {
  it.each(pairs)("%s on %s meets %d:1", (fg, bg, min) => {
    expect(contrast(token(fg), token(bg))).toBeGreaterThanOrEqual(min);
  });
});
