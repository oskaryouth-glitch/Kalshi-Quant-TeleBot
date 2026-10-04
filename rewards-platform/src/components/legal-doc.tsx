import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/section";

/** Shared shell for policy pages, including a visible draft notice while under legal review. */
export function LegalDoc({
  eyebrow,
  title,
  version,
  children,
}: {
  eyebrow: string;
  title: string;
  version: string;
  children: React.ReactNode;
}) {
  const isDraft = version.endsWith("-draft");
  return (
    <Container size="narrow" className="py-14 sm:py-20">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h1 className="mt-4 font-display text-4xl font-semibold tracking-[-0.03em] sm:text-5xl">
        {title}
      </h1>
      <p className="mt-4 text-sm text-ink-3">
        Version <span className="num">{version}</span>
      </p>
      {isDraft ? (
        <div
          role="note"
          className="mt-6 rounded-xl border border-pending/25 bg-pending-soft p-4 text-[0.9375rem] leading-relaxed text-ink"
        >
          <strong className="font-semibold">Draft, pending legal review.</strong> This document
          describes what this pre-launch website actually does today. It has not yet been reviewed
          by legal counsel and will be revised before we launch the product.
        </div>
      ) : null}
      <div className="prose-doc mt-10">{children}</div>
    </Container>
  );
}
