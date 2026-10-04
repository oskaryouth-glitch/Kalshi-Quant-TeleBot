# E001 application readiness audit

**Date:** 2026-10-04. **Status:** NOT READY to apply (see §D–§G). **No applications submitted.**
Sources are first-party provider pages retrieved 2026-10-04 via search extracts. Direct page fetches
were blocked in this environment, so each claim should be re-verified in a browser and archived
before relying on it. Anything not found is **UNKNOWN**, not assumed.

## A. Which providers to approach first, and why

| Provider              | Why first-wave or not                                                                                                                                                                                                                                                                                                                                                                       | Evidence (first-party)                                                                                                                                                                                                                                                                                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **BitLabs (Prodege)** | Only candidate whose **public terms explicitly permit monetary user rewards** (E001 criterion 2). Large, established counterparty. Terms require posting all material conversion requirements, which our product already does by design.                                                                                                                                                    | Terms of Use: "You may choose to incentivize Users in any way you wish …, including through the offer of monetary rewards, provided you comply with Applicable Laws"; Net 30 from month end, $100 minimum; integration approval requested in the Dashboard; signup collects legal status and VAT. developer.bitlabs.ai: Dashboard account, then "our sales team will contact you"; web offerwall, SDK and API options; callbacks. |
| **Offerwall.GG**      | Lowest stated barrier: **"No minimum traffic"**, "Live the same afternoon". HMAC-signed postbacks plus a reversal postback, so it can satisfy E001 criterion 5 quickly. Advertiser balances are **pre-funded**, which lowers collection risk.                                                                                                                                               | offerwall.gg home page; /developers ("One signed server-to-server request per conversion, and one more if it is later reversed"); advertiser agreement (pre-funded balances; operator AESHA Technology Services Limited, Seychelles; Seychelles law). Cash permission: UNKNOWN (marketing mentions members cashing out; not a permission).                                                                                        |
| **RevU**              | Best-documented catalog for our use: full-catalog **Get Offers API** with multi-step reward events, payouts, targeting and performance metrics; **Get Progress API** (in-progress, pending, reversals per step), which maps directly to our tracking UI; reversal postbacks on by default; IP allowlisting.                                                                                 | revu.co/docs (Get Offers, API Setup, User-Level Offer API); revu.co/publisher ("payment terms … agreed directly with your dedicated RevU account manager"; credentials via account manager). Cash permission: UNKNOWN.                                                                                                                                                                                                            |
| AdGem                 | Strong for game CPE (INFERENCE from its product focus); Offer API with goals and `attribution_window_days`; postback hashing. **Net 60** (worst for working capital). Offer API is labeled beta and needs a security token from their team. App/property review before approval.                                                                                                            | docs.adgem.com (Quickstart: "Wait for approval – Your app will be reviewed"; payments "Net 60 … from the end of the earning month"; $100 minimum ACH/PayPal; address, payment method and tax forms required before payout). Cash permission: UNKNOWN.                                                                                                                                                                             |
| ayeT Studios          | Offerwall API (server and client side), Static API (key approved by account manager), reversal callbacks, IAP callbacks; rate limit of 60 requests/hour per key on some endpoints. Onboarding through an account manager who reviews "quality of your traffic".                                                                                                                             | ayetstudios.com/openapi/publisher-doc; docs.ayetstudios.com (callbacks, reversals with "r-" prefix). Cash permission: UNKNOWN.                                                                                                                                                                                                                                                                                                    |
| Lootably              | Catalogue API recommended every 10–20 minutes; configurable user revenue split; reporting API. Approval requires you to "alert your Lootably contact", so you need a relationship first.                                                                                                                                                                                                    | documentation.lootably.com (Getting Started, Offers API, Configuring your Placement). Cash permission: UNKNOWN (not found in public docs).                                                                                                                                                                                                                                                                                        |
| Adscend Media         | Application asks for **daily active users** (we have none), traffic source and fraud prevention measures; review 1–3 business days; terms require traffic "primarily from organic sources", incentive disclosure to visitors, and advance written notice before sub-publishers. Recommends titling the wall "Adscend Media", which may conflict with our no-network-names rule (LEGAL L27). | adscendmedia.com/publishers/apply; /notices/terms-of-service; ApplicationRequirements.pdf ("URL – This is the most important information required"; contact information is verified).                                                                                                                                                                                                                                             |
| Monlix                | Site approval within 3 business days; Net 30, $20 minimum; **payouts only via Payeer, FaucetPay, AirTM or Bitcoin**, which is accounting and compliance friction for a US company. Deprioritize.                                                                                                                                                                                            | docs.monlix.com (FAQ, API integration).                                                                                                                                                                                                                                                                                                                                                                                           |

## B. What each provider requires from a pre-launch publisher (as documented)

| Provider     | Documented requirements                                                                                                                                                                         | Not documented (UNKNOWN)                                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| BitLabs      | Dashboard signup (contact email, password, **legal status**, VAT if applicable); request integration approval in the Dashboard; post all material terms; S2S callbacks                          | Traffic minimums; whether pre-launch sites are approved                                                   |
| Offerwall.GG | Create a placement (public key + secret); embed or API; HMAC postback                                                                                                                           | KYC/verification specifics (a sanctions, verification and financial-crime policy exists); cash permission |
| RevU         | Portal account (credentials via account manager); wall setup; server postback endpoint                                                                                                          | Approval criteria; payment terms (negotiated)                                                             |
| AdGem        | Publisher account; property details (name, platform incl. Web, category, store URL if any); team review; address, payment method and tax forms before payout                                    | Traffic minimums; cash permission                                                                         |
| ayeT         | Publisher account; account-manager-assisted setup including traffic-quality discussion                                                                                                          | Approval criteria; cash permission                                                                        |
| Lootably     | Signup, then "alert your Lootably contact for approval"                                                                                                                                         | Criteria; cash permission                                                                                 |
| Adscend      | Name, email, **phone**, country, websites/apps, **daily active users**, majority countries, products of interest, go-live time, traffic source, fraud prevention; 18+; verified contact details | Whether zero DAU is disqualifying (likely a negative signal; INFERENCE)                                   |
| Monlix       | Add a valid website or app; approval                                                                                                                                                            | Cash permission; US payout rails beyond the listed methods                                                |

## C. Claims and permissions that need written confirmation (per provider)

Use PROVIDER_REGISTRY questions 1–36. The critical subset for the first conversation:

1. Cash-equivalent rewards (PayPal/ACH/gift cards) to users: Q1–2 (BitLabs: confirm that our
   specific model fits the public terms).
2. Custom UI on the API, our own ranking, and showing their offers alongside competitors': Q3–6.
3. Multiple networks, ranking, duplicate campaigns and pre-start routing: Q4–7. Ask privately and
   in writing; the public site stays general (D-017 as modified).
4. Traffic sources, including referral, ambassador and game-intent pages: Q8–11, Q27–29, Q31, Q33.
5. Additional bonus layers on top of offer rewards (group/progression): Q34.
6. Reversal windows, payment terms, reserves; full catalog with milestone payouts and store IDs:
   Q12–23.
7. Whether attribution or branding is required for API integrations: LEGAL L27.

## D. Is the current website credible enough for manual review?

**Design and honesty: yes.** Professional, clear, consistently honest about being pre-launch, with
a dedicated partner page describing integration, attribution and fraud plans.

**As deployed today: no.** Blocking problems a partner manager would see:

1. **No live URL.** The site is not deployed. Adscend calls the URL "the most important information
   required".
2. **No contact email.** The partner page's "Email partnerships" button is hidden and the page shows
   "address not yet published". Contact page likewise.
3. **No legal entity, jurisdiction or address** shown ("not yet published" on About).
4. **No named people.** Reviewers verify contact details (Adscend) and look for accountability.
5. **Working name** ("Worthplay", not cleared). Rebranding after approval means re-approval with
   every network.
6. Draft legal pages (acceptable for a pre-launch review, but listing processors is incomplete).

## E. Company information still missing

Legal entity name and state; EIN (needed for W-9/tax forms; AdGem requires tax forms before
payout); registered or mailing address; business phone (Adscend requires a phone number); domain;
business email(s); a bank account or business PayPal for receiving publisher payouts; founder names
and roles (and optionally LinkedIn); a short written traffic plan and fraud-prevention description
(Adscend asks for both); privacy-policy processor list (hosting, DB, email).

## F. Legal entity, domain and business email: required or preferable?

| Item                | Documented requirement found?                                                                                                                                           | Assessment                                                                                             |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Legal entity        | **Not stated as required** in the sources found. Adscend makes "Company Name" optional; BitLabs asks for "legal status" (implying individuals may register; INFERENCE). | **Strongly preferable now; required by us before money moves** (liability, contracts, tax, LEGAL-001). |
| Live domain / URL   | Adscend: URL is "the most important information"; Monlix: "add a valid website"; AdGem: property details.                                                               | **Effectively required.**                                                                              |
| Business email      | Not stated as required. Contact details are verified (Adscend).                                                                                                         | **Preferable.** A personal email weakens credibility and ties accounts to an individual.               |
| Phone               | Required by Adscend's form.                                                                                                                                             | Required for Adscend.                                                                                  |
| Tax forms / address | Required by AdGem before payout.                                                                                                                                        | Required to get paid.                                                                                  |

## G. What to change before the first application

1. **Choose and clear the name, then buy the domain** (avoid re-approval after a rebrand). (D-004)
2. **Form the entity, get an EIN, set the mailing address**, and set the env vars. The site then
   shows real company facts and the partner page shows its email button.
3. **Create business email(s)** (partners@, support@, privacy@ or aliases).
4. **Deploy** to the real domain with `DATABASE_URL`, run migrations, and set
   `NEXT_PUBLIC_SITE_URL` (enables indexing).
5. **Add founder names and roles** to About (D-007 allows real facts only).
6. **Prepare the application packet** (below), honest about pre-launch status, with no invented
   volumes.
7. Keep the D-017 multi-network disclosure. If a network objects, that is E001 evidence.
8. Leave privacy and terms marked draft if counsel review isn't done, but list the hosting and DB
   processors once chosen.

## H. Recommended application order

- **Wave 1 (in parallel, once §G is done): BitLabs, Offerwall.GG, RevU.** Together they test E001
  criteria fastest: explicit cash permission (BitLabs), low-barrier signed postbacks and reversals
  (Offerwall.GG), and the richest multi-step catalog API (RevU).
- **Wave 2: AdGem, ayeT, Lootably.** Email or contact the account team first for ayeT and Lootably,
  since approval runs through a contact.
- **Wave 3 (backup): Adscend, Monlix, others.**

Rationale for parallelism: E001 needs at least 3 approved providers. Applying one at a time wastes
weeks. Don't apply anywhere before §G: a rejection based on an unfinished site may be hard to
reverse (INFERENCE).

## Application packet (draft text for founders to adapt; fill the bracketed facts)

> **Company:** [Legal entity], a [state] company, [address]. Contact: [name, role, email, phone].
> **Product:** A US consumer rewards platform (pre-launch) focused on Android mobile-game offers.
> We present each offer's full requirements, milestone ladder, time limit and purchase conditions
> before the user starts, and track rewards through pending / confirmed / available states.
> **Stage:** Pre-launch. No live traffic yet. We are applying before launch so integrations and
> written permissions are in place first.
> **Integration:** Catalog API into our own UI; server-to-server postbacks with signature
> verification; idempotent processing on your transaction IDs; reversal handling; raw payload
> retention for reconciliation.
> **User identifiers:** One opaque, stable internal ID per user as the sub-ID. No personal data in
> sub-IDs.
> **Rewards:** We intend to offer cash-equivalent rewards and/or gift cards **only where your terms
> permit**. Please confirm.
> **Traffic plan (initial):** Organic: the founders' own social networks and word of mouth, organic
> social content, and search. No paid acquisition at launch. Any referral or ambassador program
> launches only with your written permission. Expected volume: unknown at this stage. We will not
> estimate it without data.
> **Fraud prevention (planned):** US adults (18+) only; verification before first withdrawal; one
> account per person; device and network risk signals; withdrawal holds and manual review;
> monitoring of your rejection rates as a quality signal.
> **Attribution:** Each user's attempt at an offer is attributed to exactly one network and never
> switched afterward.
> _(Private, per D-017: in the conversation, not on the public site, ask and get written answers
> on integrating multiple networks, independent ranking, duplicate campaigns and pre-start route
> selection: Q4–7.)_
> **Questions for you:** [paste the critical subset from §C].
