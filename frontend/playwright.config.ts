import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 0,
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://127.0.0.1:5176',
  },
  webServer: {
    command: 'npx vite --host 127.0.0.1 --port 5176',
    url: 'http://127.0.0.1:5176',
    reuseExistingServer: true,
    timeout: 120000,
  },
})
