/** Joins class names, skipping falsy values. Deliberately tiny; no clsx dependency. */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
