import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:18180",
    trace: "retain-on-failure",
    channel: process.env.PLAYWRIGHT_CHANNEL,
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command:
        "cd ../backend && .venv/bin/alembic upgrade head && .venv/bin/python -m uvicorn app.api.app:create_app --factory --host 127.0.0.1 --port 18101",
      url: "http://127.0.0.1:18101/api/v1/healthz/ready",
      env: {
        APP_DATABASE_URL: "sqlite+aiosqlite:////tmp/olympiad-route-e2e.db",
        APP_DEMO_ENABLED: "true",
        APP_LOGGING_LEVEL: "WARNING",
      },
      reuseExistingServer: false,
    },
    {
      command:
        "./node_modules/.bin/vite --host 127.0.0.1 --port 18180 --strictPort",
      url: "http://127.0.0.1:18180",
      env: { VITE_API_PROXY_TARGET: "http://127.0.0.1:18101" },
      reuseExistingServer: false,
    },
  ],
});
