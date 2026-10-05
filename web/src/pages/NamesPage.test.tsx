// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, EntitiesResponse, EntityDetail } from '../api/types'
import { NamesPage } from './NamesPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
]
const moses = { lemma: '4872', he: 'משה', kind: 'person' as const, n_mentions: 766, n_verses: 700, n_here: null, first_vid: 1, last_vid: 9, kind_source: 'lexicon' as const }
const LIST: EntitiesResponse = { kind: null, book: null, q: null, total: 1, offset: 0, limit: 60, items: [moses] }
const DETAIL: EntityDetail = {
  entity: moses,
  first_label: 'Exodus 2:10',
  last_label: 'Malachi 3:22',
  first_label_he: 'שמות ב:י',
  last_label_he: 'מלאכי ג:כב',
  by_book: [{ book_id: 1, n_verses: 290 }],
  partners: [
    { lemma: '175', he: 'אהרן', kind: 'person', n_verses: 141, expected: 2.1, g2: 900 },
    { lemma: '4714', he: 'מצרים', kind: 'place', n_verses: 58, expected: 4.5, g2: 120 },
  ],
  links: [{ a: '175', b: '4714', n_verses: 20, g2: 40 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('NamesPage', () => {
  it('lists names and opens a name with its book strip and partners', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? BOOKS : p === '/api/entities' ? LIST : p === '/api/entities/4872' ? DETAIL : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/names']}>
          <Routes>
            <Route path="/names" element={<NamesPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    fireEvent.click(await screen.findByRole('button', { name: /משה/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/names?e=4872'))
    expect(await screen.findByText('Exodus 2:10')).toBeTruthy()
    expect(container.querySelectorAll('.book-strip li')).toHaveLength(2)
    expect(container.querySelectorAll('.ego-node')).toHaveLength(2)
    expect(container.querySelectorAll('.ego-side')).toHaveLength(1)
    expect(screen.getByText(/141 verses together/)).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Place' }))
    await waitFor(() => expect(calls.some((c) => c.includes('kind=place'))).toBe(true))
  })
})
