"use server";

import { headers } from "next/headers";
import { getWaitlistStore, waitlistLimiter } from "@/lib/waitlist/config";
import { submitWaitlist } from "@/lib/waitlist/service";
import type { WaitlistState } from "@/lib/waitlist/types";

/**
 * Server Action for the early-access form. Next.js Server Actions reject cross-origin
 * POSTs by comparing Origin and Host, which covers CSRF for this endpoint.
 */
export async function joinWaitlist(
  _prev: WaitlistState,
  formData: FormData,
): Promise<WaitlistState> {
  const h = await headers();
  // x-forwarded-for is only trustworthy behind a proxy that overwrites it (e.g. Vercel).
  // It is used solely as a rate-limit key and is hashed before being held in memory.
  const clientKey =
    h.get("x-forwarded-for")?.split(",")[0]?.trim() || h.get("x-real-ip") || "unknown";

  return submitWaitlist(formData, {
    store: getWaitlistStore(),
    limiter: waitlistLimiter,
    clientKey,
    log: (event, detail) => console.info(JSON.stringify({ event, ...detail })),
  });
}
