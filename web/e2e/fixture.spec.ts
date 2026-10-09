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
  '/labels',
  '/phrases',
  '/sequences',
  '/sequences/1',
  '/changes',
  '/changes?view=rewrites',
  '/borrowing',
  '/sequences/2',
  '/compare?a=c%3A0%3A1&b=c%3A1%3A1',
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
  '/unit/v%3A0?mode=syntax',
  '/discoveries?mode=syntax',
  '/poetry?sort=antithetic',
  '/structure',
  '/acrostics',
  '/divisions',
  '/divisions?book=0&kind=cut',
  '/divisions?unit=c%3A0%3A2',
  '/ketiv',
  '/ketiv?cls=swap&euphemism=1',
  '/ketiv?unit=v%3A4',
  '/citations',
  '/citations?family=word&resolved=1',
  '/citations?unit=v%3A0',
  '/phrases?view=spread',
  '/phrases?view=spread&all=1&unit=c%3A0%3A2',
  '/map',
  '/network',
  '/style',
  '/shifts',
  '/shifts?by=use&q=all',
  '/language',
  '/language?book=0',
  '/speech',
  '/speech?book=0',
  '/speech?view=voices&voice=divine',
  '/unit/v%3A1?syntax=1',
  '/unit/c%3A0%3A1?syntax=1',
  '/phrases?unit=v%3A0',
  '/changes?unit=v%3A3',
  '/borrowing?unit=v%3A5',
  '/discoveries?unit=v%3A3',
  '/typescenes?unit=c%3A0%3A1',
  '/wordplay?view=rhyme&rq=all&unit=c%3A0%3A1',
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

test('a verse page says what the analyses found and links to the filtered lists', async ({ page }) => {
  await page.goto('/unit/v%3A1')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await expect(bar).toBeVisible()
  await bar.getByRole('link', { name: /parallel with a borrowing estimate/ }).click()
  await expect(page).toHaveURL(/\/borrowing\?unit=v%3A1/)
  await expect(page.locator('.unit-filter')).toBeVisible()
  await expect(page.locator('.borrow-pair')).toHaveCount(1)
})

test('a chapter that starts in running text links to its place on the Divisions page', async ({ page }) => {
  await page.goto('/unit/c%3A0%3A2')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: 'a chapter start inside running text' }).click()
  await expect(page).toHaveURL(/\/divisions\?book=0&unit=c%3A0%3A2/)
  await expect(page.locator('.gap-item')).toHaveCount(1)
  await expect(page.locator('.gap-item .gap-verses .he')).toHaveCount(2)
  await expect(page.getByRole('img', { name: /The score of every boundary/ })).toBeVisible()
})

test('a verse with a ketiv / qere links to it, and the parallel that writes the qere', async ({ page }) => {
  await page.goto('/unit/v%3A4')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '1 word written one way and read another' }).click()
  await expect(page).toHaveURL(/\/ketiv\?unit=v%3A4/)
  await expect(page.locator('.kq-item')).toHaveCount(1)
  await expect(page.locator('.kq-item .w-focus')).toHaveCount(1)
  await page.locator('.kq-item').getByRole('link', { name: /writes .*: the qere/ }).click()
  await expect(page).toHaveURL(/\/unit\/v%3A5/)
})

test('a verse that is cited links to the citation and its source', async ({ page }) => {
  await page.goto('/unit/v%3A0')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '1 explicit citation' }).click()
  await expect(page).toHaveURL(/\/citations\?unit=v%3A0/)
  await expect(page.locator('.cite-item')).toHaveCount(1)
  await expect(page.locator('.cite-item .cite-source .he')).toHaveCount(1)
  await page.locator('.cite-item').getByRole('link', { name: 'Compare' }).click()
  await expect(page).toHaveURL(/\/compare\?/)
})

test('a pair is labelled from a list of similar verses and shows on the Labels page', async ({ page }, info) => {
  // it writes to the server's one labels file: run once, not on every device at the same time
  test.skip(info.project.name !== 'desktop')
  await page.goto('/unit/v%3A0')
  const first = page.locator('.hit').first()
  const real = first.getByRole('button', { name: 'Real' })
  await real.click()
  await expect(real).toHaveAttribute('aria-pressed', 'true')
  await page.goto('/labels')
  await expect(page.locator('.labels-list > li')).toHaveCount(1)
  await page.locator('.labels-list').getByRole('button', { name: 'Real' }).click() // clear it again
  await expect(page.locator('.labels-list > li')).toHaveCount(0)
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
