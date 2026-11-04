// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, ReceptionCitationsResponse, ReceptionResponse, ReceptionVersesResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { bounds, parseCorpus, parts, step } from '../lib/reception'
import { ReceptionPage } from './ReceptionPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 2 },
  { book_id: 4, name: 'Deuteronomy', he_name: 'דברים', osis: 'Deut', section: 'Torah', n_chapters: 1 },
]
const counts = (mishnah: number, bavli: number) => ({ mishnah, tosefta: 0, bavli, yerushalmi: 0, total: mishnah + bavli })
const verse = (id: number, ref: string) => ({
  verse_id: id,
  book_id: id < 100 ? 0 : 4,
  chapter: 6,
  verse: 7,
  ref,
  ref_he: `ה${ref}`,
  text_display: 'וְשִׁנַּנְתָּם לְבָנֶיךָ',
  display_tokens: ['וְשִׁנַּנְתָּם', 'לְבָנֶיךָ'],
  ketiv_note: null,
})
const RECEPTION: ReceptionResponse = {
  citations: 40,
  verses_cited: 12,
  by_corpus: { mishnah: 10, tosefta: 0, bavli: 30, yerushalmi: 0 },
  passages: { mishnah: 5, tosefta: 0, bavli: 20, yerushalmi: 0 },
  dropped_long: 3,
  legal_verses: 1,
  narrative_verses: 2,
  ratios: { mishnah: 10.55, tosefta: 3.9, bavli: 6.78, yerushalmi: 7.84, total: 7.21 },
  law_p: 0.001,
  law_holds: true,
  gap: 3.76,
  gap_p: 0.001,
  gap_holds: true,
  known: [{ cite: 'Mishnah Berakhot 1:3', ref: 'Deuteronomy 6:7', verse: verse(150, 'Deuteronomy 6:7'), found: true }],
  known_holds: true,
  max_span: 3,
  shifts: 999,
  alpha: 0.05,
  books: [
    { book_id: 0, verses: 20, ...counts(2, 8) },
    { book_id: 4, verses: 10, ...counts(8, 22) },
  ],
  chapters: [
    { book_id: 0, chapter: 1, unit_id: 'c:0:1', verses: 10, ...counts(0, 0) },
    { book_id: 0, chapter: 2, unit_id: 'c:0:2', verses: 10, ...counts(2, 8) },
    { book_id: 4, chapter: 6, unit_id: 'c:4:6', verses: 10, ...counts(8, 22) },
  ],
}
const VERSES: ReceptionVersesResponse = {
  corpus: null,
  book: null,
  total: 1,
  offset: 0,
  limit: 25,
  items: [{ verse: verse(150, 'Deuteronomy 6:7'), ...counts(3, 9) }],
}
const CITES: ReceptionCitationsResponse = {
  unit_id: 'v:150',
  corpus: null,
  counts: counts(1, 1),
  total: 2,
  offset: 0,
  limit: 25,
  items: [
    { corpus: 'mishnah', title: 'Mishnah Berakhot', cite: 'Mishnah Berakhot 1:3', cite_he: 'משנה ברכות א:ג', url: 'https://www.sefaria.org/Mishnah_Berakhot.1.3?lang=he', verse_id: 150, ref: 'Deuteronomy 6:7', ref_he: 'דברים ו:ז' },
    { corpus: 'bavli', title: 'Berakhot', cite: 'Berakhot 2a:1', cite_he: 'בבלי ברכות ב ע״א', url: 'https://www.sefaria.org/Berakhot.2a.1?lang=he', verse_id: 150, ref: 'Deuteronomy 6:7', ref_he: 'דברים ו:ז' },
  ],
}
const UNIT = {
  unit: { unit_id: 'v:150', unit_type: 'verse', label_en: 'Deuteronomy 6:7', label_he: 'דברים ו:ז', book_id: 4, start_verse_id: 150, end_verse_id: 150, n_verses: 1, marker: null },
  verses: [verse(150, 'Deuteronomy 6:7')],
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
      if (missing && p === '/api/reception') return new Response(JSON.stringify({ detail: { code: 'stage_missing', stage: 'reception', message: 'x' } }), { status: 503 })
      const body = p === '/api/reception' ? RECEPTION : p === '/api/reception/verses' ? VERSES : p === '/api/reception/citations' ? CITES : p === '/api/books' ? BOOKS : p.startsWith('/api/unit/') ? UNIT : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/reception" element={<ReceptionPage />} />
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

describe('reception helpers', () => {
  it('steps the chapters by quantiles of the cited ones, apart for each corpus', () => {
    const b = bounds([0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(b).toEqual([3, 5, 7, 9])
    expect([0, 1, 3, 6, 9, 50].map((r) => step(r, b))).toEqual([0, 1, 2, 3, 5, 5])
    expect(bounds([0, 0])).toEqual([])
    expect(step(2, [])).toBe(1)
    expect(parseCorpus('bavli')).toBe('bavli')
    expect(parseCorpus('midrash')).toBe('all')
    expect(parts(counts(2, 7), { mishnah: 'Mishnah', tosefta: 'Tosefta', bavli: 'Bavli', yerushalmi: 'Yerushalmi' }, String)).toBe('Mishnah 2 · Bavli 7')
  })
})

describe('ReceptionPage', () => {
  it('shows the checks, the verses cited most, the chapters and the books', async () => {
    const { container } = renderAt('/reception')
    expect(await screen.findByText('The Mishnah cites the Torah’s law more than its stories')).toBeTruthy()
    expect(screen.getAllByText('Borne out')).toHaveLength(3)
    expect(screen.getByText(/10\.55 times as often/)).toBeTruthy()
    await waitFor(() => expect(container.querySelector('.rc-verses a')).not.toBeNull())
    const top = container.querySelector('.rc-verses a')!
    expect(top.getAttribute('href')).toContain('/reception?unit=v%3A150')
    expect(screen.getByText('Mishnah 3 · Bavli 9')).toBeTruthy()
    // the chapters: Genesis 1 not cited, the other two in steps
    await waitFor(() => expect(container.querySelectorAll('rect.rc-cell')).toHaveLength(3))
    expect(container.querySelector('rect.rc-cell')!.getAttribute('class')).toBe('rc-cell rc-0')
    // the books' table and the source's licence
    const table = screen.getByRole('table')
    expect(within(table).getByText('3.00')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'CC BY 4.0' }).getAttribute('href')).toContain('creativecommons.org/licenses/by/4.0')
  })

  it('reads one corpus, in the URL and in the request', async () => {
    renderAt('/reception')
    await screen.findByText('Checks fixed in advance')
    fireEvent.click(screen.getByRole('radio', { name: 'Bavli' }))
    expect(screen.getByTestId('loc').textContent).toBe('/reception?corpus=bavli')
    await waitFor(() => expect(calls.some((c) => c.includes('/api/reception/verses') && c.includes('corpus=bavli'))).toBe(true))
  })

  it('lists who cites a verse, each passage linked to Sefaria', async () => {
    renderAt('/reception?unit=v%3A150')
    expect(await screen.findByRole('heading', { name: 'Who cites Deuteronomy 6:7' })).toBeTruthy()
    const link = await screen.findByRole('link', { name: /משנה ברכות א:ג/ })
    expect(link.getAttribute('href')).toBe('https://www.sefaria.org/Mishnah_Berakhot.1.3?lang=he')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(screen.getByRole('link', { name: /בבלי ברכות ב ע״א/ })).toBeTruthy()
    expect(calls.some((c) => c.includes('/api/reception/citations?unit=v%3A150'))).toBe(true)
  })

  it('says when the stage did not run', async () => {
    renderAt('/reception', 'en', true)
    expect(await screen.findByText('The rabbinic citations were not computed in this build (run bsim reception).')).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/reception', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('בעיני חז״ל')
    expect(await screen.findByText('המשנה מצטטת את החוק שבתורה יותר מסיפוריה')).toBeTruthy()
  })
})
