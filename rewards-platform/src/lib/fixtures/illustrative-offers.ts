/**
 * ILLUSTRATIVE FIXTURES — NOT REAL OFFERS.
 *
 * Genre names only (never real game titles), invented amounts for layout, and no
 * outcome data: every `expectedEarnings` is "insufficient-data" (DECISIONS D-006, D-019).
 * The `provenance: "illustrative"` discriminant makes the UI render an "Example" label.
 */
import type { Offer } from "@/lib/offers/types";

const STANDARD_ELIGIBILITY = [
  "New players only. If you have installed this game before, it will not count.",
  "Install through the offer link, on the phone you will play on.",
  "Android 9 or later, in the United States.",
  "Turn off any VPN while playing. VPNs can stop progress from being tracked.",
];

export const illustrativeOffers: Offer[] = [
  {
    provenance: "illustrative",
    id: "example-city-builder",
    title: "City builder",
    genre: "Simulation",
    art: "city",
    platform: "Android",
    region: "US",
    timeLimitDays: 14,
    purchase: "optional",
    milestones: [
      { label: "Install and reach level 5", rewardCents: 40, isPurchase: false },
      { label: "Reach level 15", rewardCents: 160, isPurchase: false },
      { label: "Reach level 30", rewardCents: 400, isPurchase: false },
      { label: "Reach level 45", rewardCents: 900, isPurchase: false },
      { label: "Make any in-game purchase", rewardCents: 600, isPurchase: true },
    ],
    eligibility: STANDARD_ELIGIBILITY,
    expectedEarnings: { kind: "insufficient-data" },
  },
  {
    provenance: "illustrative",
    id: "example-match-3",
    title: "Match-3 puzzle",
    genre: "Puzzle",
    art: "puzzle",
    platform: "Android",
    region: "US",
    timeLimitDays: 10,
    purchase: "none",
    milestones: [
      { label: "Install and finish level 10", rewardCents: 30, isPurchase: false },
      { label: "Finish level 50", rewardCents: 120, isPurchase: false },
      { label: "Finish level 150", rewardCents: 350, isPurchase: false },
      { label: "Finish level 300", rewardCents: 750, isPurchase: false },
    ],
    eligibility: STANDARD_ELIGIBILITY,
    expectedEarnings: { kind: "insufficient-data" },
  },
  {
    provenance: "illustrative",
    id: "example-kart-racer",
    title: "Kart racer",
    genre: "Racing",
    art: "racing",
    platform: "Android",
    region: "US",
    timeLimitDays: 7,
    purchase: "none",
    milestones: [
      { label: "Install and finish the tutorial cup", rewardCents: 50, isPurchase: false },
      { label: "Unlock the second track set", rewardCents: 150, isPurchase: false },
      { label: "Reach driver level 20", rewardCents: 400, isPurchase: false },
    ],
    eligibility: STANDARD_ELIGIBILITY,
    expectedEarnings: { kind: "insufficient-data" },
  },
  {
    provenance: "illustrative",
    id: "example-farm-sim",
    title: "Farm sim",
    genre: "Casual",
    art: "farm",
    platform: "Android",
    region: "US",
    timeLimitDays: 21,
    purchase: "required",
    milestones: [
      { label: "Install and reach farm level 8", rewardCents: 60, isPurchase: false },
      { label: "Reach farm level 20", rewardCents: 240, isPurchase: false },
      { label: "Buy the starter pack", rewardCents: 800, isPurchase: true },
      {
        label: "Reach farm level 40",
        rewardCents: 1500,
        isPurchase: false,
        gatedBehindPurchase: true,
      },
    ],
    eligibility: STANDARD_ELIGIBILITY,
    expectedEarnings: { kind: "insufficient-data" },
  },
];

export const featuredIllustrativeOffer = illustrativeOffers[0];

/** ILLUSTRATIVE progress for the featured offer, used by the reward-tracker preview. */
export const illustrativeProgress = {
  day: 6,
  statuses: ["available", "available", "pending", "not-reached", "not-reached"],
} as const;
