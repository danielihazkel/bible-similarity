// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Binomial, BinomialOccurrencesResponse, BinomialsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { BinomialsPage } from './BinomialsPage'

const pair = (p: string, f: string, s: string, n: number, own: number, extra: Partial<Binomial> = {}): Binomial => ({
  pair: p,
  first: p.split('+')[0],
  second: p.split('+')[1],
  first_form: f,
  second_form: s,
  kind: 'noun',
  n,
  n_own: own,
  fixed: own / n,
  first_letters: 3,
  second_letters: 3,
  first_syll: 2,
  second_syll: 2,
  n_early: n,
  rev_early: 0,
  n_late: 0,
  rev_late: 0,
  ...extra,
})
const DATA: BinomialsResponse = {
  pairs: 6111,
  binomials: 3,
  min_pairs: 5,
  both_ways: 1,
  letters: { differ: 87, shorter_first: 60, share: 0.69, p: 0.00026 },
  syllables: { differ: 64, shorter_first: 39, share: 0.61, p: 0.0517 },
  short_holds: false,
  rate_early: 0.0708,
  rate_late: 0.1736,
  n_early: 650,
  n_late: 144,
  difference: 0.103,
  expected: 0,
  late_p: 0.0288,
  late_holds: true,
  without_known: { difference: 0.03, p: 0.1883, rate_early: 0.06, rate_late: 0.09 },
  known: [
    { first: '8064', second: '776', n: 21, share: 0.9048, fixed: 0.9, holds: true },
    { first: '376', second: '802', n: 17, share: 1, fixed: 0.9, holds: true },
  ],
  known_late: { first: '2091', second: '3701', n_early: 24, share_early: 0.25, n_late: 25, share_late: 0.56, holds: true },
  known_holds: true,
  examples: 12,
  shuffles: 9999,
  alpha: 0.05,
  items: [
    pair('2091+3701', 'כסף', 'זהב', 64, 38, { n_late: 25, rev_late: 14 }),
    pair('776+8064', 'שמים', 'ארץ', 21, 19, { first_letters: 4, first_syll: 3 }),
    pair('1+517', 'אב', 'אם', 10, 10),
  ],
}
const verse = (id: number) => ({ verse_id: id, book_id: 12, chapter: 1, verse: id, ref: `I Chronicles 1:${id}`, ref_he: `דברי הימים א א:${id}`, text_display: 'זָהָב וָכֶסֶף', display_tokens: ['זָהָב', 'וָכֶסֶף'], ketiv_note: null })
const OCC: BinomialOccurrencesResponse = {
  pair: '2091+3701',
  items: [
    { verse: verse(1), own: true, a_tok: 0, b_tok: 1 },
    { verse: verse(2), own: false, a_tok: 0, b_tok: 1 },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path = '/binomials', locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (missing) return new Response(JSON.stringify({ detail: 'the binomials were not computed' }), { status: 404 })
      return new Response(JSON.stringify(String(url).includes('/occurrences') ? OCC : DATA))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/binomials" element={<BinomialsPage />} />
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

describe('BinomialsPage', () => {
  it('states the three checks', async () => {
    renderAt()
    const short = (await screen.findByRole('heading', { name: /shorter word comes first/ })).closest('article')!
    expect(within(short).getByText('Not borne out')).toBeTruthy()
    expect(short.textContent).toContain('60 of 87 counted in letters (p < 0.001) and 39 of 64 counted in syllables (p 0.052)')
    const late = screen.getByRole('heading', { name: /late books turn/ }).closest('article')!
    expect(late.textContent).toContain('7% of the time in the early books (Genesis to Kings) and 17% in the late')
    expect(late.textContent).toContain('Without ⁨כסף וזהב⁩: p 0.19.')
    const known = screen.getByRole('heading', { name: /Heaven and earth/ }).closest('article')!
    expect(known.textContent).toContain('⁨שמים וארץ⁩ in that order 90% of the time, ⁨איש ואשה⁩ 100%; ⁨זהב וכסף⁩ rather than ⁨כסף וזהב⁩ 25% of the time in the early books, 56% in the late.')
  })

  it('lists the pairs and filters and sorts them', async () => {
    const { container } = renderAt()
    await screen.findByText('The 3 pairs found at least 5 times')
    const rows = () => [...container.querySelectorAll('table.bn-table tbody tr')].map((r) => r.querySelector('th')!.textContent)
    expect(rows()).toEqual(['כסף וזהב', 'שמים וארץ', 'אב ואם'])
    expect(container.querySelector('table.bn-table tbody tr td.bn-turned')!.textContent).toBe('14 / 25')
    fireEvent.click(screen.getByRole('radio', { name: 'Found both ways' }))
    expect(screen.getByTestId('loc').textContent).toBe('/binomials?show=both')
    expect(rows()).toEqual(['כסף וזהב', 'שמים וארץ'])
    fireEvent.click(screen.getByRole('radio', { name: 'Most turned' }))
    expect(rows()).toEqual(['כסף וזהב', 'שמים וארץ'])
  })

  it('opens a pair with its occurrences in both orders', async () => {
    const { container } = renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Where כסף וזהב is found' }))
    expect(screen.getByTestId('loc').textContent).toBe('/binomials?pair=2091%2B3701')
    await screen.findByText('Turned round')
    const panel = container.querySelector('.bn-panel')!
    expect([...panel.querySelectorAll('h4')].map((h) => h.textContent)).toEqual(['In its own order', 'Turned round'])
    expect(panel.querySelectorAll('li.hit')).toHaveLength(2)
    expect(panel.textContent).toContain('(up to 12 of each listed)')
  })

  it('says when the stage did not run', async () => {
    renderAt('/binomials', 'en', true)
    expect(await screen.findByText(/The word pairs were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/binomials', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('צמדי מילים')
    expect(await screen.findByText('3 הצמדים שנמצאו 5 פעמים לפחות')).toBeTruthy()
    expect(screen.getAllByText('שמות עצם').length).toBe(3)
  })
})
