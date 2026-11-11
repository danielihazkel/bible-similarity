import { defineConfig, devices } from '@playwright/test'

// The public image's smoke check (M157): `docker run -p 8001:8000 … bsim-public` first.
export default defineConfig({
  testDir: '.',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:8001', channel: 'msedge', serviceWorkers: 'block' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Edge'], channel: 'msedge' } },
    { name: 'phone', use: { viewport: { width: 390, height: 800 }, isMobile: false, channel: 'msedge' } },
  ],
})
