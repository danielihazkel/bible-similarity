// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, Bracket, BracketsPage as Page, BracketsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { BracketsPage } from './BracketsPage'

const BOOKS: Book[] = [{ book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 }]
const verse = (id: number, ref: string, refHe: string, text: string) => ({
  verse_id: id,
  book_id: 0,
  chapter: 37,
  verse: 36,
  ref,
  ref_he: refHe,
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const JOSEPH: Bracket = {
  bracket: 0,
  book_id: 0,
  a: verse(1100, 'Genesis 37:36', 'בראשית לז:לו', 'והמדנים מכרו אתו אל מצרים לפוטיפר'),
  b: verse(1131, 'Genesis 39:1', 'בראשית לט:א', 'ויקנהו פוטיפר סריס פרעה'),
  a_disp: [5],
  b_disp: [1],
  between: 30,
  unit_id: 'c:0:37',
  score: 18.2,
  n_tokens: 4,
  lex: 0.31,
  sem: 0.12,
  insertion: 0.215,
  p: 0.003,
  q: 0.2,
  known: true,
}
const WEAK: Bracket = { ...JOSEPH, bracket: 1, known: false, p: 0.6, q: 0.9, insertion: -0.2, a_disp: [], b_disp: [] }
const DATA: BracketsResponse = {
  candidates: 259501,
  repetitions: 5280,
  brackets: 2105,
  mean: -0.156,
  mean_null: -0.19,
  p: 0.001,
  draws: 999,
  window: 4,
  alpha: 0.05,
  holds: true,
  leads: 0,
  strong: 205,
  known: [
    { a: 'Genesis 37:36', b: 'Genesis 39:1', found: true, bracket: 0, insertion: 0.215, p: 0.003, beats: true },
    { a: 'Ezra 4:5', b: 'Ezra 4:24', found: false, bracket: null, insertion: null, p: null, beats: false },
  ],
  known_found: 1,
  known_beat: 1,
  known_holds: false,
  books: [{ book_id: 0, brackets: 2, strong: 1 }],
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
      const u = new URL(url, 'http://x')
      calls.push(u.pathname + u.search)
      if (missing) return new Response(JSON.stringify({ detail: 'the resumptive repetitions were not computed' }), { status: 404 })
      if (u.pathname === '/api/books') return new Response(JSON.stringify(BOOKS))
      if (u.pathname === '/api/brackets') return new Response(JSON.stringify(DATA))
      const show = u.searchParams.get('show') ?? 'all'
      const items = show === 'all' ? [JOSEPH, WEAK] : [JOSEPH]
      const page: Page = { show: show as Page['show'], order: (u.searchParams.get('order') ?? 'canon') as Page['order'], book: null, total: items.length, offset: 0, limit: 25, items }
      return new Response(JSON.stringify(page))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/brackets" element={<BracketsPage />} />
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

describe('BracketsPage', () => {
  it('states both checks with their verdicts and the known brackets', async () => {
    renderAt('/brackets')
    const claim = (await screen.findByRole('heading', { name: /The block interrupts its surroundings/ })).closest('article')!
    expect(within(claim).getByText('Borne out')).toBeTruthy()
    expect(claim.textContent).toContain('2,105 repetitions. Their bracket score')
    expect(claim.textContent).toContain('averages -0.16, against -0.19')
    expect(claim.textContent).toContain('One by one, 205 beat their random brackets at p ≤ 0.05; 0 after correction')
    const known = screen.getByRole('heading', { name: /commentaries name/ }).closest('article')!
    expect(within(known).getByText('Not borne out')).toBeTruthy()
    expect([...known.querySelectorAll('li')].map((li) => li.textContent)).toEqual(['Genesis 37:36 … Genesis 39:1: found · p 0.003', 'Ezra 4:5 … Ezra 4:24: not found'])
  })

  it('lists the repetitions with both verses, the clause marked, and links to read and compare', async () => {
    const { container } = renderAt('/brackets')
    await screen.findByText('2 repetitions · page 1 of 1')
    const items = [...container.querySelectorAll('li.brk-bracket')]
    expect(items).toHaveLength(2)
    const joseph = items[0]
    expect(joseph.className).toContain('brk-strong')
    expect([...joseph.querySelectorAll('.w-shared')].map((w) => w.textContent)).toEqual(['לפוטיפר', 'פוטיפר'])
    expect(joseph.textContent).toContain('30 verses between')
    expect(joseph.textContent).toContain('bracket 0.21 (words 0.31, meaning 0.12) · p 0.003, q 0.20')
    expect(joseph.textContent).toContain('named in advance')
    expect(within(joseph as HTMLElement).getByRole('link', { name: 'read the block' }).getAttribute('href')).toBe('/read/c%3A0%3A37')
    expect(within(joseph as HTMLElement).getByRole('link', { name: 'compare the two' }).getAttribute('href')).toBe('/compare?a=v%3A1100&b=v%3A1131')
    expect(items[1].className).not.toContain('brk-strong')
  })

  it('filters, orders and picks a book through the address and the API', async () => {
    const { container } = renderAt('/brackets')
    fireEvent.click(await screen.findByRole('radio', { name: 'p ≤ 0.05' }))
    expect(screen.getByTestId('loc').textContent).toBe('/brackets?show=strong')
    await screen.findByText('1 repetition · page 1 of 1')
    expect(container.querySelectorAll('li.brk-bracket')).toHaveLength(1)
    fireEvent.click(screen.getByRole('radio', { name: 'Strongest first' }))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '0' } })
    expect(screen.getByTestId('loc').textContent).toBe('/brackets?show=strong&order=strongest&book=0')
    await vi.waitFor(() => expect(calls).toContain('/api/brackets/items?show=strong&order=strongest&book=0&limit=25&offset=0'))
    expect(within(screen.getByRole('combobox')).getAllByRole('option').map((o) => o.textContent)).toEqual(['All books', 'Genesis · בראשית (2)'])
  })

  it('says when the stage did not run', async () => {
    renderAt('/brackets', 'en', true)
    expect(await screen.findByText(/The resumptive repetitions were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/brackets', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('חזרה מסגרת')
    expect(await screen.findByText('מתאשר')).toBeTruthy()
    expect(await screen.findAllByText('30 פסוקים ביניהם')).toHaveLength(2)
  })
})
