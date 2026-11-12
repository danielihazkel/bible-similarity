import AxeBuilder from '@axe-core/playwright'
import { expect, type Page, test } from '@playwright/test'

// Every page loads against the real API, renders its heading and logs no errors.
const PAGES: [string, RegExp][] = [
  ['/', /Browse/],
  ['/search?q=%D7%A8%D7%90%D7%A9%D7%99%D7%AA&mode=lexical', /Search/],
  ['/compare?a=c%3A26%3A14&b=c%3A26%3A53', /Compare/],
  ['/discoveries', /Discoveries|Undiscovered/],
  ['/labels', /Your labels/],
  ['/labels?tab=queue', /Your labels/],
  ['/notebook', /Your notebook/],
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
  ['/divisions?book=14&kind=cut', /Where the text divides/],
  ['/divisions?unit=c%3A14%3A6', /Where the text divides/],
  ['/ketiv', /Written and read/],
  ['/ketiv?parallel=qere', /Written and read/],
  ['/citations', /Citations/],
  ['/citations?family=command&resolved=1', /Citations/],
  ['/phrases?view=spread', /Shared phrases/],
  ['/structure?view=small', /Structure/],
  ['/structure?view=small&list=verses', /Structure/],
  ['/typescenes', /Action sequences/],
  ['/wordplay?view=alliteration', /Wordplay/],
  ['/wordplay?view=rhyme', /Wordplay/],
  ['/poetry?view=pairs', /Parallel halves/],
  ['/poetry?view=meter', /Parallel halves/],
  ['/roots', /Roots/],
  ['/roots?view=key', /Roots/],
  ['/root/1288', /root/],
  ['/refrains', /Refrains/],
  ['/refrains?book=26&all=1', /Refrains/],
  ['/psalms', /Psalms/],
  ['/psalms?genre=lament_individual&sort=turn', /Psalms/],
  ['/read/c%3A26%3A13?layers=mood%2Cturns', /Psalms 13/],
  ['/pentateuch', /Pentateuch/],
  ['/pentateuch?book=3', /Pentateuch/],
  ['/read/c%3A0%3A7?layers=sources%2Cturns', /Genesis 7/],
  ['/read/c%3A16%3A4?layers=refrains%2Cturns', /Amos 4/],
  ['/read/c%3A0%3A3?layers=speakers%2Ccola%2Cleitworte%2Cphrases%2Crare%2Cwordplay%2Cketiv%2Cturns', /Genesis 3/],
  ['/read/c%3A26%3A119?layers=leitworte%2Ccola&lw=root', /Psalms 119/],
  ['/unit/c%3A31%3A3?halves=1&meter=1', /Lamentations 3/],
  ['/unit/c%3A26%3A1?halves=1&clauses=1', /Psalms 1/],
  ['/network?type=pericope&unit=s%3A50', /Network of echoes/],
  ['/network?view=directions', /Network of echoes/],
  ['/findings', /Findings/],
  ['/sequences?view=arcs', /Parallel sequences/],
  ['/sequences?view=arcs&q=all&order=any&book=37', /Parallel sequences/],
  ['/network?view=directions&basis=cited', /Network of echoes/],
  ['/sequences?order=reverse&q=all', /Parallel sequences/],
  ['/changes?view=rewrites&pair=8-37', /How parallels differ/],
  ['/unit/c%3A26%3A145?acrostic=1', /Psalms 145/],
  ['/domains', /Semantic domains/],
  ['/domains/001001', /Beings/],
  ['/unit/c%3A0%3A1?mode=domain', /Genesis 1/],
  ['/unit/c%3A0%3A1?mode=syntax', /Genesis 1/],
  ['/poetry?sort=antithetic', /Parallel halves/],
  ['/shifts', /Shifts/],
  ['/language?book=32', /Language/],
  ['/speech?book=2', /Who speaks/],
  ['/speech?view=voices&voice=1732', /Who speaks/],
  ['/speech?view=dialogue', /Who speaks/],
  ['/speech?view=dialogue&book=7&unequal=1', /Who speaks/],
  ['/forms', /Numbers and lists/],
  ['/gematria?q=%D7%90%D7%9C%D7%99%D7%A2%D7%96%D7%A8', /Gematria/],
  ['/gematria?q=2701&view=verses', /Gematria/],
  ['/gematria-links', /Equal values, related words/],
  ['/gematria-links?sort=domains&value=358', /Equal values, related words/],
  ['/els', /Letters at equal skips/],
  ['/els?scope=genesis', /Letters at equal skips/],
  ['/ciphers', /Atbash and albam/],
  ['/ciphers?cipher=albam&book=12', /Atbash and albam/],
  ['/masorah', /The Masorah’s counts/],
  ['/masorah?text=qere', /The Masorah’s counts/],
  ['/places', /Places on the map/],
  ['/places?book=5&chapter=15', /Places on the map/],
  ['/places?view=east&p=12', /Places on the map/],
  ['/place-lists', /Place lists on the ground/],
  ['/place-lists?list=josh15&show=short&group=tribes', /Place lists on the ground/],
  ['/place-arc', /The geographic arc/],
  ['/place-arc?book=12', /The geographic arc/],
  ['/place-links', /Named together, near together/],
  ['/place-links?place=52&sort=km&bins=sure', /Named together, near together/],
  ['/genealogy', /Family tree/],
  ['/genealogy?p=194', /Family tree/],
  ['/query?q=%5Bform%3Dimperative%5D+..4+%5Bfunction%3DVoct+pos%3Dname%5D', /Pattern search/],
  ['/workbench?a=chapters%3A26%3A42-83&b=book%3A26', /Workbench/],
  ['/divine', /Names of God/],
  ['/etiologies', /Naming etiologies/],
  ['/brackets', /Resumptive repetition/],
  ['/retold', /Retold speech/],
  ['/haftarot', /Haftarot/],
  ['/chronology', /The text’s own chronology/],
  ['/frameworks', /Narrative frameworks/],
  ['/binomials', /Word pairs/],
  ['/sums', /Do the sums add up/],
  ['/vocabulary', /Vocabulary over the canon/],
  ['/reception', /Rabbinic reception/],
  ['/reception?unit=v%3A5520', /Rabbinic reception/],
  ['/witnesses', /Other witnesses/],
  ['/source', /Source finder/],
  ['/witnesses?unit=v%3A2065', /Other witnesses/],
  ['/glossary', /Glossary/],
  ['/week', /This week’s parasha/],
  ['/week?date=2019-08-01&israel=1', /This week’s parasha/],
  ['/week?date=2019-04-24', /This week’s parasha/],
  ['/tours', /Guided tours/],
  ['/compare?a=c%3A26%3A14&b=c%3A26%3A53&tour=parallels&step=1', /Compare/],
  ['/sums?list=ezra2&scope=every&book=35', /Do the sums add up/],
  ['/synopses', /Synopses/],
  ['/synopses/13', /Jeremiah 52/],
  ['/forms?view=lists&book=37', /Numbers and lists/],
  ['/map?color=lists', /Map of the Tanakh/],
  ['/borrowing', /Who borrowed/],
  ['/borrowing?unit=c%3A10%3A18', /Who borrowed/],
  ['/phrases?unit=c%3A10%3A18', /Shared phrases/],
  ['/changes?unit=c%3A10%3A18', /How parallels differ|Changes/],
  ['/unit/c%3A0%3A22?syntax=1', /Genesis 22/],
  ['/lemma/1350a', /גאל/],
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
    const nav = page.locator('#main-nav')
    await expect(nav).toBeVisible()
    // each group a disclosure: closed on the home page, which is in none of them
    const wordplay = nav.getByRole('link', { name: /Wordplay/ })
    await expect(wordplay).toBeHidden()
    await nav.getByRole('button', { name: /Patterns/ }).click()
    await expect(nav.getByText('Letters and numbers')).toBeVisible()
    await wordplay.click()
    await expect(page).toHaveURL(/\/wordplay$/)
    await expect(nav).toBeHidden() // closes after navigating
    await toggle.click()
    await expect(wordplay).toBeVisible() // the current page's group opens with the menu
  } else {
    await expect(page.getByRole('button', { name: /Menu/ })).toBeHidden()
    const nav = page.locator('#main-nav')
    await nav.getByRole('button', { name: /Patterns/ }).click()
    const menu = page.locator('#menu-patterns')
    await expect(menu).toBeVisible()
    await expect(menu.getByText('Narrative', { exact: true })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(menu).toBeHidden()
    await nav.getByRole('button', { name: /Parallels/ }).click()
    await nav.getByRole('link', { name: /Sequences/ }).click()
    await expect(page).toHaveURL(/\/sequences$/)
    await expect(page.getByRole('button', { name: /Parallels/ })).toHaveClass(/active/)
  }
  // the page never scrolls sideways
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})

for (const scheme of ['light', 'dark'] as const) {
  test(`main pages have no serious accessibility violations (${scheme})`, async ({ page }) => {
    test.setTimeout(480_000) // axe on every listed page: about 4 s each, 60 pages
    await page.emulateMedia({ colorScheme: scheme })
    await checkA11y(page)
  })
}

async function checkA11y(page: Page) {
  for (const path of ['/', '/compare?a=c%3A26%3A14&b=c%3A26%3A53', '/style?book=26', '/sequences/4', '/poetry', '/names?e=1732', '/unit/c%3A0%3A1', '/findings', '/sequences?view=arcs', '/network', '/network?view=directions', '/acrostics', '/divisions?book=14', '/ketiv', '/citations', '/phrases?view=spread', '/structure?view=small', '/eval', '/typescenes', '/wordplay?view=rhyme', '/poetry?view=pairs', '/poetry?view=meter', '/unit/c%3A31%3A3?halves=1&meter=1', '/roots', '/roots?view=key', '/root/1288', '/refrains', '/psalms', '/read/c%3A26%3A22?layers=mood%2Cspeakers', '/pentateuch', '/read/c%3A0%3A7?layers=sources', '/read/c%3A0%3A3?layers=speakers%2Ccola%2Cleitworte%2Cphrases%2Crare%2Cwordplay%2Cketiv%2Cturns', '/domains', '/domains/001001', '/shifts', '/lemma/1350a', '/language?book=32', '/speech?book=2', '/speech?view=voices&voice=1732', '/speech?view=dialogue&book=7', '/forms', '/forms?view=lists', '/gematria?q=318', '/read/c%3A0%3A1?layers=gematria', '/gematria-links', '/ciphers', '/masorah', '/places', '/places?p=55', '/place-lists', '/place-arc', '/place-links', '/genealogy', '/genealogy?p=194', '/genealogy?p=1216', '/els', '/read/c%3A5%3A10?layers=places', '/query?q=%5Blemma%3D408%5D+%5Bform%3Djussive%5D', '/unit/c%3A0%3A22?syntax=1', '/labels', '/labels?tab=queue', '/notebook', '/borrowing', '/workbench?a=chapters%3A26%3A42-83&b=book%3A26', '/workbench?tab=check&q=%5Blemma%3D430%5D&set=chapters%3A26%3A42-83', '/divine?book=26', '/read/c%3A26%3A53?layers=divine', '/etiologies?order=strongest', '/brackets?order=strongest', '/retold?group=retold&order=most', '/haftarot?p=p%3AVayera', '/chronology', '/frameworks?k=hezekiah', '/binomials?pair=2091%2B3701', '/sums?list=num1', '/vocabulary', '/reception', '/reception?unit=v%3A5520', '/read/c%3A4%3A24?layers=reception', '/witnesses', '/witnesses?unit=v%3A2065', '/source?example=aleinu', '/read/c%3A1%3A20?layers=witnesses', '/glossary', '/tours', '/week?date=2019-08-01', '/findings?tour=parallels&step=1', '/synopses', '/synopses/13', '/neighbourhood/v%3A0', '/neighbourhood/c%3A26%3A23?hops=1', '/mainline', '/read/c%3A0%3A3?layers=mainline', '/prophetic', '/read/c%3A11%3A5?layers=prophetic', '/laws', '/laws?pair=4']) {
    await page.goto(path)
    await page.locator('h1').first().waitFor()
    await page.waitForLoadState('networkidle')
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
    const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    expect(serious.map((v) => `${path}: ${v.id} (${v.nodes.length})`)).toEqual([])
  }
}

test('who speaks to whom: the checks, a book’s conversations, and an exchange in the reader', async ({ page }) => {
  await page.goto('/speech?view=dialogue&book=7')
  await expect(page.getByRole('heading', { name: 'Checks fixed in advance' })).toBeVisible()
  // deference and נא hold, the last word does not (M124: compared within books, known speakers only)
  await expect(page.locator('.dlg-verdict.holds')).toHaveCount(2)
  await expect(page.locator('.dlg-verdict.fails')).toHaveCount(1)
  await expect(page.getByRole('img', { name: /most active speakers of I Samuel/ })).toBeVisible()
  await page.locator('.dlg-pairs').getByRole('button', { name: 'שאול' }).first().click()
  await expect(page).toHaveURL(/party=7586/)
  const first = page.locator('.dlg-exchange').first()
  await expect(first).toContainText('שאול')
  await first.getByRole('link').click()
  await expect(page).toHaveURL(/\/read\/c%3A7%3A\d+\?layers=speakers/)
  await expect(page.locator('.reader-legend')).toContainText(' to ')
})

test('names of God: the Elohistic Psalter found, the doubled psalms, Psalm 53 in the reader', async ({ page }) => {
  await page.goto('/divine')
  const elo = page.locator('.dv-check').first()
  await expect(elo.locator('.dv-verdict')).toHaveText('Borne out')
  await expect(elo).toContainText('42–84')
  await expect(page.locator('.dv-check').nth(1).locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(page.locator('rect.dv-cell')).toHaveCount(929)
  await expect(page.getByRole('region', { name: /Psalms 53:1-7 and Psalms 14:1-7/ }).locator('tr.dv-kind-e_ward')).toHaveCount(4)
  await page.goto('/read/c%3A26%3A53?layers=divine')
  await expect(page.locator('.reader-text .dv-elohim')).toHaveCount(7)
  await expect(page.locator('.reader-text .dv-yhwh')).toHaveCount(0)
})

test('naming etiologies: the echo holds, Naphtali and Jacob first, Reuben marked in its verse', async ({ page }) => {
  await page.goto('/etiologies')
  await expect(page.locator('.dv-check').first().locator('.dv-verdict')).toHaveText('Borne out')
  await expect(page.locator('.dv-check').nth(1).locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(page.locator('li.ety-naming')).toHaveCount(65) // the namings whose verse explains (M159; 111 found)
  await page.getByRole('radio', { name: 'Strongest first' }).click()
  // tied at p 0.0002 and a full echo: canon order, ויעקבני (Gen 27:36) before נפתולי (30:8)
  await expect(page.locator('li.ety-naming').nth(0)).toContainText('יעקב')
  await expect(page.locator('li.ety-naming').nth(1)).toContainText('נפתלי')
  await page.getByRole('radio', { name: /Named in advance/ }).click()
  const reuben = page.locator('li.ety-naming', { hasText: 'ראובן' })
  await expect(reuben.locator('.w-focus')).toHaveCount(1)
  await expect(reuben.locator('.w-shared')).toHaveCount(1)
})

test('resumptive repetition: the claim holds, Exodus 6 found and beyond chance, the strongest first', async ({ page }) => {
  await page.goto('/brackets')
  await expect(page.locator('.dv-check').first().locator('.dv-verdict')).toHaveText('Borne out')
  await expect(page.locator('.dv-check').nth(1).locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(page.locator('.brk-known li')).toHaveText([/^Genesis 37:36 … Genesis 39:1: found/, /^Exodus 6:10-12 … Exodus 6:29-30: found · p 0\.007/, /^Ezra 4:5 … Ezra 4:24: found/])
  // those named in advance by default (M159)
  await expect(page.getByRole('radio', { name: 'Named in advance' })).toBeChecked()
  await expect(page.locator('li.brk-bracket')).toHaveCount(3)
  await expect(page.locator('li.brk-bracket').nth(1)).toContainText('Exodus 6:30')
  await page.getByRole('radio', { name: 'All' }).click()
  await page.getByRole('radio', { name: 'Strongest first' }).click()
  await expect(page.locator('li.brk-bracket').first()).toContainText('Isaiah 2:17') // Ezek 48's border formula left out (M159)
})

test('retold speech: the claim not borne out, the known retellings found, the woman retells God in Genesis 3', async ({ page }) => {
  await page.goto('/retold')
  await expect(page.locator('.dv-check').first().locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(page.locator('.dv-check').nth(1).locator('.dv-verdict')).toHaveText('Borne out')
  await expect(page.locator('.brk-known li')).toHaveText([/^Genesis 2:16-17 → Genesis 3:2-3: found/, /^Genesis 24:2-8 → Genesis 24:37-41: found/, /^Genesis 41:1-7 → Genesis 41:17-24: found/])
  // the box follows the address: click, then wait for it
  await page.getByRole('checkbox', { name: 'Named in advance only' }).click()
  await expect(page).toHaveURL(/known=1/)
  await expect(page.locator('li.rt-pair')).toHaveCount(4)
  const eve = page.locator('li.rt-pair').first()
  await expect(eve.locator('.rt-teller').first()).toHaveText('First told by God')
  await expect(eve.locator('[class*="w-diff-"]').first()).toBeVisible()
})

test('haftarot: the claim holds, Tetzaveh first, Vayera finds II Kings 4 third', async ({ page }) => {
  await page.goto('/haftarot')
  await expect(page.locator('.dv-check').first().locator('.dv-verdict')).toHaveText('Borne out')
  await expect(page.locator('table.hf-table tbody tr')).toHaveCount(54)
  await expect(page.locator('table.hf-table tbody tr', { hasText: 'Tetzaveh' })).toContainText('1 (1 · 1)')
  await page.getByRole('button', { name: 'The chapters of the Prophets for Vayera' }).click()
  await expect(page.locator('.hf-chapters li').nth(2)).toHaveClass('hf-hit')
  await expect(page.locator('.hf-chapters li').nth(2)).toContainText('II Kings 4')
})

test('chronology: the Flood in 1656, Methuselah dies that year, Abijam in Jeroboam’s 18th', async ({ page }) => {
  await page.goto('/chronology')
  await expect(page.locator('.dv-check').first().locator('.dv-verdict')).toHaveText('Borne out')
  await expect(page.locator('table.ch-events tbody tr')).toHaveCount(54)
  await expect(page.locator('table.ch-events tbody tr').filter({ has: page.locator('th', { hasText: /^The Flood$/ }) })).toContainText('1656')
  await expect(page.locator('table.ch-events tbody tr').filter({ has: page.locator('th', { hasText: '\u2068מתושלח\u2069 dies' }) })).toContainText('1656')
  await expect(page.locator('.ch-conflicts li')).toHaveCount(2)
  await expect(page.locator('.ch-reign')).toHaveCount(39)
  await expect(page.locator('table.ch-syncs tbody tr')).toHaveCount(31)
  await expect(page.locator('table.ch-syncs tbody tr').first()).toContainText('\u2068אבים\u2069 king in year 18 of \u2068ירבעם\u2069')
  await expect(page.locator('table.ch-digits tbody tr.ch-end')).toHaveCount(4)
})

test('frameworks: Othniel whole, Samson three of six, Hezekiah did right', async ({ page }) => {
  await page.goto('/frameworks')
  await expect(page.locator('.dv-check').first().locator('.dv-verdict')).toHaveText('Borne out')
  const rows = page.locator('table.fw-cycle tbody tr')
  await expect(rows).toHaveCount(6)
  await expect(rows.first().locator('a.fw-hit')).toHaveCount(6)
  await expect(rows.last().locator('td').last()).toHaveText('3 / 6')
  await expect(page.locator('table.fw-kings tbody tr')).toHaveCount(39)
  await page.locator('table.fw-kings tbody tr', { hasText: 'חזקיה' }).getByRole('button').click()
  await expect(page.locator('.fw-panel .type-tag')).toHaveText('right')
  await expect(page.locator('.fw-panel')).toContainText('II Kings 18:3')
})

test('word pairs: silver and gold first of all, turned round in Chronicles', async ({ page }) => {
  await page.goto('/binomials')
  await expect(page.locator('.dv-check').nth(1).locator('.dv-verdict')).toHaveText('Borne out')
  const first = page.locator('table.bn-table tbody tr').first()
  await expect(first.locator('th')).toHaveText('כסף וזהב')
  await expect(first.locator('td.bn-turned')).toHaveText('14 / 25')
  await first.getByRole('button').click()
  await expect(page.locator('.bn-panel h4')).toHaveText(['In its own order', 'Turned round'])
  await expect(page.locator('.bn-panel')).toContainText('Chronicles')
})

test('synopsis: the fall of Jerusalem in Jeremiah 52, Jeremiah 39 and II Kings 24–25', async ({ page }) => {
  await page.goto('/synopses')
  await page.getByRole('link', { name: /Jeremiah 52:1–27/ }).click()
  await expect(page.locator('h1')).toContainText('II Kings 24:18–25:21')
  // the siege: one row, three witnesses
  const row = page.locator('.syn-row').filter({ hasText: /Jeremiah 39:1(?!\d)/ })
  await expect(row.locator('.hit-ref')).toHaveText(['Jeremiah 52:4', 'Jeremiah 39:1', 'II Kings 25:1'])
  // I Chronicles 16 against Psalms 105 and then 96: the psalms share a column
  await page.goto('/synopses/25')
  await expect(page.locator('h1')).toHaveText('I Chronicles 16:8–33 · Psalms 105:1–15 + 96:2–12')
  await expect(page.locator('.syn-flag')).toHaveCount(1)
})

test('compare: in the hollow of his hand, its measures: a link of meaning (Isa 40:12, Job 38:5)', async ({ page }) => {
  test.setTimeout(120_000) // the encoder loads on first use
  await page.goto('/compare?a=v%3A10941&b=v%3A19512&marks=meaning')
  await page.locator('.column').first().locator('.align-row').first().hover()
  const meaning = page.locator('.align-chip.meaning')
  await expect(meaning).toHaveCount(1, { timeout: 90_000 })
  await expect(meaning).toContainText('בשעלו')
  await expect(meaning).toContainText('ממדיה')
  await expect(page.locator('.column').first().locator('.w-meaning')).toHaveCount(1)
})

test('workbench: the Elohistic Psalter against the rest of Psalms, and אלהים checked on it', async ({ page }) => {
  await page.goto('/workbench?a=chapters%3A26%3A42-83&b=book%3A26')
  const a = page.getByRole('region', { name: 'Commoner in A' })
  await expect(a.locator('tbody tr').first()).toContainText('אלהים', { timeout: 30_000 })
  await expect(page.getByRole('region', { name: 'Commoner in B' }).locator('tbody tr').first()).toContainText('יהוה')
  await page.goto('/workbench?tab=check&q=%5Blemma%3D430%5D&set=chapters%3A26%3A42-83')
  await expect(page.getByText(/Denser than chance/)).toBeVisible({ timeout: 30_000 })
})

test('pattern search finds the infinitive absolute with its finite verb, as the roots stage counts it', async ({ page }) => {
  await page.goto('/query')
  await page.getByRole('searchbox', { name: 'Query' }).fill('[form=infabs lemma=@l lang=hebrew] ..3 [lemma=@l form=finite]')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByText(/432 matches in 391 verses/)).toBeVisible({ timeout: 30_000 })
  const first = page.locator('.query-hit').first()
  await expect(first).toContainText('Genesis 2:16')
  await expect(first.locator('.w-shared')).toHaveCount(2)
  await page.getByRole('button', { name: /^Exodus \d+$/ }).click()
  await expect(page).toHaveURL(/book=1$/)
  await expect(page.locator('.query-hit').first()).toContainText('Exodus')
})

test('numbers and lists: Amos 1 among the sayings, Genesis 5 among the lists', async ({ page }) => {
  await page.goto('/forms?book=16')
  await expect(page.getByRole('heading', { name: 'Checks fixed in advance' })).toBeVisible()
  await expect(page.locator('.dlg-verdict')).toHaveCount(3)
  const amos = page.locator('.saying').first()
  await expect(amos).toContainText('3 / 4')
  await expect(amos.locator('.w-shared')).toHaveCount(2)
  await page.getByRole('radio', { name: 'Lists' }).click()
  await expect(page).toHaveURL(/\/forms\?view=lists$/)
  // Genesis 1's days come first since M126 (lists alike in their openings)
  await expect(page.locator('.list').first()).toContainText('Genesis 1:')
  const gen5 = page.locator('.list', { hasText: 'Adam to Noah' })
  await expect(gen5).toContainText('Genesis 5:')
  await expect(gen5).toContainText('genealogy')
  await expect(gen5).toContainText('Adam to Noah')
  await gen5.getByRole('link', { name: 'Read the chapter' }).click()
  await expect(page).toHaveURL(/\/unit\/c%3A0%3A5$/)
})

test('gematria: Eliezer is 318, Genesis 1:1 adds up to 2701, and the reader links the two', async ({ page }) => {
  await page.goto('/gematria?q=%D7%90%D7%9C%D7%99%D7%A2%D7%96%D7%A8')
  await expect(page.getByRole('button', { name: /Standard 318/ })).toBeVisible()
  await expect(page.locator('.gm-forms li').first()).toContainText('וישב')
  await page.getByRole('radio', { name: /Lemmas/ }).click()
  await expect(page.locator('.gm-lemmas .lemma-chip', { hasText: 'אֱלִיעֶזֶר' }).first()).toBeVisible()
  await page.goto('/read/c%3A0%3A1?layers=gematria')
  await expect(page.locator('.reader-text .w-mark').first()).toHaveText('=913')
  await page.locator('.gm-total').first().click()
  await expect(page).toHaveURL(/\/gematria\?q=2701&view=verses$/)
  await expect(page.getByRole('link', { name: 'Genesis 1:1' })).toBeVisible()
  await page.keyboard.press('Control+k')
  const box = page.getByRole('dialog').getByRole('combobox')
  await box.fill('= 358')
  await box.press('Enter')
  await expect(page).toHaveURL(/\/gematria\?q=358$/)
  await expect(page.locator('.gm-forms li', { hasText: 'משיח' }).first()).toBeVisible()
})

test('equal values link nothing; Genesis 1:1 shares its numbers with Psalm 44:5', async ({ page }) => {
  await page.goto('/gematria-links')
  await expect(page.locator('.gl-tests').first().locator('.dlg-verdict')).toHaveCount(0)
  await expect(page.locator('.dlg-verdict').first()).toHaveText('does not hold')
  await expect(page.locator('.dlg-verdict').nth(1)).toHaveText('holds')
  await expect(page.locator('.gl-eq tbody tr').first()).toContainText('358')
  await expect(page.getByText(/Only Genesis 1:1 has all of them/)).toBeVisible()
  await expect(page.getByRole('link', { name: 'Psalms 44:5' })).toBeVisible()
  await expect(page.locator('.gl-pairs li')).toHaveCount(25)
})

test('atbash: the three places in Jeremiah are found, and the word panel reads ששך as בבל', async ({ page }) => {
  await page.goto('/ciphers')
  await expect(page.getByText(/The places named in advance are found: 3 of 3\./)).toBeVisible()
  // those named in advance by default (M159)
  const named = page.getByRole('checkbox', { name: 'Only those named in advance' })
  await expect(named).toBeChecked()
  await expect(page.locator('.cipher-hit')).toHaveCount(3)
  await expect(page.locator('.cipher-hit').first()).toContainText('בבל')
  await page.goto('/unit/v%3A12068')
  // ששך is the verse's 20th word (the text is shown without te'amim by default)
  await page.locator('[data-word]').nth(19).click()
  const swapped = page.locator('.word-ciphers')
  await expect(swapped).toContainText('בבל')
  await swapped.getByRole('link', { name: 'בבל' }).click()
  await expect(page).toHaveURL(/\/search\?q=%D7%91%D7%91%D7%9C&mode=lexical$/)
})

test('the Masorah: the ו of גחון is 4,829 letters past the middle, Lev 8:8 is the middle verse', async ({ page }) => {
  await page.goto('/masorah')
  const letter = page.locator('.msr-middle').first()
  await expect(letter).toContainText('the 3rd letter of גחון')
  await expect(letter).toContainText('It falls 4,829 letters after ours')
  await expect(page.locator('.msr-middle', { hasText: 'Leviticus 8:8' }).first()).toContainText('lands')
  const exodus = page.locator('.msr-totals tbody tr', { hasText: 'Exodus' })
  await expect(exodus).toContainText('The Ten Commandments are divided otherwise')
  await exodus.getByRole('link').click()
  await expect(page).toHaveURL(/\/unit\/v%3A2053$/)
})

test('the map: Jerusalem opens with Judah named with it, Joshua 10 is drawn and read with its places', async ({ page }) => {
  await page.goto('/places')
  await expect(page.locator('.geo-pt')).toHaveCount(816)
  await page.locator('.place-list').getByRole('button', { name: 'ירושלם' }).click()
  await expect(page).toHaveURL(/\/places\?p=55$/)
  await expect(page.locator('.place-panel')).toContainText('31.78° N, 35.23° E')
  await expect(page.locator('.geo-pt.selected')).toHaveCount(1)
  await page.goto('/unit/c%3A5%3A10')
  await expect(page.getByRole('region', { name: 'Where this happens' }).locator('.geo-pt')).not.toHaveCount(0)
  await page.goto('/read/c%3A5%3A10?layers=places')
  await expect(page.locator('.reader-text .pl').first()).toBeVisible()
  await expect(page.locator('.legend-places').getByRole('link', { name: 'גבעון' })).toHaveAttribute('href', /p=232/)
})

test('place lists: the wilderness stations walk the ground, Judah’s towns cluster by district', async ({ page }) => {
  await page.goto('/place-lists?list=num33')
  const rows = page.locator('.pls-table').first().locator('tbody tr')
  await expect(rows).toHaveCount(6)
  await expect(page.locator('.pls-table').first().locator('.dlg-verdict', { hasText: 'does not hold' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'The path of Numbers 33:3–49' })).toBeVisible()
  await expect(page.locator('.pls-detail .geo-pt')).toHaveCount(48)
  await expect(page.locator('.pls-steps li').first()).toContainText('רעמסס')
  await expect(page.getByText(/Judah’s towns come in districts/)).toBeVisible()
  await expect(page.locator('.pls-districts tbody tr')).toHaveCount(11)
})

test('the geographic arc: Genesis moves with its chapters, Abram goes from Mesopotamia to Canaan', async ({ page }) => {
  await page.goto('/place-arc')
  await expect(page.getByText(/556 of 929 chapters name places enough to be placed/)).toBeVisible()
  await expect(page.getByRole('heading', { name: 'The path of Genesis' })).toBeVisible()
  await expect(page.locator('.pa-book .geo-pt')).toHaveCount(35)
  await expect(page.locator('.pa-moves tbody tr')).toHaveCount(4)
  await expect(page.locator('.pa-moves .dlg-verdict', { hasText: 'does not hold' })).toHaveCount(0)
  await expect(page.locator('.pa-moves tbody tr').first()).toContainText('Genesis 11')
  await expect(page.locator('.pa-oracle-chapters tbody tr')).toHaveCount(27)
  await page.getByRole('combobox', { name: 'Book' }).selectOption('12')
  await expect(page.getByRole('heading', { name: 'The path of Jeremiah' })).toBeVisible()
  await expect(page.locator('.pa-book .geo-pt')).toHaveCount(47)
})

test('places named together lie together, and Dan and Beersheba are a far pair', async ({ page }) => {
  await page.goto('/place-links')
  await expect(page.getByText(/510 pairs of 277 places are named together/)).toBeVisible()
  await expect(page.locator('.plk-table').first().locator('.dlg-verdict', { hasText: 'does not hold' })).toHaveCount(0)
  await expect(page.locator('.plk-dot')).toHaveCount(510)
  await expect(page.locator('.plk-leads > p .dlg-verdict')).toHaveText('holds')
  await expect(page.getByText(/rank 3 of 149 far pairs/)).toBeVisible()
  await expect(page.locator('.plk-leads tbody tr')).toHaveCount(25)
  await page.goto('/place-links?place=52&sort=km')
  await expect(page.locator('.plk-pairs li').first()).toContainText('באר שבע')
})

test('the family tree: Jacob’s sons under their four mothers, with verses', async ({ page }) => {
  await page.goto('/genealogy?p=194')
  const panel = page.getByRole('region', { name: 'Person' })
  await expect(panel.locator('.gt-child-group h4')).toHaveText(['By לאה', 'By בלהה', 'By זלפה', 'By רחל', 'By adoption'])
  // Gen 48:5: Joseph's sons taken as his own, apart from his wives' children
  await expect(panel.locator('.gt-child-group').last().locator('.gt-link-name, button').filter({ hasText: /אפרים|מנשה/ })).toHaveCount(2)
  await expect(panel.locator('.gt-proof').first()).toContainText('Genesis 25:26') // chosen in the review (M91)
  await expect(page.locator('.gt-node.selected')).toContainText('יעקב')
  // by the keyboard: on a phone the bottom sheet covers the tree's lower half
  await page.locator('.gt-node.selected .gt-toggle').press('Enter')
  // twenty children are wider than the view, and only what is in view is drawn: zoom out, but
  // not so far that the cards turn to dots (M92)
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Zoom out' }).press('Enter')
  // each mother once: a header over her children, or an avatar beside him
  for (const h of ['לאה', 'בלהה', 'זלפה', 'רחל']) await expect(page.locator('.gt-header.mother, .gt-spouse').filter({ hasText: h })).toHaveCount(1)
})

test('label queue: train-book pairs the two lists rank apart, the two sides in turn', async ({ page }) => {
  test.setTimeout(150_000)
  await page.goto('/labels?tab=queue')
  const items = page.locator('.queue-list > li')
  // the pool is built once, in the background from the server's start; read while the other
  // startup threads read the DB it can take up to a minute (DESIGN §16.79)
  await expect(items).toHaveCount(20, { timeout: 90_000 })
  await expect(page.getByText(/ of 78,557 judged$/)).toBeVisible()
  // the top: one list ranks the pair first, the other does not list it; lexical and semantic alternate
  await expect(items.nth(0)).toContainText(/lexical rank 1 · semantic rank beyond 50/)
  await expect(items.nth(1)).toContainText(/lexical rank beyond 50 · semantic rank 1/)
  // no dev or test book: Joshua, Judges, Samuel, Ezekiel, the Writings outside Psalms ...
  const heads = await items.locator('.queue-head').allInnerTexts()
  for (const h of heads) expect(h).not.toMatch(/(Joshua|Judges|I Samuel|Ezekiel|Micah|Nahum|Zephaniah|Proverbs|Job|Ruth|Esther|Daniel|Ezra|Nehemiah|Zechariah|Haggai|Ecclesiastes)/)
  await page.getByRole('radio', { name: 'Semantic' }).click()
  await expect(items.nth(1)).toContainText(/semantic rank 1/)
  // Claude's suggestions (bsim llm-triage, 2026-11-04): its calibration held (AUC 0.99, the Hebrew-rationale run)
  await expect(page.getByText(/AUC 0\.99 \(shown from 0\.75\)/)).toBeVisible()
  await page.getByRole('checkbox', { name: 'Only pairs with a suggestion' }).check()
  await expect(items.first().locator('.queue-suggestion')).toContainText(/^Claude suggests: (Real|Not|Unsure) \(p [01]\.\d\d, /)
})

test('source finder: Aleinu’s six verses, the priestly blessing as one passage, the Mishnah’s Deut 6:7', async ({ page }) => {
  await page.goto('/source?example=aleinu')
  const list = page.locator('.sf-passages > li')
  await expect(list).toHaveCount(6)
  for (const ref of ['Isaiah 45:20', 'Isaiah 51:13', 'Deuteronomy 4:39', 'Isaiah 45:23', 'Exodus 15:18', 'Zechariah 14:9']) {
    await expect(page.locator('.sf-passages').getByRole('link', { name: ref, exact: true })).toHaveCount(1)
  }
  await page.getByRole('button', { name: 'The priestly blessing' }).click()
  await expect(list).toHaveCount(1)
  await expect(list.first()).toContainText('Numbers 6:24, Numbers 6:25, Numbers 6:26')
  await page.getByRole('button', { name: 'Mishnah Berakhot 1:3' }).click()
  // lying down; then walking on the way and lying down again, one stretch of the verse
  await expect(list).toHaveCount(2)
  await expect(page.locator('.sf-passages').getByRole('link', { name: 'Deuteronomy 6:7', exact: true })).toHaveCount(2)
  await expect(page.locator('.sf-passages').getByRole('link', { name: 'Deuteronomy 11:19', exact: true })).toHaveCount(2)
  // a modern sentence: nothing
  await page.getByLabel('Hebrew text').fill('אני הולך מחר לחנות לקנות לחם וחלב עם הילדים')
  await page.getByRole('button', { name: 'Find the sources' }).click()
  await expect(page.getByText('No phrase of the Bible was found in this text.')).toBeVisible()
})

test('other witnesses: the known readings, the Gerizim plus, the Samaritan Flood in 1307', async ({ page }) => {
  await page.goto('/witnesses')
  await expect(page.locator('.dv-verdict.fails')).toHaveCount(1) // the parallels claim, not borne out
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(1)
  await expect(page.locator('.wt-known .rc-found')).toHaveCount(8) // seven readings and the Flood
  await expect(page.locator('.wt-pluses li').first()).toContainText('Exodus 20:18')
  // Jared, Methuselah and Lamech die in the Samaritan's Flood year
  await expect(page.locator('.wt-chron tr.wt-flood')).toHaveCount(3)
  // the altar on Mount Gerizim after the Decalogue, word by word
  await page.goto('/witnesses?unit=v%3A2065')
  const sp = page.locator('.wt-verse .wt-text').first()
  await expect(sp.locator('.wt-added').filter({ hasText: 'בהרגריזימ' })).toHaveCount(1)
  await page.getByRole('link', { name: 'Read with the witnesses' }).click()
  await expect(page).toHaveURL(/\/read\/c%3A1%3A20\?layers=witnesses/)
  await expect(page.locator('.reader-text .wt-total').first()).toBeVisible()
})

test('rabbinic identifications: Hathach read as Daniel, with Megillah 15a and Bava Batra 4a on Sefaria', async ({ page }) => {
  await page.goto('/genealogy?p=1216')
  const card = page.getByRole('region', { name: 'Person' }).locator('.gt-identity')
  await expect(card.locator('p').first()).toContainText('The rabbis read as the same person as דניאל')
  await expect(card.getByRole('link', { name: /בבלי מגילה טו ע״א/ })).toHaveAttribute('href', 'https://www.sefaria.org/Megillah.15a.11?lang=he')
  await expect(card.getByRole('link', { name: /בבלי בבא בתרא ד ע״א/ })).toHaveCount(1)
  await expect(card.locator('.gt-proof')).toHaveCount(2) // Esther 4:5, Daniel 1:6
})

test('rabbinic reception: the law holds, divorce cited most, the Shema in Mishnah Berakhot 1:3', async ({ page }) => {
  await page.goto('/reception')
  await expect(page.locator('.dv-verdict.holds')).toHaveCount(3)
  await expect(page.locator('rect.rc-cell')).toHaveCount(929)
  await expect(page.locator('.rc-verses li').first()).toContainText('Deuteronomy 24:1')
  // Deuteronomy 6:7, known: Mishnah Berakhot 1:3 cites it
  await page.locator('.rc-known').getByRole('link', { name: 'Deuteronomy 6:7' }).click()
  await expect(page.getByRole('link', { name: /משנה ברכות א:ג/ })).toHaveAttribute('href', 'https://www.sefaria.org/Mishnah_Berakhot.1.3?lang=he')
  await page.getByRole('radio', { name: 'Bavli' }).click()
  await expect(page.locator('.rc-cites .rc-tag').first()).toHaveText('Bavli')
  await page.goto('/read/c%3A4%3A24?layers=reception')
  await expect(page.locator('.reader-text .rc-total').first()).toHaveText('143')
})

test('print and save: Jacob’s family as a poster, the map as an SVG, a synopsis on paper', async ({ page }) => {
  const text = async (d: import('@playwright/test').Download) => {
    const chunks: Buffer[] = []
    for await (const c of (await d.createReadStream()) as AsyncIterable<Buffer>) chunks.push(c)
    return Buffer.concat(chunks).toString('utf-8')
  }
  await page.goto('/genealogy?p=194')
  const panel = page.getByRole('region', { name: 'Person' })
  await panel.getByRole('button', { name: 'Open all below' }).click()
  const [poster] = await Promise.all([page.waitForEvent('download'), panel.getByRole('button', { name: 'Save as a poster (SVG)' }).click()])
  expect(poster.suggestedFilename()).toBe('family-tree-194.svg')
  const svg = await text(poster)
  expect(svg).toContain('<title>The family tree from יעקב</title>')
  for (const name of ['ראובן', 'יוסף', 'בנימין', 'דינה']) expect(svg).toContain(`>${name}</text>`)
  // the map as drawn: its points, no stylesheet classes, strokes kept thin
  await page.goto('/places')
  await expect(page.locator('.geo-pt').first()).toBeVisible()
  const [map] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Save as SVG' }).click()])
  const m = await text(map)
  expect((m.match(/<circle/g) ?? []).length).toBeGreaterThan(500)
  expect(m).not.toContain('class=')
  expect(m).toContain('vector-effect:non-scaling-stroke')
  // on paper: no menus or controls, the marks' legend kept, light from a dark screen
  await page.emulateMedia({ media: 'print', colorScheme: 'dark' })
  await page.goto('/synopses/13')
  await expect(page.locator('.syn-row').first()).toBeVisible()
  await expect(page.locator('.topbar')).toBeHidden()
  await expect(page.getByRole('button', { name: 'Print' })).toBeHidden()
  await expect(page.locator('.diff-legend')).toBeVisible()
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(255, 255, 255)')
  expect(await page.evaluate(() => getComputedStyle(document.querySelector('h1')!).color)).toBe('rgb(42, 34, 24)')
})

test('letters at equal skips: no more names in the Torah than its controls, and תורה at 50 from Genesis 1:1', async ({ page }) => {
  await page.goto('/els')
  await expect(page.getByText(/27 names at skips of 2 to 1,000 letters, forwards and backwards: 1,428,731 hits in 304,801 letters/)).toBeVisible()
  await expect(page.locator('.els-table').first().locator('.dlg-verdict', { hasText: 'does not hold' })).toHaveCount(0)
  await expect(page.locator('.els-terms tbody tr')).toHaveCount(27)
  await expect(page.locator('#known .dlg-verdict', { hasText: 'holds' })).toHaveCount(5)
  await expect(page.locator('#known tbody tr').first()).toContainText('19 times')
  await page.getByRole('radio', { name: 'Genesis' }).click()
  await expect(page.getByText(/78,063 letters/)).toBeVisible()
})

test('the main line: not borne out at paragraph openings, the five known pauses found, Genesis 3:1 in the reader', async ({ page }) => {
  await page.goto('/mainline')
  await expect(page.locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(page.getByText('The pauses the commentaries point to are found: 5 of 5.')).toBeVisible()
  await expect(page.locator('.precision-note summary')).toContainText('57% right')
  await page.goto('/read/c%3A0%3A3?layers=mainline')
  await expect(page.locator('.reader-text .ml-background').first()).toBeVisible()
})

test('the prophetic forms: every passage named in advance found, Isaiah’s first woe, the words boxed in the reader', async ({ page }) => {
  await page.goto('/prophetic')
  await expect(page.locator('.pf-known .dv-verdict')).toHaveText(['Found', 'Found', 'Found', 'Found'])
  await expect(page.getByText('Call narrative: 12 findings')).toBeVisible()
  await expect(page.locator('.precision-note summary')).toContainText('53% right')
  await page.goto('/prophetic?form=woe&book=11')
  await expect(page.locator('.pf-item').first().locator('.verse-ref')).toHaveText(/^Isaiah 1:4 – Isaiah 1:9$/)
  await page.goto('/read/c%3A11%3A5?layers=prophetic')
  await expect(page.locator('.reader-text .pf-woe').first()).toBeVisible()
})

test('the law codes: 18 of 21 known pairs, the slave release side by side', async ({ page }) => {
  await page.goto('/laws')
  await expect(page.getByText('18 of 21 pairs of passages found.')).toBeVisible()
  await expect(page.getByRole('rowheader', { name: 'Holiness Code' })).toBeVisible()
  await page.goto('/laws?pair=4')
  await expect(page.getByRole('heading', { name: 'Covenant Code beside Deuteronomic Code' })).toBeVisible()
  await expect(page.locator('.lw-side').first().locator('.verse-ref').first()).toHaveText('Exodus 21:2')
  await expect(page.locator('.lw-side .w-diff-substitution').first()).toBeVisible()
})

test("names built on God's name: not borne out for the same names, Jeremiah long, and its line on Names", async ({ page }) => {
  await page.goto('/language')
  const section = page.locator('section.theophoric')
  await expect(section.getByRole('heading', { level: 2 })).toHaveText('Names built on God’s name')
  await expect(section.locator('.dv-verdict')).toHaveText('Not borne out')
  await expect(section.getByRole('listitem').first()).toHaveText(/^Jeremiah: mostly long \(‑יהו\): 24% short of 279 endings · holds$/)
  await page.goto('/names?e=3414')
  await expect(page.getByText('Built on יה: ‑יהו 129× · ‑יה 18×.')).toBeVisible()
})

test('the gazetteer: Jerusalem is a town at 31.78° N, Abel names two places', async ({ page }) => {
  await page.goto('/names?e=3389')
  await expect(page.locator('.entity-sites li').first()).toContainText('31.78° N, 35.23° E')
  await expect(page.locator('.entity-sites li').first()).toContainText('Town')
  await page.goto('/names?e=59')
  await expect(page.locator('.entity-sites li')).toHaveCount(2)
})

test('Ctrl+K jumps to a chapter by reference and to a word by its form', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Control+k')
  // the jump box's own field: the unit page has a combobox of its own (Top k)
  const box = page.getByRole('dialog').getByRole('combobox')
  await box.fill('Ps 23')
  await expect(page.getByRole('option', { name: 'Psalms 23' })).toBeVisible()
  await box.press('Enter')
  await expect(page).toHaveURL(/\/unit\/c%3A26%3A23$/)
  await page.keyboard.press('Control+k')
  await box.fill('שָׁלוֹם')
  await page.getByRole('option', { name: /שלום.*7965/ }).click()
  await expect(page).toHaveURL(/\/lemma\/7965$/)
})

test('Jeremiah 25 names its places, hides Babylon in ששך, and Genesis 49 holds יבא שילה', async ({ page }) => {
  await page.goto('/unit/c%3A12%3A25')
  const bar = page.getByRole('navigation', { name: 'What the analyses found here' })
  await expect(bar.getByRole('link', { name: /places on the map, most named/ })).toHaveAttribute('href', '/places?unit=c%3A12%3A25')
  await bar.getByRole('link', { name: /read through atbash or albam/ }).click()
  await expect(page).toHaveURL(/\/ciphers\?unit=c%3A12%3A25/)
  await expect(page.locator('.cipher-hit').filter({ hasText: 'ששך' }).first()).toBeVisible()
  await page.goto('/unit/c%3A0%3A49')
  const gm = page.getByRole('navigation', { name: 'What the analyses found here' }).getByRole('link', { name: /the tradition.s values: .*יבא שילה/ })
  await expect(gm).toHaveAttribute('href', '/read/c%3A0%3A49?layers=gematria')
})

test('Ctrl+K opens the map at a place: Babylon, far off the land, and Zion as Jerusalem', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Control+k')
  const box = page.getByRole('dialog').getByRole('combobox')
  await box.fill('בבל')
  await expect(page.getByRole('option').first()).toContainText('Town')
  await box.press('Enter')
  await expect(page).toHaveURL(/\/places\?p=\d+$/)
  // the map has moved to it: its point inside the map
  const map = await page.getByRole('img', { name: /Places of the Bible on a map/ }).boundingBox()
  const pt = await page.locator('.geo-pt.selected').boundingBox()
  expect(pt!.x).toBeGreaterThan(map!.x)
  expect(pt!.x + pt!.width).toBeLessThan(map!.x + map!.width)
  expect(pt!.y).toBeGreaterThan(map!.y)
  expect(pt!.y + pt!.height).toBeLessThan(map!.y + map!.height)
  await page.keyboard.press('Control+k')
  await box.fill('ציון')
  await expect(page.getByRole('option', { name: /ירושלם.*Town/ })).toBeVisible()
})

test('the Hebrew interface is right to left, persists and loads every page cleanly', async ({ page }) => {
  test.setTimeout(120_000)
  const errors = collectErrors(page)
  await page.goto('/')
  await page.getByRole('button', { name: /Display/ }).click()
  await page.getByRole('radio', { name: 'עב' }).click()
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.locator('h1').first()).toHaveText('עיון')
  for (const [path] of PAGES) {
    await page.goto(path)
    await expect(page.locator('h1').first()).not.toBeEmpty()
    await expect(page.locator('.status.error')).toHaveCount(0)
    // no English words left in the headings
    expect(await page.locator('h1, h2').allTextContents()).not.toContainEqual(expect.stringMatching(/\b(the|of|and|in)\b/))
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(1)
  expect(errors).toEqual([])
})

test('the Hebrew interface has no serious accessibility violations', async ({ page }) => {
  test.setTimeout(480_000) // axe on every listed page
  await page.addInitScript(() => localStorage.setItem('bsim.locale', 'he'))
  await checkA11y(page)
})

// M168: on the real data (every nav entry, the notebook and the labels among them)
for (const locale of ['en', 'he'] as const) {
  test(`the top bar is one row from 1280px (${locale})`, async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop')
    await page.addInitScript((l) => localStorage.setItem('bsim.locale', l), locale)
    // 1280px, and the same window with a scrollbar's width taken from it
    for (const width of [1280, 1263]) {
      await page.setViewportSize({ width, height: 800 })
      await page.goto('/')
      await expect(page.locator('h1').first()).not.toBeEmpty()
      const oneRow = await page.evaluate(() => {
        const boxes = [...document.querySelector('.topbar')!.children].map((c) => c.getBoundingClientRect()).filter((r) => r.width > 0)
        return Math.max(...boxes.map((r) => r.top)) < Math.min(...boxes.map((r) => r.bottom))
      })
      expect(oneRow, `${width}px`).toBe(true)
    }
  })
}

test('the theme: dark by choice on a light system, kept over a reload', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  await page.getByRole('button', { name: /Display/ }).click()
  await page.getByRole('radio', { name: 'Dark' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(23, 20, 15)')
})
