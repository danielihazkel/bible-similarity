// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ChronologyResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { ChronologyPage } from './ChronologyPage'

const verse = (id: number, ref: string, refHe: string, tokens: string[]) => ({
  verse_id: id,
  book_id: 0,
  chapter: 5,
  verse: id,
  ref,
  ref_he: refHe,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const G53 = verse(3, 'Genesis 5:3', 'בראשית ה:ג', ['וַיְחִי', 'אָדָם', 'שְׁלֹשִׁים', 'וּמְאַת', 'שָׁנָה'])
const G55 = verse(5, 'Genesis 5:5', 'בראשית ה:ה', ['תְּשַׁע', 'מֵאוֹת', 'שָׁנָה', 'וּשְׁלֹשִׁים', 'שָׁנָה'])
const K151 = verse(9160, 'I Kings 15:1', 'מלכים א טו:א', ['וּבִשְׁנַת', 'שְׁמֹנֶה', 'עֶשְׂרֵה'])
const K159 = verse(9168, 'I Kings 15:9', 'מלכים א טו:ט', ['וּבִשְׁנַת', 'עֶשְׂרִים'])
const K1525 = verse(9184, 'I Kings 15:25', 'מלכים א טו:כה', ['בִּשְׁנַת', 'שְׁתַּיִם'])
const ev = (seq: number, event: string, year: number, extra: Partial<ChronologyResponse['events'][number]> = {}) => ({
  seq,
  event,
  name: null,
  from_event: null,
  verse: null,
  value: null,
  sign: 1,
  year,
  used: true,
  conflict: false,
  tok_first: null,
  tok_last: null,
  ...extra,
})
const king = (k: string, name: string, kingdom: 'judah' | 'israel', seq: number, reign: number, start: number, v = K151) => ({ king: k, name, kingdom, seq, verse: v, reign, short: reign === 0, start, am: 2964 + start })
const DATA: ChronologyResponse = {
  events: [
    ev(0, 'adam', 0, { name: 'אדם' }),
    ev(1, 'seth', 130, { name: 'שת', from_event: 'adam', verse: G53, value: 130, tok_first: 2, tok_last: 3 }),
    ev(2, 'adam.death', 930, { name: 'אדם', from_event: 'adam', verse: G55, value: 930, tok_first: 0, tok_last: 3 }),
    ev(3, 'flood', 1656, { from_event: 'seth', verse: G55, value: 1526 }),
    ev(4, 'flood', 1600, { from_event: 'adam', verse: G53, value: 1600, used: false, conflict: true }),
    ev(5, 'exodus', 2448, { from_event: 'flood', verse: G53, value: 792 }),
  ],
  lives: [
    { person: 'adam', name: 'אדם', born: 0, died: 930 },
    { person: 'seth', name: 'שת', born: 130, died: null },
  ],
  kings: [king('rehoboam', 'רחבעם', 'judah', 0, 17, 1), king('abijam', 'אבים', 'judah', 1, 3, 18), king('asa', 'אסא', 'judah', 2, 41, 21), king('jeroboam', 'ירבעם', 'israel', 0, 22, 1), king('nadab', 'נדב', 'israel', 1, 0, 23)],
  syncs: [
    { seq: 0, king: 'abijam', of: 'jeroboam', verse: K151, year: 18, t_judah: 17, t_israel: 18, agrees: null },
    { seq: 1, king: 'asa', of: 'jeroboam', verse: K159, year: 20, t_judah: 20, t_israel: 20, agrees: true },
    { seq: 2, king: 'nadab', of: 'asa', verse: K1525, year: 2, t_judah: 22, t_israel: 25, agrees: false },
  ],
  numbers: [
    { verse: G53, value: 130, tok_first: 2, tok_last: 3 },
    { verse: G55, value: 969, tok_first: 0, tok_last: 3 },
  ],
  conflicts: 1,
  known: [
    { event: 'flood', year: 1656, expected: 1656, holds: true },
    { event: 'exodus', year: 2448, expected: 2448, holds: true },
  ],
  known_holds: true,
  intervals: 2,
  agree: 1,
  rules: { judah: 'accession', israel: 'accession' },
  rule_counts: { 'accession/accession': 1, 'accession/non-accession': 0, 'non-accession/accession': 1, 'non-accession/non-accession': 0 },
  tolerance: 1,
  shuffles: 9999,
  alpha: 0.05,
  expected: 0.4,
  p: 0.0001,
  holds: true,
  absolute: 1,
  division: 2964,
  ends: { judah: 3026, israel: 2987 },
  tradition: { temple: 2928, division: 2964, destruction: 3338 },
  digits: {
    n: 2,
    hits: 1,
    share: 0.5,
    rest_n: 10,
    rest_share: 0.72,
    p: 0.6,
    uniform: 0.4,
    uniform_p: 0.64,
    compare_n: 17,
    compare_share: 0.647,
    by_digit: { '0': 1, '9': 1 },
    rest_by_digit: { '0': 5, '2': 2, '5': 3 },
    holds: false,
  },
  digits_chapter: 'Genesis 5',
  digits_compare: 'Genesis 11:10-26',
  digits_ends: [0, 2, 5, 7],
  digits_min: 10,
}

function renderAt(locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => (missing ? new Response(JSON.stringify({ detail: 'the chronology was not computed' }), { status: 404 }) : new Response(JSON.stringify(DATA)))),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={['/chronology']}>
          <Routes>
            <Route path="/chronology" element={<ChronologyPage />} />
          </Routes>
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ChronologyPage', () => {
  it('states the three checks', async () => {
    renderAt()
    const known = (await screen.findByRole('heading', { name: /The Flood, Abram and the Exodus/ })).closest('article')!
    expect(within(known).getByText('Borne out')).toBeTruthy()
    expect(known.textContent).toContain('The Flood 1656 (Seder Olam 1656); The Exodus 2448 (Seder Olam 2448).')
    const syncs = screen.getByRole('heading', { name: /synchronisms agree/ }).closest('article')!
    expect(syncs.textContent).toContain('1 of 2 intervals are, both kingdoms counting from the year after the accession, against 0.4')
    const digits = screen.getByRole('heading', { name: /end in 0, 2, 5 or 7/ }).closest('article')!
    expect(within(digits).getByText('Not borne out')).toBeTruthy()
    expect(digits.textContent).toContain('1 of the 2 year numbers of Genesis 5 do (50%), against 72%')
  })

  it('lists every date with the words its number was read from, and the conflict', async () => {
    const { container } = renderAt()
    await screen.findByText(/Where the text counts twice/)
    const rows = [...container.querySelectorAll('table.ch-events tbody tr')]
    expect(rows).toHaveLength(6)
    expect(rows[1].textContent).toBe('⁨שת⁩ born130⁨אדם⁩ born + 130שְׁלֹשִׁים וּמְאַתGenesis 5:3')
    expect(rows[4].className).toBe('ch-conflict')
    expect(rows[4].textContent).toContain('another year')
    expect(container.querySelector('.ch-conflicts')!.textContent).toBe('The Flood: 1656 the first way; 1600 counting ⁨אדם⁩ born + 1600. Genesis 5:3')
  })

  it('draws the lives, the reigns and a line for each synchronism', async () => {
    const { container } = renderAt()
    await screen.findByRole('img', { name: /Lifespans from Adam/ })
    expect(container.querySelectorAll('.ch-life')).toHaveLength(2)
    expect(container.querySelectorAll('.ch-life rect.ch-bar')).toHaveLength(1)
    expect([...container.querySelectorAll('.ch-mark-label')].map((x) => x.textContent)).toEqual(['The Flood 1656', 'The Exodus 2448'])
    expect(container.querySelectorAll('.ch-reign.judah')).toHaveLength(3)
    expect(container.querySelectorAll('.ch-reign.israel.odd')).toHaveLength(1)
    expect([...container.querySelectorAll('svg.ch-chart line.ch-sync')].map((l) => l.getAttribute('class'))).toEqual(['ch-sync first', 'ch-sync agrees', 'ch-sync differs'])
    const syncs = [...container.querySelectorAll('table.ch-syncs tbody tr')]
    expect(syncs.map((r) => r.lastElementChild!.textContent)).toEqual(['—', 'agrees', '−3 years'])
    expect(syncs[0].textContent).toContain('⁨אבים⁩ king in year 18 of ⁨ירבעם⁩')
    expect(container.querySelector('table.ch-rules tr.selected')!.textContent).toContain('1 / 2')
    expect(screen.getByText(/Seder Olam has the Temple destroyed in 3338/)).toBeTruthy()
  })

  it('counts Genesis 5’s last digits', async () => {
    const { container } = renderAt()
    await screen.findByRole('heading', { name: 'The numbers of Genesis 5' })
    const rows = [...container.querySelectorAll('table.ch-digits tbody tr')]
    expect(rows.map((r) => r.className)).toEqual(['ch-end', '', 'ch-end', '', '', 'ch-end', '', 'ch-end', '', ''])
    expect(rows[0].textContent).toBe('0150%')
    expect([...container.querySelectorAll('.ch-numbers li')].map((li) => li.className)).toEqual(['', 'ch-odd-end'])
    expect(screen.getByText(/Shem to Terah \(Genesis 11\): 65% of 17/)).toBeTruthy()
  })

  it('says when the stage did not run', async () => {
    renderAt('en', true)
    expect(await screen.findByText(/The chronology was not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    const { container } = renderAt('he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('מניין השנים של הכתוב')
    await screen.findByRole('heading', { name: 'שתי הממלכות' })
    expect(container.querySelector('table.ch-events tbody tr:nth-child(2) th')!.textContent).toBe('הולדת שת')
    expect(screen.getAllByText('מלכים א טו:א').length).toBeGreaterThan(0)
  })
})
