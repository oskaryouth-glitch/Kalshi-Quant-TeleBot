/**
 * Consumer-facing offer model for the marketplace UI.
 *
 * In this phase the only data is ILLUSTRATIVE (src/lib/fixtures/illustrative-offers.ts).
 * `provenance` is a discriminant so UI can never present illustrative data without a
 * visible label. A "provider" provenance (snapshot id, retrieved_at) is added only when
 * real catalog data exists — see docs/ARCHITECTURE.md Part 2.
 */

export type ArtVariant = "city" | "puzzle" | "racing" | "word" | "farm";

export type Estimate =
  | { kind: "insufficient-data" }
  /** Only from measured outcomes. Display additionally gated by MIN_DISPLAY_SAMPLE. */
  | {
      kind: "estimate";
      valueCents: number;
      sampleSize: number;
      estimatorVersion: string;
      windowStart: string;
      windowEnd: string;
    };

export type PurchaseRequirement = "none" | "optional" | "required";

export interface Milestone {
  label: string;
  rewardCents: number;
  /** This step is itself an in-game purchase paid for by the player. */
  isPurchase: boolean;
  /** Only reachable after a required purchase earlier in the ladder. */
  gatedBehindPurchase?: boolean;
}

export interface Offer {
  provenance: "illustrative";
  id: string;
  /** Genre-style name. Illustrative offers never use real game names. */
  title: string;
  genre: string;
  art: ArtVariant;
  platform: "Android";
  region: "US";
  /** Days allowed from install to finish every milestone. */
  timeLimitDays: number;
  purchase: PurchaseRequirement;
  milestones: Milestone[];
  /** Eligibility conditions that can void the reward if unmet. Shown before start. */
  eligibility: string[];
  expectedEarnings: Estimate;
}
