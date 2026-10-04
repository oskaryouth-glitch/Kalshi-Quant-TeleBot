import Link from "next/link";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost";

const base =
  "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors duration-150 " +
  "min-h-11 px-5 py-2 text-center text-[0.9375rem] disabled:cursor-not-allowed disabled:opacity-60";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink-2",
  secondary: "border border-line-strong bg-surface text-ink hover:border-ink-3",
  ghost: "text-ink hover:bg-paper-deep",
};

export function buttonClasses(variant: Variant = "primary", className?: string) {
  return cn(base, variants[variant], className);
}

export function ButtonLink({
  href,
  variant = "primary",
  className,
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: React.ReactNode;
}) {
  const isExternal = href.startsWith("mailto:") || href.startsWith("http");
  if (isExternal) {
    return (
      <a href={href} className={buttonClasses(variant, className)}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={buttonClasses(variant, className)}>
      {children}
    </Link>
  );
}

export function Arrow() {
  return (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path
        d="M3 8h9m0 0L8.5 4.5M12 8l-3.5 3.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
