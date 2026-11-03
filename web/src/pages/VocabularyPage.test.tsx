// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, VocabularyBook, VocabularyResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { VocabularyPage } from './VocabularyPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 28, name: 'Job', he_name: 'איוב', osis: 'Job', section: 'Writings', n_chapters: 42 },
  { book_id: 38, name: 'II Chronicles', he_name: 'דברי הימים ב', osis: '2Chr', section: 'Writings', n_chapters: 36 },
]
const book = (id: number, novelty: number, period: VocabularyBook['period'], extra: Partial<VocabularyBook> = {}): VocabularyBook => ({
  book_id: id,
  words: 1000,
  lemmas: 300,
  new: 50,
  new_per_k: 50,
  expected: 40.2,
  excess: 0.2,
  novelty,
  hapax: 10,
  hapax_per_k: 10,
  one_corpus: 20,
  end_words: 1000,
  end_lemmas: 300,
  period,
  ...extra,
})
const DATA: VocabularyResponse = {
  words: 261195,
  lemmas: 6103,
  hapax: 1869,
  one_corpus: { Torah: 532, Prophets: 1309, Writings: 1022 },
  heaps_k: 5.3098,
  heaps_b: 0.5645,
  late_novelty: -0.312,
  early_novelty: -0.555,
  difference: 0.243,
  late_p: 0.0419,
  splits: 12376,
  late_holds: true,
  known: [
    { book: 'Job', book_id: 28, rank: 5, at_most: 3, holds: false },
    { book: 'Song', book_id: 29, rank: 1, at_most: 5, holds: true },
  ],
  known_holds: false,
  orders: 999,
  alpha: 0.05,
  books: [book(0, -0.44, 'early', { new: 1418, expected: 1319.8 }), book(28, 0.79, null, { hapax_per_k: 22.9 }), book(38, -0.89, 'late')],
}

function renderAt(locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (missing) return new Response(JSON.stringify({ detail: { code: 'stage_missing', stage: 'vocabulary', message: 'not computed in this build' } }), { status: 503 })
      return new Response(JSON.stringify(String(url).includes('/books') ? BOOKS : DATA))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={['/vocabulary']}>
          <Routes>
            <Route path="/vocabulary" element={<VocabularyPage />} />
          </Routes>
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('VocabularyPage', () => {
  it('states the checks', async () => {
    renderAt()
    const late = (await screen.findByRole('heading', { name: /late books bring in more/ })).closest('article')!
    expect(within(late).getByText('Borne out')).toBeTruthy()
    expect(late.textContent).toContain('mean novelty of -0.31, the early books (Genesis to Kings) -0.56')
    expect(late.textContent).toContain('12,376 ways')
    const known = screen.getByRole('heading', { name: /Job and the Song/ }).closest('article')!
    expect(within(known).getByText('Not borne out')).toBeTruthy()
    expect(await within(known).findByText('Job: 5th by words found once per 1,000 words (expected in the first 3)')).toBeTruthy()
    expect(screen.getByText(/Heaps’ law over the canon: V = 5.31 N\^0.565/)).toBeTruthy()
  })

  it('draws each book’s novelty and reads a row out on hover', async () => {
    const { container } = renderAt()
    await screen.findByText('Novelty, book by book')
    const rows = container.querySelectorAll('svg.vc-chart g.vc-row')
    expect(rows).toHaveLength(3)
    expect([...container.querySelectorAll('rect.vc-bar')].map((r) => r.getAttribute('class'))).toEqual(['vc-bar vc-early', 'vc-bar vc-other', 'vc-bar vc-late'])
    fireEvent.mouseEnter(rows[0])
    expect(container.querySelector('.vc-readout')!.textContent).toBe('Genesis: 1,418 new lemmas in canon order, 1319.8 expected; novelty -0.44')
    fireEvent.mouseLeave(rows[0])
    fireEvent.focus(rows[2])
    expect(container.querySelector('.vc-readout')!.textContent).toContain('II Chronicles')
  })

  it('lists each book in a table', async () => {
    const { container } = renderAt()
    await screen.findByText('Each book')
    const rows = [...container.querySelectorAll('table.vc-table tbody tr')]
    expect(rows.map((r) => r.querySelector('th')!.textContent)).toEqual(['Genesis', 'Job', 'II Chronicles'])
    expect(rows[1].querySelectorAll('td')[7].textContent).toBe('22.9')
  })

  it('says when the stage did not run', async () => {
    renderAt('en', true)
    expect(await screen.findByText(/The vocabulary was not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('אוצר המילים לאורך המקרא')
    expect(await screen.findByText('חידוש, ספר אחר ספר')).toBeTruthy()
  })
})
