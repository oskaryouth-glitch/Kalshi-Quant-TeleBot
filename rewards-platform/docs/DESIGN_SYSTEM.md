# Design system

## Directions considered (2026-10-04)

Scored 1–5 against the founders' criteria. Scores are design judgment, not user research.

| Direction        | Description                                                                                                                                                                                               | Trust | Excitement | Differentiation | Legibility | Mobile | Total |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---: | :--------: | :-------------: | :--------: | :----: | :---: |
| **Ledger**       | Editorial fintech: warm paper, serif display, deep green accent, statement-style tables.                                                                                                                  |   5   |     2      |        3        |     5      |   4    |  19   |
| **Arcade Night** | Dark UI, saturated violet/green gradients, glow, game-HUD typography.                                                                                                                                     |   2   |     5      |        1        |     3      |   4    |  15   |
| **Scorecard** ✅ | Warm paper, charcoal ink, one electric ultramarine accent, bold grotesque display, tabular figures. The **Offer Facts label** (a standardized disclosure, like a nutrition label) is the signature motif. |   5   |     3      |        5        |     5      |   5    |  23   |

**Why Scorecard:** it turns the product thesis (standardized, honest disclosure) into the visual
identity itself. (Amended by D-019: the label is no longer the hero; offer cards lead with earning,
and the full disclosure lives in the offer detail.) Ledger is trustworthy but reads as a bank, not a consumer product. Arcade Night is
exciting, but it is the visual language of the sites users already distrust, and it differentiates
nothing. Game artwork can bring color and energy later; the interface chrome stays calm.

## Tokens (source of truth: `src/app/globals.css`)

| Token                              | Hex                               | Use                                                                        |
| ---------------------------------- | --------------------------------- | -------------------------------------------------------------------------- |
| `paper`                            | `#f7f5f0`                         | Page background                                                            |
| `paper-deep`                       | `#efebe2`                         | Hover fills, selected states                                               |
| `surface`                          | `#ffffff`                         | Cards                                                                      |
| `line` / `line-strong`             | `#e3ded3` / `#cfc8ba`             | Hairlines / input borders                                                  |
| `ink` / `ink-2` / `ink-3`          | `#16161a` / `#3d3d45` / `#5f5f69` | Text: primary / body / secondary                                           |
| `accent`                           | `#3a2ee8`                         | Links, eyebrows, focus rings, one emphasis per view                        |
| `pending`, `ok`, `bad` (+ `-soft`) |                                   | **Status meaning only**: pending / available / reversed. Never decoration. |

All text/background pairs used are tested to ≥ 4.5:1 (`src/lib/design/contrast.test.ts` reads
the CSS directly).

**Type:** Bricolage Grotesque (display; optical sizing, tight tracking) + Inter (text). Both are
self-hosted by `next/font`. Every money figure uses `.num` (tabular figures).

**Shape:** cards 20px radius; pills for buttons and badges; 2px ink rules separate the major parts
of the Offer Facts label.

**Motion:** color/opacity transitions ≤150ms only. No animated numbers, tickers or confetti.
`prefers-reduced-motion` respected globally.

## Balance: about 75% trust, 25% energy (D-019)

- **Trust (most of the surface):** warm paper, charcoal ink, generous whitespace, tabular figures,
  plain copy, explicit labels.
- **Energy (concentrated, never in the chrome):** colorful genre artwork, large dollar figures on
  offer cards, an accent gradient on the second line of the hero headline, progress bars, and hover
  lift on cards.
- **Never:** money-green or gold for amounts, animated or counting numbers, confetti, flashing,
  countdowns, emojis, fake activity.

## Offer card (browse level)

Order: artwork (with "Example" tag for fixtures) → title, genre · platform → purchase badge →
**headline amount** + its label → secondary amount → "N milestones · N-day limit" → "View offer".

- The headline amount comes only from `summarizeOffer()`. Never compute it in a component.
- The label always says what the number is ("available without purchases", "total rewards
  available", or "expected, based on N players").
- Purchase badge tones: none → ok, optional → neutral, required → pending.
- Compact rows put the purchase status and time limit on their own line, which may wrap. They are
  **never truncated** (e2e-tested at 320px and 390px).

## Offer detail (pre-start disclosure)

Header (art, "Example offer" label for fixtures, title) → stat tiles (without purchases, with
purchases, time limit, purchases) → **milestone ladder** (numbered, each reward, purchase steps and
purchase-gated steps flagged in the pending color) → "Before you start" (time-limit rule,
eligibility, verification and reversal caveat) → "Start offer" (disabled in preview). Nothing
material may be omitted. Opens as a native `<dialog>` from cards, and is also shown inline.

## Game artwork

`src/components/offers/game-art.tsx`: original flat SVG scenes per genre (city, puzzle, racing,
word, farm), each with its own saturated palette. They never depict a real game, character or
brand. Replace them with provider artwork only where provider terms allow.

## Reward tracker (illustrative)

Progress bar plus per-milestone status: available (ok), confirmed on hold or pending (pending), not
reached (neutral). The balance is split into Available and Pending or on hold. It mirrors
ARCHITECTURE 2.5.

## Voice and tone

- Plain, specific, calm. Short sentences. Contractions are fine in UI, but avoid them in legal text.
- Say what is true **now**; use "we plan to" / "will" for anything not built.
- Explain numbers rather than hype them ("Listed total: every milestone added up").
- Banned language is listed in `src/lib/copy-guard.ts`; it fails the build.
- Prefer "reward" and "milestone" to "cash" and "earn big".

## Accessibility baseline

Semantic landmarks, skip link, one `h1` per page, visible focus rings, 44px+ touch targets, form
errors tied to fields via `aria-describedby` with focus moved to the error summary, and native
`<details>` for FAQs. axe (WCAG 2.2 AA tags) runs on every page in e2e at mobile and desktop sizes.
