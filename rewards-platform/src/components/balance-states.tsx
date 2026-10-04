import { cn } from "@/lib/cn";

type Tone = "neutral" | "pending" | "ok" | "bad";

const steps: { name: string; tone: Tone; body: string }[] = [
  {
    name: "Tracking",
    tone: "neutral",
    body: "You started through us. We record which offer terms you saw and when you started.",
  },
  {
    name: "Pending",
    tone: "pending",
    body: "A milestone was reported. The offer network is still checking it.",
  },
  {
    name: "Confirmed",
    tone: "pending",
    body: "The network approved it. A short holding period may still apply before withdrawal.",
  },
  {
    name: "Available",
    tone: "ok",
    body: "Yours to withdraw, subject to the minimums shown in your account.",
  },
];

const dot: Record<Tone, string> = {
  neutral: "bg-ink-3",
  pending: "bg-pending",
  ok: "bg-ok",
  bad: "bg-bad",
};

/**
 * Plain-language view of the reward lifecycle. This is the *planned* consumer model;
 * the full internal state machine (with disputes, holds and clawbacks) lives in
 * docs/ARCHITECTURE.md. Pages using this component must describe it as planned.
 */
export function BalanceStates({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] border border-line bg-surface p-5 sm:p-7",
        className,
      )}
    >
      <ol className="grid gap-5 md:grid-cols-4 md:gap-4">
        {steps.map((s, i) => (
          <li key={s.name} className="relative">
            <div className="flex items-center gap-2.5">
              <span className={cn("size-2.5 rounded-full", dot[s.tone])} aria-hidden="true" />
              <span className="num text-xs text-ink-3">0{i + 1}</span>
              <span className="font-semibold">{s.name}</span>
              {i < steps.length - 1 ? (
                <span
                  aria-hidden="true"
                  className="ml-auto hidden h-px flex-1 bg-line-strong md:block"
                />
              ) : null}
            </div>
            <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.body}</p>
          </li>
        ))}
      </ol>
      <div className="mt-6 flex gap-3 rounded-xl bg-bad-soft/60 p-4 text-sm leading-relaxed text-ink-2">
        <span className={cn("mt-1.5 size-2.5 shrink-0 rounded-full", dot.bad)} aria-hidden="true" />
        <p>
          <span className="font-semibold text-ink">Reversed or rejected.</span> Networks sometimes
          reject or reverse a milestone, for example if it fails their fraud checks. When that
          happens we plan to show it, say why when the network tells us, and explain how to dispute
          it.
        </p>
      </div>
    </div>
  );
}
