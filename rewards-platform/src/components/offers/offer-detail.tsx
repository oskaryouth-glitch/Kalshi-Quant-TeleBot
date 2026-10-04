import { useId } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { formatUsdCents } from "@/lib/money/format";
import { needsPurchase, purchaseBadge, summarizeOffer } from "@/lib/offers/summary";
import type { Offer } from "@/lib/offers/types";
import { GameArt } from "./game-art";

/**
 * Full pre-start disclosure for one offer: every milestone and reward in order, the time
 * limit, purchase requirements and eligibility conditions. Nothing material may be omitted
 * here (DECISIONS D-019). Used both inline and inside the offer dialog.
 */
export function OfferDetail({
  offer,
  headingLevel = "h3",
  titleId,
}: {
  offer: Offer;
  headingLevel?: "h2" | "h3";
  titleId?: string;
}) {
  const s = summarizeOffer(offer);
  const badge = purchaseBadge(offer.purchase);
  const fallbackId = useId();
  const headingId = titleId ?? fallbackId;
  const Heading = headingLevel;
  const Sub = headingLevel === "h2" ? "h3" : "h4";

  return (
    <article aria-labelledby={headingId} className="text-ink">
      <div className="flex items-center gap-4">
        <div className="size-16 shrink-0 overflow-hidden rounded-2xl sm:size-20">
          <GameArt variant={offer.art} className="size-full" />
        </div>
        <div className="min-w-0">
          {offer.provenance === "illustrative" ? (
            <p className="text-[0.75rem] font-semibold tracking-wide text-pending uppercase">
              Example offer · amounts invented for illustration
            </p>
          ) : null}
          <Heading
            id={headingId}
            className="font-display text-2xl leading-tight font-semibold tracking-[-0.02em]"
          >
            {offer.title}
          </Heading>
          <p className="text-sm text-ink-3">
            {offer.genre} · {offer.platform} · {offer.region}
          </p>
        </div>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          term={s.hasPurchaseMilestones ? "Without purchases" : "Total rewards"}
          value={formatUsdCents(s.withoutPurchasesCents)}
          strong
        />
        <Stat
          term="With purchases"
          value={s.hasPurchaseMilestones ? formatUsdCents(s.totalCents) : "Not applicable"}
        />
        <Stat term="Time limit" value={`${offer.timeLimitDays} days from install`} />
        <Stat term="Purchases" value={badge.text} />
      </dl>

      <section className="mt-7" aria-label="Milestones">
        <Sub className="text-sm font-semibold tracking-wide text-ink-3 uppercase">
          Milestones, in order
        </Sub>
        <ol className="mt-3">
          {offer.milestones.map((m, i) => {
            const paid = needsPurchase(m);
            const last = i === offer.milestones.length - 1;
            return (
              <li key={m.label} className="relative flex gap-4 pb-4 last:pb-0">
                {!last ? (
                  <span
                    aria-hidden="true"
                    className="absolute top-8 bottom-0 left-[0.9375rem] w-px bg-line-strong"
                  />
                ) : null}
                <span
                  className={cn(
                    "num relative z-10 flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold",
                    paid ? "bg-pending-soft text-pending" : "bg-accent-soft text-accent",
                  )}
                >
                  {i + 1}
                </span>
                <div className="flex min-w-0 flex-1 items-start justify-between gap-3 pt-1">
                  <div>
                    <p className="leading-snug">{m.label}</p>
                    {m.isPurchase ? (
                      <p className="mt-0.5 text-[0.8125rem] font-medium text-pending">
                        Requires spending money in the game
                      </p>
                    ) : null}
                    {m.gatedBehindPurchase ? (
                      <p className="mt-0.5 text-[0.8125rem] font-medium text-pending">
                        Only reachable after the purchase above
                      </p>
                    ) : null}
                  </div>
                  <span className="num shrink-0 font-semibold">
                    {formatUsdCents(m.rewardCents)}
                  </span>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="mt-7 rounded-2xl bg-paper p-4 sm:p-5" aria-label="Before you start">
        <Sub className="font-semibold">Before you start</Sub>
        <ul className="mt-3 space-y-2.5 text-[0.9375rem] leading-relaxed text-ink-2">
          <li className="flex gap-2.5">
            <Check />
            <span>
              Finish each milestone within {offer.timeLimitDays} days of installing. Milestones
              reached after that do not pay.
            </span>
          </li>
          {offer.eligibility.map((e) => (
            <li key={e} className="flex gap-2.5">
              <Check />
              <span>{e}</span>
            </li>
          ))}
          <li className="flex gap-2.5">
            <Check />
            <span>
              Rewards are credited when the offer network confirms each milestone. That can take
              time, and networks can reject or reverse rewards.
            </span>
          </li>
        </ul>
      </section>

      {offer.provenance === "illustrative" ? (
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Badge tone="neutral">Preview only. Offers are not live yet.</Badge>
          <button
            type="button"
            disabled
            className="inline-flex min-h-11 items-center justify-center rounded-full bg-ink px-5 font-medium text-white opacity-40"
          >
            Start offer
          </button>
        </div>
      ) : null}
    </article>
  );
}

function Stat({ term, value, strong }: { term: string; value: string; strong?: boolean }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-3">
      <dt className="text-[0.75rem] text-ink-3">{term}</dt>
      <dd
        className={cn("num mt-1 leading-tight", strong ? "text-lg font-semibold" : "font-medium")}
      >
        {value}
      </dd>
    </div>
  );
}

function Check() {
  return (
    <svg
      aria-hidden="true"
      width="18"
      height="18"
      viewBox="0 0 20 20"
      className="mt-0.5 shrink-0 text-ok"
    >
      <path
        d="M5 10.5l3 3 7-7"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
