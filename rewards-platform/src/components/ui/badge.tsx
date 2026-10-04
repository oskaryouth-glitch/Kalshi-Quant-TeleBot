import { cn } from "@/lib/cn";

type Tone = "neutral" | "accent" | "pending" | "ok" | "bad";

const tones: Record<Tone, string> = {
  neutral: "bg-paper-deep text-ink-2",
  accent: "bg-accent-soft text-accent",
  pending: "bg-pending-soft text-pending",
  ok: "bg-ok-soft text-ok",
  bad: "bg-bad-soft text-bad",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium tracking-wide",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
