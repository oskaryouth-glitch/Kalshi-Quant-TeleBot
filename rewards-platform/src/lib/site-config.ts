/**
 * Single source of truth for brand, company and contact facts shown on the site.
 *
 * Rules (see docs/DECISIONS.md D-004, D-007):
 * - Nothing here may be invented. Unknown facts are `null` and the UI renders an
 *   explicit "not yet published" state rather than a plausible-looking placeholder.
 * - `scripts/launch-check.ts` fails while any launch-blocking value is missing or
 *   the brand name is still a working name.
 * - This file must stay free of path-alias imports so the launch check can run it
 *   with plain Node type-stripping.
 */

export type NameStatus = "working" | "cleared";

function env(key: string): string | null {
  const value = process.env[key];
  return value && value.trim().length > 0 ? value.trim() : null;
}

export const site = {
  /** Working name only. Not trademark-cleared. See docs/DECISIONS.md D-004. */
  name: "Worthplay",
  nameStatus: "working" as NameStatus,

  /** One-line positioning used in metadata. Not a claim of a live product. */
  tagline: "Know what a game reward takes before you start.",
  description:
    "Worthplay is a pre-launch US consumer product that lays out the requirements, milestones, deadlines and purchase conditions of rewarded mobile-game offers before you start, and ranks them by more than the biggest headline number.",

  url: env("NEXT_PUBLIC_SITE_URL") ?? "http://localhost:3000",

  /** Registered legal entity name, e.g. "Example Labs, Inc.". Required before launch. */
  legalEntity: env("NEXT_PUBLIC_LEGAL_ENTITY"),
  /** State of formation, e.g. "Delaware". Required before launch. */
  entityJurisdiction: env("NEXT_PUBLIC_ENTITY_JURISDICTION"),
  /** Registered or mailing address for legal notices. Required before launch. */
  mailingAddress: env("NEXT_PUBLIC_MAILING_ADDRESS"),

  contact: {
    partners: env("NEXT_PUBLIC_PARTNERS_EMAIL"),
    support: env("NEXT_PUBLIC_SUPPORT_EMAIL"),
    privacy: env("NEXT_PUBLIC_PRIVACY_EMAIL"),
  },

  /** Company stage. Drives honest "pre-launch" language across the site. */
  stage: "pre-launch" as const,
  market: "United States",
  minimumAge: 18,
} as const;

/** Version identifiers recorded alongside every waitlist signup as a consent record. */
export const POLICY_VERSIONS = {
  privacy: "2026-10-04-draft",
  terms: "2026-10-04-draft",
} as const;

/** Values that must be present (and a cleared name) before public launch. */
export function launchBlockers(): string[] {
  const blockers: string[] = [];
  if (site.nameStatus !== "cleared") {
    blockers.push(`Brand name "${site.name}" is a working name (trademark/domain not cleared).`);
  }
  if (!site.legalEntity) blockers.push("NEXT_PUBLIC_LEGAL_ENTITY is not set.");
  if (!site.entityJurisdiction) blockers.push("NEXT_PUBLIC_ENTITY_JURISDICTION is not set.");
  if (!site.mailingAddress) blockers.push("NEXT_PUBLIC_MAILING_ADDRESS is not set.");
  if (!site.contact.partners) blockers.push("NEXT_PUBLIC_PARTNERS_EMAIL is not set.");
  if (!site.contact.support) blockers.push("NEXT_PUBLIC_SUPPORT_EMAIL is not set.");
  if (!site.contact.privacy) blockers.push("NEXT_PUBLIC_PRIVACY_EMAIL is not set.");
  if (site.url.startsWith("http://localhost")) blockers.push("NEXT_PUBLIC_SITE_URL is not set.");
  if (POLICY_VERSIONS.privacy.endsWith("-draft")) {
    blockers.push("Privacy policy is still a draft (needs legal review).");
  }
  if (POLICY_VERSIONS.terms.endsWith("-draft")) {
    blockers.push("Terms are still a draft (needs legal review).");
  }
  return blockers;
}
