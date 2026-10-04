import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { formatUsdCents } from "@/lib/money/format";
import { purchaseBadge, summarizeOffer } from "@/lib/offers/summary";
import type { Offer } from "@/lib/offers/types";
import { GameArt } from "./game-art";

/**
 * Browse-level card. Shows only what is needed to be interested without being surprised:
 * artwork, name, the headline amount (see summarizeOffer), purchase status, milestone count
 * and time limit. Full terms live in OfferDetail (DECISIONS D-019).
 */
export function OfferCardBody({ offer, featured = false }: { offer: Offer; featured?: boolean }) {
  const s = summarizeOffer(offer);
  const badge = purchaseBadge(offer.purchase);
  return (
    <>
      <div className={cn("relative overflow-hidden", featured ? "aspect-[16/8]" : "aspect-[16/9]")}>
        <GameArt variant={offer.art} className="size-full" />
        {offer.provenance === "illustrative" ? <ExampleTag /> : null}
      </div>
      <div className="flex flex-1 flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-semibold tracking-[-0.01em] text-ink">{offer.title}</p>
            <p className="text-sm text-ink-3">
              {offer.genre} · {offer.platform}
            </p>
          </div>
          <Badge tone={badge.tone} className="shrink-0">
            {badge.text}
          </Badge>
        </div>
        <div className="mt-4">
          <p
            className={cn(
              "num font-display leading-none font-semibold tracking-[-0.03em] text-ink",
              featured ? "text-[2.6rem]" : "text-3xl",
            )}
          >
            {formatUsdCents(s.headline.primaryCents)}
          </p>
          <p className="mt-1.5 text-sm text-ink-2">{s.headline.primaryLabel}</p>
          {s.headline.secondary ? (
            <p className="num mt-0.5 text-sm text-ink-3">{s.headline.secondary}</p>
          ) : null}
        </div>
        <div className="mt-auto flex items-center justify-between gap-3 pt-4 text-sm">
          <span className="text-ink-3">
            {offer.milestones.length} milestones · {offer.timeLimitDays}-day limit
          </span>
          <span className="inline-flex items-center gap-1 font-medium text-accent">
            View offer
            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path
                d="M3 8h9m0 0L8.5 4.5M12 8l-3.5 3.5"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        </div>
      </div>
    </>
  );
}

/**
 * Compact list row for secondary offers in the marketplace preview. The purchase status and
 * time limit get a full-width line and may wrap, but are never truncated.
 */
export function OfferRowBody({ offer }: { offer: Offer }) {
  const s = summarizeOffer(offer);
  const badge = purchaseBadge(offer.purchase);
  return (
    <>
      <div className="relative size-12 shrink-0 self-start overflow-hidden rounded-xl sm:size-16">
        <GameArt variant={offer.art} className="size-full" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <p className="truncate font-semibold tracking-[-0.01em] text-ink">{offer.title}</p>
          <p className="num shrink-0 font-display text-xl leading-none font-semibold tracking-[-0.02em] text-ink">
            {formatUsdCents(s.headline.primaryCents)}
          </p>
        </div>
        <div className="mt-1 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-[0.8125rem] leading-snug">
          <p className="text-ink-3" data-testid="offer-row-meta">
            <span
              className={cn(
                "whitespace-nowrap",
                badge.tone === "pending" && "font-medium text-pending",
              )}
            >
              {badge.text}
            </span>{" "}
            <span className="whitespace-nowrap">· {offer.timeLimitDays}-day limit</span>
          </p>
          <p className="text-ink-3">{s.hasPurchaseMilestones ? "without purchases" : "total"}</p>
        </div>
      </div>
    </>
  );
}

function ExampleTag() {
  return (
    <span className="absolute top-3 left-3 rounded-full bg-white/90 px-2.5 py-1 text-[0.6875rem] font-semibold tracking-wide text-ink uppercase shadow-sm backdrop-blur">
      Example
    </span>
  );
}
