// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EchoesResponse, EchoListResponse, UnitSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { NetworkPage } from './NetworkPage'

const chapter = (id: string, en: string, he: string, book: number): UnitSummary => ({
  unit_id: id,
  unit_type: 'chapter',
  label_en: en,
  label_he: he,
  book_id: book,
  start_verse_id: 0,
  end_verse_id: 1,
  n_verses: 2,
  marker: null,
})
const LEV = chapter('c:2:21', 'Leviticus 21', 'ויקרא כא', 2)
const EZK = chapter('c:13:44', 'Ezekiel 44', 'יחזקאל מד', 13)
const KGS = chapter('c:9:8', 'I Kings 8', 'מלכים א ח', 9)
const CHR = chapter('c:38:6', 'II Chronicles 6', 'דברי הימים ב ו', 38)
const BOOKS = [
  { book_id: 2, name: 'Leviticus', he_name: 'ויקרא', osis: 'Lev', section: 'Torah', n_chapters: 27 },
  { book_id: 9, name: 'I Kings', he_name: 'מלכים א', osis: '1Kgs', section: 'Prophets', n_chapters: 22 },
  { book_id: 10, name: 'II Kings', he_name: 'מלכים ב', osis: '2Kgs', section: 'Prophets', n_chapters: 25 },
  { book_id: 12, name: 'Jeremiah', he_name: 'ירמיהו', osis: 'Jer', section: 'Prophets', n_chapters: 52 },
  { book_id: 13, name: 'Ezekiel', he_name: 'יחזקאל', osis: 'Ezek', section: 'Prophets', n_chapters: 48 },
  { book_id: 38, name: 'II Chronicles', he_name: 'דברי הימים ב', osis: '2Chr', section: 'Writings', n_chapters: 36 },
]
const check = (n: number, agree: number, p: number) => ({ n, agree, p, underpowered: n < 10 })
const ECHOES: EchoesResponse = {
  meta: {
    language_gap: 0.3,
    pairs: 2422,
    bases: { cited: 14, borrowed: 82, language: 363, conflict: 0, none: 1963 },
    checks: { cited: check(2, 2, 0.5), spelling: check(23, 23, 2.4e-7), borrowed: check(59, 58, 2e-16) },
    language_forward: 313,
    language_backward: 50,
    cycles: [[10, 12]],
  },
  books: [{ src_book: 9, dst_book: 38, cited: 2, borrowed: 21, language: 34 }],
  sources: [{ unit: KGS, lends: 12, borrows: 1, lends_explicit: 4, borrows_explicit: 1 }],
}
const LIST: EchoListResponse = {
  basis: null,
  directed: true,
  backward: null,
  book: null,
  unit: null,
  total: 2,
  offset: 0,
  limit: 25,
  items: [
    { edge_id: 1, a: KGS, b: CHR, weight: 1, n_cited: 1, borrowed: 1, gap: 0.9985, language: 1, direction: 1, basis: 'cited' },
    { edge_id: 2, a: LEV, b: EZK, weight: 1, n_cited: 0, borrowed: 0, gap: -0.3018, language: -1, direction: -1, basis: 'language' },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', echoes: EchoesResponse = ECHOES) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? BOOKS : p === '/api/echoes' ? echoes : p === '/api/echoes/list' ? LIST : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/network" element={<NetworkPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return calls
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('DirectionsView', () => {
  it('shows the checks, the book graph and each pair with its direction and evidence', async () => {
    const calls = renderAt('/network?view=directions')
    expect(await screen.findByText(/Language against the spelling of the parallels: the same direction in 23 of 23/)).toBeTruthy()
    expect(screen.getByText(/Language against the citations: 2 cases, too few to judge/)).toBeTruthy()
    expect(screen.getByText(/50 of the 363 language directions/)).toBeTruthy()
    expect(screen.getByText(/point both ways between II Kings ↔ Jeremiah/)).toBeTruthy()
    expect(screen.getByRole('rowheader', { name: 'I Kings → II Chronicles' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'I Kings 8' }).getAttribute('href')).toBe('/network?view=directions&unit=c%3A9%3A8#echo-list')
    // Ezekiel 44 looks earlier than Leviticus 21: drawn on, against the canon order
    const item = (await screen.findByRole('link', { name: 'Ezekiel 44' })).closest('li')!
    expect(item.textContent).toMatch(/Ezekiel 44 → Leviticus 21/)
    expect(item.textContent).toContain('against the canon order')
    expect(item.textContent).toContain('late-language profile +0.30')
    expect(calls).toContain('/api/echoes/list?directed=true&limit=25&offset=0')
    fireEvent.click(screen.getByRole('radio', { name: 'Conflict' }))
    await waitFor(() => expect(calls).toContain('/api/echoes/list?basis=conflict&limit=25&offset=0'))
    fireEvent.click(screen.getByLabelText('Against the canon order only'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/network?view=directions&basis=conflict&backward=1'))
  })

  it('switches views and filters by unit, in Hebrew', async () => {
    const calls = renderAt('/network?view=directions&unit=c:38:6', 'he')
    expect(await screen.findByRole('heading', { name: 'מי מהדהד את מי' })).toBeTruthy()
    await screen.findByRole('link', { name: 'יחזקאל מד' })
    expect(calls).toContain('/api/echoes/list?directed=true&unit=c%3A38%3A6&limit=25&offset=0')
    expect(screen.getByText(/הלשון מול הכתיב של המקבילות: אותו כיוון ב־23 מתוך 23/)).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'קהילות' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/network'))
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/network?view=directions', 'en', { meta: {}, books: [], sources: [] })
    expect(await screen.findByText(/run `bsim echoes`/)).toBeTruthy()
  })
})
