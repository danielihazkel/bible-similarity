import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { PUBLIC_PORT } from '../playwright.config'

// The fixture as a public read-only server serves it (`bsim fixture-serve --public`, the switches
// of configs/public.yaml; DEPLOY.md): nothing personal, no query encoder. The viewer leaves out
// what the server does not offer instead of showing errors.
test.use({ baseURL: `http://127.0.0.1:${PUBLIC_PORT}` })

function collectErrors(page: import('@playwright/test').Page) {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  return errors
}

test('the nav and the jump box leave out your labels and notebook', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('#main-nav a[href="/findings"]')).toHaveCount(1) // the nav is there
  await expect(page.locator('a[href="/labels"]')).toHaveCount(0)
  await expect(page.locator('a[href="/notebook"]')).toHaveCount(0)
  await page.keyboard.press('Control+k')
  const box = page.getByRole('combobox')
  await box.fill('findings')
  await expect(page.getByRole('option', { name: /^Findings/ })).toHaveCount(1) // pages are offered
  await box.fill('notebook')
  await expect(page.getByRole('option', { name: /^Search the text/ })).toBeVisible()
  await expect(page.getByRole('option', { name: /^(Your )?notebook/i })).toHaveCount(0)
})

test('a unit page has no label buttons and no notebook panel', async ({ page }) => {
  const errors = collectErrors(page)
  await page.goto('/unit/v%3A0')
  await expect(page.locator('.hit').first()).toBeVisible()
  await expect(page.locator('.label-buttons')).toHaveCount(0)
  await expect(page.locator('.notebook-panel')).toHaveCount(0)
  await expect(page.locator('.status.error')).toHaveCount(0)
  expect(errors).toEqual([])
})

test('the labels and notebook pages say the site keeps none', async ({ page }) => {
  for (const path of ['/labels', '/notebook']) {
    await page.goto(path)
    await expect(page.getByText('This site keeps no labels or notebook')).toBeVisible()
  }
})

test('search is lexical only, and says so', async ({ page }) => {
  await page.goto('/search?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA&mode=fused')
  await expect(page.getByText('Semantic and fused search are not offered on this site')).toBeVisible()
  await expect(page.locator('.hit').first()).toBeVisible()
  await expect(page.getByRole('radio', { name: 'Semantic' })).toHaveCount(0)
  await expect(page.locator('.status.error')).toHaveCount(0)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
})

test('the personal routes are not served', async ({ request }) => {
  for (const path of ['/api/labels', '/api/notebook', '/api/labels/queue']) {
    const r = await request.get(path)
    expect(r.status(), path).toBe(404)
  }
})
