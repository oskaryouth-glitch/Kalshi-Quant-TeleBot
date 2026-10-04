/**
 * Public-copy guardrail (docs/COMPLIANCE_NOTES.md "Public claim rules").
 *
 * These patterns encode the founders' public-claim rules: no hype, no fake social proof,
 * no implied partnerships, no unsupported earnings figures. They are checked against:
 *   - source files (src/lib/copy-guard.test.ts), for the "never, anywhere" subset, and
 *   - rendered page text (e2e/copy-guard.spec.ts), for everything.
 *
 * A match is a build failure, not a warning. If a match is a genuine false positive,
 * change the copy or (for rendered checks only) wrap a deliberate quotation in an element
 * with data-copy-guard="ignore" and explain why in a comment.
 */

export interface BannedPattern {
  pattern: RegExp;
  reason: string;
  /** If true, also enforced on raw source text, not just rendered pages. */
  source: boolean;
}

/**
 * Offer networks and competitors. Naming them publicly can imply a relationship we do not
 * have (founder rule: never imply partnerships). Internal docs may name them; pages may not.
 */
export const NETWORK_AND_COMPETITOR_NAMES = [
  "Lootably",
  "BitLabs",
  "Prodege",
  "RevU",
  "AdGem",
  "ayeT",
  "Monlix",
  "Adscend",
  "Offerwall.GG",
  "Offerwall Ad",
  "Adparagon",
  "Wannads",
  "TapResearch",
  "CPX Research",
  "TheoremReach",
  "inBrain",
  "Tapjoy",
  "Digital Turbine",
  "Fyber",
  "adjoe",
  "MyChips",
  "CPAlead",
  "Freecash",
  "Mistplay",
] as const;

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export const BANNED_PATTERNS: BannedPattern[] = [
  { pattern: /free money/i, reason: "Hype language", source: true },
  { pattern: /easy money|get rich|passive income/i, reason: "Hype language", source: true },
  { pattern: /\bup to \$\s?\d/i, reason: "Maximum-payout headline", source: true },
  {
    pattern: /partnered with|in partnership with|official partner|our partners include/i,
    reason: "Implied partnership",
    source: true,
  },
  {
    pattern: /trusted by|as seen (on|in)\b|featured in/i,
    reason: "Fake social proof",
    source: true,
  },
  {
    pattern: /[\u{1F4B0}\u{1F911}\u{1F4B8}\u{1F4B5}\u{1F3B0}\u{1F525}]/u,
    reason: "Money/hype emoji",
    source: true,
  },
  {
    pattern: new RegExp(`\\b(${NETWORK_AND_COMPETITOR_NAMES.map(escape).join("|")})\\b`, "i"),
    reason: "Names a network or competitor (implies a relationship)",
    source: true,
  },
  {
    pattern: /guaranteed? (earnings|income|payouts?|cash|money|rewards?)/i,
    reason: "Guaranteed earnings claim",
    source: false,
  },
  {
    pattern: /instant (cash|payouts?|withdrawals?|rewards?)/i,
    reason: "Instant payout claim",
    source: false,
  },
  {
    pattern: /\b(hurry|act now|limited time|last chance|don't miss)\b/i,
    reason: "False urgency",
    source: false,
  },
  { pattern: /only \d+ (left|spots|remaining)/i, reason: "False scarcity", source: false },
  { pattern: /\bjackpot\b|\bspin to win\b/i, reason: "Gambling language", source: false },
  {
    pattern: /\b\d{1,3}(,\d{3})+\+? (users|members|players|people|gamers)\b/i,
    reason: "User-count claim",
    source: false,
  },
  {
    pattern: /\$\s?\d[\d,.]*[kKmM]?\+? (paid out|earned|withdrawn)/i,
    reason: "Payout-total claim",
    source: false,
  },
  {
    pattern: /\$\s?\d+(\.\d+)?\s*(\/|per)\s*(hr|hour)\b/i,
    reason: "Hourly-rate claim",
    source: false,
  },
  { pattern: /\b\d(\.\d)?\s?(\/\s?5|stars?)\b/i, reason: "Rating/review claim", source: false },
];

export interface CopyViolation {
  match: string;
  reason: string;
}

export function findViolations(text: string, opts: { sourceOnly?: boolean } = {}): CopyViolation[] {
  const out: CopyViolation[] = [];
  for (const { pattern, reason, source } of BANNED_PATTERNS) {
    if (opts.sourceOnly && !source) continue;
    const m = text.match(pattern);
    if (m) out.push({ match: m[0], reason });
  }
  return out;
}
