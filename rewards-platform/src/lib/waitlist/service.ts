import { POLICY_VERSIONS } from "@/lib/site-config";
import type { FixedWindowRateLimiter } from "./rate-limit";
import { normalizeEmail, waitlistInputSchema, type FieldErrors } from "./schema";
import type { WaitlistStore } from "./store";
import { HONEYPOT_FIELD, type WaitlistState } from "./types";

export { HONEYPOT_FIELD, type WaitlistState };

export interface SubmitContext {
  store: WaitlistStore | null;
  limiter: FixedWindowRateLimiter;
  clientKey: string;
  log?: (event: string, detail?: Record<string, unknown>) => void;
}

/**
 * Pure(ish) submission handler, independent of Next.js so it can be unit tested.
 *
 * Privacy/abuse properties:
 * - The response is identical for new and existing emails (no list-membership disclosure).
 * - A filled honeypot gets a success-shaped response but nothing is stored.
 * - If no store is configured we say so instead of silently dropping the signup.
 * - Logged events never include the email address or note.
 */
export async function submitWaitlist(form: FormData, ctx: SubmitContext): Promise<WaitlistState> {
  const log = ctx.log ?? (() => {});

  if (!ctx.store) return { status: "unavailable" };

  const honeypot = form.get(HONEYPOT_FIELD);
  if (typeof honeypot === "string" && honeypot.length > 0) {
    log("waitlist.honeypot");
    return { status: "success" };
  }

  if (!ctx.limiter.check(ctx.clientKey)) {
    log("waitlist.rate_limited");
    return { status: "rate-limited" };
  }

  const raw = {
    email: str(form.get("email")),
    platform: str(form.get("platform")),
    note: str(form.get("note")),
    ageConfirmed: str(form.get("ageConfirmed")),
    source: str(form.get("source")),
  };

  const parsed = waitlistInputSchema.safeParse(raw);
  if (!parsed.success) {
    const errors: FieldErrors = {};
    for (const issue of parsed.error.issues) {
      const field = issue.path[0];
      if (
        (field === "email" ||
          field === "platform" ||
          field === "note" ||
          field === "ageConfirmed") &&
        !errors[field]
      ) {
        errors[field] = issue.message;
      }
    }
    return {
      status: "invalid",
      errors,
      values: { email: raw.email ?? "", platform: raw.platform ?? "", note: raw.note ?? "" },
    };
  }

  const input = parsed.data;
  try {
    const result = await ctx.store.add({
      email: input.email,
      emailNormalized: normalizeEmail(input.email),
      platform: input.platform,
      note: input.note,
      source: input.source,
      privacyPolicyVersion: POLICY_VERSIONS.privacy,
      ageConfirmed: true,
    });
    log("waitlist.stored", { result, platform: input.platform, store: ctx.store.kind });
    return { status: "success" };
  } catch (err) {
    log("waitlist.store_error", {
      store: ctx.store.kind,
      error: err instanceof Error ? err.name : "unknown",
    });
    return { status: "error" };
  }
}

function str(v: FormDataEntryValue | null): string | undefined {
  return typeof v === "string" ? v : undefined;
}
