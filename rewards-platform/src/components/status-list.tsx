import { Badge } from "@/components/ui/badge";

export type Status = "planned" | "live";

export interface Commitment {
  title: string;
  body: string;
  status: Status;
}

/** A list of commitments, each carrying an explicit Planned / Live status. */
export function StatusList({ items }: { items: Commitment[] }) {
  return (
    <ul className="divide-y divide-line rounded-[var(--radius-card)] border border-line bg-surface">
      {items.map((item) => (
        <li key={item.title} className="grid gap-2 p-5 sm:grid-cols-[1fr_auto] sm:gap-6 sm:p-6">
          <div>
            <h3 className="font-semibold tracking-[-0.01em]">{item.title}</h3>
            <p className="mt-1.5 leading-relaxed text-ink-2">{item.body}</p>
          </div>
          <div className="sm:pt-0.5">
            {item.status === "live" ? (
              <Badge tone="ok">Live</Badge>
            ) : (
              <Badge tone="neutral">Planned</Badge>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
