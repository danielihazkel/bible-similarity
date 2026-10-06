// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, DatingChapter, DatingResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { LanguagePage } from './LanguagePage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 32, name: 'Ecclesiastes', he_name: 'קהלת', osis: 'Eccl', section: 'Writings', n_chapters: 12 },
]
const feats = { lbh_lexemes: 0.001, david_plene: 0.5 }
const DATING: DatingResponse = {
  features: ['lbh_lexemes', 'david_plene'],
  coefficients: { lbh_lexemes: 2.9, david_plene: 3.7 },
  held_out_auc: 0.948,
  held_out_auc_grammar: 0.895,
  train_chapters: { early: 300, late: 90 },
  synoptic: { pairs: 26, later: 26, p: 3e-8, later_grammar: 25, p_grammar: 1e-6 },
  synoptic_examples: [
    {
      early_first: 1,
      late_first: 2,
      early_label: 'I Kings 3:5–14',
      late_label: 'II Chronicles 1:7–12',
      early_label_he: 'מלכים א ג:ה–יד',
      late_label_he: 'דברי הימים ב א:ז–יב',
      early_score: 0.02,
      late_score: 0.9,
    },
  ],
  books: [
    { book_id: 0, role: 'early', out_of_domain: false, n_chapters: 50, score: 0.08, low: 0.01, high: 0.17, features: feats },
    { book_id: 32, role: 'scored', out_of_domain: false, n_chapters: 11, score: 0.45, low: 0.06, high: 0.84, features: feats },
  ],
}
const ECCL: DatingChapter[] = [
  {
    unit_id: 'c:32:2',
    book_id: 32,
    chapter: 2,
    n_words: 381,
    role: 'scored',
    out_of_domain: false,
    score: 0.986,
    features: feats,
    drivers: ['lbh_lexemes'],
  },
]

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const body = path === '/api/books' ? BOOKS : path === '/api/dating' ? DATING : path === '/api/dating/book/32' ? ECCL : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/language" element={<LanguagePage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('LanguagePage', () => {
  it('reports the checks, the books and a book’s chapters with what drives them', async () => {
    mockApi()
    renderAt('/language')
    expect(await screen.findByText(/Chronicles comes out later in 26/)).toBeTruthy()
    expect(screen.getByText(/AUC 0.95 \(0.90 without the late words\)/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'II Chronicles 1:7–12' }).getAttribute('href')).toBe('/unit/v%3A2')
    expect(screen.getByText(/trained as early/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Ecclesiastes/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/language?book=32'))
    expect(await screen.findByRole('link', { name: 'Ecclesiastes 2' })).toBeTruthy()
    expect(screen.getByText(/late words \(מלכות/)).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    mockApi()
    renderAt('/language?book=32', 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'לשון' })).toBeTruthy()
    expect(await screen.findByRole('link', { name: 'קהלת ב' })).toBeTruthy()
  })
})
