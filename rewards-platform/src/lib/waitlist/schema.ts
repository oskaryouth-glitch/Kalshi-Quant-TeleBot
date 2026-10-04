import { z } from "zod";

export const PLATFORMS = ["android", "iphone", "other"] as const;
export type Platform = (typeof PLATFORMS)[number];

export const NOTE_MAX = 500;

/**
 * Input accepted from the early-access form. Collect only what we need (DECISIONS D-008):
 * email, phone platform, an optional note, an 18+ confirmation and an optional source tag.
 */
export const waitlistInputSchema = z.object({
  email: z
    .string({ error: "Enter your email address." })
    .trim()
    .min(1, { error: "Enter your email address." })
    .max(254, { error: "That email address is too long." })
    .pipe(z.email({ error: "Enter a valid email address." })),
  platform: z.enum(PLATFORMS, { error: "Choose the type of phone you use." }),
  note: z
    .string()
    .trim()
    .max(NOTE_MAX, { error: `Keep your note under ${NOTE_MAX} characters.` })
    .optional()
    .transform((v) => (v ? v : null)),
  ageConfirmed: z.literal("yes", { error: "You must be 18 or older to join." }),
  source: z
    .string()
    .trim()
    .optional()
    .transform((v) => (v && /^[a-z0-9_-]{1,64}$/i.test(v) ? v.toLowerCase() : null)),
});

export type WaitlistInput = z.output<typeof waitlistInputSchema>;

export type FieldErrors = Partial<Record<"email" | "platform" | "note" | "ageConfirmed", string>>;

/** Normalized form used for uniqueness. Lowercasing is a pragmatic choice; see ARCHITECTURE.md. */
export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}
