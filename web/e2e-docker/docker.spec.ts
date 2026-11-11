import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

// A smoke check of the public image (M157, DEPLOY.md step 3) against `docker run` on :8001.
const PAGES = [
  '/',
  '/findings',
  '/unit/c%3A0%3A1',
  '/read/c%3A0%3A3?layers=mainline',
  '/sequences',
  '/phrases',
  '/laws',
  '/laws?pair=4',
  '/prophetic',
  '/mainline',
  '/language',
  '/places',
  '/genealogy',
  '/eval',
  '/about',
]

for (const lang of ['en', 'he'] as const) {
  for (const path of PAGES) {
    test(`${lang}: ${path} loads, without serious accessibility violations`, async ({ page }) => {
      await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), lang)
      const errors: string[] = []
      page.on('pageerror', (e) => errors.push(e.message))
      await page.goto(path)
      await expect(page.locator('h1').first()).toBeVisible()
      await expect(page.locator('.error-box')).toHaveCount(0)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
      expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
      expect(errors).toEqual([])
    })
  }
}

test('the personal pages are off and say so; a non-commercial stage says not computed', async ({ page }) => {
  await page.goto('/labels')
  await expect(page.locator('.error-box')).toHaveCount(0)
  await expect(page.getByRole('navigation').getByRole('link', { name: 'Labels' })).toHaveCount(0)
  await page.goto('/speech')
  await expect(page.getByText(/not computed in this build/i).first()).toBeVisible()
})
