import { expect, test } from "@playwright/test";
import { findViolations } from "../src/lib/copy-guard";
import { publicRoutes } from "../src/lib/routes";

test.describe.configure({ mode: "serial" });

test("every internal link resolves and no link is empty", async ({ page, request }) => {
  const internal = new Set<string>();
  for (const route of publicRoutes) {
    await page.goto(route);
    const hrefs = await page.$$eval("a[href]", (as) => as.map((a) => a.getAttribute("href") ?? ""));
    for (const href of hrefs) {
      expect(href.trim(), `empty href on ${route}`).not.toBe("");
      expect(href, `placeholder href on ${route}`).not.toBe("#");
      if (href.startsWith("mailto:")) {
        expect(href, `malformed mailto on ${route}`).toMatch(/^mailto:[^@\s]+@[^@\s]+\.[^@\s]+/);
      } else if (href.startsWith("/")) {
        internal.add(href.split("#")[0] || "/");
      } else if (href.startsWith("#")) {
        await expect(page.locator(href), `missing anchor ${href} on ${route}`).toHaveCount(1);
      } else {
        throw new Error(`Unexpected external link on ${route}: ${href}`);
      }
    }
  }
  for (const path of internal) {
    const res = await request.get(path);
    expect(res.status(), path).toBe(200);
  }
});

test("rendered public copy passes the claim guard", async ({ page }) => {
  for (const route of publicRoutes) {
    await page.goto(route);
    // Open every disclosure so collapsed FAQ text is checked too.
    await page.$$eval("details", (ds) => ds.forEach((d) => d.setAttribute("open", "")));
    const text = await page.evaluate(() => {
      const clone = document.body.cloneNode(true) as HTMLElement;
      clone
        .querySelectorAll('[data-copy-guard="ignore"], script, style')
        .forEach((n) => n.remove());
      return clone.innerText;
    });
    const title = await page.title();
    expect(findViolations(`${title}\n${text}`), route).toEqual([]);
  }
});
