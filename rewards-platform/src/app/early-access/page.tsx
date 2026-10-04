import type { Metadata } from "next";
import Link from "next/link";
import { ContactEmail } from "@/components/contact-email";
import { WaitlistForm } from "@/components/waitlist-form";
import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/section";
import { site } from "@/lib/site-config";
import { isWaitlistOpen } from "@/lib/waitlist/config";

export const metadata: Metadata = {
  title: "Early access",
  description: `Join the ${site.name} early-access list. We ask for your email and phone type only.`,
};

const collected: Array<[string, string]> = [
  ["Email address", "To tell you when early access opens."],
  ["Phone type", "To decide whether and when to support iPhone."],
  ["Optional note", "Only if you choose to write one."],
  ["Referral tag", "If you arrived from a link with a ?ref= tag, so we know which channels work."],
  [
    "Date and policy version",
    "When you joined and which version of the privacy policy you agreed to.",
  ],
];

export default function EarlyAccessPage() {
  const open = isWaitlistOpen();

  return (
    <div className="border-b border-line">
      <Container className="grid gap-12 py-14 sm:py-20 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
        <div>
          <Eyebrow>Early access</Eyebrow>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-[-0.03em] text-balance sm:text-5xl">
            Be first to try it.
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-ink-2">
            We are pre-launch and starting with Android users in the {site.market}. Join the list
            and we will email you when early access opens. Joining does not create an account, and
            nothing is being offered or paid yet.
          </p>

          <div className="mt-10 rounded-[var(--radius-card)] border border-line bg-surface p-6">
            <h2 className="font-semibold">What we collect, and why</h2>
            <dl className="mt-4 space-y-3 text-[0.9375rem]">
              {collected.map(([term, why]) => (
                <div key={term}>
                  <dt className="font-medium text-ink">{term}</dt>
                  <dd className="text-ink-2">{why}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-5 text-sm leading-relaxed text-ink-3">
              No tracking cookies, no ad pixels and no selling your information.{" "}
              <Link href="/privacy" className="text-accent underline underline-offset-4">
                Privacy policy
              </Link>
            </p>
          </div>
        </div>

        <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6 shadow-[var(--shadow-card)] sm:p-9">
          {open ? (
            <WaitlistForm />
          ) : (
            <div role="status">
              <p className="font-display text-2xl font-semibold tracking-[-0.02em]">
                Sign-ups open soon.
              </p>
              <p className="mt-3 leading-relaxed text-ink-2">
                We are not accepting early-access sign-ups through this page yet. To be added
                manually, email <ContactEmail kind="support" subject="Early access" />.
              </p>
            </div>
          )}
        </div>
      </Container>
    </div>
  );
}
