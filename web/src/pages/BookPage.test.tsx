// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, UnitDetail, Verse } from '../api/types'
import { BookPage } from './BookPage'

const BOOKS: Book[] = [{ book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 3 }]
const verse = (id: number, chapter: number, n: number): Verse => ({
  verse_id: id,
  book_id: 0,
  chapter,
  verse: n,
  ref: `Genesis ${chapter}:${n}`,
  text_display: '',
  display_tokens: [],
  ketiv_note: null,
})
const chapter = (ch: number): UnitDetail => ({
  unit: {
    unit_id: `c:0:${ch}`,
    unit_type: 'chapter',
    label_en: `Genesis ${ch}`,
    label_he: '',
    book_id: 0,
    start_verse_id: ch * 100,
    end_verse_id: ch * 100 + 1,
    n_verses: 2,
    marker: null,
  },
  verses: [verse(ch * 100, ch, 1), verse(ch * 100 + 1, ch, 2)],
  parents: [],
  prev_id: null,
  next_id: null,
})

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const { pathname } = new URL(url, 'http://x')
      const m = decodeURIComponent(pathname).match(/^\/api\/unit\/c:0:(\d+)$/)
      const body = pathname === '/api/books' ? BOOKS : m ? chapter(Number(m[1])) : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
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
          <Route path="/browse/:bookId" element={<BookPage />} />
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

describe('BookPage verses tab', () => {
  it('lists the selected chapter’s verses as links to verse pages', async () => {
    mockApi()
    renderAt('/browse/0?tab=verses&ch=2')
    const link = await screen.findByTitle('Genesis 2:2: similar verses')
    expect(link.getAttribute('href')).toBe('/unit/v%3A201')
    expect(screen.getByRole('button', { name: '2' }).getAttribute('aria-current')).toBe('true')
  })

  it('switches chapter via the URL', async () => {
    mockApi()
    renderAt('/browse/0?tab=verses')
    await screen.findByTitle('Genesis 1:1: similar verses')
    fireEvent.click(screen.getByRole('button', { name: '3' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/browse/0?tab=verses&ch=3'))
    expect((await screen.findByTitle('Genesis 3:1: similar verses')).getAttribute('href')).toBe('/unit/v%3A300')
  })
})
