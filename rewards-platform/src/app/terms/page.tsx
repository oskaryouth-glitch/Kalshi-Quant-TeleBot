import type { Metadata } from "next";
import Link from "next/link";
import { ContactEmail } from "@/components/contact-email";
import { LegalDoc } from "@/components/legal-doc";
import { POLICY_VERSIONS, site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Terms of use",
  description: `Terms of use for the ${site.name} pre-launch website.`,
};

/*
 * DRAFT — website terms only. Reward-program terms (eligibility, holds, reversals, disputes,
 * account closure, taxes) do NOT exist yet and must be drafted with counsel before launch.
 * Governing law, dispute resolution and liability caps are deliberately left for counsel.
 * See docs/COMPLIANCE_NOTES.md.
 */
export default function TermsPage() {
  const company = site.legalEntity ?? site.name;
  return (
    <LegalDoc eyebrow="Legal" title="Terms of use" version={POLICY_VERSIONS.terms}>
      <p>
        These terms cover your use of this website, operated by {company} (“we”, “us”). By using the
        website you agree to them.
      </p>

      <h2 id="what">What this website is</h2>
      <p>
        {site.name} is pre-launch. This website describes a product we are building and lets you
        join an early-access list. It does not currently offer accounts, list offers, hold balances
        or pay rewards. Descriptions of planned features are statements of intent, not promises, and
        may change before launch.
      </p>

      <h2 id="early-access">Early access</h2>
      <ul>
        <li>You must be {site.minimumAge} or older to join.</li>
        <li>
          Joining the list does not create an account, guarantee access, or entitle you to any
          reward.
        </li>
        <li>We may decide who receives early access and when, for example by platform.</li>
        <li>
          How we handle your information is described in our{" "}
          <Link href="/privacy">privacy policy</Link>.
        </li>
      </ul>

      <h2 id="rewards">Future reward terms</h2>
      <p>
        If and when we launch the product, separate reward-program terms will apply. They will
        cover, at a minimum, eligibility, how rewards are confirmed, holding periods, reversals,
        disputes, withdrawals and account closure. We will publish them before anyone can earn a
        reward.
      </p>

      <h2 id="use">Acceptable use</h2>
      <p>Please do not:</p>
      <ul>
        <li>Submit false information or sign up on behalf of other people without permission.</li>
        <li>Use automated means to submit forms or scrape the website.</li>
        <li>
          Attempt to disrupt, probe or gain unauthorized access to the website or its systems.
        </li>
      </ul>

      <h2 id="ip">Content and trademarks</h2>
      <p>
        The website’s content and design belong to us or our licensors. Game names and other
        trademarks mentioned belong to their respective owners, and their mention does not imply any
        partnership or endorsement. Example offers shown on this website are illustrative and do not
        describe real offers.
      </p>

      <h2 id="disclaimer">No warranty</h2>
      <p>
        The website is provided “as is” and “as available”. We do our best to keep it accurate, but
        we do not warrant that it is complete, current or error-free, or that it will be available
        without interruption.
      </p>

      <h2 id="liability">Liability</h2>
      <p>
        To the extent permitted by law, we are not liable for indirect or consequential losses
        arising from your use of this website. Nothing in these terms limits liability that cannot
        be limited by law.
      </p>

      <h2 id="changes">Changes</h2>
      <p>
        We may update these terms. The version identifier at the top of this page changes with each
        update, and the current version applies from the time it is posted.
      </p>

      <h2 id="contact">Contact</h2>
      <p>
        Questions about these terms: <ContactEmail kind="support" subject="Terms question" />.
      </p>
    </LegalDoc>
  );
}
