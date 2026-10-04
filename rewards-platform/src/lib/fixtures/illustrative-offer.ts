/**
 * ILLUSTRATIVE FIXTURE — NOT REAL DATA.
 *
 * Used only to demonstrate the layout of the Offer Facts label on public pages.
 * The game is fictional. The amounts are invented for layout purposes and are not
 * drawn from any provider, campaign or user outcome. Every estimate field is
 * deliberately "insufficient-data" because we have no outcome data (DECISIONS D-006).
 *
 * The `provenance: "illustrative"` discriminant forces the label to render a visible
 * "Illustrative example" banner. There is intentionally no "live" provenance in this
 * phase of the codebase.
 */

export type Estimate =
  | { kind: "insufficient-data"; note: string }
  // Reserved for later phases. Requires sample size and estimator version (EXPERIMENTS.md).
  | { kind: "estimate"; display: string; sampleSize: number; estimatorVersion: string };

export type PurchaseRequirement = "none" | "optional" | "required";

export interface IllustrativeMilestone {
  label: string;
  rewardCents: number;
  isPurchase: boolean;
}

export interface IllustrativeOffer {
  provenance: "illustrative";
  title: string;
  subtitle: string;
  platform: string;
  region: string;
  deadline: string;
  purchase: PurchaseRequirement;
  milestones: IllustrativeMilestone[];
  estimates: {
    typicalEarnings: Estimate;
    typicalDaysToFinish: Estimate;
    trackingRecord: Estimate;
  };
}

const NO_DATA = "Not enough data yet" as const;

export const illustrativeOffer: IllustrativeOffer = {
  provenance: "illustrative",
  title: "Sample city-builder",
  subtitle: "Fictional game",
  platform: "Android",
  region: "US",
  deadline: "14 days from install",
  purchase: "optional",
  milestones: [
    { label: "Install and reach level 5", rewardCents: 40, isPurchase: false },
    { label: "Reach level 15", rewardCents: 160, isPurchase: false },
    { label: "Reach level 30", rewardCents: 400, isPurchase: false },
    { label: "Reach level 45", rewardCents: 900, isPurchase: false },
    { label: "Make any in-game purchase", rewardCents: 600, isPurchase: true },
  ],
  estimates: {
    typicalEarnings: { kind: "insufficient-data", note: NO_DATA },
    typicalDaysToFinish: { kind: "insufficient-data", note: NO_DATA },
    trackingRecord: { kind: "insufficient-data", note: NO_DATA },
  },
};
