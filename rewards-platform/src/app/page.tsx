import Link from "next/link";
import { BalanceStates } from "@/components/balance-states";
import { OfferFacts } from "@/components/offer-facts";
import { Arrow, ButtonLink } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Container } from "@/components/ui/container";
import { Section, SectionHeading } from "@/components/ui/section";
import { illustrativeOffer } from "@/lib/fixtures/illustrative-offer";

const problems = [
  {
    title: "Headline totals hide the work",
    body: "A single big number usually adds up every milestone, including late levels few people reach and purchase milestones most people skip.",
  },
  {
    title: "Requirements are hard to find",
    body: "Deadlines, level targets and purchase conditions are often buried in fine print, and they differ from one offerwall to the next.",
  },
  {
    title: "Credit is not always clear",
    body: "Progress does not always get credited, and when it does not, it is often unclear why, who to ask or what evidence you need.",
  },
];

const principles = [
  {
    title: "Requirements before you start",
    body: "Every offer gets the same label: milestones in order, deadline, and whether any purchase is involved. No hunting through fine print.",
  },
  {
    title: "Ranked by more than the headline",
    body: "We will not sort offers by their biggest possible total. Ranking will weigh what is realistic to reach, and we will publish how it works.",
  },
  {
    title: "Honest about what we don't know",
    body: "Estimates like typical earnings only appear once we have measured enough real outcomes. Until then the label says so.",
  },
  {
    title: "Pending is not the same as paid",
    body: "Your balance will show what is still being checked, what is confirmed and what you can withdraw, with reasons when something is held.",
  },
];

const faqs = [
  {
    q: "Is this live?",
    a: "Not yet. We are pre-launch. We are not listing offers, holding balances or paying rewards today. Joining early access only puts you on a list to hear when we open.",
  },
  {
    q: "How would you make money?",
    a: "Game publishers pay offer networks for new players, and those networks pay sites like ours when a milestone is verified. We pass a share of that to you as your reward and keep the rest. We plan to explain this on every offer rather than hide it.",
  },
  {
    q: "Will I have to spend money?",
    a: "Many game offers can be completed without spending. Some include purchase milestones. We will always label purchases as optional or required, and show totals both with and without them.",
  },
  {
    q: "Why Android and the US first?",
    a: "Starting narrow keeps tracking cleaner and lets us measure outcomes properly before expanding. iPhone support depends on what we learn, so early access asks which phone you use.",
  },
  {
    q: "Is this gambling?",
    a: "No. There are no chance-based prizes, spins or raffles. You earn by completing clearly stated milestones in games.",
  },
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section
        className="relative overflow-hidden border-b border-line"
        aria-labelledby="hero-heading"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60rem_30rem_at_85%_-10%,rgb(58_46_232/0.10),transparent_60%),radial-gradient(30rem_20rem_at_100%_80%,rgb(255_120_70/0.08),transparent_60%)]"
        />
        <Container className="relative grid items-center gap-12 pt-14 pb-16 sm:pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pt-24 lg:pb-24">
          <div>
            <Badge tone="accent">Pre-launch · United States · Android first</Badge>
            <h1
              id="hero-heading"
              className="mt-6 font-display text-[2.6rem] leading-[1.03] font-semibold tracking-[-0.03em] text-balance sm:text-6xl lg:text-[4.1rem]"
            >
              Know what a game reward takes before you start.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-pretty text-ink-2 sm:text-xl">
              Paid game offers usually lead with their biggest number. We are building a clearer way
              to choose: every milestone, deadline and purchase condition laid out up front, and
              honest figures on what people actually earn once we have measured them.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/early-access">
                Get early access <Arrow />
              </ButtonLink>
              <ButtonLink href="/how-it-works" variant="secondary">
                See how it works
              </ButtonLink>
            </div>
            <p className="mt-5 text-sm text-ink-3">
              Not live yet. No offers, balances or payouts today.
            </p>
          </div>

          <div className="mx-auto w-full max-w-md lg:mr-0">
            <OfferFacts offer={illustrativeOffer} />
          </div>
        </Container>
      </section>

      {/* Problem */}
      <Section labelledBy="problem-heading">
        <SectionHeading
          id="problem-heading"
          eyebrow="The problem"
          title="A big number is not an answer."
          intro="Rewarded game offers can be a fair trade of time for money. But the way they are usually presented makes it hard to tell a good one from a slog."
        />
        <ul className="mt-12 grid gap-4 md:grid-cols-3">
          {problems.map((p, i) => (
            <li
              key={p.title}
              className="rounded-[var(--radius-card)] border border-line bg-surface p-6"
            >
              <span className="num text-sm font-semibold text-accent">0{i + 1}</span>
              <h3 className="mt-3 text-lg font-semibold tracking-[-0.01em]">{p.title}</h3>
              <p className="mt-2 leading-relaxed text-ink-2">{p.body}</p>
            </li>
          ))}
        </ul>
      </Section>

      {/* Principles */}
      <Section tone="surface" labelledBy="principles-heading">
        <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
          <SectionHeading
            id="principles-heading"
            eyebrow="What we're building"
            title="Clear terms first. Honest numbers when we have them."
            intro="We would rather show you less and have it be true."
          />
          <dl className="grid gap-x-8 gap-y-10 sm:grid-cols-2">
            {principles.map((p) => (
              <div key={p.title} className="border-t-2 border-ink pt-4">
                <dt className="text-lg font-semibold tracking-[-0.01em]">{p.title}</dt>
                <dd className="mt-2 leading-relaxed text-ink-2">{p.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Section>

      {/* Balance */}
      <Section labelledBy="balance-heading">
        <SectionHeading
          id="balance-heading"
          eyebrow="Planned design"
          title="Your balance, explained."
          intro="Offer networks check milestones before they pay, and some reverse rewards later. Instead of hiding that, we plan to show exactly where each reward stands."
        />
        <BalanceStates className="mt-10" />
        <p className="mt-5 text-sm text-ink-3">
          Holding periods and withdrawal minimums are not set yet. We will publish them before
          launch.{" "}
          <Link href="/trust" className="text-accent underline underline-offset-4">
            Read our transparency principles
          </Link>
        </p>
      </Section>

      {/* Audiences */}
      <Section tone="surface" labelledBy="audiences-heading">
        <h2 id="audiences-heading" className="sr-only">
          Get involved
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col rounded-[var(--radius-card)] bg-ink p-7 text-white sm:p-9">
            <p className="text-sm font-semibold tracking-[0.14em] text-white/70 uppercase">
              For players
            </p>
            <h3 className="mt-3 font-display text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
              Hear when we open.
            </h3>
            <p className="mt-3 leading-relaxed text-white/80">
              Leave your email and phone type. That is all we ask for. No spam, and you can leave
              the list at any time.
            </p>
            <div className="mt-auto pt-7">
              <ButtonLink href="/early-access" variant="secondary" className="border-transparent">
                Get early access <Arrow />
              </ButtonLink>
            </div>
          </div>
          <div className="flex flex-col rounded-[var(--radius-card)] border border-line bg-paper p-7 sm:p-9">
            <p className="text-sm font-semibold tracking-[0.14em] text-accent uppercase">
              For offer networks
            </p>
            <h3 className="mt-3 font-display text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
              Building a publisher integration?
            </h3>
            <p className="mt-3 leading-relaxed text-ink-2">
              We are planning API-based catalog integrations, signed server-to-server postbacks,
              stable user IDs and fraud controls, starting with US Android game offers.
            </p>
            <div className="mt-auto pt-7">
              <ButtonLink href="/partners" variant="secondary">
                Read the partner overview <Arrow />
              </ButtonLink>
            </div>
          </div>
        </div>
      </Section>

      {/* FAQ */}
      <Section labelledBy="faq-heading">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <SectionHeading id="faq-heading" eyebrow="Questions" title="Straight answers." />
          <div className="divide-y divide-line border-y border-line">
            {faqs.map((f) => (
              <details key={f.q} className="group py-1">
                <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 text-lg font-medium [&::-webkit-details-marker]:hidden">
                  {f.q}
                  <span
                    aria-hidden="true"
                    className="text-2xl leading-none text-ink-3 transition-transform group-open:rotate-45"
                  >
                    +
                  </span>
                </summary>
                <p className="pb-5 leading-relaxed text-ink-2">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </Section>
    </>
  );
}
