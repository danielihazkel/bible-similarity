// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SegmentCurve, SegmentGapsResponse, SegmentsResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { DivisionsPage } from './DivisionsPage'

const group = (score: number, n = 10) => ({ n, score, null: 0.5, p: 0.001, lex: score - 0.02, sem: score + 0.01 })
const SEGMENTS: SegmentsResponse = {
  meta: {
    window: 4,
    window_grid: { '2': 0.5666, '4': 0.5678 },
    gaps: 100,
    groups: { mam_pe: group(0.65, 1565), mam_samekh: group(0.55), chapter_only: group(0.62), unmarked: group(0.48) },
    contrasts: {
      pe_samekh: { a: 0.65, b: 0.55, diff: 0.1, p: 0.001 },
      chapter: { a: 0.73, b: 0.62, diff: 0.11, p: 0.002 },
    },
    calibration: { n: 10, score: 0.507, null: 0.5, p: 0.065, lex: null, sem: null },
    seams: { n: 241, share: 0.68, null: 0.55, p: 0.001, near: 2 },
    agreement: { mam: { books: 38, pk: 0.399, pk_null: 0.463, wd: 0.47, wd_null: 0.52, better: 18 } },
    kinds: { turn: 1, cut: 1, quiet: 0 },
  },
  books: [],
}
const verse = (id: number, text: string): Verse => ({
  verse_id: id,
  book_id: 27,
  chapter: 5,
  verse: id,
  ref: `Hosea 5:${id}`,
  ref_he: 'הושע',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const GAPS = (kind: 'turn' | 'cut' | null, unit: string | null): SegmentGapsResponse => ({
  kind,
  book: null,
  unit,
  total: 1,
  offset: 0,
  limit: 25,
  items: [
    {
      verse_id: 16,
      book_id: 14,
      label: 'Hosea 6:1',
      label_he: 'הושע ו:א',
      score: 0.09,
      lex: 0.2,
      sem: 0.74,
      mam: null,
      oshb: null,
      chapter: true,
      seam: false,
      kind: 'cut',
      verses: [verse(15, 'אֵלֵךְ אָשׁוּבָה'), verse(16, 'לְכוּ וְנָשׁוּבָה')],
    },
  ],
})
const CURVE: SegmentCurve = {
  book_id: 14,
  points: [
    { verse_id: 15, chapter: 5, verse: 15, score: 0.2, mam: null, oshb: null, chapter_start: false, seam: false, kind: null },
    { verse_id: 16, chapter: 6, verse: 1, score: 0.09, mam: null, oshb: null, chapter_start: true, seam: false, kind: 'cut' },
    { verse_id: 17, chapter: 6, verse: 2, score: 0.8, mam: 'pe', oshb: 'pe', chapter_start: false, seam: false, kind: null },
  ],
  agreement: [{ book_id: 14, ref: 'mam', k: 5, pk: 0.448, pk_null: 0.477, pk_p: 0.322, wd: 0.45, wd_null: 0.5, wd_p: 0.17 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', segments: SegmentsResponse = SEGMENTS) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const body =
        u.pathname === '/api/books'
          ? [{ book_id: 14, name: 'Hosea', he_name: 'הושע', osis: 'Hos', section: 'Prophets', n_chapters: 14 }]
          : u.pathname === '/api/segments'
            ? segments
            : u.pathname === '/api/segments/gaps'
              ? GAPS((u.searchParams.get('kind') as 'turn' | 'cut' | null) ?? null, u.searchParams.get('unit'))
              : u.pathname === '/api/segments/book/14'
                ? CURVE
                : u.pathname.startsWith('/api/unit/')
                  ? { unit: { unit_id: 'c:14:6', unit_type: 'chapter', label_en: 'Hosea 6', label_he: 'הושע ו', book_id: 14, start_verse_id: 16, end_verse_id: 26, n_verses: 11, marker: null }, verses: [], parents: [], prev_id: null, next_id: null }
                  : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/divisions" element={<DivisionsPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { ...r, calls }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('DivisionsPage', () => {
  it('shows the tests and the unmarked turns, then switches list', async () => {
    const { calls } = renderAt('/divisions')
    expect(await screen.findByText('Open paragraph פ (MAM)')).toBeTruthy()
    expect(screen.getByText(/Open paragraphs \(פ\) score 0.65, closed ones \(ס\) 0.55/)).toBeTruthy()
    expect(screen.getByText(/68% of the style seams lie within 2 verses/)).toBeTruthy()
    expect(screen.getByText(/in 18 of 38 books/)).toBeTruthy()
    expect(screen.getByText(/score 0.51 \(p 0.07\)/)).toBeTruthy()
    const link = await screen.findByRole('link', { name: 'Hosea 6:1' })
    expect(link.getAttribute('href')).toBe('/unit/v%3A16')
    expect(calls).toContain('/api/segments/gaps?kind=turn&limit=25&offset=0')
    fireEvent.click(screen.getByRole('radio', { name: 'Chapters in running text' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/divisions?kind=cut'))
    await waitFor(() => expect(calls).toContain('/api/segments/gaps?kind=cut&limit=25&offset=0'))
  })

  it("draws a book's boundaries and narrows to a chapter", async () => {
    const { container } = renderAt('/divisions?book=14')
    await screen.findByRole('img', { name: /The score of every boundary in Hosea/ })
    expect(container.querySelectorAll('.division-chart .div-pe')).toHaveLength(1)
    expect(container.querySelectorAll('.division-chart .div-none')).toHaveLength(2)
    expect(screen.getByText(/MAM paragraphs: Pk 0.45 against 0.48/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Chapter'), { target: { value: '6' } })
    await waitFor(() => expect(container.querySelectorAll('.division-chart line[stroke-width]')).toHaveLength(2))
  })

  it('lists a unit’s points of every kind, in Hebrew', async () => {
    const { calls } = renderAt('/divisions?unit=c:14:6', 'he')
    expect(await screen.findByRole('heading', { name: 'היכן הטקסט מתחלק' })).toBeTruthy()
    await screen.findByRole('link', { name: 'הושע ו:א' })
    expect(calls).toContain('/api/segments/gaps?unit=c%3A14%3A6&limit=25&offset=0')
    expect(screen.getByText('פרקים בתוך טקסט רציף', { selector: '.hit-head span' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'כל הסוגים' }).getAttribute('aria-checked')).toBe('true')
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/divisions', 'en', { meta: {}, books: [] })
    expect(await screen.findByText(/run `bsim segments`/)).toBeTruthy()
  })
})
