# Design system

## Directions considered (2026-10-04)

Scored 1–5 against the founders' criteria. Scores are design judgment, not user research.

| Direction        | Description                                                                                                                                                                                               | Trust | Excitement | Differentiation | Legibility | Mobile | Total |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---: | :--------: | :-------------: | :--------: | :----: | :---: |
| **Ledger**       | Editorial fintech: warm paper, serif display, deep green accent, statement-style tables.                                                                                                                  |   5   |     2      |        3        |     5      |   4    |  19   |
| **Arcade Night** | Dark UI, saturated violet/green gradients, glow, game-HUD typography.                                                                                                                                     |   2   |     5      |        1        |     3      |   4    |  15   |
| **Scorecard** ✅ | Warm paper, charcoal ink, one electric ultramarine accent, bold grotesque display, tabular figures. The **Offer Facts label** (a standardized disclosure, like a nutrition label) is the signature motif. |   5   |     3      |        5        |     5      |   5    |  23   |

**Why Scorecard:** it turns the product thesis (standardized, honest disclosure) into the visual
identity itself. Ledger is trustworthy but reads as a bank, not a consumer product. Arcade Night is
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

## Offer Facts label (signature component)

Fixed row order, so labels can be compared at a glance:

1. Header: "Offer Facts", platform · region
2. Game title, subtitle
3. Deadline, Purchases (none / optional / required)
4. **Listed total** (with note "every milestone added up, including purchases"), **Without purchases**
5. Milestones in order, with purchase milestones tagged
6. "From real outcomes": typical earnings, typical days to finish, tracking record. Each shows
   either a value with `n=` or "Not enough data yet"

Rules: never show the listed total larger or bolder than the without-purchases total. Never omit
section 6; its honesty is the point. The illustrative banner is mandatory for fixture data
(enforced by type).

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
