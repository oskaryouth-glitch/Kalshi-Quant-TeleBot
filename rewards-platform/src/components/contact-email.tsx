import { cn } from "@/lib/cn";
import { site } from "@/lib/site-config";

type Kind = keyof typeof site.contact;

/**
 * Renders a configured contact address, or an explicit "not configured" state.
 * We never fall back to a plausible-looking placeholder address (DECISIONS D-007).
 * `npm run check:launch` fails while any address is missing.
 */
export function ContactEmail({
  kind,
  subject,
  className,
}: {
  kind: Kind;
  subject?: string;
  className?: string;
}) {
  const address = site.contact[kind];
  if (!address) {
    return (
      <span data-missing-config={kind} className={cn("text-ink-3 italic", className)}>
        address not yet published
      </span>
    );
  }
  const href = `mailto:${address}${subject ? `?subject=${encodeURIComponent(subject)}` : ""}`;
  return (
    <a href={href} className={cn("text-accent underline underline-offset-4", className)}>
      {address}
    </a>
  );
}

export function contactHref(kind: Kind, subject?: string): string | null {
  const address = site.contact[kind];
  if (!address) return null;
  return `mailto:${address}${subject ? `?subject=${encodeURIComponent(subject)}` : ""}`;
}
