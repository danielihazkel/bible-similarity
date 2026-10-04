// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, BookStyle, StylometryResponse } from '../api/types'
import { SearchPage } from './SearchPage'
import { StylometryPage } from './StylometryPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Psalms', he_name: 'תהילים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const ST: StylometryResponse = {
  points: [{ unit_id: 'c:0:1', label_en: 'Genesis 1', label_he: 'בראשית א', book_id: 0, n_words: 434, x: 0.2, y: 0.4 }],
  axes: [
    { pc: 1, variance: 0.07, positive: ['יקטל (עתיד)'], negative: ['ה הידיעה'] },
    { pc: 2, variance: 0.06, positive: ['ויקטל (עתיד מהופך)'], negative: ['שם עצם'] },
  ],
  order: [1, 0],
  delta: [{ a: 0, b: 1, delta: 1.2 }],
}
const STYLE: BookStyle = {
  book_id: 1,
  n_words: 19000,
  over: [{ feature: 'verb:h', label: 'עתיד מוארך', rate: 0.004, z: 2.4 }],
  under: [{ feature: 'conj', label: 'ו החיבור', rate: 0.2, z: -1.9 }],
  closest: [{ a: 1, b: 0, delta: 1.2 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? BOOKS : p === '/api/stylometry' ? ST : p === '/api/stylometry/book/1' ? STYLE : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/style" element={<StylometryPage />} />
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

describe('StylometryPage', () => {
  it('describes the axes and shows a book profile from the Delta matrix', async () => {
    const { container } = renderAt('/style')
    expect(await screen.findByText('יקטל (עתיד)')).toBeTruthy()
    expect(container.querySelectorAll('.aff-cell')).toHaveLength(2)
    fireEvent.click(container.querySelector('.aff-cell')!) // related order: Psalms row first
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/style?book=1'))
    const profile = await screen.findByLabelText('Book style profile')
    expect(profile.textContent).toContain('עתיד מוארך')
    expect(profile.textContent).toContain('Genesis (1.20)')
  })
})

describe('structural mode', () => {
  it('is not offered for free-text search', async () => {
    renderAt('/search?mode=structural')
    const radios = await screen.findAllByRole('radio', { name: /Lexical|Semantic|Fused|Structural/ })
    expect(radios.map((r) => r.textContent)).toEqual(['Lexical', 'Semantic', 'Fused'])
    expect(screen.getByRole('radio', { name: 'Fused' }).getAttribute('aria-checked')).toBe('true')
  })
})
