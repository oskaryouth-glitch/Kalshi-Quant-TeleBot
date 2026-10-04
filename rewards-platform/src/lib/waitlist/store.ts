import type { Platform } from "./schema";

export interface WaitlistRecord {
  email: string;
  emailNormalized: string;
  platform: Platform;
  note: string | null;
  source: string | null;
  privacyPolicyVersion: string;
  ageConfirmed: true;
}

export type AddResult = "created" | "already-exists";

/** Persistence boundary for early-access signups. Implementations must be idempotent per email. */
export interface WaitlistStore {
  readonly kind: string;
  add(record: WaitlistRecord): Promise<AddResult>;
}

/** Development and test store. Never selected in production (see config.ts). */
export class MemoryWaitlistStore implements WaitlistStore {
  readonly kind = "memory";
  private readonly records = new Map<string, WaitlistRecord & { createdAt: Date }>();

  async add(record: WaitlistRecord): Promise<AddResult> {
    if (this.records.has(record.emailNormalized)) return "already-exists";
    this.records.set(record.emailNormalized, { ...record, createdAt: new Date() });
    return "created";
  }

  get size(): number {
    return this.records.size;
  }
}
