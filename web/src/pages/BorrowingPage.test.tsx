// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, BorrowingResponse, BorrowingSequence } from '../api/types'
import { BorrowLineBetween } from '../components/BorrowLine'
import { LocaleProvider } from '../context/Locale'
import { BorrowingPage } from './BorrowingPage'

const BOOKS: Book[] = [
  { book_id: 15, name: 'Ezra', he_name: 'עזרא', osis: 'Ezra', section: 'Writings', n_chapters: 10 },
  { book_id: 16, name: 'Nehemiah', he_name: 'נחמיה', osis: 'Neh', section: 'Writings', n_chapters: 13 },
]
const SEQ: BorrowingSequence = {
  seq_id: 7,
  a_book: 15,
  b_book: 16,
  a_first: 20767,
  b_first: 21165,
  a_label: 'Ezra 2:1–70',
  b_label: 'Nehemiah 7:6–72',
  a_label_he: 'עזרא ב:א–ע',
  b_label_he: 'נחמיה ז:ו–עב',
  n_pairs: 65,
  language: -0.02,
  spelling: -0.2,
  smoothing: -0.27,
  expansion: null,
  n_spelling: 5,
  n_substitution: 12,
  known: null,
  votes: -2,
  n_votes: 2,
  direction: 'b_to_a',
}
const check = (agree: number, n: number, p: number) => ({ agree, n, p, unclear: null })
const RES: BorrowingResponse = {
  unit: null,
  checks: {
    language: check(30, 35, 2.2e-5),
    spelling: check(29, 31, 1e-7),
    smoothing: check(15, 28, 0.85),
    expansion: check(15, 33, 0.73),
    all_signs: check(21, 24, 3e-4),
  },
  used_signs: ['language', 'spelling'],
  held_out: { agree: 30, n: 32, p: 1e-7, unclear: 3 },
  books: [
    { a_book: 15, b_book: 16, sequences: 1, n_pairs: 65, votes: -2, a_to_b: 0, b_to_a: 1, known: null, direction: 'b_to_a', items: [SEQ] },
  ],
}

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const body = path === '/api/books' ? BOOKS : path === '/api/borrowing' ? RES : path === '/api/borrowing/between' ? [SEQ] : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
}

function renderAt(ui: React.ReactNode, locale: 'en' | 'he' = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter>
          <Routes>
            <Route path="*" element={ui} />
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

describe('BorrowingPage', () => {
  it('shows the check, which signs vote and each book pair’s direction', async () => {
    mockApi()
    renderAt(<BorrowingPage />)
    expect(await screen.findByText(/29 of 31 right/)).toBeTruthy()
    expect(screen.getAllByText(/does not vote/)).toHaveLength(2)
    expect(screen.getByText(/30 of 32 right, 3 undecided/)).toBeTruthy()
    expect((await screen.findAllByText('Nehemiah → Ezra'))[0].tagName).toBe('STRONG')
    expect(screen.getByRole('link', { name: 'Ezra 2:1–70 ↔ Nehemiah 7:6–72' }).getAttribute('href')).toBe('/sequences/7')
    expect(screen.getAllByText('Ezra later').length).toBeGreaterThan(0)
  })

  it('reads in Hebrew', async () => {
    mockApi()
    renderAt(<BorrowingPage />, 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'מי שאל ממי' })).toBeTruthy()
    expect((await screen.findAllByText('נחמיה ← עזרא'))[0].tagName).toBe('STRONG')
  })
})

describe('BorrowLineBetween', () => {
  it('says which side looks like the borrower', async () => {
    mockApi()
    renderAt(<BorrowLineBetween a="c:15:2" b="c:16:7" />)
    expect(await screen.findByText(/Which borrowed\? Nehemiah 7:6–72 → Ezra 2:1–70 \(2 signs/)).toBeTruthy()
  })
})
