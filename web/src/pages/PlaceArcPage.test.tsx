// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ArcChapter, PlaceArcBookResponse, PlaceArcResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PlaceArcPage } from './PlaceArcPage'

const chapter = (book_id: number, n: number, he: string, ch: Partial<ArcChapter> = {}): ArcChapter => ({
  book_id,
  chapter: n,
  unit_id: `c:${book_id}:${n}`,
  label_en: `${book_id === 0 ? 'Genesis' : 'Jeremiah'} ${n}`,
  label_he: `${book_id === 0 ? 'בראשית' : 'ירמיהו'} ${n}`,
  first_vid: n * 10,
  n_mentions: 4,
  n_places: 3,
  lat: 31.5,
  lon: 35.2,
  spread_km: 40,
  reach_km: 30,
  step_km: null,
  prev_chapter: null,
  top_place: { place_id: 7, he, kind: 'town' },
  oracle: false,
  ...ch,
})
const end = (label_en: string, label_he: string, unit_id: string, lat: number, lon: number, from: number, to: number) => ({
  label_en,
  label_he,
  unit_id,
  n_mentions: 9,
  n_places: 5,
  lat,
  lon,
  spread_km: 300,
  top_place: null,
  to_from_region: from,
  to_to_region: to,
  nearest: 'canaan',
})
const ARC: PlaceArcResponse = {
  meta: { shuffles: 9999, alpha: 0.05, min_mentions: 2, min_chapters: 3 },
  arc: { chapters: 929, placed: 556, books: 31, steps: 516, mean_step: 223.2, null_mean: 267.1, p: 0.0001, books_held: 9 },
  books: [
    { book_id: 0, name: 'Genesis', he_name: 'בראשית', chapters: 50, n: 35, mean_step: 228, null_mean: 354.6, ratio: 0.643, p: 0.0002 },
    { book_id: 12, name: 'Jeremiah', he_name: 'ירמיהו', chapters: 52, n: 47, mean_step: 320.7, null_mean: 436.3, ratio: 0.735, p: 0.0004 },
    { book_id: 17, name: 'Obadiah', he_name: 'עובדיה', chapters: 1, n: 1, mean_step: null, null_mean: null, ratio: null, p: null },
  ],
  moves: [
    { key: 'abram', from_region: 'mesopotamia', to_region: 'canaan', start: end('Genesis 11', 'בראשית יא', 'c:0:11', 32.9, 43.0, 135, 743), end: end('Genesis 12', 'בראשית יב', 'c:0:12', 32.6, 34.6, 916, 106), km: 785.8, holds: true },
    { key: 'exile', from_region: 'canaan', to_region: 'mesopotamia', start: null, end: null, km: null, holds: null },
  ],
  oracles: {
    labels_en: ['Amos 1–2', 'Isaiah 13–23'],
    labels_he: ['עמוס א–ב', 'ישעיהו יג–כג'],
    chapters: 27,
    placed: 27,
    alpha: 0.025,
    spread: { n: 27, n_other: 143, observed: 411.6, other: 295.5, median: 424.7, other_median: 225.4, null_mean: 314.6, p: 0.0738 },
    reach: { n: 27, n_other: 143, observed: 330.8, other: 275.4, median: 260.4, other_median: 165.5, null_mean: 284.5, p: 0.191 },
    holds: false,
    items: [chapter(12, 48, 'מואב', { oracle: true, spread_km: 26.2, reach_km: 66.4 })],
  },
}
const BOOK = (id: number): PlaceArcBookResponse => ({
  book: ARC.books.find((b) => b.book_id === id)!,
  items:
    id === 0
      ? [chapter(0, 2, 'עדן'), chapter(0, 4, 'נוד', { step_km: 120.4, prev_chapter: 2 }), chapter(0, 5, 'כנען', { step_km: 900, prev_chapter: 4 })]
      : [chapter(12, 46, 'מצרים', { oracle: true }), chapter(12, 47, 'עזה', { oracle: true, step_km: 266.9, prev_chapter: 46 })],
})

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', arc: PlaceArcResponse = ARC) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const id = p.match(/^\/api\/place-arc\/(\d+)$/)?.[1]
      const body = p === '/api/place-arc' ? arc : id != null ? BOOK(Number(id)) : p === '/api/places/basemap' ? { box: [0, 0, 1, 1], shapes: [] } : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/place-arc" element={<PlaceArcPage />} />
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

describe('PlaceArcPage', () => {
  it('sums up the arc and draws the first tested book', async () => {
    const { container, calls } = renderAt('/place-arc')
    expect(await screen.findByText(/556 of 929 chapters name places enough to be placed/)).toBeTruthy()
    expect(screen.getByText(/9 of the 31 books/)).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.pa-chapters li')).toHaveLength(3))
    expect(calls.some((c) => c.endsWith('/api/place-arc/0'))).toBe(true)
    const items = container.querySelectorAll('.pa-chapters li')
    // a step over an unplaced chapter names the chapter it comes from; the longest is marked
    expect(items[1].textContent).toContain('120 km from ch. 2')
    expect(items[2].className).toContain('long')
    expect(items[0].querySelector('a')?.getAttribute('href')).toBe('/unit/c%3A0%3A2')
    expect(container.querySelectorAll('.pa-book .geo-map circle')).toHaveLength(3)
    expect(container.querySelector('.pa-path')).toBeTruthy()
  })

  it('switches books from the table and the select', async () => {
    const { container } = renderAt('/place-arc')
    await screen.findByRole('heading', { name: 'The path of Genesis' })
    const rows = container.querySelectorAll('.pa-table tbody tr')
    expect(rows[2].textContent).toContain('too few')
    fireEvent.click(screen.getByRole('button', { name: 'Show Jeremiah on the map' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/place-arc?book=12'))
    expect(await screen.findByRole('heading', { name: 'The path of Jeremiah' })).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.pa-chapters li')).toHaveLength(2))
    expect(container.querySelectorAll('.pa-chapters .type-tag')).toHaveLength(2)
    fireEvent.change(screen.getByRole('combobox', { name: 'Book' }), { target: { value: '0' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/place-arc'))
  })

  it('lists the known moves and the oracles’ tests', async () => {
    const { container } = renderAt('/place-arc')
    await screen.findByRole('heading', { name: 'Known moves' })
    expect(screen.getByText('1 of 1 moves hold.')).toBeTruthy()
    const moves = container.querySelectorAll('.pa-moves tbody tr')
    expect(moves[0].textContent).toContain('Abram to Canaan')
    expect(moves[0].textContent).toContain('135 km from Mesopotamia, 743 km from Canaan')
    expect(moves[0].textContent).toContain('786 km')
    expect(moves[1].textContent).toContain('too few places')
    expect(container.querySelectorAll('.pa-moves .geo-map circle')).toHaveLength(2)
    expect(screen.getByText(/The oracles against the nations \(Amos 1–2, Isaiah 13–23\)/)).toBeTruthy()
    const tests = container.querySelectorAll('.pa-oracles .pa-table:not(.pa-oracle-chapters) tbody tr')
    expect(tests[0].textContent).toContain('412 km (median 425 km; 27 chapters)')
    expect(tests[0].textContent).toContain('0.07')
    expect(container.querySelector('.pa-oracle-chapters tbody tr')?.textContent).toContain('מואב')
  })

  it('reads in Hebrew', async () => {
    const { container } = renderAt('/place-arc', 'he')
    expect(await screen.findByRole('heading', { name: 'הקשת הגאוגרפית' })).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'המסלול של בראשית' })).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.pa-chapters li')).toHaveLength(3))
    expect(container.querySelectorAll('.pa-chapters li')[1].textContent).toContain('מפרק ב')
    expect(screen.getByText('הגלות לבבל')).toBeTruthy()
  })

  it('says when the build has no arc', async () => {
    renderAt('/place-arc', 'en', { meta: {}, arc: null, books: [], moves: [], oracles: null })
    expect(await screen.findByText(/Not computed in this build: run `bsim place-arc`/)).toBeTruthy()
  })
})
