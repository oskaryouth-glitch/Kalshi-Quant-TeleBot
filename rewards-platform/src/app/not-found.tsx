import { Arrow, ButtonLink } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/section";

export default function NotFound() {
  return (
    <Container size="narrow" className="py-24 sm:py-32">
      <Eyebrow>404</Eyebrow>
      <h1 className="mt-4 font-display text-4xl font-semibold tracking-[-0.03em] sm:text-5xl">
        This page does not exist.
      </h1>
      <p className="mt-5 text-lg leading-relaxed text-ink-2">
        The link may be out of date, or the page may have moved.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <ButtonLink href="/">
          Go to the home page <Arrow />
        </ButtonLink>
        <ButtonLink href="/contact" variant="secondary">
          Contact us
        </ButtonLink>
      </div>
    </Container>
  );
}
