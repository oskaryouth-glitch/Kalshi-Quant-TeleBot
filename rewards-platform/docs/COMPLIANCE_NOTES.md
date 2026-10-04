# Compliance notes

**This is not legal advice.** It is an engineering and product list of questions for counsel, plus
the rules the codebase enforces. Labels: **CONFIRMED** (true of this codebase today), **ASSUMPTION**,
**UNKNOWN — needs counsel**.

## Public claim rules (enforced)

Founder rules, enforced by `src/lib/copy-guard.ts` on source files (unit test) and rendered page text
(e2e):

- Never claim a partnership, endorsement, user count, payout total, earnings statistic, hourly rate,
  rating or review that we do not have.
- Never name offer networks or competitors on public pages (D-013). Never use their logos.
- No hype ("free money"), maximum-payout headlines ("up to $"), false urgency or scarcity, or
  gambling language.
- Planned features are labeled **Planned** (partner page) or described in future tense ("we plan
  to", "will").
- Example offers are visibly labeled illustrative (frame banner, card tag, detail header), use
  genre names rather than real games, and carry no outcome figures (D-006, D-019).
- No "real money", "real cash" or named payout methods until cash rewards and payout rails are
  confirmed (D-020).
- An offer card's headline amount never requires spending money (D-019, `summarizeOffer`).

A copy change that trips the guard is a build failure. Fix the copy; don't weaken the pattern.

## What the shell actually does with data (CONFIRMED, as of 2026-10-04)

- Collects: email, phone platform, optional note (≤500 chars), 18+ confirmation, optional `?ref=` tag
  (`[a-z0-9_-]{1,64}`, otherwise discarded), privacy-policy version and timestamp.
- Does **not** collect: name, phone number, IP address with the signup, device IDs.
- The rate limiter holds a salted SHA-256 of the client IP in process memory only.
- No cookies are set (asserted in e2e). No third-party scripts. Fonts are self-hosted at build time.
- Application logs contain event names, platform and store kind, **never** the email or note
  (asserted in unit tests).
- The hosting provider's own request logs are outside our code; the privacy policy discloses this.

**Rule:** any new data collection (analytics, accounts, payouts) requires a privacy-policy update and
a `POLICY_VERSIONS` bump **before** it ships.

## Draft documents

`/privacy` and `/terms` are drafts (`POLICY_VERSIONS.*` end in `-draft`). They show a visible
"Draft, pending legal review" notice and block `npm run check:launch`. Deliberately left for
counsel: governing law and venue, dispute resolution or arbitration, liability caps, and the full
reward-program terms.

## Open questions for counsel (UNKNOWN — needs counsel)

1. **Entity and jurisdiction** for operating a US rewards program.
2. **Money transmission / stored value.** Does holding user reward balances that are redeemable for
   cash (PayPal) or gift cards trigger state money-transmitter or stored-value rules? Does paying
   through a licensed payout provider change the answer?
3. **Unclaimed property (escheat).** Treatment of dormant balances; permissible expiry and dormancy
   terms.
4. **Tax reporting.** 1099 obligations for user rewards, TIN collection thresholds, and whether a
   payout provider can handle them. (Engineering note: the federal 1099-MISC/NEC threshold may have
   changed for payments made in 2026. **Unverified**, so confirm with tax counsel.)
5. **Age.** Age-assurance standard before first payout; state laws on minors and online services;
   COPPA posture (we target 18+ and do not knowingly collect from under-13s).
6. **FTC.** Earnings representations once we show outcome-based figures; "typical" language;
   endorsement and disclosure rules for creator and affiliate marketing (Endorsement Guides).
7. **Contests and sweepstakes.** Not applicable while there are no chance-based prizes. Any future
   bonus or raffle mechanic needs review first.
8. **Privacy.** CCPA/CPRA and other state laws: applicability thresholds, "sale/share" analysis once
   any analytics or ads exist, data-retention schedule (draft says launch + 12 months).
9. **Email.** CAN-SPAM requires a valid physical postal address in commercial email. The mailing
   address is therefore a launch blocker for sending anything.
10. **Provider terms.** Contract review of each network's publisher agreement (indemnities,
    clawbacks, audit rights, exclusivity, traffic-source restrictions).
11. **Reward-program terms.** Holds, reversals (including after withdrawal), negative balances,
    account closure, dispute process, chargeback-like recovery.

## Referral, ambassador and game-data questions (added 2026-10-04)

12. **Endorsements:** referrer and ambassador disclosure requirements (FTC Endorsement Guides:
    material connection includes "the possibility of being paid", disclosed with the endorsement;
    a bare "ambassador" is insufficient; CONFIRMED from ftc.gov). Our monitoring obligations.
13. **Pyramid/MLM:** confirm that single-level, no-buy-in, conversion-qualified referral rewards
    are clear of pyramid characteristics under federal and state law.
14. **Ambassadors:** contractor agreements, worker classification, tax reporting for stipends and
    referral rewards; NIL rules if student-athletes participate.
15. **Campus rules:** per-campus solicitation and trademark policies before any on-campus activity.
16. **Store data:** terms for Apple's iTunes Search/Lookup API and any licensed vendor; display
    rights for third-party ratings; no scraping of Google Play.
17. **Game names in marketing:** nominative use of game titles on landing pages vs provider and
    advertiser restrictions on branded traffic.

## Launch blockers (from `npm run check:launch`)

Working brand name; legal entity; entity jurisdiction; mailing address; partners, support and
privacy emails; production site URL; privacy draft; terms draft.
