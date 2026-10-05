// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CommunityResponse, NetworkNode, NetworkResponse, UnitSummary } from '../api/types'
import { NetworkPage } from './NetworkPage'

const unit = (id: string, label: string, book: number): UnitSummary => ({
  unit_id: id,
  unit_type: 'pericope',
  label_en: label,
  label_he: label,
  book_id: book,
  start_verse_id: 0,
  end_verse_id: 1,
  n_verses: 2,
  marker: null,
})
const node = (u: UnitSummary, community: number, x: number, pagerank: number): NetworkNode => ({
  unit: u,
  pagerank,
  strength: 2,
  partners: 3,
  cross_book: 0.25,
  community,
  x,
  y: 0.5,
})
const G20 = unit('s:20', 'Genesis 20:1–18', 0)
const G26 = unit('s:26', 'Genesis 26:1–33', 0)
const PS = unit('s:99', 'Psalms 23:1–6', 26)
const BOOKS = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const NET: NetworkResponse = {
  unit_type: 'pericope',
  communities: [
    { community: 0, size: 1, lemmas: [{ lemma: '7462', he_lemma: 'רעה' }], books: [{ book_id: 26, n_verses: 1 }] },
    { community: 1, size: 2, lemmas: [{ lemma: '87', he_lemma: 'אברהם' }], books: [{ book_id: 0, n_verses: 2 }] },
  ],
  central: [node(PS, 0, 0.5, 0.01), node(G20, 1, 0, 0.005)],
}
const COMM: CommunityResponse = {
  unit_type: 'pericope',
  community: NET.communities[1],
  nodes: [node(G20, 1, 0, 0.005), node(G26, 1, 1, 0.004)],
  edges: [{ a: 's:20', b: 's:26', weight: 0.9 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('NetworkPage', () => {
  it("opens the focused unit's community, draws it and switches communities", async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = decodeURIComponent(new URL(url, 'http://x').pathname)
        const body =
          p === '/api/books'
            ? BOOKS
            : p === '/api/network/pericope'
              ? NET
              : p === '/api/network/pericope/1'
                ? COMM
                : p === '/api/network/pericope/0'
                  ? { ...COMM, community: NET.communities[0], nodes: [node(PS, 0, 0.5, 0.01)], edges: [] }
                  : p === '/api/unit-network/s:20'
                    ? { node: node(G20, 1, 0, 0.005), rank: 7, of: 3482, community_size: 2 }
                    : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/network?type=pericope&unit=s%3A20']}>
          <Routes>
            <Route path="/network" element={<NetworkPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('Community of 2 pericopes')).toBeTruthy()
    expect(container.querySelectorAll('.network-graph circle')).toHaveLength(2)
    expect(container.querySelectorAll('.network-graph line')).toHaveLength(1)
    expect(container.querySelector('.network-graph .node.focus')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Genesis 26:1–33, 3 echoes' }).getAttribute('href')).toBe('/unit/s%3A26')
    // most echoed list, then another community
    expect(screen.getByRole('link', { name: 'Psalms 23:1–6' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /רעה/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toContain('c=0'))
    expect(await screen.findByText('Community of 1 pericopes')).toBeTruthy()
  })
})
