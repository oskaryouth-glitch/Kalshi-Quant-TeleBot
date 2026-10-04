import { Container } from "./container";
import { Eyebrow } from "./section";

export function PageHeader({
  eyebrow,
  title,
  intro,
  children,
}: {
  eyebrow: string;
  title: React.ReactNode;
  intro?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <header className="border-b border-line pt-14 pb-12 sm:pt-20 sm:pb-16">
      <Container>
        <div className="max-w-3xl">
          <Eyebrow>{eyebrow}</Eyebrow>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-[-0.03em] text-balance sm:text-5xl">
            {title}
          </h1>
          {intro ? (
            <p className="mt-5 text-lg leading-relaxed text-pretty text-ink-2 sm:text-xl">
              {intro}
            </p>
          ) : null}
          {children}
        </div>
      </Container>
    </header>
  );
}
