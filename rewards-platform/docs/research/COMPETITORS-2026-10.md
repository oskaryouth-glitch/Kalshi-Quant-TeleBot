# Competitor notes (2026-10-04)

**Method and limits:** direct fetches of freecash.com, testerup.com and swagbucks.com were blocked by
this environment's egress proxy. These notes come from search-engine extracts of first-party pages,
app-store listings, help-center articles and third-party reviews (retrieved 2026-10-04). No
screenshots were reviewed, so visual details are **inferred** from page text. Labels: **OBSERVED**
(in first-party text), **REPORTED** (third-party), **INFERENCE**.

| Product   | What they lead with                                                                     | Patterns worth learning from                                                                                                                                                                                                                        | Patterns we reject                                                                                                                                                                                          |
| --------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Freecash  | "Get paid for testing apps, games & surveys" (OBSERVED, freecash.com/en)                | Pre-start check "Have you installed this game before?", which blocks offers that won't credit; "Next cashout" progress bar toward the withdrawal minimum; offer detail opens before "Play and Earn" (OBSERVED, freecash.com/academy beginner guide) | Cards show "UP TO $350.00" with a "5.0" rating ("Reviews are not verified by us"); casino category and roulette "double your winnings"; streaks, leaderboard, daily bonus ladder; coins currency (OBSERVED) |
| Testerup  | "Get rewarded to test mobile games and complete surveys" (OBSERVED, testerup.com)       | Explicit "rewards shown are examples… fixed returns are not guaranteed"; 18+; verification before first payout; PayPal-only payouts (OBSERVED)                                                                                                      | Reviewers report full rewards needing thousands of levels and purchase milestones (REPORTED, sidehustlenation.com)                                                                                          |
| Benjamin  | "Earn real cash playing games & surveys" (OBSERVED, benjaminone.com)                    | Dollar amounts, not points ("not confusing points or coins"); anti-gimmick line "No spin wheels. No fake prizes."; clear rules (new users only, start download in-app, disable VPN, up to 48h to appear) (OBSERVED, Play listing and help center)   | Earnings claims ("Earn a Benjamin ($100) or more every month"; "$5 to $200+ per game") (OBSERVED)                                                                                                           |
| Swagbucks | Broad "get paid for everyday activities"; points (SB) (OBSERVED, swagbucks.com/g/about) | Longevity and BBB accreditation as trust signals (REPORTED)                                                                                                                                                                                         | "Paid over $706,372,645" payout totals as social proof; points currency (OBSERVED)                                                                                                                          |

**Recurring complaints across the category** (REPORTED: Trustpilot, Reddit): milestones (especially
purchases and late levels) not tracking; rewards reduced or stopped near cash-out thresholds;
accounts locked at withdrawal; "up to" amounts that need very long play.

**Implications adopted (D-019):** show dollars, not points; give each offer an artwork-led card with
the amount prominent; open the full detail before start; ask eligibility questions up front (adopted
as "Before you start" items; a pre-start "installed before?" prompt is a future product step); use a
progress-to-withdrawal UI. **Rejected:** "up to" headlines, unverified ratings, payout-total social
proof, casino or chance mechanics, streak and leaderboard pressure, and earnings-per-month claims.

**Gaps vs. competitors we cannot close honestly yet:** social proof (no users), payout-method logos
(cash rewards unconfirmed), real game titles and artwork (no catalog or permissions).
