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

test("home marketplace preview is explicitly illustrative and shows no outcome claims", async ({
  page,
}) => {
  await page.goto("/");
  const banner = page.getByTestId("illustrative-banner");
  await expect(banner).toContainText("Examples");
  await expect(banner).toContainText("not real offers");
  // No placeholder outcome rows or estimates anywhere on the homepage (D-019).
  await expect(page.getByText(/not enough data yet/i)).toHaveCount(0);
  await expect(page.getByText(/expected, based on/i)).toHaveCount(0);
  await expect(page.getByText(/tracking record|typical days/i)).toHaveCount(0);
  // The headline amount on an offer with purchases is labeled as the no-purchase amount.
  await expect(page.getByText("available without purchases").first()).toBeVisible();
});

test("opening an offer shows every material term before starting", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Farm sim, example offer/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { level: 2, name: "Farm sim" })).toBeVisible();
  await expect(dialog).toContainText("Example offer");
  await expect(dialog).toContainText("21 days from install");
  await expect(dialog).toContainText("Purchase required");
  await expect(dialog).toContainText("Only reachable after the purchase above");
  await expect(dialog).toContainText("New players only");
  await expect(
    dialog.getByRole("listitem").filter({ hasText: "Reach farm level 40" }),
  ).toContainText("$15.00");
  await expect(dialog.getByRole("button", { name: "Start offer" })).toBeDisabled();

  // Closes with Escape and with the close button.
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await page.getByRole("link", { name: /Kart racer, example offer/ }).click();
  await expect(page.getByRole("dialog")).toContainText("7 days from install");
  await page.getByRole("button", { name: "Close offer details" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
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

test("no horizontal overflow at 320px on any page", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 320, height: 640 } });
  const page = await context.newPage();
  for (const route of publicRoutes) {
    await page.goto(route);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `overflow on ${route}`).toBeLessThanOrEqual(0);
    // The menu button must be fully on-screen.
    const button = page.getByRole("button", { name: "Open menu" });
    const box = await button.boundingBox();
    expect(box && box.x + box.width <= 320, `menu button clipped on ${route}`).toBe(true);
  }
  await context.close();
});

test("offer rows never clip purchase requirements or time limits", async ({ browser }) => {
  for (const width of [320, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 800 } });
    const page = await context.newPage();
    await page.goto("/");
    const metas = page.getByTestId("offer-row-meta");
    const count = await metas.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const clipped = await metas
        .nth(i)
        .evaluate((el) =>
          [el, ...Array.from(el.querySelectorAll("*"))].some(
            (n) =>
              n.scrollWidth > n.clientWidth + 1 ||
              n.getBoundingClientRect().right > window.innerWidth,
          ),
        );
      expect(clipped, `row ${i} clipped at ${width}px`).toBe(false);
    }
    await expect(metas.filter({ hasText: "Purchase required" })).toHaveCount(1);
    await context.close();
  }
});
