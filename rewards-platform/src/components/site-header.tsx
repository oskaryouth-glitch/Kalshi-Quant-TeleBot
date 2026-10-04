"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { cn } from "@/lib/cn";
import { primaryNav } from "@/lib/navigation";
import { Logo } from "./logo";
import { buttonClasses } from "./ui/button";

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [lastPath, setLastPath] = useState(pathname);
  const panelId = useId();

  // Close the mobile menu after navigation (state adjustment during render, no effect needed).
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-paper/85 backdrop-blur-md supports-[backdrop-filter]:bg-paper/75">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Logo />

        <nav aria-label="Primary" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {primaryNav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isActive(item.href) ? "page" : undefined}
                  className={cn(
                    "rounded-full px-3.5 py-2 text-[0.9375rem] text-ink-2 transition-colors hover:text-ink",
                    isActive(item.href) && "bg-paper-deep text-ink",
                  )}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/early-access"
            className={buttonClasses("primary", "hidden min-h-10 px-4 sm:inline-flex")}
          >
            Get early access
          </Link>
          <button
            type="button"
            className="inline-flex size-11 items-center justify-center rounded-full text-ink hover:bg-paper-deep md:hidden"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((v) => !v)}
          >
            <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
            <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
              {open ? (
                <path
                  d="M5 5l12 12M17 5L5 17"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              ) : (
                <path
                  d="M3.5 7h15M3.5 15h15"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      <div id={panelId} hidden={!open} className="border-t border-line bg-paper md:hidden">
        <nav aria-label="Mobile" className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <ul className="flex flex-col">
            {primaryNav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isActive(item.href) ? "page" : undefined}
                  className="flex min-h-12 items-center border-b border-line text-lg text-ink"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <Link href="/early-access" className={buttonClasses("primary", "mt-5 w-full")}>
            Get early access
          </Link>
        </nav>
      </div>
    </header>
  );
}
