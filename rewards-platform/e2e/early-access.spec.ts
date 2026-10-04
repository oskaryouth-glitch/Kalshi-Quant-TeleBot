import { expect, test } from "@playwright/test";
import postgres from "postgres";

const dbUrl = process.env.E2E_DATABASE_URL;

test.describe("early access form", () => {
  test.skip(!dbUrl, "E2E_DATABASE_URL not set; the form is closed without a database");

  let sql: postgres.Sql;
  test.beforeAll(() => {
    sql = postgres(dbUrl!, { max: 1, onnotice: () => {} });
  });
  test.afterAll(async () => {
    await sql.end();
  });

  // The limiter keys on x-forwarded-for; give each test its own client so the
  // (deliberately strict) rate limit does not couple tests together.
  test.beforeEach(async ({ page }) => {
    await page.setExtraHTTPHeaders({
      "x-forwarded-for": `198.51.100.${Math.floor(Math.random() * 250)}`,
    });
  });

  const unique = (tag: string) =>
    `e2e-${tag}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;

  test("shows accessible field errors for an empty submission", async ({ page }) => {
    await page.goto("/early-access");
    await page.getByRole("button", { name: "Join early access" }).click();
    await expect(page.locator("#form-status")).toContainText("fix the highlighted fields");
    await expect(page.locator("#form-status")).toBeFocused();
    await expect(page.getByLabel("Email address")).toHaveAttribute("aria-invalid", "true");
    await expect(page.locator("#email-error")).toBeVisible();
    await expect(page.locator("#platform-error")).toBeVisible();
    await expect(page.locator("#age-error")).toContainText("18");
  });

  test("stores a valid signup once, with the referral tag", async ({ page }) => {
    const email = unique("ok");
    await page.goto("/early-access?ref=partner_page");
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Android").check();
    await page.getByLabel(/I am 18 or older/).check();
    await page.getByRole("button", { name: "Join early access" }).click();
    await expect(page.getByRole("status")).toContainText("You’re on the list");

    const rows = await sql`select platform, source, age_confirmed, privacy_policy_version
                           from waitlist_signups where email_normalized = ${email}`;
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      platform: "android",
      source: "partner_page",
      age_confirmed: true,
    });

    // Duplicate (different case) gets the identical response and no new row.
    await page.goto("/early-access");
    await page.getByLabel("Email address").fill(email.toUpperCase());
    await page.getByLabel("iPhone").check();
    await page.getByLabel(/I am 18 or older/).check();
    await page.getByRole("button", { name: "Join early access" }).click();
    await expect(page.getByRole("status")).toContainText("You’re on the list");
    const [{ count }] = await sql`select count(*)::int as count from waitlist_signups
                                  where email_normalized = ${email}`;
    expect(count).toBe(1);
  });

  test("works without JavaScript (progressive enhancement)", async ({ browser }) => {
    const context = await browser.newContext({
      javaScriptEnabled: false,
      extraHTTPHeaders: { "x-forwarded-for": "198.51.100.251" },
    });
    const page = await context.newPage();
    const email = unique("nojs");
    await page.goto("/early-access");
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Other / not sure").check();
    await page.getByLabel(/I am 18 or older/).check();
    await page.getByRole("button", { name: "Join early access" }).click();
    await expect(page.getByText("You’re on the list")).toBeVisible();
    const rows = await sql`select 1 from waitlist_signups where email_normalized = ${email}`;
    expect(rows).toHaveLength(1);
    await context.close();
  });
});
