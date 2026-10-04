import type { Metadata } from "next";
import { ContactEmail } from "@/components/contact-email";
import { Arrow, ButtonLink } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Section } from "@/components/ui/section";
import { site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "About",
  description: `${site.name} is an early-stage, pre-launch company building a clearer way to choose rewarded mobile-game offers.`,
};

export default function AboutPage() {
  const facts: Array<[string, React.ReactNode]> = [
    ["Stage", "Pre-launch. The product is not live."],
    [
      "Legal entity",
      site.legalEntity ? (
        `${site.legalEntity}${site.entityJurisdiction ? `, a ${site.entityJurisdiction} company` : ""}`
      ) : (
        <span className="text-ink-3 italic">not yet published</span>
      ),
    ],
    ["Market", `${site.market}, adults ${site.minimumAge}+`],
    ["Initial focus", "Rewarded offers in Android mobile games"],
    ["Contact", <ContactEmail key="c" kind="support" />],
  ];

  return (
    <>
      <PageHeader
        eyebrow="About"
        title="We think choosing an offer should be the easy part."
        intro={`${site.name} is an early-stage company building a consumer product for rewarded mobile-game offers. We have not launched yet.`}
      />
      <Section>
        <div className="grid gap-14 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="max-w-2xl space-y-5 text-lg leading-relaxed text-ink-2">
            <h2 className="font-display text-2xl font-semibold tracking-[-0.02em] text-ink">
              Why we are building this
            </h2>
            <p>
              Lots of apps and websites will pay you to try new mobile games. The offers themselves
              are often similar from one place to the next. What is hard is knowing which ones are
              worth your time: what each one really requires, how long it tends to take, and whether
              your progress will actually be credited.
            </p>
            <p>
              We want to answer those questions honestly. That starts with showing every offer’s
              requirements in one consistent format, and grows into figures based on real, measured
              outcomes, published with their sample sizes and limits.
            </p>
            <h2 className="pt-4 font-display text-2xl font-semibold tracking-[-0.02em] text-ink">
              How we work
            </h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>
                We test assumptions before building on them, and change course when they fail.
              </li>
              <li>We do not claim partnerships, users or results we do not have.</li>
              <li>We label plans as plans. This site will say when something becomes real.</li>
            </ul>
          </div>
          <aside aria-labelledby="facts-heading">
            <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6">
              <h2 id="facts-heading" className="font-semibold">
                Company facts
              </h2>
              <dl className="mt-4 divide-y divide-line text-[0.9375rem]">
                {facts.map(([term, detail]) => (
                  <div key={term} className="grid grid-cols-[7.5rem_1fr] gap-3 py-3">
                    <dt className="text-ink-3">{term}</dt>
                    <dd className="text-ink">{detail}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="mt-6 flex flex-col gap-3">
              <ButtonLink href="/early-access">
                Get early access <Arrow />
              </ButtonLink>
              <ButtonLink href="/partners" variant="secondary">
                For partners
              </ButtonLink>
            </div>
          </aside>
        </div>
      </Section>
    </>
  );
}
