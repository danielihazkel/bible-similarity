import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

// Every page loads against the real API, renders its heading and logs no errors.
const PAGES: [string, RegExp][] = [
  ['/', /Browse/],
  ['/search?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA&mode=lexical', /Search/],
  ['/compare?a=c%3A26%3A14&b=c%3A26%3A53', /Compare/],
  ['/discoveries', /Discoveries|Undiscovered/],
  ['/phrases', /Shared phrases/],
  ['/sequences', /Parallel sequences/],
  ['/sequences/4', /Samuel/],
  ['/changes', /How parallels differ/],
  ['/poetry', /Parallel halves/],
  ['/wordplay', /Wordplay/],
  ['/names?e=1732', /People and places/],
  ['/structure', /Structure/],
  ['/map', /Map/],
  ['/style?book=26', /Style/],
  ['/unit/c%3A0%3A1?halves=1', /Genesis 1/],
  ['/browse/0?tab=verses', /Genesis/],
  ['/lemma/430', /Concordance|אלה/],
  ['/eval', /Evaluation/],
  ['/acrostics', /Acrostics/],
  ['/network?type=pericope&unit=s%3A50', /Network of echoes/],
  ['/sequences?order=reverse&q=all', /Parallel sequences/],
  ['/changes?view=rewrites&pair=8-37', /How parallels differ/],
  ['/unit/c%3A26%3A145?acrostic=1', /Psalms 145/],
  ['/about', /About/],
]

function collectErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  return errors
}

for (const [path, heading] of PAGES) {
  test(`loads ${path}`, async ({ page }) => {
    const errors = collectErrors(page)
    await page.goto(path)
    await expect(page.locator('h1').first()).toHaveText(heading)
    await expect(page.locator('.status.error')).toHaveCount(0)
    await page.waitForLoadState('networkidle')
    expect(errors).toEqual([])
  })
}

test('navigation menus work at the current width', async ({ page }, info) => {
  await page.goto('/')
  if (info.project.name === 'phone') {
    const toggle = page.getByRole('button', { name: /Menu/ })
    await expect(toggle).toBeVisible()
    await expect(page.locator('#main-nav')).toBeHidden()
    await toggle.click()
    await expect(page.locator('#main-nav')).toBeVisible()
    await page.getByRole('link', { name: /Wordplay/ }).click()
    await expect(page).toHaveURL(/\/wordplay$/)
    await expect(page.locator('#main-nav')).toBeHidden() // closes after navigating
  } else {
    await expect(page.getByRole('button', { name: /Menu/ })).toBeHidden()
    await page.getByRole('button', { name: /Patterns/ }).click()
    const menu = page.locator('#menu-patterns')
    await expect(menu).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(menu).toBeHidden()
    await page.getByRole('button', { name: /Parallels/ }).click()
    await page.getByRole('link', { name: /Sequences/ }).click()
    await expect(page).toHaveURL(/\/sequences$/)
    await expect(page.getByRole('button', { name: /Parallels/ })).toHaveClass(/active/)
  }
  // the page never scrolls sideways
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})

for (const scheme of ['light', 'dark'] as const) {
  test(`main pages have no serious accessibility violations (${scheme})`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme })
    await checkA11y(page)
  })
}

async function checkA11y(page: Page) {
  for (const path of ['/', '/sequences/4', '/poetry', '/names?e=1732', '/unit/c%3A0%3A1', '/network', '/acrostics', '/eval']) {
    await page.goto(path)
    await page.locator('h1').first().waitFor()
    await page.waitForLoadState('networkidle')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    expect(serious.map((v) => `${path}: ${v.id} (${v.nodes.length})`)).toEqual([])
  }
}
