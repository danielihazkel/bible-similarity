// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, PatternResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { QueryPage } from './QueryPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
]
const TOKENS = ['וּמֵעֵץ', 'הַדַּעַת', 'כִּי', 'בְּיוֹם', 'אֲכָלְךָ', 'מִמֶּנּוּ', 'מוֹת', 'תָּמוּת׃']
const FOUND: PatternResponse = {
  q: '[form=infabs root=@r] [root=@r form=finite]',
  error: null,
  patterns: 2,
  total: 1,
  matches: 1,
  books: [
    { book_id: 0, matches: 37, verses: 33 },
    { book_id: 1, matches: 46, verses: 41 },
  ],
  offset: 0,
  limit: 20,
  items: [
    {
      verse_id: 47,
      label: 'Genesis 2:17',
      label_he: 'בראשית ב:יז',
      unit_id: 'c:0:2',
      text: 'מוֹת … תָּמוּת׃',
      matches: [{ words: [11, 12], tokens: [6, 7] }],
      verse: { verse_id: 47, book_id: 0, chapter: 2, verse: 17, ref: 'Genesis 2:17', ref_he: 'בראשית ב:יז', text_display: TOKENS.join(' '), display_tokens: TOKENS, ketiv_note: null },
    },
  ],
}
const BAD: PatternResponse = { ...FOUND, q: '[form=infabs] [colour=red]', error: { code: 'unknown_key', at: 15, token: 'colour' }, total: 0, matches: 0, books: [], items: [] }

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en') {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const body = u.pathname === '/api/books' ? BOOKS : u.pathname === '/api/patterns' ? (u.searchParams.get('q')?.includes('colour') ? BAD : FOUND) : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/query" element={<QueryPage />} />
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

describe('QueryPage', () => {
  it('asks for a query, runs an example and lists the verses with the matched words marked', async () => {
    const { container, calls } = renderAt('/query')
    expect(screen.getByText('Write a query above, or start from an example.')).toBeTruthy()
    expect(calls.some((c) => c.startsWith('/api/patterns'))).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: '[form=infabs root=@r] [root=@r form=finite]' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/query?q=%5Bform%3Dinfabs+root%3D%40r%5D+%5Broot%3D%40r+form%3Dfinite%5D'))
    expect(await screen.findByText(/1 match in 1 verse/)).toBeTruthy()
    expect(container.querySelectorAll('.query-hit .w-shared')).toHaveLength(2)
    expect((screen.getByRole('searchbox', { name: 'Query' }) as HTMLInputElement).value).toBe(FOUND.q)
    expect(screen.getByRole('link', { name: 'Read the chapter' }).getAttribute('href')).toBe('/unit/c%3A0%3A2')
    expect(screen.getByRole('link', { name: /Genesis 2:17/ }).getAttribute('href')).toBe('/unit/v%3A47')
  })

  it('narrows to a book from the counts per book', async () => {
    const { calls } = renderAt('/query?q=%5Bform%3Dinfabs%5D')
    fireEvent.click(await screen.findByRole('button', { name: 'Exodus 46' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/query?q=%5Bform%3Dinfabs%5D&book=1'))
    await waitFor(() => expect(calls.some((c) => c.includes('book=1'))).toBe(true))
    fireEvent.click(await screen.findByRole('button', { name: 'All books' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/query?q=%5Bform%3Dinfabs%5D'))
  })

  it('says what is wrong with a query and marks where', async () => {
    const { container } = renderAt('/query')
    fireEvent.change(screen.getByRole('searchbox', { name: 'Query' }), { target: { value: '  [form=infabs] [colour=red] ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByText(/There is no key “colour”/)).toBeTruthy()
    expect(container.querySelector('.query-problem mark')?.textContent).toBe('colour')
    expect(screen.getByTestId('loc').textContent).toBe('/query?q=%5Bform%3Dinfabs%5D+%5Bcolour%3Dred%5D')
  })

  it('reads in Hebrew, with the syntax guide', async () => {
    renderAt('/query?q=%5Bform%3Dinfabs%5D', 'he')
    expect(await screen.findByRole('heading', { name: 'חיפוש תבניות', level: 1 })).toBeTruthy()
    expect(await screen.findByText(/התאמה אחת, בפסוק אחד/)).toBeTruthy()
    fireEvent.click(screen.getByText('איך כותבים שאילתה'))
    expect(screen.getByRole('table', { name: 'המפתחות וערכיהם' })).toBeTruthy()
  })
})
