// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PentateuchChaptersResponse, PentateuchResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PentateuchPage } from './PentateuchPage'

const DATA: PentateuchResponse = {
  meta: {
    verses: 4890,
    assigned: 4802,
    reference_p: 2787,
    p_like: 2736,
    agreement: 0.784,
    tests: {
      kappa: { observed: 0.559, null: 0.161, p: 0.001 },
      kappa_genesis: { observed: 0.301, null: 0.002, p: 0.004 },
      names: { observed: 0.058, null: -0.001, p: 0.28 },
    },
    confusion: { p_like_p: 2216, p_like_non: 468, non_p: 571, non_non: 1547 },
    books: { Genesis: { verses: 1508, agree: 0.7, p_like: 0.38, p_ref: 0.22 } },
    names: { p_like: { yhwh: 59, elohim: 101, share: 0.369 }, non_p: { yhwh: 136, elohim: 183, share: 0.426 }, reference_p: 0.012, reference_non: 0.493 },
    grid: [
      { chunk_verses: 10, smooth: 2, kappa: 0.559, kappa_genesis: 0.301, names: 0.058, kappa_p: 0.005, kappa_genesis_p: 0.005, names_p: 0.24 },
      { chunk_verses: 20, smooth: 5, kappa: 0.697, kappa_genesis: 0.385, names: 0.233, kappa_p: 0.005, kappa_genesis_p: 0.005, names_p: 0.015 },
    ],
  },
  p_like: [
    { token: '1696', he: 'דבר', weight: 0.47 },
    { token: '3205@h', he: 'ילד', weight: 0.22 },
  ],
  non_p: [{ token: '5973', he: 'עם', weight: -0.86 }],
  synonyms: [{ name: 'I', members: ['589', '595'], he: ['אני', 'אנכי'], p_like: [111, 4], non_p: [61, 81] }],
}
const CHAPTERS: PentateuchChaptersResponse = {
  book: 0,
  total: 2,
  offset: 0,
  limit: 60,
  items: [
    { unit_id: 'c:0:1', label: 'Genesis 1', label_he: 'בראשית א', book_id: 0, chapter: 1, verses: 31, p_like: 0.55, assigned: 31, p_ref: 1 },
    { unit_id: 'c:0:2', label: 'Genesis 2', label_he: 'בראשית ב', book_id: 0, chapter: 2, verses: 25, p_like: 0.8, assigned: 24, p_ref: 0.125 },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: PentateuchResponse = DATA) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/pentateuch' ? data : p === '/api/pentateuch/chapters' ? CHAPTERS : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/pentateuch" element={<PentateuchPage />} />
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

describe('PentateuchPage', () => {
  it('states the three checks, the confusion, the books and the grid', async () => {
    const { container } = renderAt('/pentateuch')
    expect(await screen.findByText(/agrees with the reference on 78% of the verses: Cohen's kappa 0\.559, against 0\.161 .* \(p 0\.001\)/)).toBeTruthy()
    expect(screen.getByText(/Within Genesis.*kappa 0\.301, against 0\.002 \(p 0\.004\)/)).toBeTruthy()
    expect(screen.getByText(/It is 37% of the divine names on the P-like side and 43% on the other .* p 0\.28\); in the reference itself, 1% in P and 49% outside it/)).toBeTruthy()
    expect([...container.querySelectorAll('.pent-confusion tbody tr')].map((r) => r.textContent)).toEqual(['P-like side2216468', 'Other side5711547'])
    expect(container.querySelector('.pent-books tbody tr')?.textContent).toBe('Genesis150870%38%22%')
    expect(container.querySelectorAll('.pent-grid tr.fixed')).toHaveLength(1)
  })

  it('names the words that decide it, with their stems', async () => {
    renderAt('/pentateuch')
    expect(await screen.findByText('דבר')).toBeTruthy()
    expect(screen.getByText('(hiphil)')).toBeTruthy()
    expect(screen.getByText('אני / אנכי')).toBeTruthy()
    expect(screen.getByText('111 / 4')).toBeTruthy()
  })

  it('draws each chapter against the reference and switches books through the URL', async () => {
    const { container, calls } = renderAt('/pentateuch')
    expect(await screen.findByRole('link', { name: 'Genesis 1' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Genesis 1' }).getAttribute('href')).toBe('/read/c%3A0%3A1?layers=sources')
    expect(screen.getByRole('img', { name: 'P-like 80% · reference P 13%' })).toBeTruthy()
    expect(container.querySelectorAll('.src-bar-ref')).toHaveLength(2)
    fireEvent.change(screen.getByLabelText('Book'), { target: { value: '2' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/pentateuch?book=2'))
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/pentateuch/chapters?') && c.includes('book=2'))).toBe(true))
  })

  it('reads in Hebrew', async () => {
    renderAt('/pentateuch', 'he')
    expect(await screen.findByRole('heading', { name: 'מקורות התורה', level: 1 })).toBeTruthy()
    expect(await screen.findByRole('link', { name: 'בראשית א' })).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/pentateuch', 'en', { meta: {}, p_like: [], non_p: [], synonyms: [] })
    expect(await screen.findByText(/run `bsim pentateuch`/)).toBeTruthy()
  })
})
