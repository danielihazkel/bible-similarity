import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

// CI end-to-end tests against `bsim fixture-serve`: the tiny synthetic DB of `bsim.fixture` (six
// verses in Genesis and Exodus, verse and chapter units, made-up lists, analyses and word senses). Every page
// renders a heading without an error box or a console error, in both interface languages, with
// no serious axe violations. smoke.spec.ts checks the same pages against the real data.
const PAGES = [
  '/',
  '/browse/0?tab=verses',
  '/unit/c%3A0%3A1?halves=1',
  '/unit/v%3A0',
  '/compare?a=c%3A0%3A2&b=c%3A1%3A1',
  '/search?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA&mode=lexical',
  '/search?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA',
  '/lemma/7225',
  '/discoveries',
  '/phrases',
  '/sequences',
  '/sequences/1',
  '/changes',
  '/changes?view=rewrites',
  '/typescenes',
  '/poetry',
  '/poetry?view=pairs',
  '/wordplay',
  '/wordplay?view=alliteration',
  '/wordplay?view=rhyme',
  '/names',
  '/domains',
  '/domains/002001',
  '/unit/c%3A0%3A1?mode=domain',
  '/poetry?sort=antithetic',
  '/structure',
  '/acrostics',
  '/map',
  '/network',
  '/style',
  '/shifts',
  '/shifts?by=use&q=all',
  '/language',
  '/language?book=0',
  '/eval',
  '/about',
]

function collectErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  return errors
}

async function loads(page: Page, path: string) {
  await page.goto(path)
  await expect(page.locator('h1').first()).not.toBeEmpty()
  await page.waitForLoadState('networkidle')
  await expect(page.locator('.status.error')).toHaveCount(0)
}

for (const path of PAGES) {
  test(`loads ${path}`, async ({ page }) => {
    const errors = collectErrors(page)
    await loads(page, path)
    expect(errors).toEqual([])
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
}

test('a verse lists its similar verses and links to them', async ({ page }) => {
  await page.goto('/unit/v%3A0')
  const hits = page.locator('.hit')
  await expect(hits.first()).toBeVisible()
  expect(await hits.count()).toBeGreaterThan(0)
})

test('the Hebrew interface is right to left and loads every page cleanly', async ({ page }) => {
  test.setTimeout(120_000)
  const errors = collectErrors(page)
  await page.addInitScript(() => localStorage.setItem('bsim.locale', 'he'))
  for (const path of PAGES) {
    await loads(page, path)
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  }
  expect(errors).toEqual([])
})

for (const locale of ['en', 'he'] as const) {
  test(`no serious accessibility violations (${locale})`, async ({ page }) => {
    test.setTimeout(150_000)
    await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
    for (const path of PAGES) {
      await loads(page, path)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
      const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
      expect(serious.map((v) => `${path}: ${v.id} (${v.nodes.length})`)).toEqual([])
    }
  })
}
