// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { BasemapResponse, Book, PlaceDetail, PlaceSite, PlacesResponse, PlaceVersesResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PlacesPage } from './PlacesPage'

const BOOKS = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
] as Book[]
const site = (place_id: number, he: string, kind: PlaceSite['kind'], lat: number | null, lon: number | null, n: number): PlaceSite => ({
  place_id,
  he,
  kind,
  lat,
  lon,
  score: 500,
  coord_source: 'openbible',
  runner_up: null,
  n_identifications: 1,
  n_verses: n,
  n_here: null,
  first_vid: 10,
  lemmas: ['3389'],
})
const PLACES: PlacesResponse = {
  meta: { places: 3, located: 2 },
  kind: null,
  book: null,
  unit: null,
  items: [site(1, 'ירושלם', 'town', 31.78, 35.23, 600), site(2, 'ירדן', 'water', 31.76, 35.56, 160), site(3, 'נוד', null, null, null, 1)],
}
const BASEMAP: BasemapResponse = {
  box: [-10, 5, 70, 47],
  shapes: [
    { layer: 'land', rings: [[[34, 29], [37, 29], [37, 34], [34, 34], [34, 29]]] },
    { layer: 'lakes', rings: [[[35.4, 31.2], [35.6, 31.2], [35.6, 31.8], [35.4, 31.2]]] },
    { layer: 'rivers', rings: [[[35.5, 32.7], [35.55, 31.8]]] },
  ],
}
const verse = { verse_id: 10, book_id: 5, chapter: 10, verse: 1, ref: 'Joshua 10:1', ref_he: 'יהושע י:א', text_display: 'מֶלֶךְ יְרוּשָׁלַ͏ִם', display_tokens: ['מֶלֶךְ', 'יְרוּשָׁלַ͏ִם'], ketiv_note: null }
const DETAIL: PlaceDetail = {
  place: site(1, 'ירושלם', 'town', 31.78, 35.23, 600),
  first_label: 'Joshua 10:1',
  first_label_he: 'יהושע י:א',
  names: [{ lemma: '3389', he: 'ירושלם', n_verses: 600 }],
  by_book: [{ book_id: 1, n_verses: 3 }],
  partners: [{ place_id: 2, he: 'ירדן', kind: 'water', n_verses: 4 }],
}
const VERSES: PlaceVersesResponse = { place_id: 1, total: 1, offset: 0, limit: 10, items: [{ verse, tokens: [1] }] }

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', places: PlacesResponse = PLACES) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/books'
          ? BOOKS
          : p === '/api/places'
            ? places
            : p === '/api/places/basemap'
              ? BASEMAP
              : p === '/api/places/1'
                ? DETAIL
                : p === '/api/places/1/verses'
                  ? VERSES
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
            <Route path="/places" element={<PlacesPage />} />
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

describe('PlacesPage', () => {
  it('draws the region with the located places, sized and coloured by kind', async () => {
    const { container } = renderAt('/places')
    expect(await screen.findByText('3 places named, 2 on the map.')).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.geo-land')).toHaveLength(1))
    expect(container.querySelectorAll('.geo-lake')).toHaveLength(1)
    expect(container.querySelectorAll('.geo-river')).toHaveLength(1)
    const pts = container.querySelectorAll('.geo-pt')
    expect([...pts].map((p) => p.getAttribute('class'))).toEqual(['geo-pt kind-town', 'geo-pt kind-water'])
    expect(Number(pts[0].getAttribute('r'))).toBeGreaterThan(Number(pts[1].getAttribute('r')))
    expect([...container.querySelectorAll('.geo-label')].map((t) => t.textContent)).toEqual(['ירושלם', 'ירדן'])
    // the list holds the unlocated place too
    expect(container.querySelectorAll('.place-list li')).toHaveLength(3)
  })

  it('opens a place: its names, books, the places named with it and its verses', async () => {
    const { container } = renderAt('/places')
    fireEvent.click(await screen.findByRole('button', { name: 'ירושלם' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/places?p=1'))
    expect(await screen.findAllByRole('link', { name: 'Joshua 10:1' })).toHaveLength(2)
    expect(container.querySelector('.place-panel')?.textContent).toContain('31.78° N, 35.23° E · identification voted 500 / 1,000')
    expect(container.querySelector('.place-panel .name-chip')?.getAttribute('href')).toBe('/names?e=3389')
    await waitFor(() => expect(container.querySelectorAll('.place-verse .w-focus')).toHaveLength(1))
    expect(container.querySelector('.geo-pt.selected')).not.toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'ירדן' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/places?p=2'))
  })

  it('filters by kind, book and chapter', async () => {
    const { calls } = renderAt('/places')
    fireEvent.click(await screen.findByRole('radio', { name: 'Water' }))
    await waitFor(() => expect(calls.some((c) => c.includes('kind=water'))).toBe(true))
    fireEvent.change(screen.getByRole('combobox', { name: 'Book' }), { target: { value: '1' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/places?kind=water&book=1'))
    fireEvent.change(await screen.findByRole('combobox', { name: 'Chapter' }), { target: { value: '3' } })
    await waitFor(() => expect(calls.some((c) => c.includes('unit=c%3A1%3A3'))).toBe(true))
  })

  it('steps through the places with the keyboard and zooms', async () => {
    const { container } = renderAt('/places')
    const map = await screen.findByRole('img', { name: /Places of the Bible on a map/ })
    const before = map.getAttribute('viewBox')
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }))
    await waitFor(() => expect(map.getAttribute('viewBox')).not.toBe(before))
    fireEvent.keyDown(map, { key: 'ArrowRight' })
    expect(container.querySelector('.geo-map figcaption')?.textContent).toBe('ירושלם: 600 verses')
    fireEvent.keyDown(map, { key: 'Enter' })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/places?p=1'))
  })

  it('reads in Hebrew', async () => {
    renderAt('/places', 'he')
    expect(await screen.findByRole('heading', { name: 'מקומות על המפה' })).toBeTruthy()
    expect(await screen.findByText('3 מקומות נזכרים, 2 מהם על המפה.')).toBeTruthy()
  })

  it('says when the build has no places', async () => {
    renderAt('/places', 'en', { meta: {}, kind: null, book: null, unit: null, items: [] })
    expect(await screen.findByText(/Not computed in this build: run `bsim places`/)).toBeTruthy()
  })
})
