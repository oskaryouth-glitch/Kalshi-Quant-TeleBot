import type { Metadata } from "next";
import { ContactEmail } from "@/components/contact-email";
import { PageHeader } from "@/components/ui/page-header";
import { Section } from "@/components/ui/section";
import { site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Contact",
  description: `Contact ${site.name} about partnerships, early access or privacy.`,
};

const channels = [
  {
    kind: "partners" as const,
    title: "Partnerships",
    body: "Offer networks, publisher programs and integration questions. Please include your publisher terms and integration documentation if you can.",
    subject: `Partnership inquiry: ${site.name}`,
  },
  {
    kind: "support" as const,
    title: "General and early access",
    body: "Questions about the product, early access, or anything on this site you think is unclear or overstated.",
    subject: "Question",
  },
  {
    kind: "privacy" as const,
    title: "Privacy requests",
    body: "Ask what we hold about you, or ask us to correct or delete it. We will confirm your request from the email address on file.",
    subject: "Privacy request",
  },
];

export default function ContactPage() {
  return (
    <>
      <PageHeader
        eyebrow="Contact"
        title="Talk to a person."
        intro="Email is the best way to reach us while we are pre-launch."
      />
      <Section>
        <ul className="grid gap-4 md:grid-cols-3">
          {channels.map((c) => (
            <li
              key={c.kind}
              className="flex flex-col rounded-[var(--radius-card)] border border-line bg-surface p-6"
            >
              <h2 className="text-lg font-semibold tracking-[-0.01em]">{c.title}</h2>
              <p className="mt-2 leading-relaxed text-ink-2">{c.body}</p>
              <p className="mt-auto pt-6 font-medium break-all">
                <ContactEmail kind={c.kind} subject={c.subject} />
              </p>
            </li>
          ))}
        </ul>
        {site.mailingAddress ? (
          <div className="mt-10 max-w-md">
            <h2 className="font-semibold">Mailing address</h2>
            <address className="mt-2 leading-relaxed whitespace-pre-line text-ink-2 not-italic">
              {site.legalEntity ? `${site.legalEntity}\n` : ""}
              {site.mailingAddress}
            </address>
          </div>
        ) : null}
      </Section>
    </>
  );
}
