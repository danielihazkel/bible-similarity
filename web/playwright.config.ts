import { defineConfig, devices } from '@playwright/test'

// End-to-end smoke tests against the real `bsim serve` (the built viewer + the real results DB),
// in the locally installed Microsoft Edge (no browser download). `npm run build` first; run with
// `npm run e2e`. Needs artifacts/results.sqlite (the pipeline) — not part of `npm test`.
const PORT = 8777

export default defineConfig({
  testDir: 'e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    channel: 'msedge',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Edge'], channel: 'msedge' } },
    { name: 'phone', use: { viewport: { width: 390, height: 800 }, isMobile: false, channel: 'msedge' } },
  ],
  webServer: {
    command: `uv run bsim serve --port ${PORT}`,
    cwd: '..',
    url: `http://127.0.0.1:${PORT}/api/books`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
