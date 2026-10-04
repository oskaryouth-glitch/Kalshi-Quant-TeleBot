import { useId } from "react";
import { cn } from "@/lib/cn";
import type { Estimate, IllustrativeOffer } from "@/lib/fixtures/illustrative-offer";
import { formatUsdCents, sumCents } from "@/lib/money/format";

/**
 * The Offer Facts label: a fixed-order, standardized disclosure for a single offer.
 * Order of rows is part of the design system (DESIGN_SYSTEM.md "Offer Facts") so users
 * can compare labels the way they compare nutrition labels.
 */
export function OfferFacts({ offer, className }: { offer: IllustrativeOffer; className?: string }) {
  const listedTotal = sumCents(offer.milestones.map((m) => m.rewardCents));
  const withoutPurchases = sumCents(
    offer.milestones.filter((m) => !m.isPurchase).map((m) => m.rewardCents),
  );
  const headingId = useId();

  return (
    <figure
      aria-labelledby={headingId}
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-card)] border border-ink/90 bg-surface shadow-[var(--shadow-lift)]",
        className,
      )}
    >
      {offer.provenance === "illustrative" ? (
        <div
          className="flex items-center justify-between gap-3 bg-[repeating-linear-gradient(135deg,var(--color-pending-soft)_0_10px,#fbe7c2_10px_20px)] px-5 py-2 text-[0.75rem] font-semibold tracking-wide text-pending uppercase"
          data-testid="illustrative-banner"
        >
          <span>Illustrative example</span>
          <span className="font-medium normal-case">Fictional game · not a real offer</span>
        </div>
      ) : null}

      <div className="px-5 pt-4 pb-5 sm:px-6">
        <div className="flex items-baseline justify-between gap-4 border-b-[6px] border-ink pb-2">
          <h3
            id={headingId}
            className="font-display text-[1.65rem] leading-none font-bold tracking-[-0.03em]"
          >
            Offer Facts
          </h3>
          <span className="text-xs text-ink-3">
            {offer.platform} · {offer.region}
          </span>
        </div>

        <div className="border-b border-ink/80 py-2.5">
          <p className="font-semibold">{offer.title}</p>
          <p className="text-sm text-ink-3">{offer.subtitle}</p>
        </div>

        <dl className="text-[0.9375rem]">
          <Row term="Deadline" detail={offer.deadline} />
          <Row term="Purchases" detail={purchaseCopy(offer.purchase)} />
          <Row
            term="Listed total"
            detail={<span className="num font-semibold">{formatUsdCents(listedTotal)}</span>}
            note="Every milestone added up, including purchases"
            strong
          />
          <Row
            term="Without purchases"
            detail={<span className="num font-semibold">{formatUsdCents(withoutPurchases)}</span>}
            strong
          />
        </dl>

        <div className="mt-1 border-t-[3px] border-ink pt-2">
          <p className="text-xs font-semibold tracking-wide text-ink-3 uppercase">
            Milestones, in order
          </p>
          <ol className="mt-1.5">
            {offer.milestones.map((m, i) => (
              <li
                key={m.label}
                className="flex items-baseline justify-between gap-3 border-b border-line py-1.5 text-[0.9375rem] last:border-b-0"
              >
                <span className="flex items-baseline gap-2.5">
                  <span className="num w-4 shrink-0 text-xs text-ink-3">{i + 1}</span>
                  <span>
                    {m.label}
                    {m.isPurchase ? (
                      <span className="ml-2 rounded bg-pending-soft px-1.5 py-0.5 text-[0.6875rem] font-semibold text-pending">
                        Purchase
                      </span>
                    ) : null}
                  </span>
                </span>
                <span className="num shrink-0 text-ink-2">{formatUsdCents(m.rewardCents)}</span>
              </li>
            ))}
          </ol>
        </div>

        <div className="mt-2 border-t-[3px] border-ink pt-2">
          <p className="text-xs font-semibold tracking-wide text-ink-3 uppercase">
            From real outcomes (shown once measured)
          </p>
          <dl className="text-[0.9375rem]">
            <EstimateRow term="Typical earnings" estimate={offer.estimates.typicalEarnings} />
            <EstimateRow
              term="Typical days to finish"
              estimate={offer.estimates.typicalDaysToFinish}
            />
            <EstimateRow term="Tracking record" estimate={offer.estimates.trackingRecord} />
          </dl>
        </div>
      </div>
      <figcaption className="sr-only">
        Illustrative Offer Facts label for a fictional game. Amounts are for layout only and are not
        a real offer. Outcome-based fields show that there is not enough data yet.
      </figcaption>
    </figure>
  );
}

function purchaseCopy(p: IllustrativeOffer["purchase"]): string {
  switch (p) {
    case "none":
      return "None";
    case "optional":
      return "Optional, listed separately";
    case "required":
      return "Required";
  }
}

function Row({
  term,
  detail,
  note,
  strong,
}: {
  term: string;
  detail: React.ReactNode;
  note?: string;
  strong?: boolean;
}) {
  return (
    <div className="border-b border-line py-2 last:border-b-0">
      <div className="flex items-baseline justify-between gap-4">
        <dt className={cn(strong ? "font-semibold text-ink" : "text-ink-2")}>{term}</dt>
        <dd className="text-right">{detail}</dd>
      </div>
      {note ? <p className="mt-0.5 text-xs text-ink-3">{note}</p> : null}
    </div>
  );
}

function EstimateRow({ term, estimate }: { term: string; estimate: Estimate }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line py-2 last:border-b-0">
      <dt className="text-ink-2">{term}</dt>
      <dd className="text-right">
        {estimate.kind === "insufficient-data" ? (
          <span className="inline-flex items-center gap-1.5 text-sm text-ink-3">
            <span
              aria-hidden="true"
              className="inline-block size-1.5 rounded-full bg-line-strong"
            />
            {estimate.note}
          </span>
        ) : (
          <span className="num font-semibold">
            {estimate.display}
            <span className="ml-1 text-xs font-normal text-ink-3">n={estimate.sampleSize}</span>
          </span>
        )}
      </dd>
    </div>
  );
}
