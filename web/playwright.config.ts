import { defineConfig, devices } from '@playwright/test'

// End-to-end tests of the built viewer (`npm run build` first) against a live API, in two setups:
// - `npm run e2e`: smoke.spec.ts against the real `bsim serve` (the real results DB, so it needs
//   the pipeline's artifacts);
// - `npm run e2e:fixture` (CI; playwright.fixture.config.ts): fixture.spec.ts against
//   `bsim fixture-serve`, the tiny synthetic DB of `bsim.fixture` (no data, no model).
// Locally both run in the installed Microsoft Edge (no browser download); CI uses Playwright's
// own Chromium (`npx playwright install chromium`).
export function e2eConfig(fixture: boolean) {
  const port = fixture ? 8778 : 8777
  const channel = process.env.CI ? undefined : 'msedge'
  return defineConfig({
    testDir: 'e2e',
    testMatch: fixture ? 'fixture.spec.ts' : 'smoke.spec.ts',
    timeout: 30_000,
    expect: { timeout: 10_000 },
    fullyParallel: false,
    reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
    use: {
      baseURL: `http://127.0.0.1:${port}`,
      channel,
      trace: 'retain-on-failure',
    },
    projects: [
      { name: 'desktop', use: { ...devices[channel ? 'Desktop Edge' : 'Desktop Chrome'], channel } },
      { name: 'phone', use: { viewport: { width: 390, height: 800 }, isMobile: false, channel } },
    ],
    webServer: {
      command: fixture ? `uv run bsim fixture-serve --port ${port}` : `uv run bsim serve --port ${port}`,
      cwd: '..',
      url: `http://127.0.0.1:${port}/api/books`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  })
}

export default e2eConfig(false)
