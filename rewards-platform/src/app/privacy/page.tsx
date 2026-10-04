import type { Metadata } from "next";
import { ContactEmail } from "@/components/contact-email";
import { LegalDoc } from "@/components/legal-doc";
import { POLICY_VERSIONS, site } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Privacy policy",
  description: `What personal information the ${site.name} pre-launch website collects, why, and your choices.`,
};

/*
 * DRAFT — scoped strictly to what this pre-launch site does (see docs/COMPLIANCE_NOTES.md).
 * If the site starts collecting anything new (analytics, accounts, payouts), this page must be
 * updated BEFORE that ships, and POLICY_VERSIONS.privacy bumped.
 */
export default function PrivacyPage() {
  const controller = site.legalEntity ?? site.name;
  return (
    <LegalDoc eyebrow="Legal" title="Privacy policy" version={POLICY_VERSIONS.privacy}>
      <p>
        This policy explains what personal information {controller} (“we”, “us”) collects through
        this website, why, and what you can do about it. We are pre-launch: this website describes a
        product we are building and lets you join an early-access list. It does not offer accounts,
        rewards or payouts.
      </p>

      <h2 id="summary">The short version</h2>
      <ul>
        <li>
          If you join early access, we collect your email address, phone type, an optional note, a
          confirmation that you are 18 or older and, if present, a referral tag from the link you
          followed.
        </li>
        <li>We use it to tell you when early access opens and to plan which phones to support.</li>
        <li>We do not use advertising pixels, tracking cookies or third-party analytics.</li>
        <li>We do not sell or share your personal information for advertising.</li>
        <li>You can ask us to delete your information at any time.</li>
      </ul>

      <h2 id="collect">What we collect</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Information</th>
            <th scope="col">When</th>
            <th scope="col">Why</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Email address</td>
            <td>You join early access</td>
            <td>To email you about early access</td>
          </tr>
          <tr>
            <td>Phone type (Android, iPhone, other)</td>
            <td>You join early access</td>
            <td>To decide which platforms to support</td>
          </tr>
          <tr>
            <td>Optional note</td>
            <td>Only if you write one</td>
            <td>Product feedback</td>
          </tr>
          <tr>
            <td>18+ confirmation, sign-up date, policy version</td>
            <td>You join early access</td>
            <td>A record of your eligibility statement and consent</td>
          </tr>
          <tr>
            <td>Referral tag (from a ?ref= link)</td>
            <td>Only if the link you followed had one</td>
            <td>To understand which channels bring people to us</td>
          </tr>
          <tr>
            <td>Emails you send us</td>
            <td>You contact us</td>
            <td>To reply to you</td>
          </tr>
        </tbody>
      </table>

      <h3>Technical information</h3>
      <p>
        Like any website, our hosting provider receives technical information such as your IP
        address, browser type and the pages requested, and may keep it in server logs for security
        and operations. Our own application uses your IP address only to limit repeated form
        submissions; it is converted to a one-way hash in temporary memory and is not stored with
        your sign-up.
      </p>
      <p>
        This website does not set cookies for tracking or advertising, and does not load third-party
        analytics or advertising scripts. Fonts are served from our own domain.
      </p>

      <h2 id="use">How we use it</h2>
      <ul>
        <li>To send you emails about early access, which you asked for when you joined.</li>
        <li>To understand demand, for example how many people use Android versus iPhone.</li>
        <li>To protect the site from abuse, such as automated sign-ups.</li>
      </ul>
      <p>
        We will not use your early-access information for unrelated marketing, and we will not add
        you to any other list without asking.
      </p>

      <h2 id="sharing">Who we share it with</h2>
      <p>
        We do not sell your personal information, and we do not share it for cross-context
        behavioral advertising. We use service providers to run this website, such as hosting,
        database and email providers. They process information on our behalf and only as needed to
        provide their service. We will list these providers here before we launch. We may also
        disclose information if required by law.
      </p>

      <h2 id="retention">How long we keep it</h2>
      <p>
        We keep early-access sign-ups until we launch and for up to 12 months after that, unless you
        ask us to delete them sooner. We then delete them or ask whether you want to stay in touch.
      </p>

      <h2 id="choices">Your choices and rights</h2>
      <p>
        You can ask us to tell you what information we hold about you, correct it, or delete it, by
        emailing <ContactEmail kind="privacy" subject="Privacy request" />. We will verify the
        request by replying to the email address on file. Depending on where you live, including
        California, you may have additional rights under state privacy laws, and we will not treat
        you differently for exercising them.
      </p>

      <h2 id="age">Age</h2>
      <p>
        This website and our planned product are intended for adults {site.minimumAge} and over. We
        do not knowingly collect information from anyone under {site.minimumAge}. If you believe
        someone under {site.minimumAge} has joined our list, contact us and we will delete their
        information.
      </p>

      <h2 id="security">Security</h2>
      <p>
        We use reasonable technical measures to protect the information we hold, including encrypted
        connections (HTTPS) and restricted access to our database. No system is perfectly secure,
        and we will notify you as required by law if a breach affects your information.
      </p>

      <h2 id="changes">Changes</h2>
      <p>
        We will update this policy before we collect anything new, for example when we launch
        accounts or rewards. The version identifier at the top of this page changes with each
        update.
      </p>

      <h2 id="contact">Contact</h2>
      <p>
        Questions or requests: <ContactEmail kind="privacy" subject="Privacy question" />
        {site.mailingAddress ? (
          <>
            {" "}
            or by mail at {controller}, {site.mailingAddress}
          </>
        ) : null}
        .
      </p>
    </LegalDoc>
  );
}
