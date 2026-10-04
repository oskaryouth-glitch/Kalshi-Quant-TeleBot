"use client";

import { useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import type { Offer } from "@/lib/offers/types";
import { OfferCardBody, OfferRowBody } from "./offer-card";
import { OfferDetail } from "./offer-detail";

/**
 * Hero preview of the future marketplace. ILLUSTRATIVE ONLY: the frame always carries an
 * "Example preview" label, and every offer must have provenance "illustrative".
 *
 * Cards are links to the inline example detail (#example-offer) so the page works without
 * JavaScript; with JavaScript they open the full offer detail in a native modal <dialog>.
 */
export function MarketplacePreview({ offers }: { offers: Offer[] }) {
  const [featured, ...rest] = offers;
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [active, setActive] = useState<Offer | null>(null);
  const titleId = useId();

  useEffect(() => {
    const d = dialogRef.current;
    if (active && d && !d.open) d.showModal();
  }, [active]);

  const open = (offer: Offer) => (e: React.MouseEvent) => {
    e.preventDefault();
    setActive(offer);
  };

  return (
    <div className="relative">
      <div className="overflow-hidden rounded-[1.75rem] border border-line bg-surface shadow-[var(--shadow-lift)]">
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-5">
          <p className="font-semibold tracking-[-0.01em]">Offers for you</p>
          <span
            data-testid="illustrative-banner"
            className="rounded-full bg-pending-soft px-2.5 py-1 text-[0.6875rem] font-semibold tracking-wide text-pending uppercase"
          >
            Examples · not real offers
          </span>
        </div>
        <div aria-hidden="true" className="flex gap-2 overflow-hidden px-4 pt-3 sm:px-5">
          {["All games", "No purchase needed", "Puzzle", "Racing"].map((chip, i) => (
            <span
              key={chip}
              className={cn(
                "shrink-0 rounded-full px-3 py-1 text-[0.8125rem]",
                i === 0 ? "bg-ink text-white" : "bg-paper-deep text-ink-2",
              )}
            >
              {chip}
            </span>
          ))}
        </div>

        <div className="space-y-3 p-4 sm:p-5">
          <a
            href="#example-offer"
            onClick={open(featured)}
            aria-haspopup="dialog"
            className="group flex flex-col overflow-hidden rounded-2xl border border-line bg-surface transition duration-150 hover:-translate-y-0.5 hover:border-line-strong hover:shadow-[var(--shadow-card)]"
          >
            <OfferCardBody offer={featured} featured />
          </a>
          <ul className="divide-y divide-line rounded-2xl border border-line">
            {rest.map((offer) => (
              <li key={offer.id}>
                <a
                  href="#example-offer"
                  onClick={open(offer)}
                  aria-haspopup="dialog"
                  aria-label={`${offer.title}, example offer. View details`}
                  className="flex items-center gap-3 p-3 transition-colors hover:bg-paper sm:gap-4"
                >
                  <OfferRowBody offer={offer} />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        onClose={() => setActive(null)}
        onClick={(e) => {
          // Clicking the backdrop (the dialog element itself) closes it.
          if (e.target === e.currentTarget) e.currentTarget.close();
        }}
        className="m-auto max-h-[92vh] w-[min(40rem,calc(100vw-1.5rem))] overflow-y-auto overscroll-contain rounded-[1.5rem] bg-surface p-0 text-ink shadow-[var(--shadow-lift)] backdrop:bg-ink/50 backdrop:backdrop-blur-[2px]"
      >
        {active ? (
          <div className="relative p-5 sm:p-7">
            <form method="dialog" className="absolute top-3 right-3">
              <button
                type="submit"
                className="inline-flex size-10 items-center justify-center rounded-full text-ink-2 hover:bg-paper-deep"
              >
                <span className="sr-only">Close offer details</span>
                <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true">
                  <path
                    d="M5 5l10 10M15 5L5 15"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </form>
            <OfferDetail offer={active} headingLevel="h2" titleId={titleId} />
          </div>
        ) : null}
      </dialog>
    </div>
  );
}
