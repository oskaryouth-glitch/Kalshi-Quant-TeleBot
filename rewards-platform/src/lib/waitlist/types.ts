import type { FieldErrors } from "./schema";

/** Shared between the server action and the client form. Keep free of server-only imports. */
export type WaitlistState =
  | { status: "idle" }
  | { status: "success" }
  | { status: "invalid"; errors: FieldErrors; values: Record<string, string> }
  | { status: "rate-limited" }
  | { status: "unavailable" }
  | { status: "error" };

export const HONEYPOT_FIELD = "website";
