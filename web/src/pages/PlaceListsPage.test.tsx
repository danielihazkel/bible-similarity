// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DistrictDetail, PlaceList, PlaceListDetail, PlaceListsResponse, PlaceSite } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PlaceListsPage } from './PlaceListsPage'

const site = (place_id: number, he: string, lat: number, lon: number, score: number | null): PlaceSite => ({
  place_id,
  he,
  kind: 'town',
  lat,
  lon,
  score,
  coord_source: 'openbible',
  runner_up: null,
  n_identifications: 1,
  n_verses: 3,
  n_here: null,
  first_vid: 10,
  lemmas: ['1'],
})
const untested = { n: 2, path_km: null, null_mean: null, null_sd: null, p: null, short_km: null, order_score: null, hist: null }
const LIST: PlaceList = {
  key: 'num33',
  kind: 'itinerary',
  label_en: 'Numbers 33:3–49',
  label_he: 'במדבר לג:ג–מט',
  first_vid: 10,
  last_vid: 56,
  n_named: 4,
  all: { n: 3, path_km: 120.4, null_mean: 300, null_sd: 40, p: 0.0001, short_km: 100, order_score: 0.9, hist: { lo: 100, hi: 500, counts: [1, 4, 9, 3] } },
  sure: untested,
}
const GEN10: PlaceList = { ...LIST, key: 'gen10', kind: 'nations', label_en: 'Genesis 10:1–32', label_he: 'בראשית י:א–לב', all: { ...LIST.all, p: 0.2 } }
const verse = (verse_id: number) => ({ verse_id, label_en: `Numbers 33:${verse_id}`, label_he: `במדבר לג:${verse_id}` })
const DETAIL: PlaceListDetail = {
  list: LIST,
  steps: [
    { pos: 1, place: site(1, 'רעמסס', 30.8, 31.8, 514), verse: verse(3), km: null, sure: true, short_pos: 1 },
    { pos: 2, place: site(2, 'סכות', 30.5, 32.1, 278), verse: verse(5), km: 40.2, sure: false, short_pos: 3 },
    { pos: 3, place: site(3, 'אתם', 30.4, 32.3, 54), verse: verse(6), km: 80.2, sure: false, short_pos: 2 },
  ],
}
const district = (d: number, n: number, p: number | null) => ({
  district: d,
  label_en: `Joshua 15:${d}`,
  label_he: `יהושע טו:${d}`,
  first_vid: d,
  last_vid: d,
  all: { n, within_km: p == null ? null : 10, null_mean: p == null ? null : 40, p },
  sure: null,
})
const GROUPING = {
  key: 'judah',
  n_named: 3,
  all: { n: 3, districts: 2, within_km: 10, null_mean: 40, p: 0.001, all_km: 30, nearest_same: 0.67 },
  sure: { n: 1, districts: null, within_km: null, null_mean: null, p: null, all_km: null, nearest_same: null },
  districts: [district(1, 2, 0.01), district(2, 1, null)],
}
const LISTS: PlaceListsResponse = {
  meta: { shuffles: 9999, alpha: 0.05, sure_score: 500, order: { all: { n: 2, held: 1 }, sure: { n: 0, held: 0 } } },
  lists: [GEN10, LIST],
  groupings: [GROUPING, { ...GROUPING, key: 'tribes' }],
}
const DISTRICTS: DistrictDetail = {
  grouping: GROUPING,
  towns: [
    { district: 1, place: site(4, 'צרעה', 31.77, 34.98, 856), verse: verse(33), sure: true },
    { district: 1, place: site(5, 'אשתאול', 31.78, 35.0, 229), verse: verse(33), sure: false },
    { district: 2, place: site(6, 'לכיש', 31.56, 34.85, 500), verse: verse(39), sure: true },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', lists: PlaceListsResponse = LISTS) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/place-lists'
          ? lists
          : p === '/api/place-lists/num33' || p === '/api/place-lists/gen10'
            ? { ...DETAIL, list: p.endsWith('gen10') ? GEN10 : LIST }
            : p.startsWith('/api/place-districts/')
              ? { ...DISTRICTS, grouping: { ...GROUPING, key: p.split('/').pop() } }
              : p === '/api/places/basemap'
                ? { box: [-10, 5, 70, 47], shapes: [] }
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
            <Route path="/place-lists" element={<PlaceListsPage />} />
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

describe('PlaceListsPage', () => {
  it('tables each list against random orders and opens the first', async () => {
    const { container } = renderAt('/place-lists')
    expect(await screen.findByText(/1 of 2 lists make a shorter path than random orders of their places \(9,999 orders each\)/)).toBeTruthy()
    const rows = container.querySelectorAll('.pls-table')[0].querySelectorAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].textContent).toContain('Table of nations')
    expect(rows[0].getAttribute('aria-current')).toBe('true')
    expect(rows[1].textContent).toContain('120 km')
    expect(rows[1].textContent).toContain('3 of 4')
    expect(rows[1].textContent).toContain('90%')
    expect(rows[1].querySelector('.dlg-verdict')?.textContent).toBe('holds')
    expect(rows[0].querySelector('.dlg-verdict')?.textContent).toBe('does not hold')
    expect(rows[1].textContent).toContain('2 places: too few')
    expect(await screen.findByRole('heading', { name: 'The path of Genesis 10:1–32' })).toBeTruthy()
  })

  it('draws a list as a path with its steps, the longest marked', async () => {
    const { container } = renderAt('/place-lists?list=num33')
    expect(await screen.findByRole('heading', { name: 'The path of Numbers 33:3–49' })).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.pls-detail .geo-pt')).toHaveLength(3))
    expect(container.querySelector('.pls-path.text')).not.toBeNull()
    // a short list: numbers and names on the map
    expect([...container.querySelectorAll('.pls-detail .geo-label')].map((x) => x.textContent).sort()).toEqual(['1 רעמסס', '2 סכות', '3 אתם'])
    const steps = container.querySelectorAll('.pls-steps li')
    expect([...steps].map((s) => s.getAttribute('value'))).toEqual(['1', '2', '3'])
    expect(steps[0].querySelector('.type-tag')?.textContent).toBe('sure')
    expect(steps[2].className).toContain('long')
    expect(container.querySelector('.pls-hist svg')?.getAttribute('aria-label')).toContain('120 km')
    expect(container.querySelectorAll('.pls-bar')).toHaveLength(4)
    fireEvent.click(screen.getByRole('radio', { name: 'A short path' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/place-lists?list=num33&show=short'))
    expect(container.querySelector('.pls-path.short')).not.toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'סכות' }))
    expect(container.querySelector('.pls-steps li.on')?.textContent).toContain('סכות')
  })

  it('switches the list from the table', async () => {
    renderAt('/place-lists')
    fireEvent.click(await screen.findByRole('button', { name: 'Open Numbers 33:3–49' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/place-lists?list=num33'))
  })

  it('shows Joshua’s districts coloured on the map with their tests', async () => {
    const { container, calls } = renderAt('/place-lists')
    expect(await screen.findByText(/3 towns in 2 districts: two towns of one district lie 10 km apart on average, against 40 km/)).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.pls-districts .geo-pt')).toHaveLength(3))
    const fills = [...container.querySelectorAll('.pls-districts .geo-pt')].map((c) => (c as SVGElement).style.fill)
    expect(new Set(fills).size).toBe(2)
    const rows = container.querySelectorAll('.pls-districts tbody tr')
    expect(rows[0].textContent).toContain('Joshua 15:1')
    expect(rows[1].textContent).toContain('one town')
    fireEvent.click(screen.getByRole('radio', { name: 'The tribes’ towns (Joshua 18–19)' }))
    await waitFor(() => expect(calls.some((c) => c.includes('/place-districts/tribes'))).toBe(true))
    expect(screen.getByTestId('loc').textContent).toBe('/place-lists?group=tribes')
  })

  it('reads in Hebrew', async () => {
    renderAt('/place-lists', 'he')
    expect(await screen.findByRole('heading', { name: 'רשימות המקומות על פני הארץ' })).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'המסלול של בראשית י:א–לב' })).toBeTruthy()
    expect(screen.getByText(/1 מתוך 2 רשימות יוצרות מסלול קצר/)).toBeTruthy()
  })

  it('says when the build has no lists', async () => {
    renderAt('/place-lists', 'en', { meta: {}, lists: [], groupings: [] })
    expect(await screen.findByText(/Not computed in this build: run `bsim place-lists`/)).toBeTruthy()
  })
})
