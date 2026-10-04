import { formatUsdCents, sumCents } from "@/lib/money/format";
import type { Estimate, Offer } from "./types";

/**
 * Minimum number of people who started an offer before an expected-earnings figure may be
 * shown. Provisional; to be finalized with the methodology in docs/EXPERIMENTS.md.
 */
export const MIN_DISPLAY_SAMPLE = 30;

export function isDisplayableEstimate(e: Estimate): e is Extract<Estimate, { kind: "estimate" }> {
  return (
    e.kind === "estimate" &&
    Number.isSafeInteger(e.valueCents) &&
    e.sampleSize >= MIN_DISPLAY_SAMPLE &&
    e.estimatorVersion.trim().length > 0
  );
}

export interface OfferHeadline {
  /** The single most prominent number on a card, in cents. */
  primaryCents: number;
  /** What the primary number means. Always shown next to it. */
  primaryLabel: string;
  /** Secondary line, e.g. the maximum including purchases. */
  secondary: string | null;
  /** True only when the primary number comes from measured outcomes. */
  isExpected: boolean;
}

export interface OfferSummary {
  totalCents: number;
  withoutPurchasesCents: number;
  hasPurchaseMilestones: boolean;
  firstReward: { label: string; rewardCents: number } | null;
  headline: OfferHeadline;
}

/**
 * Decides what a browse card leads with (docs/DECISIONS.md D-019):
 *  - Measured expected earnings, once displayable → primary; maximum is secondary.
 *  - Otherwise → the total available WITHOUT purchases is primary, so the biggest number
 *    on a card is never one that requires spending money. Totals including purchases are
 *    secondary. Maximums are never labeled as "expected".
 */
export function summarizeOffer(offer: Offer): OfferSummary {
  const totalCents = sumCents(offer.milestones.map((m) => m.rewardCents));
  const withoutPurchasesCents = sumCents(
    offer.milestones.filter((m) => !needsPurchase(m)).map((m) => m.rewardCents),
  );
  const hasPurchaseMilestones = offer.milestones.some(needsPurchase);
  const first = offer.milestones[0] ?? null;

  let headline: OfferHeadline;
  if (isDisplayableEstimate(offer.expectedEarnings)) {
    headline = {
      primaryCents: offer.expectedEarnings.valueCents,
      primaryLabel: `expected, based on ${offer.expectedEarnings.sampleSize} players`,
      secondary: `${formatUsdCents(totalCents)} max`,
      isExpected: true,
    };
  } else if (hasPurchaseMilestones) {
    headline = {
      primaryCents: withoutPurchasesCents,
      primaryLabel: "available without purchases",
      secondary: `${formatUsdCents(totalCents)} with purchases`,
      isExpected: false,
    };
  } else {
    headline = {
      primaryCents: totalCents,
      primaryLabel: "total rewards available",
      secondary: null,
      isExpected: false,
    };
  }

  return {
    totalCents,
    withoutPurchasesCents,
    hasPurchaseMilestones,
    firstReward: first ? { label: first.label, rewardCents: first.rewardCents } : null,
    headline,
  };
}

/** True if reaching this milestone requires spending money (directly or via an earlier gate). */
export function needsPurchase(m: Offer["milestones"][number]): boolean {
  return m.isPurchase || m.gatedBehindPurchase === true;
}

export function purchaseBadge(p: Offer["purchase"]): {
  text: string;
  tone: "ok" | "neutral" | "pending";
} {
  switch (p) {
    case "none":
      return { text: "No purchase needed", tone: "ok" };
    case "optional":
      return { text: "Optional purchase", tone: "neutral" };
    case "required":
      return { text: "Purchase required", tone: "pending" };
  }
}
