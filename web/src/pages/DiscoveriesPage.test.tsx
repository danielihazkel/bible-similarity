// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DiscoveriesResponse, UnitSummary, Verse } from '../api/types'
import { DiscoveriesPage } from './DiscoveriesPage'

const unit = (id: number, label: string): UnitSummary => ({
  unit_id: `v:${id}`,
  unit_type: 'verse',
  label_en: label,
  label_he: `he ${label}`,
  book_id: id,
  start_verse_id: id,
  end_verse_id: id,
  n_verses: 1,
  marker: null,
})
const verse = (id: number, text: string): Verse => ({
  verse_id: id,
  book_id: id,
  chapter: 1,
  verse: 1,
  ref: `B${id} 1:1`,
  ref_he: 'הפניה',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})

const response = (offset: number): DiscoveriesResponse => ({
  unit_type: 'verse',
  mode: 'semantic',
  book: null,
  cross_book: false,
  total: 120,
  offset,
  limit: 50,
  items: [
    {
      score: 0.89,
      tie: 0.89,
      rank_ab: 1,
      rank_ba: 1,
      a: unit(1, 'Psalms 115:8'),
      b: unit(2, 'Psalms 135:18'),
      a_verse: verse(1, 'כְּמוֹהֶם יִהְיוּ עֹשֵׂיהֶם'),
      b_verse: verse(2, 'כְּמוֹהֶם יִהְיוּ עֹשֵׂיהֶם'),
      a_preview: null,
      b_preview: null,
    },
  ],
})

function mockApi() {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const body =
        u.pathname === '/api/discoveries'
          ? response(Number(u.searchParams.get('offset')))
          : u.pathname === '/api/books'
            ? []
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
          <Route path="/discoveries" element={<DiscoveriesPage />} />
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

describe('DiscoveriesPage', () => {
  it('lists unlinked pairs with semantic verses by default', async () => {
    const calls = mockApi()
    renderAt('/discoveries')
    const card = (await screen.findByText('Psalms 115:8')).closest('li')!
    expect(card.textContent).toContain('Psalms 135:18')
    expect(card.textContent).toContain('mutual')
    expect(card.querySelector('a[href^="/compare"]')?.getAttribute('href')).toBe('/compare?a=v%3A1&b=v%3A2')
    expect(calls).toContain('/api/discoveries?unit_type=verse&mode=semantic&limit=50&offset=0')
    expect(screen.getByText(/120 pairs · page 1 of 3/)).toBeTruthy()
  })

  it('pages and resets the page on a filter change', async () => {
    const calls = mockApi()
    renderAt('/discoveries')
    await screen.findByText('Psalms 115:8')
    fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/discoveries?page=2'))
    await waitFor(() => expect(calls.some((c) => c.endsWith('offset=50'))).toBe(true))
    fireEvent.click(screen.getByLabelText('Different books only'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/discoveries?cross=1'))
    await waitFor(() => expect(calls.some((c) => c.includes('cross_book=true'))).toBe(true))
  })
})
