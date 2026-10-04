// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AffinityPair, AffinityResponse, Book, MapResponse } from '../api/types'
import { MapPage } from './MapPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
]
const MAP: MapResponse = {
  unit_type: 'chapter',
  points: [
    { unit_id: 'c:0:1', label_en: 'Genesis 1', label_he: 'בראשית א', book_id: 0, n_verses: 31, x: 0.1, y: 0.2, cluster: 0 },
    { unit_id: 'c:1:1', label_en: 'Exodus 1', label_he: 'שמות א', book_id: 1, n_verses: 22, x: 0.8, y: 0.7, cluster: 1 },
  ],
  clusters: [
    { cluster: 0, size: 1, lemmas: [{ lemma: '7549', he_lemma: 'רקיע' }] },
    { cluster: 1, size: 1, lemmas: [{ lemma: '6547', he_lemma: 'פרעה' }] },
  ],
}
const AFF: AffinityResponse = { order: [1, 0], cells: [{ a: 0, b: 1, n_pairs: 12, expected: 3, lift: 4 }] }
const verse = (id: number) => ({
  verse_id: id,
  book_id: id,
  chapter: 1,
  verse: 1,
  ref: `B${id}`,
  text_display: 'אֵלֶּה',
  display_tokens: ['אֵלֶּה'],
  ketiv_note: null,
})
const PAIRS: AffinityPair[] = [
  {
    score: 0.03,
    a: { ...MAP.points[0], unit_id: 'v:0', unit_type: 'verse', start_verse_id: 0, end_verse_id: 0, n_verses: 1, marker: null, label_en: 'Genesis 46:8' },
    b: { ...MAP.points[1], unit_id: 'v:1', unit_type: 'verse', start_verse_id: 1, end_verse_id: 1, n_verses: 1, marker: null, label_en: 'Exodus 1:1' },
    a_verse: verse(0),
    b_verse: verse(1),
    link: null,
  },
]

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('MapPage', () => {
  it('shows cluster labels, the affinity matrix and a book pair on click', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body =
          p === '/api/books' ? BOOKS : p === '/api/map/chapter' ? MAP : p === '/api/affinity' ? AFF : p === '/api/affinity/1/0' ? PAIRS : null
        return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/map']}>
          <Routes>
            <Route path="/map" element={<MapPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const legend = await screen.findByLabelText('Clusters')
    expect(legend.textContent).toContain('רקיע')
    await waitFor(() => expect(container.querySelectorAll('.aff-cell')).toHaveLength(2))
    // related order puts Exodus (1) first: the first cell is Exodus row x Genesis column
    fireEvent.click(container.querySelector('.aff-cell')!)
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/map?pair=1-0'))
    expect(await screen.findByText('Exodus 1:1')).toBeTruthy()
    expect(calls).toContain('/api/affinity/1/0')
  })
})
