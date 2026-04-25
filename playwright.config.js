import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:8000',
    headless: true,
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'python -m uvicorn backend.app.test_server:app --port 8000',
    url: 'http://localhost:8000/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
