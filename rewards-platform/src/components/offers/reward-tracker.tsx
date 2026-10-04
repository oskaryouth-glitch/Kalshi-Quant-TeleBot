import { cn } from "@/lib/cn";
import { formatUsdCents, sumCents } from "@/lib/money/format";
import type { Offer } from "@/lib/offers/types";
import { GameArt } from "./game-art";

export type MilestoneStatus = "available" | "confirmed" | "pending" | "not-reached";

const statusUi: Record<MilestoneStatus, { text: string; dot: string; chip: string }> = {
  available: { text: "Available", dot: "bg-ok", chip: "bg-ok-soft text-ok" },
  confirmed: {
    text: "Confirmed, on hold",
    dot: "bg-pending",
    chip: "bg-pending-soft text-pending",
  },
  pending: { text: "Pending check", dot: "bg-pending", chip: "bg-pending-soft text-pending" },
  "not-reached": { text: "Not reached", dot: "bg-line-strong", chip: "bg-paper-deep text-ink-3" },
};

/**
 * ILLUSTRATIVE progress view for one offer: per-milestone status and the balance split.
 * Mirrors the planned reward lifecycle (docs/ARCHITECTURE.md 2.5). Not live functionality.
 */
export function RewardTracker({
  offer,
  statuses,
  day,
  className,
}: {
  offer: Offer;
  statuses: MilestoneStatus[];
  day: number;
  className?: string;
}) {
  const sumWhere = (s: MilestoneStatus) =>
    sumCents(offer.milestones.filter((_, i) => statuses[i] === s).map((m) => m.rewardCents));
  const reached = statuses.filter((s) => s !== "not-reached").length;
  const pct = Math.round((reached / offer.milestones.length) * 100);

  return (
    <div
      className={cn(
        "overflow-hidden rounded-[1.75rem] border border-line bg-surface shadow-[var(--shadow-lift)]",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
        <p className="font-semibold tracking-[-0.01em]">My offers</p>
        <span className="rounded-full bg-pending-soft px-2.5 py-1 text-[0.6875rem] font-semibold tracking-wide text-pending uppercase">
          Example
        </span>
      </div>
      <div className="p-5">
        <div className="flex items-center gap-3">
          <div className="size-12 shrink-0 overflow-hidden rounded-xl">
            <GameArt variant={offer.art} className="size-full" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{offer.title}</p>
            <p className="text-sm text-ink-3">
              Day {day} of {offer.timeLimitDays} · {reached} of {offer.milestones.length} milestones
            </p>
          </div>
        </div>
        <div
          className="mt-4 h-2 overflow-hidden rounded-full bg-paper-deep"
          role="img"
          aria-label={`${reached} of ${offer.milestones.length} milestones reached`}
        >
          <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
        </div>

        <ol className="mt-5 space-y-2.5">
          {offer.milestones.map((m, i) => {
            const ui = statusUi[statuses[i]];
            return (
              <li key={m.label} className="flex items-center gap-3 text-[0.9375rem]">
                <span className={cn("size-2.5 shrink-0 rounded-full", ui.dot)} aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate">{m.label}</span>
                <span className="num shrink-0 text-ink-2">{formatUsdCents(m.rewardCents)}</span>
                <span
                  className={cn(
                    "hidden shrink-0 rounded-full px-2 py-0.5 text-[0.75rem] font-medium sm:inline",
                    ui.chip,
                  )}
                >
                  {ui.text}
                </span>
                <span className="sr-only sm:hidden">{ui.text}</span>
              </li>
            );
          })}
        </ol>

        <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-line pt-4">
          <div>
            <dt className="text-[0.75rem] text-ink-3">Available</dt>
            <dd className="num font-display text-2xl font-semibold tracking-[-0.02em]">
              {formatUsdCents(sumWhere("available"))}
            </dd>
          </div>
          <div>
            <dt className="text-[0.75rem] text-ink-3">Pending or on hold</dt>
            <dd className="num font-display text-2xl font-semibold tracking-[-0.02em] text-ink-2">
              {formatUsdCents(sumWhere("pending") + sumWhere("confirmed"))}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
