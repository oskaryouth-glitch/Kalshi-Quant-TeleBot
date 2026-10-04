import { cn } from "@/lib/cn";
import { Container } from "./container";

export function Section({
  id,
  className,
  children,
  tone = "paper",
  labelledBy,
}: {
  id?: string;
  className?: string;
  children: React.ReactNode;
  tone?: "paper" | "surface" | "ink";
  labelledBy?: string;
}) {
  return (
    <section
      id={id}
      aria-labelledby={labelledBy}
      className={cn(
        "py-16 sm:py-24",
        tone === "surface" && "border-y border-line bg-surface",
        tone === "ink" && "bg-ink text-white",
        className,
      )}
    >
      <Container>{children}</Container>
    </section>
  );
}

export function Eyebrow({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-[0.8125rem] font-semibold uppercase tracking-[0.14em] text-accent",
        className,
      )}
    >
      {children}
    </p>
  );
}

export function SectionHeading({
  id,
  eyebrow,
  title,
  intro,
  className,
}: {
  id?: string;
  eyebrow?: string;
  title: React.ReactNode;
  intro?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("max-w-2xl", className)}>
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <h2
        id={id}
        className="mt-3 font-display text-3xl font-semibold tracking-[-0.025em] text-balance sm:text-4xl"
      >
        {title}
      </h2>
      {intro ? (
        <p className="mt-4 text-lg leading-relaxed text-pretty text-ink-2">{intro}</p>
      ) : null}
    </div>
  );
}
