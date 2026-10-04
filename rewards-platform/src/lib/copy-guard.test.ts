import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { findViolations } from "./copy-guard";

const root = fileURLToPath(new URL("..", import.meta.url)); // src/

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return walk(p);
    return /\.(tsx|ts)$/.test(name) && !/\.test\.ts$/.test(name) && !p.endsWith("copy-guard.ts")
      ? [p]
      : [];
  });
}

describe("copy guard: patterns", () => {
  it.each([
    "Earn FREE MONEY today",
    "Earn up to $150 playing",
    "Proudly partnered with Lootably",
    "Trusted by 10,000+ players",
    "💰 cash out now",
    "Hurry, only 3 left!",
    "Guaranteed payouts",
    "$1.2M paid out",
    "Earn $7.40/hr",
    "Rated 4.8/5",
    "Play games. Earn real money.",
    "Cash out to PayPal",
  ])("flags %j", (text) => {
    expect(findViolations(text).length).toBeGreaterThan(0);
  });

  it.each([
    "Know what a game reward takes before you start.",
    "Listed total $21.00",
    "Payouts are not immediate",
    "We will not rank offers by their maximum possible total.",
    "Adults 18+ in the United States",
  ])("allows %j", (text) => {
    expect(findViolations(text)).toEqual([]);
  });
});

describe("copy guard: source files", () => {
  const files = walk(root);

  it("finds source files to scan", () => {
    expect(files.length).toBeGreaterThan(10);
  });

  it.each(files.map((f) => [f.slice(root.length), f]))("%s has no banned copy", (_rel, file) => {
    expect(findViolations(readFileSync(file, "utf8"), { sourceOnly: true })).toEqual([]);
  });
});
