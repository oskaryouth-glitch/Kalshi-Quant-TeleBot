# Naming, domain and trademark screening process (D-004)

**Status:** not started. "Worthplay" is a **working name only** and must not be locked in because it
appears in the implementation. Changing it is a one-line config change (`src/lib/site-config.ts`)
plus metadata and copy review.

**Why it comes first:** provider approvals attach to a domain and brand. Rebranding after approval
means re-approval with every network (E001 readiness §G).

## Steps (founders, with counsel for clearance)

1. **Criteria.** Short, pronounceable, spellable after hearing it once; no money or gambling
   connotations (no "cash", "jackpot", "lucky"); works beyond college and beyond games (D-032); not
   confusingly close to competitors or the networks we work with.
2. **Long list.** 20–40 candidates.
3. **Knockout screen (free, founders):**
   - USPTO trademark search (USPTO Trademark Center / search system) for identical and similar
     marks in likely classes. Candidates to discuss with counsel: Class 9 (software/apps), Class 35
     (promotional and loyalty/incentive services), Class 41 (entertainment/gaming information),
     Class 42 (SaaS).
   - State trademark databases where the entity forms.
   - Common-law use: web search, Google Play and App Store search, social platforms.
   - Domain availability (.com preferred; note aftermarket prices without buying yet).
   - Social handles on the main platforms.
4. **Shortlist of 3–5** that pass knockout.
5. **Counsel clearance search and opinion** on the top 1–2 (a cost decision for founders).
6. **Decide; register the domain and handles; consider filing** (counsel advises on intent-to-use
   filing and classes).
7. **Update the implementation:** set `name` and `nameStatus: "cleared"` in `site-config.ts`;
   review metadata, the OG image and copy; rerun `npm run check:launch`.

Record the outcome as a new decision superseding D-004.
