import type { Metadata } from "next";
import { ContactEmail, contactHref } from "@/components/contact-email";
import { StatusList, type Commitment } from "@/components/status-list";
import { Arrow, ButtonLink } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Section, SectionHeading } from "@/components/ui/section";
import { site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "For partners",
  description: `${site.name} is a pre-launch US consumer rewards publisher focused on Android game offers. How we plan to integrate, attribute, control fraud and present offers.`,
};

const snapshot: Array<[string, string]> = [
  ["Stage", "Pre-launch. No live traffic and no live integrations yet."],
  ["Market", `${site.market} only. Adults ${site.minimumAge}+.`],
  ["Initial focus", "Android mobile game offers, including multi-milestone (CPE) offers."],
  ["Integration model", "Offer catalog API feeding our own interface. Server-to-server postbacks."],
  [
    "User rewards",
    "Cash-equivalent and/or gift card rewards, only where a network's terms permit them in writing.",
  ],
  [
    "Traffic sources",
    "Starting with organic search, organic social content and direct visits. We confirm permitted sources with each network before using them.",
  ],
];

const integration: Commitment[] = [
  {
    title: "Stable, opaque user identifiers",
    body: "Each user gets one internal ID that we pass as the sub-ID. It never contains an email address or other personal data, and it is never reassigned.",
    status: "planned",
  },
  {
    title: "Verified server-to-server postbacks",
    body: "Conversion and reversal callbacks are verified using each network's signing scheme (signatures, secrets or IP allowlists, as documented). Unverified callbacks are rejected and logged.",
    status: "planned",
  },
  {
    title: "Idempotent processing",
    body: "Network transaction IDs are stored once and never overwritten. Duplicate or replayed callbacks cannot credit a user twice.",
    status: "planned",
  },
  {
    title: "Single attribution per attempt",
    body: "If we work with more than one network, each user's attempt at an offer is attributed to exactly one network, chosen before they start. We never switch attribution after a user begins.",
    status: "planned",
  },
  {
    title: "Reversals honored end to end",
    body: "A reversal from a network removes the matching reward from the user's balance. Holding periods before withdrawal will be set with each network's reversal window in mind.",
    status: "planned",
  },
  {
    title: "Raw records kept for reconciliation",
    body: "Original catalog responses and postback payloads are preserved unchanged, so we can reconcile against your reporting and investigate disputes with evidence.",
    status: "planned",
  },
];

const quality: Commitment[] = [
  {
    title: "Adults in the US only",
    body: `Accounts are for people ${site.minimumAge} and over in the ${site.market}. Offers are shown only where the network's targeting allows.`,
    status: "planned",
  },
  {
    title: "One account per person",
    body: "Duplicate-account detection and verification before a first withdrawal.",
    status: "planned",
  },
  {
    title: "Risk signals and withdrawal holds",
    body: "Device, network and behavior signals feed holds and manual review. A flagged account cannot withdraw until it is reviewed.",
    status: "planned",
  },
  {
    title: "Your fraud guidance, applied",
    body: "Where a network publishes fraud or traffic-quality requirements, we build to them and treat repeated rejections from a network as a signal to investigate our own traffic.",
    status: "planned",
  },
];

const presentation: Commitment[] = [
  {
    title: "Requirements shown as you define them",
    body: "Milestones, deadlines and restrictions are displayed accurately and not reworded in ways that change their meaning.",
    status: "planned",
  },
  {
    title: "No inflated headlines",
    body: "We do not lead with maximum possible totals. Purchase milestones are labeled and totals are shown both with and without them.",
    status: "planned",
  },
  {
    title: "Clear incentive disclosure",
    body: "Users always know they are completing an offer in exchange for a reward, and that the reward depends on the network verifying the milestone.",
    status: "planned",
  },
];

const questions = [
  "Are cash-equivalent rewards (for example PayPal) and gift card rewards permitted?",
  "May we build our own interface on your catalog API, and sort and rank offers ourselves?",
  "May we integrate other networks at the same time?",
  "Which traffic sources are permitted: organic social, paid social, search, brand bidding?",
  "What are the reversal rules and the longest reversal window?",
  "What are the payment schedule, minimum payout and any reserve or holding terms?",
  "Is there a full catalog endpoint, with per-milestone payouts and store identifiers?",
  "How are conversion and reversal postbacks signed?",
];

export default function PartnersPage() {
  const mail = contactHref("partners", `Partnership inquiry: ${site.name}`);

  return (
    <>
      <PageHeader
        eyebrow="For offer networks"
        title="A US rewards publisher you can audit."
        intro={`${site.name} is a pre-launch consumer rewards product for US adults, starting with Android game offers. We are looking for publisher partnerships with networks that support custom API integrations and allow cash-equivalent user rewards.`}
      >
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          {mail ? (
            <ButtonLink href={mail}>
              Email partnerships <Arrow />
            </ButtonLink>
          ) : null}
          <ButtonLink href="#integration" variant="secondary">
            Integration plan
          </ButtonLink>
        </div>
      </PageHeader>

      <Section labelledBy="snapshot-heading">
        <SectionHeading id="snapshot-heading" eyebrow="At a glance" title="Where we are today." />
        <dl className="mt-10 grid border-t border-line md:grid-cols-2 md:gap-x-10">
          {snapshot.map(([term, detail]) => (
            <div
              key={term}
              className="grid gap-1 border-b border-line py-5 sm:grid-cols-[10rem_1fr] sm:gap-6"
            >
              <dt className="font-semibold">{term}</dt>
              <dd className="leading-relaxed text-ink-2">{detail}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-6 max-w-3xl text-sm leading-relaxed text-ink-3">
          Everything below marked <span className="font-semibold text-ink-2">Planned</span>{" "}
          describes how we intend to build. We will not describe a control as live until it is in
          production.
        </p>
      </Section>

      <Section id="integration" tone="surface" labelledBy="integration-heading">
        <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <SectionHeading
            className="lg:sticky lg:top-24 lg:self-start"
            id="integration-heading"
            eyebrow="Integration and attribution"
            title="Clean data in, clean data out."
            intro="Our product depends on accurate attribution as much as yours does. If tracking is wrong, we cannot show users honest numbers."
          />
          <StatusList items={integration} />
        </div>
      </Section>

      <Section labelledBy="quality-heading">
        <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <SectionHeading
            className="lg:sticky lg:top-24 lg:self-start"
            id="quality-heading"
            eyebrow="Traffic quality"
            title="We would rather lose a conversion than send you a bad one."
            intro="Rewarded traffic attracts abuse. We treat fraud control as part of keeping your trust, not just protecting our own margin."
          />
          <StatusList items={quality} />
        </div>
      </Section>

      <Section tone="surface" labelledBy="presentation-heading">
        <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <SectionHeading
            className="lg:sticky lg:top-24 lg:self-start"
            id="presentation-heading"
            eyebrow="Consumer presentation"
            title="Your offers, described accurately."
            intro="Our working hypothesis: people who understand an offer before they start finish more often and dispute less. We intend to measure whether that holds."
          />
          <StatusList items={presentation} />
        </div>
      </Section>

      <Section labelledBy="questions-heading">
        <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <SectionHeading
            className="lg:sticky lg:top-24 lg:self-start"
            id="questions-heading"
            eyebrow="Before we integrate"
            title="What we will ask you in writing."
            intro="We confirm these points with every network before sending traffic, and keep the answers on file."
          />
          <ol className="grid gap-3 sm:grid-cols-2">
            {questions.map((q, i) => (
              <li
                key={q}
                className="flex gap-3 rounded-2xl border border-line bg-surface p-4 leading-relaxed"
              >
                <span className="num text-sm font-semibold text-accent">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="text-ink-2">{q}</span>
              </li>
            ))}
          </ol>
        </div>
      </Section>

      <Section tone="ink" labelledBy="partner-contact-heading">
        <div className="max-w-2xl">
          <h2
            id="partner-contact-heading"
            className="font-display text-3xl font-semibold tracking-[-0.025em] sm:text-4xl"
          >
            Talk to us.
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-white/80">
            If you run an offer network or publisher program and want to evaluate us, email{" "}
            <ContactEmail
              kind="partners"
              subject={`Partnership inquiry: ${site.name}`}
              className="text-white decoration-white/50"
            />
            . Sending your publisher terms, integration docs and any application form you use helps
            us answer quickly.
          </p>
        </div>
      </Section>
    </>
  );
}
