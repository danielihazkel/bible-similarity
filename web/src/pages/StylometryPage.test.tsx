// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import type { Book, BookStyle, SeamsResponse, StylometryResponse } from '../api/types'
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

const SEAM = {
  book_id: 1,
  verse_id: 12,
  label: 'Psalms 3:1',
  label_he: 'תהלים ג:א',
  shift: 0.9,
  threshold: 0.5,
  rank: 1,
  features: [{ feature: 'aramaic', label: 'ארמית', z: 4.2 }],
}
const SEAMS_BOOK: SeamsResponse = {
  book: 1,
  block_words: 600,
  threshold: 0.5,
  curve: [
    { verse_id: 10, chapter: 2, verse: 11, shift: 0.3 },
    { verse_id: 11, chapter: 2, verse: 12, shift: 0.5 },
    { verse_id: 12, chapter: 3, verse: 1, shift: 0.9 },
  ],
  seams: [SEAM],
}
const SEAMS_TOP: SeamsResponse = { book: null, block_words: 600, threshold: null, curve: [], seams: [SEAM] }

function renderAt(path: string, locale: Locale = 'en') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const p = new URL(url, 'http://x').pathname
      const u = new URL(url, 'http://x')
      const body =
        p === '/api/books'
          ? BOOKS
          : p === '/api/stylometry'
            ? ST
            : p === '/api/stylometry/book/1'
              ? STYLE
              : p === '/api/seams'
                ? u.searchParams.get('book') === '1'
                  ? SEAMS_BOOK
                  : SEAMS_TOP
                : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/style" element={<StylometryPage />} />
            <Route path="/search" element={<SearchPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>
    </LocaleProvider>,
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
    // the seams of the chosen book: the shift curve with its peak, and the changing features
    await waitFor(() => expect(container.querySelector('.shift-chart .chart-peak')).toBeTruthy())
    expect(container.querySelector('.seam-list')?.textContent).toContain('ארמית')
  })

  it('lists the corpus seams with their books when no book is chosen', async () => {
    const { container } = renderAt('/style')
    await waitFor(() => expect(container.querySelector('.seam-list')?.textContent).toContain('Psalms 3:1 · Psalms'))
    expect(container.querySelector('.shift-chart')).toBeNull()
  })
})

describe('StylometryPage in Hebrew', () => {
  it('names books, axes and seams in Hebrew and keeps the charts left to right', async () => {
    const { container } = renderAt('/style?book=1', 'he')
    expect(await screen.findByRole('heading', { name: 'סגנון' })).toBeTruthy()
    expect(screen.getByText('הציר האופקי')).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'היכן הסגנון משתנה' })).toBeTruthy()
    const profile = await screen.findByLabelText('הפרופיל הסגנוני של הספר')
    expect(profile.textContent).toContain('תהילים')
    expect(profile.textContent).toContain('בראשית (1.20)')
    expect(container.textContent).not.toMatch(/Genesis|Psalms|Horizontal axis/)
    await waitFor(() => expect(container.querySelector('.seam-list')?.textContent).toContain('תהלים ג:א'))
    // the peak is labelled from the curve with Hebrew numerals, not parsed from the English label
    expect([...container.querySelectorAll('.shift-chart text')].map((t) => t.textContent)).toContain('ג:א')
    expect(container.querySelector('.scatter')?.getAttribute('dir')).toBe('ltr')
    expect(container.querySelector('.table-wrap')?.getAttribute('dir')).toBe('ltr')
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
