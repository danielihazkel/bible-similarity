// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, WitnessesResponse, WitnessPlusesResponse, WitnessUnitResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { parseKind, variantsPer100, witnessUrl } from '../lib/witnesses'
import { WitnessesPage } from './WitnessesPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 11, name: 'Isaiah', he_name: 'ישעיה', osis: 'Isa', section: 'Prophets', n_chapters: 66 },
]
const verse = (id: number, ref: string, tokens: string[]) => ({
  verse_id: id,
  book_id: id < 1000 ? 0 : 11,
  chapter: 1,
  verse: 1,
  ref,
  ref_he: `ה${ref}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const ops = { spelling: 1, form: 2, substitution: 3, omitted: 1, added: 4, moved: 0 }
const DATA: WitnessesResponse = {
  samaritan: { verses: 5834, words: 82335, same: 72261, ...ops },
  scrolls: { scrolls: 262, verses: 11689, words: 144932, read: 44402, same: 34254, ...ops },
  plus_min: 3,
  max_unc: 1,
  sp_pluses: 89,
  parallel_verses: 374,
  plus_in_parallel: 0.0187,
  plus_elsewhere: 0.015,
  ratio: 1.25,
  null_mean: 1.55,
  p: 0.637,
  shifts: 999,
  alpha: 0.05,
  holds: false,
  known: [
    { witness: 'sp', ref: 'Exodus 20:14', verse: verse(7, 'Exodus 20:14', ['לֹא', 'תַחְמֹד']), plus: 20, reads: null, found: true, note: 'the altar on Mount Gerizim' },
    { witness: '1Qisaa', ref: 'Isaiah 53:11', verse: verse(1100, 'Isaiah 53:11', ['מֵעֲמַל']), plus: null, reads: 'אור', found: true, note: null },
  ],
  chronology_known: [{ event: 'flood', expected: 1307, year: 1307, holds: true }],
  known_holds: true,
  chronology: [
    { seq: 0, event: 'adam', name: 'אדם', death: false, verse_id: null, ref: null, ref_he: null, sp_value: null, sp_year: 0, mt_year: 0 },
    { seq: 12, event: 'jared.death', name: 'ירד', death: true, verse_id: 5, ref: 'Genesis 5:20', ref_he: 'בראשית ה:כ', sp_value: 847, sp_year: 1307, mt_year: 1422 },
    { seq: 20, event: 'flood', name: null, death: false, verse_id: 6, ref: 'Genesis 7:6', ref_he: 'בראשית ז:ו', sp_value: 600, sp_year: 1307, mt_year: 1656 },
  ],
  books: [{ kind: 'sp', book_id: 0, verses: 1533, words: 200, read: 200, pluses: 3, ...ops }],
  scroll_rows: [{ scroll: '1Qisaa', book_id: 11, first_vid: 1000, verses: 1290, words: 16888, read: 1000, same: 900, pluses: 4, ...ops }],
}
const PLUSES: WitnessPlusesResponse = {
  kind: 'sp',
  book: null,
  total: 1,
  offset: 0,
  limit: 25,
  items: [{ witness: 'sp', verse: verse(7, 'Exodus 20:14', ['לֹא', 'תַחְמֹד']), plus: 92, variants: 95 }],
}
const UNIT: WitnessUnitResponse = {
  unit_id: 'v:7',
  witnesses: ['sp', '4Q41'],
  total: 1,
  offset: 0,
  limit: 25,
  items: [
    {
      verse: verse(7, 'Exodus 20:14', ['לֹא', 'תַחְמֹד', 'בֵּית']),
      readings: [
        {
          witness: 'sp',
          n_words: 3,
          n_read: 3,
          plus: 1,
          variants: 2,
          words: [
            { t: 'לא', r: true, op: 'same', mt: 0 },
            { t: 'תחמוד', r: true, op: 'spelling', mt: 1 },
            { t: 'והיה', r: true, op: 'added', mt: null },
          ],
          missing: [2],
        },
        { witness: '4Q41', n_words: 1, n_read: 0, plus: 0, variants: 0, words: [{ t: 'לא', r: false, op: 'same', mt: 0 }], missing: [] },
      ],
    },
  ],
}
const U = {
  unit: { unit_id: 'v:7', unit_type: 'verse', label_en: 'Exodus 20:14', label_he: 'שמות כ:יד', book_id: 1, start_verse_id: 7, end_verse_id: 7, n_verses: 1, marker: null },
  verses: [verse(7, 'Exodus 20:14', ['לֹא'])],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

const calls: string[] = []

function renderAt(path: string, locale: 'en' | 'he' = 'en', missing = false) {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      if (missing && p === '/api/witnesses') return new Response(JSON.stringify({ detail: { code: 'stage_missing', stage: 'witnesses', message: 'x' } }), { status: 503 })
      const body = p === '/api/witnesses' ? DATA : p === '/api/witnesses/pluses' ? PLUSES : p === '/api/witnesses/unit' ? UNIT : p === '/api/books' ? BOOKS : p.startsWith('/api/unit/') ? U : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/witnesses" element={<WitnessesPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('witnesses helpers', () => {
  it('counts variants per 100 words read, spelling left out, and builds links', () => {
    expect(variantsPer100({ spelling: 50, form: 1, substitution: 2, omitted: 3, added: 4, moved: 0 }, 200)).toBe('5.0')
    expect(variantsPer100({ spelling: 0, form: 0, substitution: 0, omitted: 0, added: 0, moved: 0 }, 0)).toBe('—')
    expect(parseKind('scroll')).toBe('scroll')
    expect(parseKind('x')).toBe('sp')
    expect(witnessUrl({ unit: 'v:7' })).toBe('/witnesses?unit=v%3A7')
    expect(witnessUrl({ kind: 'sp' })).toBe('/witnesses')
  })
})

describe('WitnessesPage', () => {
  it('shows the checks, the pluses, both chronologies and the tables', async () => {
    const { container } = renderAt('/witnesses')
    expect(await screen.findByText('The Samaritan adds most where the Torah has a parallel')).toBeTruthy()
    expect(screen.getByText('Not borne out')).toBeTruthy()
    expect(screen.getByText('Borne out')).toBeTruthy()
    expect(screen.getByText(/1\.25 times, against 1\.55/)).toBeTruthy()
    expect(screen.getByText(/The Samaritan Flood in year 1,307 from Adam/)).toBeTruthy()
    // the pluses, linked to the comparison
    await waitFor(() => expect(container.querySelector('.wt-pluses a')).not.toBeNull())
    expect(container.querySelector('.wt-pluses a')!.getAttribute('href')).toBe('/witnesses?unit=v%3A7')
    expect(screen.getByText('92 words')).toBeTruthy()
    // the two chronologies: Jared dies in the Flood's year in the Samaritan
    const chron = container.querySelector('.wt-chron')!
    const jared = within(chron as HTMLElement).getByText(/ירד/).closest('tr')!
    expect(jared.className).toBe('wt-flood')
    expect(jared.textContent).toContain('1,422')
    expect(jared.textContent).toContain('−115')
    // the books and the scrolls, and the licence
    expect(screen.getAllByText('5.0').length).toBeGreaterThan(0)
    expect(container.querySelector('section[aria-labelledby="wt-scrolls"] tbody th')?.textContent).toBe('1Qisaa')
    expect(screen.getByRole('link', { name: 'CC BY-NC 4.0' }).getAttribute('href')).toContain('by-nc/4.0')
  })

  it('reads the scrolls’ pluses, in the URL and in the request', async () => {
    renderAt('/witnesses')
    await screen.findByText('Checks fixed in advance')
    fireEvent.click(screen.getByRole('radio', { name: 'Scrolls' }))
    expect(screen.getByTestId('loc').textContent).toBe('/witnesses?kind=scroll')
    await waitFor(() => expect(calls.some((c) => c.includes('/api/witnesses/pluses') && c.includes('kind=scroll'))).toBe(true))
  })

  it('compares a verse word by word: the changes marked, the unread bracketed, what is lacking', async () => {
    const { container } = renderAt('/witnesses?unit=v%3A7')
    expect(await screen.findByRole('heading', { name: 'The witnesses of Exodus 20:14' })).toBeTruthy()
    await waitFor(() => expect(container.querySelector('.wt-verse')).not.toBeNull())
    const v = container.querySelector('.wt-verse')!
    expect([...v.querySelectorAll('dt')].map((d) => d.textContent)).toEqual(['Masoretic', 'Samaritan', '4Q41'])
    expect(v.querySelector('.wt-spelling')!.textContent).toBe('תחמוד')
    expect(v.querySelector('.wt-text .wt-added')!.textContent).toBe('והיה')
    expect(v.querySelector('.wt-text .wt-unread')!.textContent).toBe('לא')
    expect(v.querySelector('.wt-omitted')!.textContent).toBe('בֵּית')
    expect(calls.some((c) => c.includes('/api/witnesses/unit?unit=v%3A7'))).toBe(true)
  })

  it('says when the stage did not run', async () => {
    renderAt('/witnesses', 'en', true)
    expect(await screen.findByText(/The other witnesses were not compared in this build/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/witnesses', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('עדי נוסח אחרים')
    expect(await screen.findByText('השומרוני מוסיף בעיקר היכן שיש לתורה מקבילה')).toBeTruthy()
  })
})
