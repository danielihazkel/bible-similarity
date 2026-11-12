import AxeBuilder from '@axe-core/playwright'
import { readFileSync } from 'node:fs'
import { expect, type Locator, type Page, test } from '@playwright/test'

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
  '/labels?tab=queue',
  '/notebook',
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
  '/poetry?view=meter',
  '/roots',
  '/roots?view=key',
  '/roots?kind=inf_abs',
  '/root/7218',
  '/read/c%3A0%3A1',
  '/refrains',
  '/refrains?all=1&unit=v%3A2&known=1',
  '/read/c%3A0%3A1?layers=refrains',
  '/psalms',
  '/psalms?unit=c%3A0%3A1&turned=1&sort=turn',
  '/read/c%3A0%3A1?layers=mood',
  '/pentateuch',
  '/pentateuch?book=1',
  '/read/c%3A0%3A1?layers=sources',
  '/read/c%3A0%3A1?layers=speakers%2Ccola%2Cleitworte%2Cphrases%2Crare%2Cwordplay%2Cketiv%2Cturns',
  '/read/c%3A0%3A2?layers=wordplay%2Cketiv%2Cturns%2Cleitworte&lw=root',
  '/poetry?view=meter&group=pool',
  '/unit/c%3A0%3A1?halves=1&meter=1',
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
  '/structure?view=small',
  '/structure?view=small&list=verses',
  '/structure?view=small&unit=c%3A0%3A1&mirrored=1',
  '/map',
  '/network',
  '/findings',
  '/sequences?view=arcs',
  '/sequences?view=arcs&q=all&book=1',
  '/network?view=directions',
  '/network?view=directions&backward=1&unit=c%3A1%3A1',
  '/style',
  '/shifts',
  '/shifts?by=use&q=all',
  '/language',
  '/language?book=0',
  '/speech',
  '/speech?book=0',
  '/speech?view=voices&voice=divine',
  '/speech?view=dialogue',
  '/speech?view=dialogue&book=1&unequal=1',
  '/forms',
  '/gematria?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA',
  '/read/c%3A0%3A1?layers=gematria',
  '/gematria-links',
  '/gematria-links?sort=value&same=1',
  '/els',
  '/ciphers',
  '/ciphers?cipher=albam&known=1',
  '/masorah',
  '/masorah?text=qere',
  '/places',
  '/places?p=1&book=0',
  '/read/c%3A0%3A1?layers=places',
  '/place-lists',
  '/place-lists?list=trek&show=short',
  '/place-arc',
  '/place-arc?book=1',
  '/place-links',
  '/place-links?place=1&sort=km&bins=no_lists',
  '/genealogy',
  '/genealogy?p=10',
  '/genealogy?p=1',
  '/query',
  '/query?q=%5Blemma%3D430%5D+%5Blemma%3D559%5D',
  '/workbench',
  '/divine',
  '/divine?book=0',
  '/read/c%3A0%3A1?layers=divine',
  '/etiologies',
  '/etiologies?show=leads&order=strongest',
  '/brackets',
  '/brackets?show=strong&order=strongest&book=0',
  '/retold',
  '/retold?group=carried&order=most&known=1',
  '/haftarot',
  '/haftarot?p=p%3ABereshit',
  '/chronology',
  '/frameworks',
  '/frameworks?k=asa',
  '/binomials',
  '/binomials?pair=2091%2B3701&show=both&order=turned',
  '/sums',
  '/sums?list=ezra2&scope=every&step=yes',
  '/vocabulary',
  '/reception',
  '/reception?unit=v%3A0',
  '/source',
  '/source?example=priestly',
  '/witnesses',
  '/witnesses?unit=c%3A0%3A1',
  '/read/c%3A0%3A1?layers=witnesses',
  '/read/c%3A0%3A1?layers=reception',
  '/glossary',
  '/tours',
  '/masorah?tour=numbers&step=3',
  '/compare?a=v%3A0&b=v%3A1&marks=meaning',
  '/synopses',
  '/synopses/1',
  '/synopses/1?base=2',
  '/workbench?a=chapters%3A0%3A1&feature=domain',
  '/workbench?tab=check&q=%5Blemma%3D430%5D&set=chapters%3A0%3A1&within=corpus',
  '/forms?view=lists&kind=genealogy',
  '/map?color=lists',
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
  '/neighbourhood/v%3A0',
  '/mainline',
  '/mainline?order=canon&known=1',
  '/read/c%3A0%3A1?layers=mainline',
  '/prophetic',
  '/prophetic?form=woe&known=1',
  '/read/c%3A0%3A1?layers=prophetic',
  '/laws',
  '/laws?pair=1',
  '/laws?view=laws&code=covenant',
  '/neighbourhood/c%3A0%3A1?hops=1&off=fused',
  '/pages',
  '/pages?q=gematria',
]

function collectErrors(page: Page): string[] {
  const errors: string[] = []
  // the fixture has no parasha units: this week's reading answers 503 and the home page leaves its
  // line out, as it should (M136); the browser still logs the response, once for each such answer
  let week503 = 0
  page.on('response', (r) => {
    if (r.status() === 503 && new URL(r.url()).pathname === '/api/week') week503++
  })
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => {
    if (m.type() !== 'error') return
    if (week503 > 0 && m.text().includes('status of 503')) {
      week503--
      return
    }
    errors.push(m.text())
  })
  return errors
}

// A page has loaded when its heading is there and no `Loading` is left (not `networkidle`, which
// Playwright advises against: it waits on every request and so on the page's timing)
async function loads(page: Page, path: string) {
  await page.goto(path)
  await expect(page.locator('h1').first()).not.toBeEmpty()
  await expect(page.locator('p.status[role="status"]')).toHaveCount(0)
  await expect(page.locator('.status.error')).toHaveCount(0)
}

for (const path of PAGES) {
  test(`loads ${path}`, async ({ page }) => {
    const errors = collectErrors(page)
    await loads(page, path)
    expect(errors).toEqual([])
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(1)
    // a table that scrolls sideways in its wrapper can be reached from the keyboard (M167)
    await expect
      .poll(() => page.evaluate(() => [...document.querySelectorAll('.table-wrap')].filter((w) => w.scrollWidth > w.clientWidth + 1 && !w.hasAttribute('tabindex')).length))
      .toBe(0)
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

test('a verse page names its places, its hidden names and its letter value', async ({ page }) => {
  await page.goto('/unit/v%3A0')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: /1 place on the map, most named אמר/ }).click()
  await expect(page).toHaveURL(/\/places\?unit=v%3A0/)
  await expect(page.locator('.geo-pt')).toHaveCount(1)
  await page.goBack()
  await bar.getByRole('link', { name: /name read through atbash or albam \(יהוה read as מצפץ\)/ }).click()
  await expect(page).toHaveURL(/\/ciphers\?unit=v%3A0/)
  await expect(page.locator('.cipher-hit')).toHaveCount(1)
  await page.goBack()
  await bar.getByRole('link', { name: /^letter value / }).click()
  await expect(page).toHaveURL(/\/gematria\?q=\d+&view=verses/)
})

test('a chapter whose lines fall like a lament links to the stresses of its lines', async ({ page }) => {
  await page.goto('/unit/v%3A1')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: /lines fall like a lament/ }).click()
  await expect(page).toHaveURL(/\/unit\/c%3A0%3A1\?halves=1&meter=1/)
  await expect(page.locator('.source .meter-badge').first()).toHaveText('3:1')
  await page.goto('/poetry?view=meter')
  await expect(page.getByRole('heading', { name: 'Does Lamentations fall?' })).toBeVisible()
})

test('a verse with two words of one root links to them, and on to the root', async ({ page }) => {
  await page.goto('/unit/v%3A0')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: /pair of words of one root/ }).click()
  await expect(page).toHaveURL(/\/roots\?unit=v%3A0/)
  await expect(page.locator('.root-pair')).toHaveCount(1)
  await page.locator('.root-pair').getByRole('link', { name: /root/ }).click()
  await expect(page).toHaveURL(/\/root\/7218/)
  await expect(page.locator('.root-members .lemma-chip')).toHaveCount(1)
})

test('the unit page opens the layered reader, whose layers paint the words', async ({ page }) => {
  await page.goto('/unit/c%3A0%3A1')
  await page.getByRole('link', { name: 'Read with layers' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1$/)
  // speakers and turns are on by default: Genesis 1:2 is spoken, a turn comes before 1:3
  await expect(page.locator('.reader-text .spk')).toHaveCount(2)
  await expect(page.locator('.reader-gap.gap-turn')).toHaveCount(1)
  await page.getByRole('button', { name: 'Wordplay' }).click()
  await expect(page).toHaveURL(/layers=speakers%2Cleitworte%2Cwordplay%2Cturns/)
  await expect(page.locator('.reader-text .wp')).toHaveCount(2)
  await page.locator('.reader-text .wp').first().click()
  await expect(page.locator('.reader-text .wp-partner')).toHaveCount(1)
  await page.getByRole('link', { name: /Next/ }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A2\?layers=/)
})

test('gematria: a word in each system, its forms and lemmas, and a verse total from the reader', async ({ page }) => {
  await page.goto('/gematria?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA')
  await expect(page.getByText(/The value of ראשית in each system/)).toBeVisible()
  await expect(page.getByText(/911 \(Standard\): 1 written form \(4 words in the text\), 1 lemma and 0 verses\./)).toBeVisible()
  await expect(page.locator('.gm-forms li')).toHaveCount(1)
  await page.getByRole('button', { name: /Ordinal/ }).click()
  await expect(page).toHaveURL(/system=ordinal/)
  await page.goto('/read/c%3A0%3A1?layers=gematria')
  await expect(page.locator('.reader-text .w-mark').first()).toHaveText('=913')
  await page.locator('.gm-total').first().click()
  await expect(page).toHaveURL(/\/gematria\?q=1282&view=verses$/)
  await expect(page.locator('.hit')).toHaveCount(1)
})

test('atbash and albam: the checks, a name read through a swap, and its chapter', async ({ page }) => {
  // every swap, not only those named in advance (the default since M159)
  await page.goto('/ciphers?known=0')
  await expect(page.locator('.dlg-verdict')).toHaveCount(4)
  await expect(page.locator('.cipher-hit')).toHaveCount(2)
  await page.getByRole('radio', { name: 'Atbash' }).click()
  await expect(page).toHaveURL(/\/ciphers\?known=0&cipher=atbash$/)
  await expect(page.locator('.cipher-hit')).toHaveCount(1)
  await expect(page.locator('.cipher-hit .w-shared')).toHaveCount(1)
  await page.goto('/findings')
  await page.getByRole('link', { name: /Atbash and albam/ }).first().click()
  await expect(page).toHaveURL(/\/ciphers/)
})

test('the Masorah’s counts: the middles against ours, the totals and their findings', async ({ page }) => {
  await page.goto('/masorah')
  await expect(page.locator('.msr-middle')).toHaveCount(4)
  await expect(page.locator('.msr-middle .dlg-verdict')).toHaveText(['off', 'lands', 'lands', 'off'])
  await page.getByRole('radio', { name: 'As read' }).click()
  await expect(page).toHaveURL(/\/masorah\?text=qere$/)
  await expect(page.locator('.msr-middle').first()).toContainText('It falls 4 letters after ours')
  await expect(page.locator('.msr-totals tbody tr')).toHaveCount(2)
  await page.goto('/findings')
  await page.getByRole('link', { name: /The Masorah’s counts/ }).first().click()
  await expect(page).toHaveURL(/\/masorah/)
})

test('places on the map: the points, a place panel, the unit page and the reader', async ({ page }) => {
  await page.goto('/places')
  await expect(page.locator('.geo-pt')).toHaveCount(2)
  await expect(page.locator('.geo-land')).toHaveCount(1)
  await page.locator('.place-list').getByRole('button', { name: 'אמר' }).click()
  await expect(page).toHaveURL(/\/places\?p=1$/)
  await expect(page.locator('.place-panel')).toContainText('31.78° N, 35.23° E')
  await expect(page.locator('.place-verse')).toHaveCount(2)
  await page.getByRole('radio', { name: 'Regions' }).click()
  await expect(page.locator('.geo-pt')).toHaveCount(1)
  await page.goto('/unit/c%3A0%3A1')
  const where = page.getByRole('region', { name: 'Where this happens' })
  await expect(where.locator('.geo-pt')).toHaveCount(1)
  await where.getByRole('link', { name: 'Open on the map' }).click()
  await expect(page).toHaveURL(/\/places\?unit=c%3A0%3A1$/)
  await page.goto('/read/c%3A0%3A1?layers=places')
  await expect(page.locator('.reader-text .pl-town')).toHaveCount(2)
})

test('equal values: the tests, the equivalences, Genesis 1:1 and the pairs', async ({ page }) => {
  await page.goto('/gematria-links')
  await expect(page.locator('.gl-tests')).toHaveCount(2)
  await expect(page.locator('.gl-tests').first().locator('tbody tr')).toHaveCount(3)
  await expect(page.locator('.gl-eq tbody tr')).toHaveCount(2)
  await expect(page.locator('.gl-props tbody tr')).toHaveCount(2)
  await expect(page.getByRole('link', { name: 'v:3' })).toHaveAttribute('href', '/unit/v%3A3')
  await expect(page.locator('.gl-pairs li')).toHaveCount(1)
  await page.getByRole('checkbox', { name: 'With pairs spelled alike' }).click()
  await expect(page.locator('.gl-pairs li')).toHaveCount(2)
  await page.goto('/findings')
  await page.getByRole('link', { name: /Equal values, related words\?/ }).first().click()
  await expect(page).toHaveURL(/\/gematria-links/)
})

test('place lists: a list against its shuffles, its path on the map, the districts', async ({ page }) => {
  await page.goto('/place-lists')
  const lists = page.locator('.pls-table').first().locator('tbody tr')
  await expect(lists).toHaveCount(1)
  await expect(lists.first()).toContainText('441 km')
  await expect(lists.first().locator('.dlg-verdict')).toHaveText('holds')
  await expect(page.locator('.pls-detail .geo-pt')).toHaveCount(2)
  await expect(page.locator('.pls-path.text')).toHaveCount(1)
  await expect(page.locator('.pls-bar')).toHaveCount(4)
  await expect(page.locator('.pls-steps li')).toHaveCount(2)
  await page.getByRole('radio', { name: 'A short path' }).click()
  await expect(page).toHaveURL(/show=short/)
  await expect(page.locator('.pls-path.short')).toHaveCount(1)
  await expect(page.locator('.pls-districts .geo-pt')).toHaveCount(2)
  await expect(page.locator('.pls-districts tbody tr')).toHaveCount(2)
  await page.goto('/findings')
  await page.getByRole('link', { name: /Place lists on the ground/ }).first().click()
  await expect(page).toHaveURL(/\/place-lists/)
})

test('the geographic arc: a book’s chapters on the map, a known move, the oracles', async ({ page }) => {
  await page.goto('/place-arc')
  await expect(page.getByRole('heading', { name: 'The path of Genesis' })).toBeVisible()
  await expect(page.locator('.pa-book .geo-pt')).toHaveCount(2)
  await expect(page.locator('.pa-book .pa-path')).toHaveCount(1)
  await expect(page.locator('.pa-chapters li')).toHaveCount(2)
  await expect(page.locator('.pa-chapters li').nth(1)).toContainText('270 km')
  await page.getByRole('button', { name: 'Show Exodus on the map' }).click()
  await expect(page).toHaveURL(/book=1/)
  await expect(page.getByRole('heading', { name: 'The path of Exodus' })).toBeVisible()
  await expect(page.locator('.pa-chapters .type-tag')).toHaveCount(1)
  await expect(page.locator('.pa-moves tbody tr')).toHaveCount(1)
  await expect(page.locator('.pa-moves .dlg-verdict')).toHaveText('holds')
  await expect(page.locator('.pa-moves .geo-pt')).toHaveCount(2)
  await expect(page.locator('.pa-oracle-chapters tbody tr')).toHaveCount(1)
  await page.goto('/findings')
  await page.getByRole('link', { name: /The geographic arc/ }).first().click()
  await expect(page).toHaveURL(/\/place-arc/)
})

test('places named together: the test, the decay, the leads and the pairs', async ({ page }) => {
  await page.goto('/place-links')
  await expect(page.getByText(/1 pairs of 2 places|1 pair/).first()).toBeVisible()
  await expect(page.locator('.plk-table').first().locator('tbody tr')).toHaveCount(3)
  await expect(page.locator('.plk-dot.far')).toHaveCount(1)
  await expect(page.locator('.plk-bins tbody tr')).toHaveCount(2)
  await expect(page.locator('.plk-leads .dlg-verdict')).toHaveText('holds')
  await expect(page.locator('.plk-leads tbody tr')).toHaveCount(1)
  await expect(page.locator('.plk-leads .plk-link')).toHaveCount(1)
  await expect(page.locator('.plk-pairs li')).toHaveCount(1)
  await page.locator('.plk-leads tbody a').first().click()
  await expect(page).toHaveURL(/place=1/)
  await expect(page.getByRole('button', { name: 'Show every pair' })).toBeVisible()
  await page.goto('/findings')
  await page.getByRole('link', { name: /Named together, near together/ }).first().click()
  await expect(page).toHaveURL(/\/place-links/)
})

/** Drag the family tree until an element inside it is in the middle part of the view. */
async function dragIntoView(page: Page, target: Locator) {
  for (let i = 0; i < 6; i++) {
    const vp = (await page.locator('.gt-viewport').boundingBox())!
    const b = (await target.boundingBox())!
    const cx = vp.x + vp.width / 2
    const cy = vp.y + vp.height / 2
    const dx = cx - (b.x + b.width / 2)
    const dy = cy - (b.y + b.height / 2)
    if (Math.abs(dx) < vp.width / 4 && Math.abs(dy) < vp.height / 4) return
    const step = (d: number, room: number) => Math.max(-room, Math.min(room, d))
    await page.mouse.move(cx, cy)
    await page.mouse.down()
    await page.mouse.move(cx + step(dx, vp.width / 2 - 10), cy + step(dy, vp.height / 2 - 10), { steps: 8 })
    await page.mouse.up()
  }
}

test('the family tree: the rabbis’ reading of a person, with its passage on Sefaria', async ({ page }) => {
  await page.goto('/genealogy?p=1')
  const card = page.getByRole('region', { name: 'Person' }).locator('.gt-identity')
  await expect(card.locator('p').first()).toHaveText('The rabbis read as the same person as שת · Read as one.')
  await expect(card.getByRole('link', { name: /בבלי מגילה יד ע״א/ })).toHaveAttribute('href', 'https://www.sefaria.org/Megillah.14a.13?lang=he')
  await card.getByRole('button', { name: 'שת' }).click()
  await expect(page).toHaveURL(/\/genealogy\?p=4$/)
  await expect(page.getByRole('region', { name: 'Person' }).locator('.gt-identity p').first()).toHaveText('The rabbis read as the same person as אדם · Read as one.')
})

test('the family tree: open and close, a person and the verses, search, a phone', async ({ page }) => {
  await page.goto('/genealogy')
  await expect(page.getByText(/13 people and 12 parent links/)).toBeVisible()
  const node = (he: string) => page.locator('.gt-node').filter({ has: page.locator('.gt-name', { hasText: he }) })
  await expect(node('יבל')).toHaveCount(1)
  // spouses beside as avatars (D103): Adah's and Zillah's children hang from the line to each, so no mother headers
  await expect(page.locator('.gt-spouse')).toHaveText(['חוה', 'עדה', 'צלה'])
  await expect(page.locator('.gt-header', { hasText: /^by / })).toHaveCount(0)
  await expect(page.locator('.gt-header', { hasText: 'not stated (1)' })).toHaveCount(1)
  await expect(node('אנוש')).toHaveClass(/conflict/)
  await expect(page.locator('.gt-edges .gt-edge.desc')).toHaveCount(1)
  // the tree fills the screen (D103): on a phone, drag Lamech into view first, as a reader would
  await dragIntoView(page, node('למך').getByRole('button', { name: 'Hide those below' }))
  await node('למך').getByRole('button', { name: 'Hide those below' }).click()
  await expect(node('יבל')).toHaveCount(0)
  await page.getByRole('button', { name: 'Show 3 people below' }).click()
  await expect(node('יבל')).toHaveCount(1)
  await node('אנוש').locator('.gt-name').click()
  await expect(page).toHaveURL(/\/genealogy\?p=10$/)
  const panel = page.getByRole('region', { name: 'Person' })
  await expect(panel.locator('.gt-conflict .gt-link')).toHaveCount(2)
  await expect(panel.locator('.gt-proof .w-focus').first()).toBeVisible()
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  // search opens the line to Balaam, under "unattached"
  await page.getByRole('searchbox', { name: 'Find a person' }).fill('בלעם')
  await page.locator('.gt-matches').getByRole('button', { name: 'בלעם' }).click()
  await expect(page).toHaveURL(/p=13$/)
  await expect(node('בלעם')).toHaveClass(/selected/)
  await expect(page.locator('.gt-node .gt-name', { hasText: 'Exodus' })).toHaveCount(1)
  // drag moves the tree without choosing anyone
  const canvas = page.locator('.gt-canvas')
  const before = await canvas.getAttribute('style')
  await page.locator('.gt-viewport').scrollIntoViewIfNeeded()
  const box = (await page.locator('.gt-viewport').boundingBox())!
  // between the tree's top edge and whatever covers its lower part (a phone's bottom sheet)
  const side = await page.locator('.gt-side').boundingBox()
  const bottom = side && side.y > box.y ? Math.min(side.y, box.y + box.height) : box.y + box.height
  const y = (box.y + bottom) / 2
  await page.mouse.move(box.x + box.width / 2, y)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2 + 100, y + 60, { steps: 6 })
  await page.mouse.up()
  await expect(canvas).not.toHaveAttribute('style', before!)
  await expect(page).toHaveURL(/p=13$/)
  // a phone: the panel is a bottom sheet
  await page.setViewportSize({ width: 390, height: 800 })
  await expect(panel).toBeVisible()
  expect(await page.locator('.gt-side').evaluate((e) => getComputedStyle(e).position)).toBe('fixed')
  await panel.getByRole('button', { name: 'Close', exact: true }).click()
  await expect(page.locator('.gt-side')).toBeHidden()
})

test('letters at equal skips: the counts against the controls, the names, the tradition', async ({ page }) => {
  await page.goto('/els')
  await expect(page.getByText(/2 names at skips of 2 to 1,000 letters/)).toBeVisible()
  await expect(page.locator('.els-table').first().locator('tbody tr')).toHaveCount(3)
  await expect(page.locator('.els-dot')).toHaveCount(6)
  await expect(page.locator('.els-terms tbody tr')).toHaveCount(2)
  await expect(page.locator('#known tbody tr')).toContainText('from letter 6 of the verse')
  await page.goto('/findings')
  await page.getByRole('link', { name: /Letters at equal skips/ }).first().click()
  await expect(page).toHaveURL(/\/els/)
})

test('a place name shows where it lies: its site, kind and point', async ({ page }) => {
  await page.goto('/names?e=559')
  const sites = page.locator('.entity-sites li')
  await expect(sites).toHaveCount(1)
  await expect(sites.first()).toContainText('Town')
  await expect(sites.first()).toContainText('31.78° N, 35.23° E · identification voted 640 / 1,000')
  await expect(page.getByText('In SDBH’s domains, mostly a place.')).toBeVisible()
})

test('a verse in two refrains links to them, and on to the refrain in its passage', async ({ page }) => {
  await page.goto('/unit/v%3A2')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '2 refrains' }).click()
  await expect(page).toHaveURL(/\/refrains\?unit=v%3A2&all=1/)
  await expect(page.locator('li.refrain')).toHaveCount(2)
  await page.locator('li.refrain').first().getByRole('link', { name: 'Read in the passage' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=refrains/)
  await expect(page.locator('.reader-text .rf')).toHaveCount(8)
})

test('a psalm links to its form and turn, and on to its words of distress and praise', async ({ page }) => {
  await page.goto('/unit/c%3A0%3A1')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '1 psalm: its genre, form and turn' }).click()
  await expect(page).toHaveURL(/\/psalms\?unit=c%3A0%3A1/)
  await expect(page.locator('li.psalm')).toHaveCount(1)
  await expect(page.getByRole('img', { name: /Mood of/ })).toBeVisible()
  await page.locator('li.psalm').getByRole('link', { name: 'Read with its mood' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=mood/)
  await expect(page.locator('.reader-text .md-praise').first()).toBeVisible()
  await expect(page.locator('.reader-text .md-distress').first()).toBeVisible()
})

test('a chapter of the Pentateuch opens in the reader with its side of the P / non-P split', async ({ page }) => {
  await page.goto('/unit/c%3A0%3A1')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '3 verses on the P-like side' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=sources/)
  await expect(page.locator('.reader-text .src-tag')).toHaveCount(3)
  await expect(page.locator('.reader-text .src-differs')).toHaveCount(1)
  await page.getByRole('link', { name: "The split on the Pentateuch's sources page" }).click()
  await expect(page.getByRole('heading', { name: "The Pentateuch's sources", level: 1 })).toBeVisible()
})

test('a chapter with an exchange links to who speaks to whom, and on to the reader', async ({ page }) => {
  await page.goto('/unit/c%3A0%3A1')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '1 exchange between two speakers' }).click()
  await expect(page).toHaveURL(/\/speech\?view=dialogue&book=0$/)
  await expect(page.getByRole('img', { name: /most active speakers of/ })).toBeVisible()
  await expect(page.locator('.dlg-verdict.holds')).toHaveCount(2)
  await expect(page.locator('.dlg-exchange')).toHaveCount(1)
  await page.locator('.dlg-exchange').getByRole('link').click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=speakers/)
  await expect(page.locator('.reader-legend')).toContainText('to 4872')
})

test('a chapter with a numerical saying and a list links to them on the Numbers and lists page', async ({ page }) => {
  await page.goto('/unit/c%3A0%3A1')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '2 graded numerical sayings and lists' }).click()
  await expect(page).toHaveURL(/\/forms\?unit=c%3A0%3A1$/)
  await expect(page.locator('.dlg-verdict')).toHaveCount(3)
  await expect(page.locator('.saying')).toHaveCount(1)
  await expect(page.locator('.saying .w-shared')).toHaveCount(2)
  await page.getByRole('radio', { name: 'Lists' }).click()
  await expect(page).toHaveURL(/\/forms\?view=lists$/)
  await expect(page.locator('.list')).toHaveCount(2)
  await expect(page.locator('.list').first()).toContainText('genealogy')
})

test('pattern search: a query, its verses with the words marked, a book, and a broken query', async ({ page }) => {
  await page.goto('/query')
  const box = page.getByRole('searchbox', { name: 'Query' })
  await box.fill('[lemma=430] [lemma=559] ..2 [lemma=3068]')
  await box.press('Enter')
  await expect(page.getByText(/2 matches in 2 verses/)).toBeVisible()
  await expect(page.locator('.query-hit')).toHaveCount(2)
  await expect(page.locator('.query-hit').first().locator('.w-shared')).toHaveCount(3)
  await box.fill('[lemma=430] [pos=]')
  await box.press('Enter')
  await expect(page.getByRole('alert')).toContainText('A condition is key=value')
  await expect(page.locator('.query-problem mark')).toHaveText('pos=')
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.getByRole('button', { name: '[form=imperative] ..4 [function=Voct pos=name]' }).click()
  await expect(page).toHaveURL(/\/query\?q=%5Bform%3Dimperative%5D/)
  await expect(page.getByText('Nothing matches this pattern.')).toBeVisible()
})

test('names of God: the checks, the strip, a book and the reader layer', async ({ page }) => {
  await page.goto('/divine')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(1)
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('rect.dv-cell')).toHaveCount(3)
  await expect(page.locator('rect.dv-cell.dv-mid')).toHaveCount(1) // Genesis 1: יהוה 2, אלהים 2
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.getByRole('region', { name: 'Books' }).getByRole('button').first().click()
  await expect(page).toHaveURL(/\/divine\?book=0/)
  await page.locator('#chapters').getByRole('link', { name: '1', exact: true }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=divine/)
  await expect(page.locator('.reader-text .dv')).toHaveCount(3)
  await expect(page.locator('.reader-text .dv-yhwh')).toHaveCount(1)
})

test('naming etiologies: the checks, the namings, a filter', async ({ page }) => {
  await page.goto('/etiologies')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(1)
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('li.ety-naming')).toHaveCount(2)
  await expect(page.locator('li.ety-naming').first().locator('.w-focus')).toHaveText('דָּגָן')
  await expect(page.locator('li.ety-naming').first().locator('.w-shared')).toHaveText('רֵאשִׁית')
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.getByRole('radio', { name: 'Beyond chance (1)' }).click()
  await expect(page).toHaveURL(/\/etiologies\?show=leads/)
  await expect(page.locator('li.ety-naming')).toHaveCount(1)
  await expect(page.locator('li.ety-lead')).toHaveCount(1)
})

test('resumptive repetition: the checks, the repetitions, a filter', async ({ page }) => {
  // every repetition, not only those named in advance (the default since M159)
  await page.goto('/brackets?show=all')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(1)
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('li.brk-bracket')).toHaveCount(2)
  await expect(page.locator('li.brk-bracket').first().locator('.w-shared')).toHaveCount(3)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.getByRole('radio', { name: 'p ≤ 0.05' }).click()
  await expect(page).toHaveURL(/\/brackets\?show=strong/)
  await expect(page.locator('li.brk-bracket')).toHaveCount(1)
  await page.locator('li.brk-bracket').getByRole('link', { name: 'compare the two' }).click()
  await expect(page).toHaveURL(/\/compare\?a=v%3A0&b=v%3A4/)
})

test('retold speech: the checks, the groups, the passages and their changes, a filter', async ({ page }) => {
  await page.goto('/retold')
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(2)
  await expect(page.locator('table.rt-groups tbody tr')).toHaveCount(6)
  await expect(page.locator('li.rt-pair')).toHaveCount(2)
  await expect(page.locator('li.rt-pair').first().locator('.rt-teller').first()).toHaveText('First told by God')
  await expect(page.locator('li.rt-pair').first().locator('.w-diff-omitted')).toHaveCount(1)
  await expect(page.locator('li.rt-pair').nth(1).locator('.rt-teller').nth(1)).toHaveText('Told again by the narrator')
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.getByRole('radio', { name: 'Carried out by the narrator' }).click()
  await expect(page).toHaveURL(/\/retold\?group=carried/)
  await expect(page.locator('li.rt-pair')).toHaveCount(1)
})

test('haftarot: the checks, the systems, a parasha and its chapters', async ({ page }) => {
  await page.goto('/haftarot')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(2)
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('table.hf-modes tbody tr')).toHaveCount(3)
  await expect(page.locator('table.hf-table tbody tr')).toHaveCount(2)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.locator('table.hf-table tbody tr').first().getByRole('button').click()
  await expect(page).toHaveURL(/\/haftarot\?p=p%3ABereshit/)
  await expect(page.locator('.hf-chapters li')).toHaveCount(2)
  await expect(page.locator('.hf-chapters li.hf-hit')).toHaveCount(1)
})

test('chronology: the checks, the dates and their conflict, the reigns and the synchronisms', async ({ page }) => {
  await page.goto('/chronology')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(3)
  await expect(page.locator('table.ch-events tbody tr')).toHaveCount(5)
  await expect(page.locator('table.ch-events tbody tr.ch-conflict')).toHaveCount(1)
  await expect(page.locator('.ch-life')).toHaveCount(2)
  await expect(page.locator('.ch-reign')).toHaveCount(4)
  await expect(page.locator('svg.ch-chart line.ch-sync')).toHaveCount(2)
  await expect(page.locator('table.ch-syncs tbody tr').last()).toContainText('agrees')
  await page.locator('.ch-reigns summary').click()
  await expect(page.locator('.ch-reigns tbody tr')).toHaveCount(4)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
})

test('frameworks: the checks, the cycle slot by slot, a king and his verdict', async ({ page }) => {
  await page.goto('/frameworks')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(3)
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('table.fw-cycle tbody tr')).toHaveCount(2)
  await expect(page.locator('table.fw-cycle tbody tr').first().locator('a.fw-hit')).toHaveCount(6)
  await expect(page.locator('table.fw-kings tbody tr')).toHaveCount(3)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.locator('table.fw-kings tbody tr').nth(1).getByRole('button').click()
  await expect(page).toHaveURL(/\/frameworks\?k=asa/)
  await expect(page.locator('.fw-panel .type-tag.fw-good')).toBeVisible()
})

test('word pairs: the checks, the pairs, a pair turned round', async ({ page }) => {
  await page.goto('/binomials')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(2)
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('table.bn-table tbody tr')).toHaveCount(2)
  await page.getByRole('radio', { name: 'Found both ways' }).click()
  await expect(page.locator('table.bn-table tbody tr')).toHaveCount(1)
  await page.locator('table.bn-table tbody tr').first().getByRole('button').click()
  await expect(page).toHaveURL(/pair=2091%2B3701/)
  await expect(page.locator('.bn-panel li.hit')).toHaveCount(2)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
})

test('sums: the checks, a list opened, the parallels filtered', async ({ page }) => {
  await page.goto('/sums')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(5) // three checks, two lists as known
  await expect(page.locator('table.sm-table tbody tr')).toHaveCount(2)
  await expect(page.locator('table.sm-table tbody tr.sm-off')).toHaveCount(1)
  await page.getByRole('button', { name: /The returnees \(Ezra\)/ }).click()
  await expect(page).toHaveURL(/list=ezra2/)
  await expect(page.locator('.sm-panel li.hit')).toHaveCount(3)
  await expect(page.locator('li.sm-parallel')).toHaveCount(2)
  await page.getByRole('radio', { name: 'One step apart' }).click()
  await expect(page).toHaveURL(/step=yes/)
  await expect(page.locator('li.sm-parallel')).toHaveCount(1)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
})

test('rabbinic reception: the checks, who cites a verse, the reader’s counts and the dossier', async ({ page }) => {
  await page.goto('/reception')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(1)
  await expect(page.locator('rect.rc-cell')).not.toHaveCount(0)
  await page.locator('.rc-verses a').first().click()
  await expect(page).toHaveURL(/\/reception\?unit=v%3A0/)
  const cite = page.getByRole('link', { name: /משנה ברכות א:ג/ })
  await expect(cite).toHaveAttribute('href', 'https://www.sefaria.org/Mishnah_Berakhot.1.3?lang=he')
  await page.getByRole('link', { name: 'Read with its citations' }).click()
  await expect(page.locator('.reader-text .rc-total').first()).toHaveText('3')
  await page.goto('/unit/v%3A0')
  await expect(page.locator('.dossier-chip').filter({ hasText: 'rabbinic citations' })).toHaveAttribute('href', '/reception?unit=v%3A0')
})

test('source finder: an example searched, a pasted text, the limit', async ({ page }) => {
  await page.goto('/source')
  await page.getByRole('button', { name: 'The priestly blessing' }).click()
  await expect(page).toHaveURL(/\/source\?example=priestly/)
  await expect(page.getByLabel('Hebrew text')).toHaveValue(/יברכך/)
  // the fixture's six verses hold no priestly blessing
  await expect(page.getByText('No phrase of the Bible was found in this text.')).toBeVisible()
  await page.getByLabel('Hebrew text').fill('א'.repeat(5001))
  await expect(page.getByRole('button', { name: 'Find the sources' })).toBeDisabled()
})

test('other witnesses: the checks, a plus compared word by word, the reader’s counts and the dossier', async ({ page }) => {
  await page.goto('/witnesses')
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1)
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(1)
  await page.locator('.wt-pluses a').first().click()
  await expect(page).toHaveURL(/\/witnesses\?unit=v%3A1/)
  const sp = page.locator('.wt-verse .wt-text').first()
  await expect(sp.locator('.wt-added')).toHaveCount(4)
  await page.getByRole('link', { name: 'Read with the witnesses' }).click()
  await expect(page.locator('.reader-text .wt-total').first()).toHaveText('ש 0')
  await page.goto('/unit/c%3A0%3A1')
  await expect(page.locator('.dossier-chip').filter({ hasText: 'other witnesses' })).toHaveAttribute('href', '/witnesses?unit=c%3A0%3A1')
})

test('vocabulary: the checks, the novelty chart, a lemma’s first use', async ({ page }) => {
  await page.goto('/vocabulary')
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(2)
  await expect(page.locator('svg.vc-chart g.vc-row')).toHaveCount(2)
  await page.locator('svg.vc-chart g.vc-row').nth(1).hover()
  await expect(page.locator('.vc-readout')).toContainText('9 new lemmas')
  await expect(page.locator('table.vc-table tbody tr')).toHaveCount(2)
  await page.goto('/lemma/7225')
  await expect(page.locator('.conc-first')).toContainText('found once in the Bible')
  await page.locator('.conc-first a').click()
  await expect(page).toHaveURL(/\/unit\/v%3A0/)
})

test('a guided tour from the home page, step by step, and a term explained on Findings', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Start: Counting and dating' }).click()
  await expect(page).toHaveURL(/\/chronology\?tour=numbers&step=1/)
  await expect(page.locator('.tour-bar')).toContainText('step 1 of 4')
  await page.locator('.tour-bar').getByRole('button', { name: 'Next' }).click()
  await expect(page).toHaveURL(/\/sums\?list=ezra2&tour=numbers&step=2/)
  await expect(page.locator('.tour-bar-caption')).toContainText('Ezra lists the families')
  await page.locator('.tour-bar').getByRole('button', { name: 'Leave the tour' }).click()
  await expect(page).toHaveURL(/\/sums\?list=ezra2$/)
  await expect(page.locator('.tour-bar')).toHaveCount(0)
  await page.goto('/findings')
  const term = page.locator('.findings-page .term-button').first()
  await term.focus()
  await expect(page.locator('.findings-page .term-tip.open')).toHaveCount(1)
  await page.keyboard.press('Escape')
  await expect(page.locator('.findings-page .term-tip.open')).toHaveCount(0)
})

test('synopses: two chains joined into three columns, marked against a chosen one', async ({ page }) => {
  await page.goto('/synopses')
  await page.locator('.synopses-table a').first().click()
  await expect(page).toHaveURL(/\/synopses\/1$/)
  await expect(page.locator('.syn-row')).toHaveCount(3)
  await expect(page.locator('.syn-row').nth(1).locator('.syn-cell:not(.empty)')).toHaveCount(3)
  await expect(page.locator('.syn-cell.base')).toHaveCount(3)
  await page.getByLabel('Mark against').selectOption('1')
  await expect(page).toHaveURL(/base=1/)
  await expect(page.locator('.syn-cell.base')).toHaveCount(2)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
})

test('compare: the words of a hovered pair linked in meaning', async ({ page }) => {
  await page.goto('/compare?a=v%3A0&b=v%3A1&marks=meaning')
  await page.locator('.column').first().locator('.align-row').first().hover()
  await expect(page.locator('.align-chip').first()).toBeVisible()
  await expect(page.locator('.column').first().locator('.align-row .w-shared').first()).toBeVisible()
  await page.locator('.align-chip').first().hover()
  await expect(page.locator('.column').first().locator('.align-row .w-focus')).toHaveCount(1)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
})

test('workbench: a set built from the form, its contrast, a broken pattern item, and a check', async ({ page }) => {
  await page.goto('/workbench')
  await expect(page.getByText(/Build set A to begin/)).toBeVisible()
  const add = page.getByRole('form', { name: 'Add to the set: Set A' })
  await add.getByLabel('Add to the set').selectOption('chapters')
  await add.getByLabel('From chapter').fill('1')
  await add.getByRole('button', { name: 'Add' }).click()
  await expect(page).toHaveURL(/a=chapters%3A0%3A1/)
  // only ראשית reaches 5 words over both sets, and it is commoner in the rest
  await expect(page.getByRole('region', { name: 'Commoner in B' }).getByRole('link', { name: 'ראשית' })).toBeVisible()
  await expect(page.getByText('Nothing scored on this side.')).toBeVisible()
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  await page.goto('/workbench?a=book%3A0&b=pattern%3A%5Blemma%3D430')
  await expect(page.getByRole('alert')).toContainText('Set B: The pattern')
  await page.getByRole('radio', { name: 'Check a pattern' }).click()
  await page.getByRole('textbox', { name: 'Pattern search query' }).fill('[lemma=430]')
  await page.getByRole('button', { name: 'Check' }).click()
  await expect(page.getByText(/Write a pattern and build a set/)).toBeVisible()
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

test('a verse in a chapter echoed by another book links to its directed echoes', async ({ page }) => {
  await page.goto('/unit/v%3A5')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await bar.getByRole('link', { name: '2 directed echoes with other books' }).click()
  await expect(page).toHaveURL(/\/network\?view=directions&unit=v%3A5/)
  await expect(page.locator('.echo-item')).toHaveCount(2)
  await expect(page.locator('.echo-item').filter({ hasText: 'against the canon order' })).toHaveCount(1)
  await page.locator('.echo-item').first().getByRole('link', { name: 'Compare' }).click()
  await expect(page).toHaveURL(/\/compare\?/)
})

for (const locale of ['en', 'he'] as const) {
  test(`Ctrl+K jumps to a passage, a word, a place or a page (${locale})`, async ({ page }) => {
    await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
    await page.goto('/map')
    await page.keyboard.press('Control+k')
    // the jump box's own field: a page may have comboboxes of its own (the unit page's Top k)
    const box = page.getByRole('dialog').getByRole('combobox')
    await expect(box).toBeFocused()
    await box.fill('Gen 1:2')
    await expect(page.getByRole('option').first()).toHaveAttribute('aria-selected', 'true')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
    await box.press('Enter')
    await expect(page).toHaveURL(/\/unit\/v%3A1$/)
    await page.keyboard.press('Control+k')
    await box.fill('ראשית')
    await page.getByRole('option', { name: /ראשית.*7225/ }).click()
    await expect(page).toHaveURL(/\/lemma\/7225$/)
    // a place named by its name opens the map at it
    await page.keyboard.press('Control+k')
    await box.fill('אמר')
    await expect(page.getByRole('option').first()).toContainText(locale === 'en' ? 'Town' : 'עיר')
    await box.press('Enter')
    await expect(page).toHaveURL(/\/places\?p=1$/)
    await expect(page.locator('.geo-pt.selected')).toHaveCount(1)
    await page.keyboard.press('Control+k')
    await box.fill(locale === 'en' ? 'netw' : 'רשת')
    await box.press('Enter')
    await expect(page).toHaveURL(/\/network$/)
  })
}

test('an arc across the canon opens its chain from the keyboard', async ({ page }) => {
  await page.goto('/sequences?view=arcs&q=all')
  const arcs = page.locator('.arc-diagram a.arc')
  await expect(arcs).toHaveCount(2)
  const first = page.getByRole('link', { name: /^v:0–1 ↔ v:3–4/ })
  await first.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/sequences\/1$/)
})

test('the home page leads to the findings, and each finding to its evidence', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: /What the analyses found/ }).click()
  await expect(page).toHaveURL(/\/findings$/)
  const leads = page.getByRole('region', { name: 'Leads, not findings' })
  await expect(leads.locator('.finding')).toHaveCount(1)
  await leads.getByRole('link', { name: 'Rare words over a few verses: Phrases' }).click()
  await expect(page).toHaveURL(/\/phrases\?view=spread$/)
})

// the two tests that write to the server's one labels file, one after the other: the queue's one
// pair is the pair the first labels, and each expects the file empty when it starts
test.describe('labels', () => {
  test.describe.configure({ mode: 'serial' })

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
    // the list with a label in it (the page-by-page check sees it empty)
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
    await page.locator('.labels-list').getByRole('button', { name: 'Real' }).click() // clear it again
    await expect(page.locator('.labels-list > li')).toHaveCount(0)
  })

  test('a pair is judged from the label queue and leaves it', async ({ page }, info) => {
    // it writes to the server's one labels file: run once, not on every device at the same time
    test.skip(info.project.name !== 'desktop')
    await page.goto('/labels')
    await page.getByRole('radio', { name: 'What to judge next' }).click()
    await expect(page).toHaveURL(/\/labels\?tab=queue$/)
    // the fixture's one discovery between two train-book verses
    const items = page.locator('.queue-list > li')
    await expect(items).toHaveCount(1)
    await expect(page.getByText('1 pair to judge · 0 of 1 judged')).toBeVisible()
    // the fixture's made-up `bsim llm-triage` run: a suggestion, never a label
    await expect(items.locator('.queue-suggestion')).toContainText('Claude suggests: Not (p 0.20, shared formula).')
    await expect(items.getByRole('button', { name: 'Not' })).toHaveAttribute('aria-pressed', 'false')
    // the button shows the label at once; the queue asked again before the server has written it
    // would still hold the pair (seen in a full run under load), so wait for the write
    const written = page.waitForResponse((r) => r.url().endsWith('/api/labels') && r.request().method() === 'PUT')
    await items.getByRole('button', { name: 'Not' }).click()
    await expect(items.getByRole('button', { name: 'Not' })).toHaveAttribute('aria-pressed', 'true')
    expect((await written).ok()).toBe(true)
    await page.getByRole('button', { name: 'Next pairs' }).click()
    await expect(page.getByText('Nothing left to judge here.')).toBeVisible()
    await page.getByRole('radio', { name: 'Your labels' }).click()
    await expect(page.locator('.labels-list > li')).toHaveCount(1)
    await expect(page.locator('.labels-list')).toContainText('judged in the queue')
    await page.locator('.labels-list').getByRole('button', { name: 'Not' }).click() // clear it again
    await expect(page.locator('.labels-list > li')).toHaveCount(0)
  })
})

test('a verse is kept with a note and a collection, and shows in the notebook', async ({ page }, info) => {
  // it writes to the server's one labels file: run once, not on every device at the same time
  test.skip(info.project.name !== 'desktop')
  await page.goto('/unit/v%3A1')
  const panel = page.getByRole('region', { name: 'Notebook' })
  await panel.getByRole('button', { name: /Keep in notebook/ }).click()
  await expect(panel.getByText('In your notebook')).toBeVisible()
  await panel.getByPlaceholder('Your note (plain text)').fill('ויאמר: the second time')
  await panel.getByRole('button', { name: 'Save note' }).click()
  await expect(panel.getByText('Saved')).toBeVisible()
  await panel.getByRole('combobox', { name: 'Add to a collection…' }).selectOption('__new__')
  await panel.getByRole('textbox', { name: 'Name of the new collection' }).fill('Speeches')
  await panel.getByRole('button', { name: 'Create and add' }).click()
  await expect(panel.getByRole('button', { name: 'Take it out of “Speeches”' })).toBeVisible()
  await panel.getByRole('link', { name: 'Open the notebook' }).click()
  await expect(page).toHaveURL(/\/notebook$/)
  await expect(page.locator('.notebook-entry')).toHaveCount(1)
  await expect(page.locator('.notebook-entry textarea')).toHaveValue('ויאמר: the second time')
  await page.getByRole('button', { name: 'Speeches (1)' }).click()
  await expect(page).toHaveURL(/\/notebook\?c=\d+$/)
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  // the study page (M162): one HTML file of what is shown, the verse and the note in it
  const [file] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download a study page' }).click()])
  expect(file.suggestedFilename()).toMatch(/^notebook-\d+-\d{4}-\d{2}-\d{2}\.html$/)
  const html = readFileSync(await file.path(), 'utf8')
  expect(html).toContain('<title>Notebook: Speeches</title>')
  expect(html).toContain('ויאמר: the second time')
  expect(html).toMatch(/href="http:\/\/127\.0\.0\.1:\d+\/unit\/v%3A1"/)
  // printed: the note as text, the editors and the controls left out
  await page.emulateMedia({ media: 'print' })
  await expect(page.locator('.nb-print-note')).toHaveText('ויאמר: the second time')
  await expect(page.locator('.notebook-entry textarea')).toBeHidden()
  await expect(page.locator('.nb-collections-bar')).toBeHidden()
  await page.emulateMedia({ media: 'screen' })
  await expect(page.locator('.nb-print-note')).toBeHidden()
  // clean up: the collection, then the entry
  await page.getByRole('button', { name: 'Delete collection' }).click()
  await page.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(page.getByText('No collections yet.')).toBeVisible()
  await page.locator('.notebook-entry').getByRole('button', { name: 'Remove from notebook' }).click()
  await page.getByRole('button', { name: 'Remove', exact: true }).click()
  await expect(page.getByText(/Nothing kept yet/)).toBeVisible()
})

// one test a page, so they spread over the workers and a failure names its page
for (const path of PAGES) {
  test(`in Hebrew, right to left and clean: ${path}`, async ({ page }) => {
    const errors = collectErrors(page)
    await page.addInitScript(() => localStorage.setItem('bsim.locale', 'he'))
    await loads(page, path)
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    expect(errors).toEqual([])
  })
}

for (const locale of ['en', 'he'] as const) {
  for (const path of PAGES) {
    test(`no serious accessibility violations (${locale}): ${path}`, async ({ page }) => {
      await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
      await loads(page, path)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
      const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
      expect(serious.map((v) => `${v.id} (${v.nodes.length})`)).toEqual([])
    })
  }
}

for (const locale of ['en', 'he'] as const) {
  test(`Claude's note on a discovery, a suggestion in Hebrew (${locale})`, async ({ page }) => {
    await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
    // the fixture's made-up `bsim llm-notes` run: the fused discovery v:0 / v:3
    await page.goto('/discoveries?mode=fused')
    const note = page.locator('.disc .queue-suggestion')
    await expect(note).toHaveCount(1)
    await expect(note).toContainText(locale === 'en' ? 'Claude suggests: Real (p 0.70, shared phrase).' : 'Claude מציע:')
    await expect(note.locator('[lang="he"]')).toHaveText('שתיהן פותחות בראשית')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  })
}

for (const locale of ['en', 'he'] as const) {
  test(`how often an analysis is right, by Claude's reading (${locale})`, async ({ page }) => {
    await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
    // the fixture's two made-up `bsim llm-audit` runs (§16.86, D147)
    await page.goto('/etiologies')
    const note = page.locator('.precision-note[data-detector="etiologies"]')
    await expect(note.locator('summary')).toContainText(locale === 'en' ? '63% right [0.49, 0.75] of what this page lists' : '63% נכונים')
    await note.locator('summary').click()
    await expect(note.locator('li')).toHaveCount(3)
    await page.goto('/findings')
    const table = page.locator('.precision-table')
    await expect(table.locator('tbody tr')).toHaveCount(2)
    await expect(table.getByRole('link', { name: locale === 'en' ? 'Naming etiologies' : 'מדרשי שמות' })).toHaveAttribute('href', '/etiologies')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
  })
}

test("a verse's neighbourhood: from its page, a kind switched off, another verse in the middle", async ({ page }) => {
  await page.goto('/unit/v%3A0')
  await page.getByRole('link', { name: 'Its neighbourhood as a graph' }).click()
  await expect(page).toHaveURL(/\/neighbourhood\/v%3A0$/)
  await expect(page.locator('.nbh-node.centre')).toHaveCount(1)
  const nodes = await page.locator('.nbh-graph circle').count()
  expect(nodes).toBeGreaterThan(1)
  const edges = await page.locator('.nbh-edge').count()
  await page.getByRole('checkbox', { name: 'Only on the combined list' }).uncheck()
  await expect(page).toHaveURL(/off=fused/)
  expect(await page.locator('.nbh-edge').count()).toBeLessThanOrEqual(edges)
  // v:5 has hits of its own (v:3's are all its neighbours, left out)
  await page.getByRole('row', { name: /^v:5/ }).getByRole('link', { name: 'Put in the middle' }).click()
  await expect(page).toHaveURL(/\/neighbourhood\/v%3A5\?off=fused$/)
  await expect(page.locator('.nbh-node.centre')).toHaveCount(1)
  await expect(page.getByRole('checkbox', { name: 'Only on the combined list' })).not.toBeChecked()
  await page.goto('/neighbourhood/v%3A3')
  await expect(page.getByText('Nothing is stored as like this passage.')).toBeVisible()
})

test('the main line: the claim, a pause, and its background marked in the reader', async ({ page }) => {
  await page.goto('/mainline')
  await expect(page.locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(page.locator('.ml-pause')).toHaveCount(1)
  await page.getByRole('link', { name: 'read it with the layer' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=mainline$/)
  await expect(page.locator('.reader-text .ml-background').first()).toBeVisible()
})

test('the prophetic forms: the passages named in advance, a woe saying, its words boxed in the reader', async ({ page }) => {
  await page.goto('/prophetic')
  await expect(page.locator('.pf-known .dv-verdict')).toHaveText(['Not all found', 'Found'])
  await expect(page.locator('.pf-item')).toHaveCount(3)
  await page.getByRole('radio', { name: 'Woe saying' }).click()
  await expect(page).toHaveURL(/\/prophetic\?form=woe$/)
  await expect(page.locator('.pf-item')).toHaveCount(1)
  await expect(page.locator('.pf-item .w-focus')).toHaveCount(2)
  await page.getByRole('link', { name: 'read it with the layer' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A0%3A1\?layers=prophetic$/)
  await expect(page.locator('.reader-text .pf')).toHaveCount(3)
})

test('the law codes: the known pairs, a pair side by side, the laws by code', async ({ page }) => {
  await page.goto('/laws')
  await expect(page.locator('.lw-known .dv-verdict')).toHaveText(['Found', 'Not found'])
  await expect(page.locator('.lw-pair')).toHaveCount(1)
  await page.locator('.lw-pair').getByRole('button', { name: 'side by side' }).click()
  await expect(page).toHaveURL(/\/laws\?pair=1$/)
  await expect(page.locator('.lw-side')).toHaveCount(2)
  await expect(page.locator('.lw-side .w-diff-substitution')).toHaveCount(1)
  await expect(page.locator('.lw-side .w-diff-added')).toHaveCount(1)
  await page.getByRole('radio', { name: 'Laws' }).click()
  await page.getByRole('combobox', { name: 'Code' }).selectOption('covenant')
  await expect(page).toHaveURL(/view=laws&code=covenant/)
  await expect(page.locator('.lw-law')).toHaveCount(1)
  await expect(page.locator('.lw-law')).toContainText('Apodictic')
})

test('a selection is in the URL: a reload keeps it, Back undoes it', async ({ page }) => {
  await page.goto('/map')
  const first = page.locator('.cluster-legend button').first()
  await first.click()
  await expect(page).toHaveURL(/cluster=\d+/)
  await page.reload()
  await expect(page.locator('.cluster-legend button').first()).toHaveAttribute('aria-pressed', 'true')
  await page.goBack()
  await expect(page).not.toHaveURL(/cluster=/)
  await expect(page.locator('.cluster-legend button').first()).toHaveAttribute('aria-pressed', 'false')
})

test('the reader keeps the chosen word in the URL', async ({ page }) => {
  await page.goto('/read/c%3A0%3A1')
  await page.locator('.w-click').first().click()
  await expect(page).toHaveURL(/[?&]w=\d+%3A\d+|[?&]w=\d+:\d+/)
  await page.reload()
  await expect(page.getByRole('region', { name: 'Word analysis' })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('region', { name: 'Word analysis' })).toHaveCount(0)
})

test('a section opened by hand stays open in the URL', async ({ page }) => {
  await page.goto('/query')
  await page.locator('.query-help summary').click()
  await expect(page).toHaveURL(/open=help/)
  await page.reload()
  await expect(page.locator('.query-help')).toHaveAttribute('open', '')
})

test.describe('the offline app', () => {
  test.use({ serviceWorkers: 'allow' })

  test('a page opened before opens again offline, under the banner', async ({ page, context }, info) => {
    test.skip(info.project.name !== 'desktop')
    const heading = page.getByRole('heading', { level: 1 })
    const banner = page.locator('.app-banner')
    await page.goto('/unit/v%3A0')
    await expect(heading).toBeVisible()
    // installed, and in control of the page at once (clientsClaim)
    await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null), { timeout: 20_000 }).toBe(true)
    await expect(banner).toBeEmpty()
    await page.reload() // the page's answers, fetched under the worker, are kept
    await expect(heading).toBeVisible()
    const title = await heading.textContent()

    await context.setOffline(true)
    await page.reload()
    await expect(banner).toContainText("You're offline")
    await expect(heading).toHaveText(title!)
    await expect(page.locator('.status.error').first()).toBeHidden()
    // the shell opens anywhere; a page never opened waits for its answers
    await page.goto('/lemma/7225')
    await expect(banner).toContainText("You're offline")
    await expect(page.locator('.status.error')).toContainText('not opened before the connection went')
    await context.setOffline(false) // and it loads once the connection is back
    await expect(banner).toBeEmpty()
    await expect(heading).toBeVisible()
    await expect(page.locator('.status.error')).toHaveCount(0)
  })

  test('the manifest names the app, and its icons are there', async ({ request }) => {
    const r = await request.get('/manifest.webmanifest')
    expect(r.headers()['content-type']).toContain('application/manifest+json')
    const manifest = await r.json()
    expect(manifest.name).toBe('Tanakh Similarity')
    expect(manifest.name_localized.he.value).toBe('מקבילות בתנ״ך')
    for (const icon of manifest.icons) expect((await request.get(icon.src)).ok(), icon.src).toBe(true)
    expect((await request.get('/sw.js')).headers()['cache-control']).toBe('no-cache')
  })
})

// M167: the faults the UI/UX audit found
test.describe('the audit’s faults (M167)', () => {
  test('no table is left to the browser’s defaults', async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop')
    for (const path of ['/laws', '/mainline', '/prophetic', '/reception', '/witnesses?unit=c%3A0%3A1', '/neighbourhood/c%3A0%3A1', '/language', '/findings']) {
      await loads(page, path)
      await expect(page.locator('main table').first()).toBeVisible()
      const bare = await page.evaluate(() =>
        [...document.querySelectorAll('main table')].filter((t) => getComputedStyle(t).borderCollapse !== 'collapse').map((t) => t.className || '(no class)'),
      )
      expect(bare, path).toEqual([])
    }
    // the precision table scrolls inside its own region on a narrow screen
    await expect(page.locator('.table-wrap > .precision-table')).toBeVisible()
  })

  test('the law pairs of one passage say so, with the way back to all of them', async ({ page }) => {
    await loads(page, '/laws?unit=c%3A0%3A1')
    await expect(page.locator('.unit-filter')).toContainText('Only those touching')
    await page.getByRole('button', { name: 'Show all' }).click()
    await expect(page).toHaveURL(/\/laws$/)
    await expect(page.locator('.unit-filter')).toHaveCount(0)
  })

  test('a choice of a few is one tab stop, moved with the arrow keys', async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop')
    await loads(page, '/laws')
    const strongest = page.getByRole('radio', { name: 'Strongest first' })
    const canon = page.getByRole('radio', { name: 'Canon order' })
    await strongest.focus()
    await page.keyboard.press('ArrowRight')
    await expect(page).toHaveURL(/order=canon/)
    await expect(canon).toBeFocused()
    await expect(canon).toHaveAttribute('aria-checked', 'true')
    await expect(strongest).toHaveAttribute('tabindex', '-1')
    await page.keyboard.press('ArrowLeft')
    await expect(page).not.toHaveURL(/order=canon/)
    await expect(strongest).toBeFocused()
  })

  test('the Hebrew top bar keeps a menu’s arrow on its label’s line', async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop')
    await page.addInitScript(() => localStorage.setItem('bsim.locale', 'he'))
    await loads(page, '/')
    const heights = await page.evaluate(() => {
      const h = (el: Element) => Math.round(el.getBoundingClientRect().height)
      return { link: h(document.querySelector('#main-nav > a')!), menus: [...document.querySelectorAll('.nav-group-button')].map(h) }
    })
    expect(heights.menus).toEqual([heights.link, heights.link, heights.link])
  })

  test('the phone menu closes on Escape', async ({ page }, info) => {
    test.skip(info.project.name !== 'phone')
    await loads(page, '/')
    const toggle = page.getByRole('button', { name: /Menu/ })
    await toggle.click()
    await expect(page.locator('#main-nav')).toHaveClass(/open/)
    await page.keyboard.press('Escape')
    await expect(page.locator('#main-nav')).not.toHaveClass(/open/)
    await expect(toggle).toBeFocused()
  })

  test.describe('in the dark theme', () => {
    test.use({ colorScheme: 'dark' })
    for (const locale of ['en', 'he'] as const) {
      test(`an error box passes axe (${locale})`, async ({ page }) => {
        await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
        await page.goto('/unit/v%3A999999')
        const box = page.locator('.status.error')
        await expect(box).toBeVisible()
        const results = await new AxeBuilder({ page }).include('.status.error').withTags(['wcag2a', 'wcag2aa']).analyze()
        expect(results.violations.map((v) => v.id)).toEqual([])
        // the token, not the light theme's red
        expect(await box.evaluate((el) => getComputedStyle(el).color)).toBe('rgb(242, 139, 130)')
      })
    }
  })
})

// M168: the top bar in one row, the Display menu, the theme switch
test.describe('the Display menu and the theme (M168)', () => {
  // the lines the bar's visible parts sit on
  const rows = (page: Page) =>
    page.evaluate(() => {
      const boxes = [...document.querySelector('.topbar')!.children].map((c) => c.getBoundingClientRect()).filter((r) => r.width > 0)
      boxes.sort((a, b) => a.top - b.top)
      let n = 0
      let bottom = -Infinity
      for (const r of boxes) {
        if (r.top >= bottom) n++
        bottom = Math.max(bottom, r.bottom)
      }
      return n
    })
  const background = (page: Page) => page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  const LIGHT = 'rgb(250, 246, 238)'
  const DARK = 'rgb(23, 20, 15)'

  for (const locale of ['en', 'he'] as const) {
    test(`the top bar is one row from 1280px (${locale})`, async ({ page }, info) => {
      test.skip(info.project.name !== 'desktop')
      await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
      // 1280px, and the same window with a scrollbar's width taken from it
      for (const width of [1280, 1263]) {
        await page.setViewportSize({ width, height: 800 })
        await loads(page, '/')
        expect(await rows(page), `${width}px`).toBe(1)
      }
      // narrower, down to the phone menu: the pages on a second row, never a third
      for (const width of [1150, 1000, 905]) {
        await page.setViewportSize({ width, height: 800 })
        await loads(page, '/')
        expect(await rows(page), `${width}px`).toBeLessThanOrEqual(2)
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
        expect(overflow, `${width}px`).toBeLessThanOrEqual(1)
      }
    })

    test(`the Display menu opens inside the window and passes axe in both themes (${locale})`, async ({ page }) => {
      await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
      await loads(page, '/')
      const button = page.getByRole('button', { name: locale === 'he' ? /תצוגה/ : /Display/ })
      await button.click()
      const panel = page.locator('#display-panel')
      await expect(panel).toBeVisible()
      await expect(panel.getByRole('radiogroup')).toHaveCount(3)
      const box = (await panel.boundingBox())!
      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize()!.width)
      for (const theme of locale === 'he' ? ['בהיר', 'כהה'] : ['Light', 'Dark']) {
        await panel.getByRole('radio', { name: theme }).click()
        const results = await new AxeBuilder({ page }).include('.topbar').withTags(['wcag2a', 'wcag2aa']).analyze()
        expect(results.violations.map((v) => v.id), theme).toEqual([])
      }
      await page.keyboard.press('Escape')
      await expect(panel).toHaveCount(0)
      await expect(button).toBeFocused()
    })
  }

  test('a chosen theme is kept over a reload, whatever the system says', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' })
    await loads(page, '/')
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    await page.getByRole('button', { name: /Display/ }).click()
    await page.getByRole('radio', { name: 'Dark' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    expect(await background(page)).toBe(DARK)
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    expect(await background(page)).toBe(DARK)
    await page.getByRole('button', { name: /Display/ }).click()
    await expect(page.getByRole('radio', { name: 'Dark' })).toBeChecked()
    // light on a dark system
    await page.emulateMedia({ colorScheme: 'dark' })
    await page.getByRole('radio', { name: 'Light' }).click()
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    expect(await background(page)).toBe(LIGHT)
  })

  test('on auto the theme follows the system as it changes', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    await loads(page, '/')
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    expect(await background(page)).toBe(DARK)
    await page.emulateMedia({ colorScheme: 'light' })
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    expect(await background(page)).toBe(LIGHT)
    await page.getByRole('button', { name: /Display/ }).click()
    await expect(page.getByRole('radio', { name: 'Auto' })).toBeChecked()
  })

  test('paper is light from a chosen dark theme', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('bsim.theme', 'dark'))
    await loads(page, '/')
    expect(await background(page)).toBe(DARK)
    await page.emulateMedia({ media: 'print' })
    expect(await background(page)).toBe('rgb(255, 255, 255)')
  })
})

// M169: pinned pages, recent pages, the index of every page, the jump box before typing
test.describe('pinned and recent pages, the index of every page (M169)', () => {
  // the lines the bar's visible parts sit on
  const rows = (page: Page) =>
    page.evaluate(() => {
      const boxes = [...document.querySelector('.topbar')!.children].map((c) => c.getBoundingClientRect()).filter((r) => r.width > 0)
      boxes.sort((a, b) => a.top - b.top)
      let n = 0
      let bottom = -Infinity
      for (const r of boxes) {
        if (r.top >= bottom) n++
        bottom = Math.max(bottom, r.bottom)
      }
      return n
    })
  const start = (page: Page, locale: 'en' | 'he', pins: string[]) =>
    page.addInitScript(
      ([l, p]) => {
        localStorage.setItem('bsim.locale', l as string)
        if (!localStorage.getItem('bsim.pins')) localStorage.setItem('bsim.pins', JSON.stringify(p))
      },
      [locale, pins] as const,
    )

  for (const locale of ['en', 'he'] as const) {
    test(`the bar at its fullest, a pin and the pin button in it, is one row from 1280px (${locale})`, async ({ page }, info) => {
      test.skip(info.project.name !== 'desktop')
      await start(page, locale, ['/map'])
      for (const width of [1280, 1263]) {
        await page.setViewportSize({ width, height: 800 })
        await loads(page, '/phrases')
        await expect(page.locator('.topbar > .pin-button')).toBeVisible()
        await expect(page.locator('#menu-pinned')).toHaveCount(1)
        expect(await rows(page), `${width}px`).toBe(1)
      }
      for (const width of [1150, 1000, 905]) {
        await page.setViewportSize({ width, height: 800 })
        await loads(page, '/phrases')
        expect(await rows(page), `${width}px`).toBeLessThanOrEqual(2)
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
        expect(overflow, `${width}px`).toBeLessThanOrEqual(1)
      }
    })

    test(`before typing, the jump box lists the pinned pages and what was opened last; "gen" finds Genesis (${locale})`, async ({ page }) => {
      await start(page, locale, ['/gematria'])
      await loads(page, '/unit/c%3A0%3A1')
      await loads(page, '/map')
      await loads(page, '/search')
      await page.keyboard.press('Control+k')
      const box = page.getByRole('dialog').getByRole('combobox')
      await expect(box).toBeFocused()
      // the jump box's own options: a page may have a select's of its own
      const list = page.getByRole('dialog').getByRole('listbox')
      const options = list.getByRole('option')
      await expect(options.first()).toContainText(locale === 'en' ? 'Gematria' : 'גימטריה')
      await expect(options.first()).toHaveAttribute('aria-selected', 'true')
      await expect(list.getByRole('option', { name: 'c:0:1' })).toHaveCount(1) // the fixture's label of Genesis 1
      await expect(list.getByRole('option', { name: locale === 'en' ? /^Map/ : /^מפה/ })).toHaveCount(1)
      await expect(options.last()).toHaveText(locale === 'en' ? 'All pages' : 'כל העמודים')
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
      expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
      // a book by the start of its name
      await box.fill(locale === 'en' ? 'gen' : 'ברא')
      await list.getByRole('option', { name: locale === 'en' ? /^Genesis/ : /^בראשית/ }).click()
      await expect(page).toHaveURL(/\/browse\/0$/)
    })
  }

  test('a page pinned from the bar is in the Pinned menu from any page, and still there after a reload', async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop') // a phone pins from the index (the next test)
    await loads(page, '/phrases')
    await expect(page.getByRole('button', { name: /^Pinned/ })).toHaveCount(0)
    const pin = page.getByRole('button', { name: 'Pin Phrases' })
    await pin.click()
    await expect(pin).toHaveAttribute('aria-pressed', 'true')
    await page.reload()
    await expect(page.getByRole('button', { name: 'Pin Phrases' })).toHaveAttribute('aria-pressed', 'true')
    await loads(page, '/unit/v%3A0')
    await expect(page.locator('.topbar > .pin-button')).toHaveCount(0) // a passage is not a page of the nav
    const menu = page.getByRole('button', { name: /^Pinned/ })
    await menu.click()
    for (const theme of ['Light', 'Dark']) {
      await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t.toLowerCase()), theme)
      const results = await new AxeBuilder({ page }).include('.topbar').withTags(['wcag2a', 'wcag2aa']).analyze()
      expect(results.violations.map((v) => v.id), theme).toEqual([])
    }
    await page.locator('#menu-pinned').getByRole('link', { name: /Phrases/ }).click()
    await expect(page).toHaveURL(/\/phrases$/)
    // each menu ends with the link to every page
    await page.getByRole('button', { name: /^Parallels/ }).click()
    await page.locator('#menu-parallels').getByRole('link', { name: 'All pages' }).click()
    await expect(page).toHaveURL(/\/pages$/)
    await expect(page.getByRole('heading', { level: 1, name: 'All pages' })).toBeVisible()
  })

  test('the index of every page: a filter in the URL, a page pinned from its row', async ({ page }) => {
    await loads(page, '/pages')
    expect(await page.locator('.pages-row').count()).toBeGreaterThan(60)
    await page.getByRole('searchbox', { name: 'Filter' }).fill('gematria')
    await expect(page).toHaveURL(/\/pages\?q=gematria$/)
    await expect(page.locator('.pages-row')).toHaveCount(2)
    await page.getByRole('button', { name: 'Pin Gematria' }).click()
    await expect(page.getByRole('heading', { level: 2, name: 'Pinned' })).toBeVisible()
    await page.reload()
    await expect(page.locator('.pages-row')).toHaveCount(3) // the two, and Gematria again under Pinned
    await expect(page.getByRole('button', { name: 'Pin Gematria' }).first()).toHaveAttribute('aria-pressed', 'true')
    expect(await page.evaluate(() => localStorage.getItem('bsim.pins'))).toBe('["/gematria"]')
  })
})

// M170: the start page
test.describe('the start page (M170)', () => {
  test('a first visit has the guided tours where the recent passages will be', async ({ page }) => {
    await loads(page, '/')
    await expect(page.locator('main h2')).toHaveText(['New here?', 'The books'])
    await expect(page.locator('.tour-card')).toHaveCount(4)
    await page.getByRole('link', { name: /^All pages/ }).click()
    await expect(page).toHaveURL(/\/pages$/)
  })

  for (const locale of ['en', 'he'] as const) {
    test(`from a cold start the passage read last is one click away (${locale})`, async ({ page }) => {
      await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
      await loads(page, '/unit/v%3A1')
      await loads(page, '/read/c%3A0%3A1')
      await loads(page, '/map')
      // a cold start: the address typed again
      await loads(page, '/')
      await expect(page.locator('main h2')).toHaveText(locale === 'en' ? ['Continue', 'The books'] : ['המשיכו מכאן', 'הספרים'])
      const cards = page.locator('.start-passages a')
      await expect(cards).toHaveCount(2)
      await expect(cards.first()).toContainText('c:0:1') // the fixture's label of Genesis 1
      await expect(cards.first()).toContainText(locale === 'en' ? 'in the reader' : 'בקורא')
      await expect(page.locator('.start-pages a')).toHaveText([locale === 'en' ? 'Map' : 'מפה'])
      // the tours are one line now
      await expect(page.locator('.tour-card')).toHaveCount(0)
      await expect(page.locator('.start-tours a').first()).toHaveAttribute('href', '/tours')
      for (const theme of ['light', 'dark']) {
        await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme)
        const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
        expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id), theme).toEqual([])
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(overflow).toBeLessThanOrEqual(1)
      await cards.first().click()
      await expect(page).toHaveURL(/\/read\/c%3A0%3A1$/)
    })
  }

  test('the jump field of the start page: a reference, a book, Escape', async ({ page }) => {
    await loads(page, '/')
    const field = page.locator('.jump-inline').getByRole('combobox')
    await expect(page.locator('.jump-pop')).toHaveCount(0)
    await field.fill('gen')
    const list = page.locator('.jump-pop').getByRole('listbox')
    await expect(list.getByRole('option').first()).toContainText('Genesis')
    const results = await new AxeBuilder({ page }).include('.jump-inline').withTags(['wcag2a', 'wcag2aa']).analyze()
    expect(results.violations.map((v) => v.id)).toEqual([])
    await field.press('Escape')
    await expect(field).toHaveValue('')
    await expect(page.locator('.jump-pop')).toHaveCount(0)
    await field.fill('Gen 1:2')
    await expect(list.getByRole('option').first()).toHaveAttribute('aria-selected', 'true')
    await field.press('Enter')
    await expect(page).toHaveURL(/\/unit\/v%3A1$/)
    // Ctrl+K still opens the box over the start page, beside the field
    await page.goto('/')
    await page.keyboard.press('Control+k')
    await expect(page.getByRole('dialog').getByRole('combobox')).toBeFocused()
  })

  test('the notebook entries changed last are on the start page, each with the start of its note', async ({ page }) => {
    // the notebook answered here, not written on the server: other tests keep and count its entries
    const unit = (id: string) => ({ unit_id: id, unit_type: 'verse', label_en: id, label_he: id, book_id: 0, start_verse_id: 0, end_verse_id: 0, n_verses: 1, marker: null })
    const entry = (id: string, note: string, updated_at: string) => ({ unit: unit(id), note, collections: [], created_at: updated_at, updated_at, verse: null })
    await page.route('**/api/notebook', (route) =>
      route.fulfill({
        json: {
          writable: true,
          hidden: 0,
          collections: [],
          entries: [entry('v:0', 'an older note', '2026-11-01T08:00:00'), entry('v:2', 'the note changed last\nits second line', '2026-11-12T08:00:00')],
        },
      }),
    )
    await loads(page, '/')
    await expect(page.locator('.start-notes li')).toHaveText(['v:2the note changed last', 'v:0an older note'])
    const results = await new AxeBuilder({ page }).include('.start-page').withTags(['wcag2a', 'wcag2aa']).analyze()
    expect(results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id)).toEqual([])
    await page.locator('.start-notes a').first().click()
    await expect(page).toHaveURL(/\/unit\/v%3A2$/)
  })
})
