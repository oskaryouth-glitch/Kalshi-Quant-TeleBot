import Link from "next/link";
import { site } from "@/lib/site-config";

/**
 * Mark: three ruled lines of a disclosure label, top line in accent.
 * It references the "Offer Facts" label rather than money imagery (DESIGN_SYSTEM.md).
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg className={className} width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
      <rect width="28" height="28" rx="8" fill="var(--color-ink)" />
      <rect x="7" y="8" width="14" height="2.6" rx="1.3" fill="var(--color-accent)" />
      <rect x="7" y="12.7" width="10.5" height="2.6" rx="1.3" fill="#fff" />
      <rect x="7" y="17.4" width="7" height="2.6" rx="1.3" fill="#fff" opacity="0.55" />
    </svg>
  );
}

export function Logo() {
  return (
    <Link
      href="/"
      className="inline-flex items-center gap-2.5 rounded-md"
      aria-label={`${site.name} home`}
    >
      <LogoMark />
      <span className="font-display text-[1.1875rem] font-semibold tracking-[-0.02em]">
        {site.name}
      </span>
    </Link>
  );
}
