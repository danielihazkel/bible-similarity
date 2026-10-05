// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ChangesResponse, RewriteProfile, RewritesResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { ChangesPage } from './ChangesPage'

const RES: ChangesResponse = {
  op: 'substitution',
  a_book: null,
  b_book: null,
  totals: { substitution: 1963, added: 1632 },
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      a_key: '3068',
      b_key: '430',
      a_form: null,
      b_form: null,
      a_he: 'יהוה',
      b_he: 'אלהים',
      count: 31,
      n_sequences: 9,
      examples: [{ seq_id: 7, a: 15292, b: 15956, a_label: 'Psalms 14:2', b_label: 'Psalms 53:3', a_label_he: 'תהלים יד:ב', b_label_he: 'תהלים נג:ג' }],
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

describe('ChangesPage', () => {
  it('lists grouped changes with totals per kind and links to the sequence', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? [] : p === '/api/changes' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/changes']}>
          <Routes>
            <Route path="/changes" element={<ChangesPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('אלהים')).toBeTruthy()
    expect(screen.getByText('Substituted 1,963')).toBeTruthy()
    const example = screen.getByText('Psalms 14:2 → Psalms 53:3')
    expect(example.getAttribute('href')).toBe('/sequences/7')
    fireEvent.click(screen.getByText('Added 1,632'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/changes?op=added'))
    await waitFor(() => expect(calls.some((c) => c.includes('op=added'))).toBe(true))
  })
})

describe('ChangesPage in Hebrew', () => {
  it('names the kinds of change and the examples in Hebrew', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? [] : p === '/api/changes' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <LocaleProvider initial="he">
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={['/changes']}>
            <Routes>
              <Route path="/changes" element={<ChangesPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </LocaleProvider>,
    )
    expect(await screen.findByText('אלהים')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'במה נבדלות המקבילות' })).toBeTruthy()
    expect(screen.getByText('הוחלף 1,963')).toBeTruthy()
    expect(screen.getByText('תהלים יד:ב ← תהלים נג:ג').getAttribute('href')).toBe('/sequences/7')
    expect(screen.getByRole('columnheader', { name: 'מוקדם' })).toBeTruthy()
    expect(screen.queryByText('Earlier')).toBeNull()
  })
})

const PROFILE: RewriteProfile = {
  a_book: 8,
  b_book: 37,
  verse_pairs: 144,
  a_words: 2221,
  b_words: 2160,
  spelling: 157,
  form: 148,
  substitution: 302,
  omitted: 313,
  added: 252,
  moved: 17,
  to_plene: 135,
  to_defective: 15,
}
const REWRITES: RewritesResponse = {
  a_book: 8,
  b_book: 37,
  op: null,
  max_q: 0.05,
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    { a_book: 8, b_book: 37, op: 'substitution', a_key: '3068', b_key: '430', a_he: 'יהוה', b_he: 'אלהים', n: 14, base: 61, rate: 0.2295, g2: 77.6, p: 1e-18, q: 5e-16 },
  ],
}

describe('ChangesPage rewrites', () => {
  it('shows a book pair profile and its systematic changes', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const books = [
          { book_id: 8, name: 'II Samuel', he_name: 'שמואל ב', osis: '2Sam', section: 'Prophets', n_chapters: 24 },
          { book_id: 37, name: 'I Chronicles', he_name: 'דברי הימים א', osis: '1Chr', section: 'Writings', n_chapters: 29 },
        ]
        const body =
          p === '/api/books' ? books : p === '/api/rewrite-profiles' ? [PROFILE] : p === '/api/rewrites' ? REWRITES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/changes?view=rewrites&pair=8-37']}>
          <Routes>
            <Route path="/changes" element={<ChangesPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('14 / 61')).toBeTruthy()
    expect(screen.getByText('אלהים')).toBeTruthy()
    expect(await screen.findByText(/135× and drops one 15× \(\s*90% fuller\)/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Examples' }).getAttribute('href')).toBe('/changes?op=substitution&a=8&b=37')
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/rewrites?a_book=8&b_book=37&max_q=0.05'))).toBe(true))
    expect(calls.some((c) => c.startsWith('/api/changes'))).toBe(false)
  })
})
