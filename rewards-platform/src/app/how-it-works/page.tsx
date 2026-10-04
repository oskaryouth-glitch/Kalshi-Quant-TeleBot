import type { Metadata } from "next";
import Link from "next/link";
import { BalanceStates } from "@/components/balance-states";
import { Arrow, ButtonLink } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Section, SectionHeading } from "@/components/ui/section";
import { site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "How rewarded game offers will work: discover, compare, choose, complete verified milestones, track progress and get paid. Requirements vary by offer.",
};

const steps = [
  {
    name: "Discover",
    body: "Browse game offers available to you. Every offer is shown with the same Offer Facts label, so you can compare like with like.",
  },
  {
    name: "Compare",
    body: "See the milestones in order, the deadline, and whether any purchase is involved. Totals are shown with and without purchase milestones.",
  },
  {
    name: "Choose",
    body: "Pick an offer you actually want to play. When you start, we record the exact terms you saw and the time you started.",
  },
  {
    name: "Complete verified milestones",
    body: "Play the game and reach the stated milestones before the deadline. The offer network, not us, verifies each one.",
  },
  {
    name: "Track progress",
    body: "Each milestone shows as tracking, pending, confirmed or available, with a plain explanation of what each means.",
  },
  {
    name: "Get paid",
    body: "Once rewards are available and you reach the withdrawal minimum, withdraw them. Payout methods will be announced before launch.",
  },
];

const realities = [
  {
    title: "Requirements vary",
    body: "Every offer sets its own milestones, deadlines and rules, and some are only open to new players of that game. Read the label before you start.",
  },
  {
    title: "Verification takes time",
    body: "Networks check milestones before they pay. A reward can sit as pending for a while, and some offers take longer than others.",
  },
  {
    title: "Not every milestone is credited",
    body: "Tracking can fail, and networks can reject or reverse rewards. We plan to show you the status of every milestone and help you dispute missing credit.",
  },
  {
    title: "Payouts are not immediate",
    body: "Expect to wait. A holding period before withdrawal protects against reversals and fraud. We will publish it before launch.",
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <PageHeader
        eyebrow="How it works"
        title="From browsing to getting paid, with no surprises."
        intro={`This is how ${site.name} is designed to work once it launches. We are not live yet, and details may change as we learn. We will update this page when they do.`}
      />

      <Section labelledBy="steps-heading">
        <h2 id="steps-heading" className="sr-only">
          Steps
        </h2>
        <ol className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {steps.map((s, i) => (
            <li
              key={s.name}
              className="relative rounded-[var(--radius-card)] border border-line bg-surface p-6"
            >
              <span className="num inline-flex size-9 items-center justify-center rounded-full bg-ink text-sm font-semibold text-white">
                {i + 1}
              </span>
              <h3 className="mt-4 text-lg font-semibold tracking-[-0.01em]">{s.name}</h3>
              <p className="mt-2 leading-relaxed text-ink-2">{s.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section tone="surface" labelledBy="status-heading">
        <SectionHeading
          id="status-heading"
          eyebrow="Reward status"
          title="What each status will mean."
          intro="A reward is not money in your pocket until it is available. Here is the path each milestone reward will follow."
        />
        <BalanceStates className="mt-10" />
      </Section>

      <Section labelledBy="realities-heading">
        <SectionHeading
          id="realities-heading"
          eyebrow="Good to know"
          title="The honest fine print, up front."
        />
        <ul className="mt-10 grid gap-x-10 gap-y-8 md:grid-cols-2">
          {realities.map((r) => (
            <li key={r.title} className="border-t-2 border-ink pt-4">
              <h3 className="text-lg font-semibold tracking-[-0.01em]">{r.title}</h3>
              <p className="mt-2 leading-relaxed text-ink-2">{r.body}</p>
            </li>
          ))}
        </ul>
        <div className="mt-14 flex flex-col items-start gap-4 rounded-[var(--radius-card)] border border-line bg-surface p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <p className="max-w-xl leading-relaxed text-ink-2">
            Want the detail on how we will rank offers, handle reversals and treat disputes?{" "}
            <Link href="/trust" className="text-accent underline underline-offset-4">
              Read our transparency principles
            </Link>
            .
          </p>
          <ButtonLink href="/early-access">
            Get early access <Arrow />
          </ButtonLink>
        </div>
      </Section>
    </>
  );
}
