// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, ConcordanceResponse, ResolveResponse } from '../api/types'
import { ConcordancePage } from './ConcordancePage'
import { SearchPage } from './SearchPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהילים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const conc = (book: string | null): ConcordanceResponse => ({
  lemma: '7225',
  he_lemma: 'ראשית',
  n_words: 51,
  n_verses: 50,
  by_book: [
    { book_id: 0, n_verses: 6 },
    { book_id: 26, n_verses: 3 },
  ],
  book: book === null ? null : Number(book),
  total: book === null ? 50 : 3,
  offset: 0,
  limit: 50,
  items: [
    {
      verse: {
        verse_id: 0,
        book_id: 0,
        chapter: 1,
        verse: 1,
        ref: 'Genesis 1:1',
        ref_he: 'הפניה',
        text_display: 'בְּרֵאשִׁית בָּרָא',
        display_tokens: ['בְּרֵאשִׁית', 'בָּרָא'],
        ketiv_note: null,
      },
      label_en: 'Genesis 1:1',
      label_he: 'בראשית א:א',
      display_idxs: [0],
    },
  ],
})

function mockApi(resolved: ResolveResponse['unit'] = null) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const body =
        u.pathname === '/api/books'
          ? BOOKS
          : u.pathname === '/api/lemma/7225'
            ? conc(u.searchParams.get('book'))
            : u.pathname === '/api/resolve'
              ? { query: u.searchParams.get('q'), unit: resolved }
              : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
  return calls
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/lemma/:lemma" element={<ConcordancePage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ConcordancePage', () => {
  it('lists verses with the lemma highlighted and filters by book', async () => {
    const calls = mockApi()
    const { container } = renderAt('/lemma/7225')
    expect(await screen.findByText(/51 occurrences in 50 verses, 2 books/)).toBeTruthy()
    expect(container.querySelector('.w-shared')?.textContent).toBe('בְּרֵאשִׁית')
    fireEvent.click(await screen.findByRole('button', { name: /Psalms/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/lemma/7225?book=26'))
    await waitFor(() => expect(calls.some((c) => c.includes('book=26'))).toBe(true))
  })
})

describe('SearchPage references', () => {
  it('offers the referenced unit and skips text search for non-Hebrew input', async () => {
    const calls = mockApi({
      unit_id: 'v:0',
      unit_type: 'verse',
      label_en: 'Genesis 1:1',
      label_he: 'בראשית א:א',
      book_id: 0,
      start_verse_id: 0,
      end_verse_id: 0,
      n_verses: 1,
      marker: null,
    })
    renderAt('/search?q=Gen%201%3A1')
    const link = await screen.findByRole('link', { name: 'Genesis 1:1' })
    expect(link.getAttribute('href')).toBe('/unit/v%3A0')
    expect(calls.some((c) => c.startsWith('/api/search'))).toBe(false)
  })
})
