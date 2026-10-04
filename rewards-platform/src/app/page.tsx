import Link from "next/link";
import { MarketplacePreview } from "@/components/offers/marketplace-preview";
import { OfferDetail } from "@/components/offers/offer-detail";
import { RewardTracker } from "@/components/offers/reward-tracker";
import { Arrow, ButtonLink } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Container } from "@/components/ui/container";
import { Section, SectionHeading } from "@/components/ui/section";
import {
  featuredIllustrativeOffer,
  illustrativeOffers,
  illustrativeProgress,
} from "@/lib/fixtures/illustrative-offers";

/*
 * Homepage hierarchy (DECISIONS D-019): attraction → selection → transparency → tracking,
 * with trust explained throughout and in depth on /trust. All offer data is illustrative.
 */

const steps = [
  {
    title: "Pick a game you would actually play",
    body: "Browse game offers with the reward amount up front, and whether any purchase is involved.",
  },
  {
    title: "Reach the milestones",
    body: "Each milestone pays its own reward, so you earn as you go. You do not have to finish every step to get paid for the ones you reach.",
  },
  {
    title: "Withdraw your rewards",
    body: "Once a reward is confirmed and you reach the withdrawal minimum, it is yours to withdraw. Payout options will be announced before launch.",
  },
];

const trustPoints = [
  {
    title: "Dollars, not points",
    body: "Rewards are shown in US dollars. No coins or exchange rates to decode.",
  },
  {
    title: "The big number never needs spending",
    body: "When an offer includes purchases, the headline amount is what you can earn without them.",
  },
  {
    title: "Numbers we can back up",
    body: "Typical earnings appear only once we have measured enough real outcomes. No invented averages.",
  },
  {
    title: "No pressure tactics",
    body: "No countdowns, spins or fake activity feeds. Just offers, terms and your progress.",
  },
];

const faqs = [
  {
    q: "Is this live?",
    a: "Not yet. We are pre-launch: the offers on this page are examples with invented amounts, and we are not listing offers, holding balances or paying rewards today. Joining early access puts you on a list to hear when we open.",
  },
  {
    q: "Why would a game pay me to play?",
    a: "Game studios pay to find new players. They pay offer networks, and those networks pay sites like ours when a player reaches a milestone. We pass part of that to you as your reward and keep the rest. Using the product will be free.",
  },
  {
    q: "Will I have to spend money?",
    a: "Many offers can be completed without spending. Some include purchase milestones. Every offer is labeled “no purchase needed”, “optional purchase” or “purchase required”, and the headline amount on a card never depends on spending.",
  },
  {
    q: "How long do rewards take?",
    a: "Each milestone has to be confirmed by the offer network first, and a short holding period may apply before you can withdraw. We will publish holding periods and withdrawal minimums before launch.",
  },
  {
    q: "Why Android and the US first?",
    a: "Starting narrow keeps tracking reliable while we learn. iPhone support depends on demand, so early access asks which phone you use.",
  },
  {
    q: "Is this gambling?",
    a: "No. There are no chance-based prizes, spins or raffles. You earn by reaching clearly stated milestones in games.",
  },
];

const heroChecks = ["Dollars, not points", "Purchases always labeled", "Free to use"];

const ladderPoints = [
  "Every milestone in order, with what each one pays",
  "The time limit, and when the clock starts",
  "Which steps need a purchase, and which do not",
  "Who is eligible, like new players only",
];

export default function HomePage() {
  return (
    <>
      {/* 1. Attraction */}
      <section
        className="relative overflow-hidden border-b border-line"
        aria-labelledby="hero-heading"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(48rem_28rem_at_88%_0%,rgb(58_46_232/0.13),transparent_62%),radial-gradient(34rem_22rem_at_72%_100%,rgb(255_128_80/0.10),transparent_60%),radial-gradient(26rem_18rem_at_0%_100%,rgb(56_189_248/0.08),transparent_60%)]"
        />
        <Container className="relative grid grid-cols-1 items-center gap-12 pt-12 pb-16 sm:pt-16 lg:grid-cols-[1fr_minmax(0,30rem)] lg:gap-16 lg:pt-20 lg:pb-24">
          <div>
            <Badge tone="accent">Pre-launch · Android · United States</Badge>
            <h1
              id="hero-heading"
              className="mt-6 font-display text-[2.7rem] leading-[1.02] font-semibold tracking-[-0.035em] text-balance sm:text-6xl lg:text-[3.9rem]"
            >
              Play new games.{" "}
              <span className="bg-gradient-to-r from-accent to-[#6a4dff] bg-clip-text text-transparent">
                Get paid as you progress.
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-pretty text-ink-2 sm:text-xl">
              Pick a mobile game, reach the milestones it lists, and earn a reward for each one.
              Every requirement, time limit and purchase condition is shown before you start.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/early-access">
                Get early access <Arrow />
              </ButtonLink>
              <ButtonLink href="/how-it-works" variant="secondary">
                See how it works
              </ButtonLink>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-2">
              {heroChecks.map((t) => (
                <li key={t} className="inline-flex items-center gap-1.5">
                  <svg
                    aria-hidden="true"
                    width="16"
                    height="16"
                    viewBox="0 0 20 20"
                    className="text-ok"
                  >
                    <path
                      d="M5 10.5l3 3 7-7"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  {t}
                </li>
              ))}
            </ul>
            <p className="mt-6 text-sm text-ink-3">
              Not live yet. Offers shown are examples with invented amounts.
            </p>
          </div>

          <div className="mx-auto w-full max-w-md lg:max-w-none">
            <MarketplacePreview offers={illustrativeOffers} />
          </div>
        </Container>
      </section>

      {/* 2. Selection: how earning works */}
      <Section labelledBy="earn-heading">
        <SectionHeading
          id="earn-heading"
          eyebrow="How earning works"
          title="Pick a game. Hit milestones. Get paid."
          intro="Game studios pay to find new players. When you reach a milestone, part of that payment comes to you as your reward."
        />
        <ol className="mt-12 grid gap-4 md:grid-cols-3">
          {steps.map((s, i) => (
            <li
              key={s.title}
              className="rounded-[var(--radius-card)] border border-line bg-surface p-6"
            >
              <span className="num inline-flex size-9 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
                {i + 1}
              </span>
              <h3 className="mt-4 text-lg font-semibold tracking-[-0.01em]">{s.title}</h3>
              <p className="mt-2 leading-relaxed text-ink-2">{s.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      {/* 3. Transparency: the full detail before starting */}
      <Section id="example-offer" tone="surface" labelledBy="ladder-heading">
        <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
          <div className="lg:sticky lg:top-24">
            <SectionHeading
              id="ladder-heading"
              eyebrow="Before you start"
              title="See the whole ladder, not just the top prize."
              intro="Open any offer and you get the full picture before you install anything."
            />
            <ul className="mt-8 space-y-3 text-ink-2">
              {ladderPoints.map((t) => (
                <li key={t} className="flex gap-3">
                  <span
                    aria-hidden="true"
                    className="mt-2.5 size-1.5 shrink-0 rounded-full bg-accent"
                  />
                  <span className="leading-relaxed">{t}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-[1.75rem] border border-line bg-surface p-5 shadow-[var(--shadow-card)] sm:p-7">
            <OfferDetail offer={featuredIllustrativeOffer} />
          </div>
        </div>
      </Section>

      {/* 4. Tracking */}
      <Section labelledBy="tracking-heading">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <div className="order-2 lg:order-1">
            <RewardTracker
              offer={featuredIllustrativeOffer}
              statuses={[...illustrativeProgress.statuses]}
              day={illustrativeProgress.day}
              className="mx-auto max-w-md lg:mx-0"
            />
          </div>
          <div className="order-1 lg:order-2">
            <SectionHeading
              id="tracking-heading"
              eyebrow="Track every reward"
              title="Know what you have earned, and when you can withdraw it."
              intro="Each milestone shows where it stands: pending while the offer network checks it, confirmed once approved, and available when it is yours to withdraw."
            />
            <p className="mt-5 leading-relaxed text-ink-2">
              Networks sometimes reject or reverse a reward, for example after fraud checks. If that
              happens, you will see it on the milestone, with the reason when the network gives one.
            </p>
            <Link
              href="/how-it-works"
              className="mt-6 inline-flex items-center gap-1.5 font-medium text-accent underline-offset-4 hover:underline"
            >
              How reward status works <Arrow />
            </Link>
          </div>
        </div>
      </Section>

      {/* 5. Trust */}
      <Section tone="surface" labelledBy="trust-heading">
        <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <SectionHeading
              id="trust-heading"
              eyebrow="Straight with you"
              title="Exciting offers. No fine-print surprises."
            />
            <Link
              href="/trust"
              className="mt-6 inline-flex items-center gap-1.5 font-medium text-accent underline-offset-4 hover:underline"
            >
              Read our transparency principles <Arrow />
            </Link>
          </div>
          <dl className="grid gap-x-8 gap-y-10 sm:grid-cols-2">
            {trustPoints.map((p) => (
              <div key={p.title} className="border-t-2 border-ink pt-4">
                <dt className="text-lg font-semibold tracking-[-0.01em]">{p.title}</dt>
                <dd className="mt-2 leading-relaxed text-ink-2">{p.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Section>

      {/* Audiences */}
      <Section labelledBy="audiences-heading">
        <h2 id="audiences-heading" className="sr-only">
          Get involved
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col rounded-[var(--radius-card)] bg-ink p-6 text-white sm:p-9">
            <p className="text-sm font-semibold tracking-[0.14em] text-white/70 uppercase">
              For players
            </p>
            <h3 className="mt-3 font-display text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">
              Be first in line when we open.
            </h3>
            <p className="mt-3 leading-relaxed text-white/80">
              We ask for your email, your phone type and a quick age check. No spam, and you can
              leave the list at any time.
            </p>
            <div className="mt-auto pt-7">
              <ButtonLink href="/early-access" variant="secondary" className="border-transparent">
                Get early access <Arrow />
              </ButtonLink>
            </div>
          </div>
          <div className="flex flex-col rounded-[var(--radius-card)] border border-line bg-surface p-6 sm:p-9">
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
      <Section tone="surface" labelledBy="faq-heading">
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
