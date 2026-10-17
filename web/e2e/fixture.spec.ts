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
  '/query',
  '/query?q=%5Blemma%3D430%5D+%5Blemma%3D559%5D',
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
  await page.goto('/ciphers')
  await expect(page.locator('.dlg-verdict')).toHaveCount(4)
  await expect(page.locator('.cipher-hit')).toHaveCount(2)
  await page.getByRole('radio', { name: 'Atbash' }).click()
  await expect(page).toHaveURL(/\/ciphers\?cipher=atbash$/)
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
  // clean up: the collection, then the entry
  await page.getByRole('button', { name: 'Delete collection' }).click()
  await page.getByRole('button', { name: 'Delete', exact: true }).click()
  await expect(page.getByText('No collections yet.')).toBeVisible()
  await page.locator('.notebook-entry').getByRole('button', { name: 'Remove from notebook' }).click()
  await page.getByRole('button', { name: 'Remove', exact: true }).click()
  await expect(page.getByText(/Nothing kept yet/)).toBeVisible()
})

test('the Hebrew interface is right to left and loads every page cleanly', async ({ page }) => {
  test.setTimeout(240_000)
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
    test.setTimeout(300_000)
    await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
    for (const path of PAGES) {
      await loads(page, path)
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
      const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
      expect(serious.map((v) => `${path}: ${v.id} (${v.nodes.length})`)).toEqual([])
    }
  })
}
