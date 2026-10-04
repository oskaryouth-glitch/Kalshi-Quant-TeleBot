"use client";

import { useActionState, useEffect, useRef } from "react";
import { joinWaitlist } from "@/app/early-access/actions";
import { buttonClasses } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { NOTE_MAX } from "@/lib/waitlist/schema";
import { HONEYPOT_FIELD, type WaitlistState } from "@/lib/waitlist/types";

const initialState: WaitlistState = { status: "idle" };

const platformOptions = [
  { value: "android", label: "Android" },
  { value: "iphone", label: "iPhone" },
  { value: "other", label: "Other" },
] as const;

export function WaitlistForm() {
  const [state, formAction, pending] = useActionState(joinWaitlist, initialState);
  const statusRef = useRef<HTMLDivElement>(null);
  const successRef = useRef<HTMLDivElement>(null);
  const sourceRef = useRef<HTMLInputElement>(null);

  // Read ?ref= after hydration rather than via useSearchParams, which would force this
  // statically rendered form to bail out to client-only rendering and break no-JS submits.
  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get("ref");
    if (ref && sourceRef.current) sourceRef.current.value = ref;
  }, []);

  // Move focus to the outcome so keyboard and screen-reader users hear it.
  useEffect(() => {
    if (state.status === "success") successRef.current?.focus();
    else if (state.status !== "idle") statusRef.current?.focus();
  }, [state]);

  if (state.status === "success") {
    return (
      <div
        ref={successRef}
        tabIndex={-1}
        role="status"
        className="rounded-[var(--radius-card)] border border-ok/30 bg-ok-soft p-6 sm:p-8"
      >
        <p className="font-display text-2xl font-semibold tracking-[-0.02em] text-ink">
          You’re on the list.
        </p>
        <p className="mt-3 leading-relaxed text-ink-2">
          We will email you when early access opens. That is the only reason we will use your
          address. If you change your mind, reply to any email from us or use the contact details in
          our privacy policy and we will delete it.
        </p>
      </div>
    );
  }

  const errors = state.status === "invalid" ? state.errors : {};
  const values = state.status === "invalid" ? state.values : {};
  const hasErrors = Object.keys(errors).length > 0;

  return (
    <form action={formAction} noValidate className="space-y-7" aria-describedby="form-status">
      <div
        id="form-status"
        ref={statusRef}
        tabIndex={-1}
        aria-live="polite"
        className={cn(
          "rounded-xl text-[0.9375rem] leading-relaxed outline-none empty:hidden",
          (hasErrors ||
            state.status === "rate-limited" ||
            state.status === "error" ||
            state.status === "unavailable") &&
            "border border-bad/25 bg-bad-soft p-4 text-ink",
        )}
      >
        {hasErrors ? "Please fix the highlighted fields below." : null}
        {state.status === "rate-limited"
          ? "Too many attempts from your connection. Please wait a few minutes and try again."
          : null}
        {state.status === "error"
          ? "Something went wrong on our side and your details were not saved. Please try again later."
          : null}
        {state.status === "unavailable"
          ? "Early access sign-ups are not open yet. Your details were not saved."
          : null}
      </div>

      <Field id="email" label="Email address" error={errors.email}>
        <input
          id="email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          required
          maxLength={254}
          defaultValue={values.email}
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={errors.email ? "email-error" : undefined}
          className={inputClasses(Boolean(errors.email))}
        />
      </Field>

      <fieldset aria-describedby={errors.platform ? "platform-error" : undefined}>
        <legend className="font-medium text-ink">Which phone do you use?</legend>
        <p className="mt-1 text-sm text-ink-3">
          We are starting with Android. This tells us how many people want iPhone support.
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {platformOptions.map((opt) => (
            <label
              key={opt.value}
              className="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-line-strong bg-surface px-4 transition-colors hover:border-ink-3 has-[:checked]:border-ink has-[:checked]:bg-paper-deep has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent"
            >
              <input
                type="radio"
                name="platform"
                value={opt.value}
                required
                defaultChecked={values.platform === opt.value}
                className="size-4 accent-[var(--color-ink)]"
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
        <FieldError id="platform-error" message={errors.platform} />
      </fieldset>

      <Field
        id="note"
        label="Anything you want us to know?"
        hint={`Optional. For example, what would make a rewards app trustworthy to you. Up to ${NOTE_MAX} characters.`}
        error={errors.note}
      >
        <textarea
          id="note"
          name="note"
          rows={3}
          maxLength={NOTE_MAX}
          defaultValue={values.note}
          aria-invalid={errors.note ? true : undefined}
          aria-describedby={cn("note-hint", errors.note && "note-error") || undefined}
          className={cn(inputClasses(Boolean(errors.note)), "min-h-24 py-3")}
        />
      </Field>

      <div>
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            name="ageConfirmed"
            value="yes"
            required
            aria-invalid={errors.ageConfirmed ? true : undefined}
            aria-describedby={errors.ageConfirmed ? "age-error" : undefined}
            className="mt-1 size-4 shrink-0 accent-[var(--color-ink)]"
          />
          <span className="leading-relaxed text-ink-2">
            I am 18 or older. I have read the{" "}
            <a href="/privacy" className="text-accent underline underline-offset-4">
              privacy policy
            </a>{" "}
            and agree to be emailed about early access.
          </span>
        </label>
        <FieldError id="age-error" message={errors.ageConfirmed} />
      </div>

      {/* Honeypot: hidden from people and assistive tech; bots tend to fill it. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Leave this field empty
          <input
            type="text"
            name={HONEYPOT_FIELD}
            tabIndex={-1}
            autoComplete="off"
            defaultValue=""
          />
        </label>
      </div>
      <input ref={sourceRef} type="hidden" name="source" defaultValue="" />

      <button
        type="submit"
        disabled={pending}
        className={buttonClasses("primary", "w-full sm:w-auto")}
      >
        {pending ? "Joining…" : "Join early access"}
      </button>
    </form>
  );
}

function inputClasses(invalid: boolean) {
  return cn(
    "block w-full rounded-xl border bg-surface px-4 text-base text-ink placeholder:text-ink-3",
    "min-h-12 transition-colors focus:border-ink focus:outline-none focus-visible:outline-2 focus-visible:outline-accent",
    invalid ? "border-bad" : "border-line-strong hover:border-ink-3",
  );
}

function Field({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="font-medium text-ink">
        {label}
      </label>
      {hint ? (
        <p id={`${id}-hint`} className="mt-1 text-sm text-ink-3">
          {hint}
        </p>
      ) : null}
      <div className="mt-2">{children}</div>
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-2 text-sm font-medium text-bad">
      {message}
    </p>
  );
}
