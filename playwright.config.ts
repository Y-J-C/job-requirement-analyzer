import { defineConfig, devices } from "@playwright/test";

const webUrl = "http://localhost:3001";

process.env.E2E_RUN_ID ??= `${Date.now()}-${process.pid}`;

export default defineConfig({
  testDir: "./e2e/tests",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  reporter: "list",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: webUrl,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "corepack pnpm dev:e2e",
    url: webUrl,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
