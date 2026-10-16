// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DecayTest, PlaceLinkPair, PlaceLinkPairsResponse, PlaceLinksResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PlaceLinksPage } from './PlaceLinksPage'

const site = (place_id: number, he: string, lat: number, lon: number) => ({ place_id, he, kind: 'town' as const, lat, lon })
const DAN = site(52, 'דן', 33.25, 35.65)
const BEERSHEBA = site(60, 'באר שבע', 31.24, 34.84)
const BABYLON = site(12, 'בבל', 32.54, 44.42)
const pair = (a: ReturnType<typeof site>, b: ReturnType<typeof site>, g2: number, km: number, lead_rank: number | null): PlaceLinkPair => ({
  a,
  b,
  n_together: 9,
  n_a: 56,
  n_b: 33,
  expected: 0.08,
  g2,
  km,
  lead_rank,
})
const test_ = (rho: number, p: number): DecayTest => ({ places: 277, pairs: 510, rho, null_mean: -0.001, null_q05: -0.14, null_q95: 0.13, p, median_km: 68, verses: 23206 })
const bins = [
  { bin: 1, lo_km: 0, hi_km: 10, pairs: 1340, linked: 85, share: 0.0634, median_g2: 28.03 },
  { bin: 2, lo_km: 10, hi_km: null, pairs: 3555, linked: 79, share: 0.0222, median_g2: 26.89 },
]
const DATA: PlaceLinksResponse = {
  meta: { shuffles: 9999, alpha: 0.05, min_together: 2, sure_score: 500, far_km: 150, top: 10, far_pairs: 149 },
  lists_en: ['Genesis 10', 'Numbers 33–34'],
  lists_he: ['בראשית י', 'במדבר לג–לד'],
  variants: [
    { variant: 'all', test: test_(-0.3189, 0.0001), bins },
    { variant: 'sure', test: { places: null, pairs: 2, rho: null, null_mean: null, null_q05: null, null_q95: null, p: null, median_km: null, verses: null }, bins: [] },
    { variant: 'no_lists', test: test_(-0.2969, 0.0003), bins: [{ ...bins[0], linked: 56, share: 0.0717 }] },
  ],
  known: [{ a: 'דן', b: 'באר שבע', found: true, pair: pair(DAN, BEERSHEBA, 71.4, 235.6, 3), rank: 3, holds: true }],
  leads: [pair(BABYLON, site(29, 'כשדים', 30.96, 46.1), 187.1, 237.1, 1), pair(DAN, BEERSHEBA, 71.4, 235.6, 3)],
  scatter: [
    { km: 5, g2: 30, far: false },
    { km: 235.6, g2: 71.4, far: true },
  ],
}
const PAIRS: PlaceLinkPairsResponse = { place: null, sort: 'g2', far: false, total: 1, offset: 0, limit: 25, items: [pair(DAN, BEERSHEBA, 71.4, 235.6, 3)] }

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: PlaceLinksResponse = DATA) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/place-links' ? data : p === '/api/place-links/pairs' ? PAIRS : p === '/api/places/basemap' ? { box: [0, 0, 1, 1], shapes: [] } : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/place-links" element={<PlaceLinksPage />} />
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

describe('PlaceLinksPage', () => {
  it('sums up the test, its variants and the chart', async () => {
    const { container } = renderAt('/place-links')
    expect(await screen.findByText(/510 pairs of 277 places are named together in 2 verses or more/)).toBeTruthy()
    expect(screen.getByText(/Spearman’s ρ -0.32/)).toBeTruthy()
    const rows = container.querySelectorAll('.plk-table')[0].querySelectorAll('tbody tr')
    expect(rows).toHaveLength(3)
    expect(rows[1].textContent).toContain('2 pairs: too few')
    expect(rows[2].textContent).toContain('Leaving out Genesis 10, Numbers 33–34')
    expect(container.querySelectorAll('.plk-dot')).toHaveLength(2)
    expect(container.querySelectorAll('.plk-dot.far')).toHaveLength(1)
  })

  it('shows the decay per variant', async () => {
    const { container } = renderAt('/place-links')
    await screen.findByRole('heading', { name: 'The decay' })
    const bins = () => container.querySelectorAll('.plk-bins tbody tr')
    expect(bins()).toHaveLength(2)
    expect(bins()[0].textContent).toContain('6.3%')
    expect(bins()[1].textContent).toContain('10 km and more')
    // the sure sites have no bins: two choices
    expect(screen.getAllByRole('radio').filter((r) => r.closest('.segmented')?.getAttribute('aria-label') === 'Places')).toHaveLength(2)
    fireEvent.click(screen.getByRole('radio', { name: 'Without the place lists' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/place-links?bins=no_lists'))
    expect(bins()).toHaveLength(1)
    expect(bins()[0].textContent).toContain('7.2%')
  })

  it('lists the leads with the known answer, and the pairs', async () => {
    const { container, calls } = renderAt('/place-links')
    await screen.findByRole('heading', { name: 'Far apart, named together' })
    expect(screen.getByText(/236 km apart, rank 3 of 149 far pairs/)).toBeTruthy()
    const leads = container.querySelectorAll('.plk-leads tbody tr')
    expect(leads).toHaveLength(2)
    expect(leads[0].textContent).toContain('187.1')
    expect(leads[1].querySelector('a')?.getAttribute('href')).toBe('/place-links?place=52#pairs')
    expect(container.querySelectorAll('.plk-leads .plk-link')).toHaveLength(2)
    await waitFor(() => expect(container.querySelectorAll('.plk-pairs li')).toHaveLength(1))
    fireEvent.click(screen.getByRole('radio', { name: 'Farthest first' }))
    await waitFor(() => expect(calls.some((c) => c.includes('sort=km'))).toBe(true))
  })

  it('filters the pairs by a place', async () => {
    const { calls } = renderAt('/place-links?place=52')
    expect(await screen.findByText('Only the pairs of דן')).toBeTruthy()
    expect(calls.some((c) => c.includes('place=52'))).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Show every pair' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/place-links'))
  })

  it('reads in Hebrew', async () => {
    renderAt('/place-links', 'he')
    expect(await screen.findByRole('heading', { name: 'נזכרים יחד, שוכנים יחד?' })).toBeTruthy()
    expect(await screen.findByText(/236 ק״מ ביניהם, במקום 3 מתוך 149 זוגות רחוקים/)).toBeTruthy()
    expect(screen.getByText(/בלי בראשית י, במדבר לג–לד/)).toBeTruthy()
  })

  it('says when the build has no test', async () => {
    renderAt('/place-links', 'en', { meta: {}, lists_en: [], lists_he: [], variants: [], known: [], leads: [], scatter: [] })
    expect(await screen.findByText(/Not computed in this build: run `bsim place-links`/)).toBeTruthy()
  })
})
