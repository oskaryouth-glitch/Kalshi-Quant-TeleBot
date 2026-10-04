import Link from "next/link";
import { footerNav } from "@/lib/navigation";
import { site } from "@/lib/site-config";
import { LogoMark } from "./logo";

export function SiteFooter() {
  const year = new Date().getUTCFullYear();
  const owner = site.legalEntity ?? site.name;

  return (
    <footer className="mt-auto border-t border-line bg-paper">
      <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div className="max-w-xs">
            <div className="flex items-center gap-2.5">
              <LogoMark />
              <span className="font-display text-lg font-semibold tracking-[-0.02em]">
                {site.name}
              </span>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-ink-3">
              Pre-launch. We are not yet listing offers, holding balances or paying rewards.
            </p>
          </div>
          {footerNav.map((group) => (
            <nav key={group.heading} aria-label={group.heading}>
              <h2 className="text-sm font-semibold text-ink">{group.heading}</h2>
              <ul className="mt-3 space-y-2">
                {group.items.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className="text-sm text-ink-3 hover:text-ink">
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <div className="mt-12 flex flex-col gap-3 border-t border-line pt-6 text-xs leading-relaxed text-ink-3 sm:flex-row sm:justify-between">
          <p>
            © {year} {owner}. Intended for adults ({site.minimumAge}+) in the {site.market}.
          </p>
          <p className="max-w-xl sm:text-right">
            Game names and trademarks belong to their owners. We do not claim partnerships or
            endorsements we do not have.
          </p>
        </div>
      </div>
    </footer>
  );
}
