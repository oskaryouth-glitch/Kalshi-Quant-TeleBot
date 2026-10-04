import { describe, expect, it } from "vitest";
import { illustrativeOffers } from "@/lib/fixtures/illustrative-offers";
import { MIN_DISPLAY_SAMPLE, isDisplayableEstimate, summarizeOffer } from "./summary";
import type { Offer } from "./types";

const base: Offer = {
  provenance: "illustrative",
  id: "t",
  title: "Test",
  genre: "Test",
  art: "city",
  platform: "Android",
  region: "US",
  timeLimitDays: 7,
  purchase: "none",
  milestones: [
    { label: "A", rewardCents: 100, isPurchase: false },
    { label: "B", rewardCents: 250, isPurchase: false },
  ],
  eligibility: [],
  expectedEarnings: { kind: "insufficient-data" },
};

const estimate = (sampleSize: number, estimatorVersion = "v1") =>
  ({
    kind: "estimate",
    valueCents: 120,
    sampleSize,
    estimatorVersion,
    windowStart: "2027-01-01",
    windowEnd: "2027-03-31",
  }) as const;

describe("summarizeOffer headline", () => {
  it("leads with the total when no purchases are involved", () => {
    const s = summarizeOffer(base);
    expect(s.headline).toEqual({
      primaryCents: 350,
      primaryLabel: "total rewards available",
      secondary: null,
      isExpected: false,
    });
  });

  it("never leads with a number that requires spending money", () => {
    const s = summarizeOffer({
      ...base,
      purchase: "optional",
      milestones: [...base.milestones, { label: "Buy", rewardCents: 900, isPurchase: true }],
    });
    expect(s.headline.primaryCents).toBe(350);
    expect(s.headline.primaryLabel).toBe("available without purchases");
    expect(s.headline.secondary).toBe("$12.50 with purchases");
  });

  it("excludes milestones gated behind a required purchase from the no-purchase total", () => {
    const s = summarizeOffer({
      ...base,
      purchase: "required",
      milestones: [
        { label: "A", rewardCents: 100, isPurchase: false },
        { label: "Buy", rewardCents: 500, isPurchase: true },
        { label: "After", rewardCents: 2000, isPurchase: false, gatedBehindPurchase: true },
      ],
    });
    expect(s.withoutPurchasesCents).toBe(100);
    expect(s.totalCents).toBe(2600);
    expect(s.headline.primaryCents).toBe(100);
  });

  it("uses measured expected earnings only when the sample is large enough", () => {
    const small = summarizeOffer({ ...base, expectedEarnings: estimate(MIN_DISPLAY_SAMPLE - 1) });
    expect(small.headline.isExpected).toBe(false);

    const big = summarizeOffer({ ...base, expectedEarnings: estimate(MIN_DISPLAY_SAMPLE) });
    expect(big.headline).toMatchObject({
      primaryCents: 120,
      isExpected: true,
      secondary: "$3.50 max",
    });
    expect(big.headline.primaryLabel).toContain(String(MIN_DISPLAY_SAMPLE));
  });

  it("refuses estimates without an estimator version", () => {
    expect(isDisplayableEstimate(estimate(500, " "))).toBe(false);
  });
});

describe("illustrative fixtures", () => {
  it("are all illustrative, genre-named and carry no outcome data", () => {
    for (const o of illustrativeOffers) {
      expect(o.provenance).toBe("illustrative");
      expect(o.expectedEarnings.kind).toBe("insufficient-data");
      expect(summarizeOffer(o).headline.isExpected).toBe(false);
    }
  });

  it("label purchase requirements consistently with their milestones", () => {
    for (const o of illustrativeOffers) {
      const hasPurchase = o.milestones.some((m) => m.isPurchase);
      expect(o.purchase === "none", o.id).toBe(!hasPurchase);
      const gated = o.milestones.some((m) => m.gatedBehindPurchase);
      if (gated) expect(o.purchase, o.id).toBe("required");
    }
  });
});
