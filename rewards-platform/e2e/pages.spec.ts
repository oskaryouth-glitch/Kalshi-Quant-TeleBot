import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { publicRoutes } from "../src/lib/routes";
import { site } from "../src/lib/site-config";

for (const route of publicRoutes) {
  test.describe(`page ${route}`, () => {
    test("renders cleanly, accessibly and without layout overflow", async ({ page }, info) => {
      const problems: string[] = [];
      page.on("console", (m) => {
        if (m.type() === "error" || m.type() === "warning")
          problems.push(`${m.type()}: ${m.text()}`);
      });
      page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));

      const res = await page.goto(route, { waitUntil: "networkidle" });
      expect(res?.status()).toBe(200);

      // Metadata
      await expect(page).toHaveTitle(new RegExp(site.name));
      const description = await page.locator('meta[name="description"]').getAttribute("content");
      expect(description?.length ?? 0).toBeGreaterThan(40);
      await expect(page.locator("html")).toHaveAttribute("lang", "en");

      // Structure: exactly one h1, landmarks present.
      await expect(page.locator("h1")).toHaveCount(1);
      await expect(page.locator("main#main")).toHaveCount(1);
      await expect(page.locator("header").first()).toBeVisible();
      await expect(page.locator("footer")).toBeVisible();

      // No horizontal scrolling at this viewport.
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, "horizontal overflow in px").toBeLessThanOrEqual(0);

      // Accessibility: no serious or critical axe violations (WCAG 2.x A/AA rules).
      const axe = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();
      const serious = axe.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      );
      expect(
        serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
      ).toEqual([]);

      // Privacy: the site sets no cookies.
      expect(await page.context().cookies()).toEqual([]);

      expect(problems).toEqual([]);

      await page.screenshot({
        path: `e2e/.artifacts/${info.project.name}${route === "/" ? "/home" : route}.png`,
        fullPage: true,
      });
    });
  });
}

test("unknown routes return a helpful 404", async ({ page }) => {
  const res = await page.goto("/this-does-not-exist");
  expect(res?.status()).toBe(404);
  await expect(page.locator("h1")).toHaveText("This page does not exist.");
});

test("home shows the Offer Facts label as an explicit illustration", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("illustrative-banner")).toContainText("Illustrative example");
  await expect(page.getByTestId("illustrative-banner")).toContainText("not a real offer");
  await expect(page.getByText("Not enough data yet", { exact: true })).toHaveCount(3);
});

test("security headers are present", async ({ request }) => {
  const res = await request.get("/");
  const h = res.headers();
  expect(h["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(h["content-security-policy"]).toContain("object-src 'none'");
  expect(h["x-content-type-options"]).toBe("nosniff");
  expect(h["x-frame-options"]).toBe("DENY");
  expect(h["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(h["x-powered-by"]).toBeUndefined();
  expect(h["set-cookie"]).toBeUndefined();
});

test("metadata routes respond", async ({ request }) => {
  for (const path of ["/robots.txt", "/sitemap.xml", "/icon.svg", "/opengraph-image"]) {
    const res = await request.get(path);
    expect(res.status(), path).toBe(200);
  }
  const sitemap = await (await request.get("/sitemap.xml")).text();
  for (const route of publicRoutes) expect(sitemap).toContain(`<loc>${new URL(route, site.url)}`);
});
