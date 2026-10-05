// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, ParallelismResponse } from '../api/types'
import { PoetryPage } from './PoetryPage'

const BOOKS: Book[] = [
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
  { book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const RES: ParallelismResponse = {
  unit_type: 'chapter',
  book: null,
  exclude_poetic: true,
  parallel_at: 0.5,
  coefficients: { cos: 0.8 },
  held_out_auc: { Ps: 0.85, Prov: 0.9 },
  sort: 'prob',
  min_parallel: 0,
  typing: null,
  books: [
    { book_id: 1, poetic_accents: false, mean_prob: 0.2, share_parallel: 0.1, n_scored: 1200 },
    { book_id: 26, poetic_accents: true, mean_prob: 0.5, share_parallel: 0.55, n_scored: 2400 },
  ],
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      unit: {
        unit_id: 'c:1:15',
        unit_type: 'chapter',
        label_en: 'Exodus 15',
        label_he: 'שמות טו',
        book_id: 1,
        start_verse_id: 100,
        end_verse_id: 126,
        n_verses: 27,
        marker: null,
      },
      mean_prob: 0.43,
      n_parallel: 10,
      share_antithetic: 0.2,
      share_parallel: 0.6,
      n_scored: 27,
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('PoetryPage', () => {
  it('ranks units, shows book shares and keeps filters in the URL', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? BOOKS : p === '/api/parallelism' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/poetry']}>
          <Routes>
            <Route path="/poetry" element={<PoetryPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const link = await screen.findByText('Exodus 15')
    expect(link.getAttribute('href')).toBe('/unit/c%3A1%3A15?halves=1')
    expect(screen.getByText('60%')).toBeTruthy()
    expect(container.querySelectorAll('.book-bars li')).toHaveLength(2)
    expect(container.querySelector('.book-bars li.poetic')?.textContent).toContain('Psalms')
    expect(calls.some((c) => c.includes('exclude_poetic=true'))).toBe(true)
    fireEvent.click(screen.getByLabelText('Include Psalms, Proverbs, Job'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/poetry?all=1'))
  })
})
