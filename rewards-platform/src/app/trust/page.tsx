import type { Metadata } from "next";
import { BalanceStates } from "@/components/balance-states";
import { ContactEmail } from "@/components/contact-email";
import { PageHeader } from "@/components/ui/page-header";
import { Section, SectionHeading } from "@/components/ui/section";
import { site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Trust & transparency",
  description: `The rules ${site.name} holds itself to: requirements before you start, no maximum-payout ranking, no unsupported numbers, clear reward status, and an evidence-based dispute process.`,
};

const principles = [
  {
    title: "You see the requirements before you start",
    body: "Before you install anything, each offer shows every milestone in order, what each one pays, the time limit, eligibility rules, and whether purchases are optional or required. If a network gives us incomplete information, the offer will say what is missing rather than guess.",
  },
  {
    title: "The biggest number is never the headline",
    body: "Offer cards lead with what you can earn without spending. Totals that include purchases are shown, but never as the headline, and we will not rank offers by their maximum possible total.",
  },
  {
    title: "No numbers we cannot back up",
    body: "Figures like typical earnings, typical time and tracking record only appear once we have measured enough real outcomes. Each will show how many outcomes it is based on and over what period. Until then, we simply do not show them.",
  },
  {
    title: "Pending is not the same as available",
    body: "Your balance will separate rewards being checked, rewards confirmed by the network, and rewards you can withdraw. If something is held, you will see why.",
  },
  {
    title: "Reversals are shown, not hidden",
    body: "Networks sometimes reverse rewards after approving them, often because of fraud checks or refunds. When that happens we will show it on the milestone, with the reason when the network gives one.",
  },
  {
    title: "Disputes run on evidence",
    body: "When you start an offer, we record the terms you saw, when you started and which milestones were reported. If credit goes missing, that record is the starting point for a claim with the network, and we will tell you the outcome.",
  },
];

const wontDo = [
  "Countdown timers, “only 3 left” or other artificial urgency",
  "Fake activity feeds, testimonials, user counts or earnings totals",
  "Spins, raffles or any chance-based prizes",
  "Unlabeled paid placement in rankings",
  "Claim a partnership or endorsement we do not have",
  "Sell your personal information",
];

const measurement: Array<[string, string]> = [
  [
    "Typical earnings",
    "What people who started the offer through us actually earned, including those who stopped early, not just those who finished. Shown with the number of people it is based on.",
  ],
  [
    "Time and effort",
    "We cannot see inside games, so we cannot measure how long an offer takes to play. We will not show play-time estimates or earnings per hour unless we can measure play time reliably.",
  ],
  [
    "Tracking record",
    "How often milestones that users report completing are actually credited by the network, measured per game and per network.",
  ],
  [
    "Minimum sample",
    "Each figure stays hidden until it is based on enough outcomes to be meaningful. We will publish the thresholds and our method before launch.",
  ],
];

export default function TrustPage() {
  return (
    <>
      <PageHeader
        eyebrow="Trust & transparency"
        title="Trust is something we have to earn, not claim."
        intro="These are the rules we are holding ourselves to. We are pre-launch, so most of this describes how the product will work. Where something is planned rather than built, we say so."
      />

      <Section labelledBy="principles-heading">
        <h2 id="principles-heading" className="sr-only">
          Principles
        </h2>
        <ol className="grid gap-x-12 gap-y-10 md:grid-cols-2">
          {principles.map((p, i) => (
            <li key={p.title} className="grid grid-cols-[2.5rem_1fr] gap-x-2">
              <span className="num pt-0.5 font-display text-xl font-semibold text-accent">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <h3 className="text-lg font-semibold tracking-[-0.01em]">{p.title}</h3>
                <p className="mt-2 leading-relaxed text-ink-2">{p.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section tone="surface" labelledBy="money-heading">
        <div className="grid gap-10 lg:grid-cols-2">
          <SectionHeading
            id="money-heading"
            eyebrow="How we make money"
            title="Where your reward comes from."
          />
          <div className="space-y-4 text-lg leading-relaxed text-ink-2">
            <p>
              Game publishers pay offer networks to find new players. When you reach a milestone and
              the network verifies it, the network pays us. We pass part of that payment to you as
              your reward and keep the rest.
            </p>
            <p>
              Our share also has to cover the costs that come with rewards: payment fees, fraud,
              reversals, and support. We do not charge you anything to use the product.
            </p>
            <p className="text-base text-ink-3">
              Each offer you start is tracked through one network, recorded when you start, so your
              progress is tracked in one place.
            </p>
          </div>
        </div>
      </Section>

      <Section labelledBy="measure-heading">
        <SectionHeading
          id="measure-heading"
          eyebrow="How our numbers will work"
          title="Every figure comes with its limits."
          intro="Once we have measured enough real outcomes, offers will start showing figures based on them. Here is what each one will mean."
        />
        <dl className="mt-10 divide-y divide-line border-y border-line">
          {measurement.map(([term, detail]) => (
            <div key={term} className="grid gap-2 py-5 md:grid-cols-[16rem_1fr] md:gap-10">
              <dt className="font-semibold">{term}</dt>
              <dd className="leading-relaxed text-ink-2">{detail}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section tone="surface" labelledBy="balance-heading">
        <SectionHeading
          id="balance-heading"
          eyebrow="Reward status (planned)"
          title="Where each reward stands."
        />
        <BalanceStates className="mt-10" />
      </Section>

      <Section labelledBy="wont-heading">
        <div className="grid gap-10 lg:grid-cols-2">
          <SectionHeading
            id="wont-heading"
            eyebrow="What we will not do"
            title="No dark patterns."
            intro="Reward sites often rely on pressure and hype. We are building the opposite."
          />
          {/* Quotes examples of banned patterns on purpose; excluded from the rendered copy guard. */}
          <ul
            data-copy-guard="ignore"
            className="divide-y divide-line rounded-[var(--radius-card)] border border-line bg-surface"
          >
            {wontDo.map((item) => (
              <li key={item} className="flex items-start gap-3 p-4 leading-relaxed">
                <svg
                  aria-hidden="true"
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  className="mt-0.5 shrink-0 text-bad"
                >
                  <path
                    d="M6 6l8 8M14 6l-8 8"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
                <span>
                  <span className="sr-only">We will not: </span>
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section tone="ink" labelledBy="concern-heading">
        <div className="max-w-2xl">
          <h2
            id="concern-heading"
            className="font-display text-3xl font-semibold tracking-[-0.025em] sm:text-4xl"
          >
            See something that does not match these rules?
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-white/80">
            Tell us at{" "}
            <ContactEmail
              kind="support"
              subject="Transparency concern"
              className="text-white decoration-white/50"
            />
            . If anything on this site overstates what we do, we want to fix it.
          </p>
        </div>
      </Section>
    </>
  );
}
