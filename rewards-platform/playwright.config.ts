import { defineConfig, devices } from "@playwright/test";

/**
 * E2E runs against a PRODUCTION build (`npm run build` first) served by `next start`.
 * The early-access page renders the open form only if DATABASE_URL was set at build time.
 *
 * Env:
 *   E2E_DATABASE_URL            Postgres used by the waitlist tests (also passed to the server)
 *   PLAYWRIGHT_CHROMIUM_PATH    optional custom Chromium binary (sandboxed environments)
 *   PLAYWRIGHT_NO_PROXY=1       launch Chromium with --no-proxy-server (sandboxed environments)
 */
const port = Number(process.env.E2E_PORT ?? 3200);
const launchOptions = {
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
  args: process.env.PLAYWRIGHT_NO_PROXY ? ["--no-proxy-server"] : [],
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], browserName: "chromium", launchOptions },
    },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 900 }, launchOptions },
    },
  ],
  webServer: {
    command: `npx next start -p ${port} -H 127.0.0.1`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: { DATABASE_URL: process.env.E2E_DATABASE_URL ?? "" },
  },
});
