// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, CompareResponse, SearchResponse, UnitSummary, Verse } from '../api/types'
import { BooksPage } from './BooksPage'
import { ComparePage } from './ComparePage'
import { SearchPage } from './SearchPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const verse = (id: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 26,
  chapter: 14,
  verse: id,
  ref: `Ps ${id}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const unit = (id: string, label: string, first: number, last: number): UnitSummary => ({
  unit_id: id,
  unit_type: 'chapter',
  label_en: label,
  label_he: label,
  book_id: 26,
  start_verse_id: first,
  end_verse_id: last,
  n_verses: last - first + 1,
  marker: null,
})
const SEARCH: SearchResponse = {
  query: 'נבל',
  normalized: 'נבל',
  tokens: ['נבל'],
  mode: 'fused',
  k: 10,
  hits: [
    {
      rank: 1,
      score: 0.03,
      lex_score: 5,
      lex_rank: 1,
      sem_score: 0.4,
      sem_rank: 2,
      verse: verse(1, ['אָמַר', 'נָבָל']),
      label_en: 'Psalms 14:1',
      label_he: 'תהלים יד א',
    },
  ],
}
const COMPARE: CompareResponse = {
  a: unit('c:26:14', 'Psalms 14', 1, 1),
  b: unit('c:26:53', 'Psalms 53', 2, 2),
  bma: 0.912,
  a_to_b: [{ src: 1, tgt: 2, cosine: 0.95, shared: [{ lemma: '5036', he_lemma: 'נבל' }] }],
  b_to_a: [{ src: 2, tgt: 1, cosine: 0.95, shared: [{ lemma: '5036', he_lemma: 'נבל' }] }],
  verses: { '1': verse(1, ['אָמַר', 'נָבָל']), '2': verse(2, ['אָמַר', 'נָבָל']) },
}

const DIFF = { a: 1, b: 2, a_marks: {}, b_marks: { '1': 'substitution' }, counts: { same: 1, substitution: 1 }, shared: 0.5, loose: false }

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function mockApi(encoderReady: boolean, encoderError: string | null = null) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/books'
          ? BOOKS
          : p === '/api/search'
            ? SEARCH
            : p === '/api/compare'
              ? COMPARE
              : p === '/api/meta'
                ? { build: {}, runtime: { encoder_ready: encoderReady, encoder_error: encoderError } }
                : p === '/api/resolve'
                  ? { query: '', unit: null }
                  : p.startsWith('/api/unit/')
                    ? { unit: COMPARE.a, verses: [], parents: [], prev_id: null, next_id: null }
                    : p === '/api/diff'
                      ? DIFF
                      : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  return calls
}

function renderAt(path: string, routes: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>{routes}</Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('BooksPage', () => {
  it('groups the books by section and links each to its page', async () => {
    mockApi(true)
    renderAt('/', <Route path="/" element={<BooksPage />} />)
    expect(await screen.findByRole('heading', { name: /Torah/ })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Writings/ })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Psalms/ }).getAttribute('href')).toBe('/browse/26')
  })
})

describe('SearchPage', () => {
  it('waits for the semantic encoder while it is still loading', async () => {
    const calls = mockApi(false)
    renderAt('/search?q=נבל', <Route path="/search" element={<SearchPage />} />)
    expect(await screen.findByText(/semantic encoder is still loading/)).toBeTruthy()
    expect(screen.getByText('Waiting for the semantic encoder…')).toBeTruthy()
    expect(calls.some((c) => c.startsWith('/api/meta'))).toBe(true)
    expect(calls.some((c) => c.startsWith('/api/search'))).toBe(false)
  })

  it('says when the semantic encoder failed and offers lexical search', async () => {
    const calls = mockApi(false, 'no model')
    renderAt('/search?q=נבל', <Route path="/search" element={<SearchPage />} />)
    expect(await screen.findByText(/failed to load on the server \(no model\)/)).toBeTruthy()
    expect(screen.queryByText(/still loading/)).toBeNull()
    expect(calls.some((c) => c.startsWith('/api/search'))).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Search lexically' }))
    expect(await screen.findByText('Psalms 14:1')).toBeTruthy()
  })

  it('does not check the encoder for lexical search', async () => {
    const calls = mockApi(false)
    renderAt('/search?q=נבל&mode=lexical', <Route path="/search" element={<SearchPage />} />)
    expect(await screen.findByText('Psalms 14:1')).toBeTruthy()
    expect(screen.queryByText(/semantic encoder is still loading/)).toBeNull()
    expect(calls.some((c) => c.startsWith('/api/meta'))).toBe(false)
  })

  it('stays quiet once the encoder is ready', async () => {
    mockApi(true)
    renderAt('/search?q=נבל', <Route path="/search" element={<SearchPage />} />)
    expect(await screen.findByText('Psalms 14:1')).toBeTruthy()
    await waitFor(() => expect(screen.queryByText(/semantic encoder is still loading/)).toBeNull())
  })
})

describe('ComparePage', () => {
  it('asks for two units, then shows the BMA and the verse alignment', async () => {
    mockApi(true)
    const empty = renderAt('/compare', <Route path="/compare" element={<ComparePage />} />)
    expect(await screen.findByText(/Choose two units/)).toBeTruthy()
    empty.unmount()
    const page = renderAt('/compare?a=c:26:14&b=c:26:53', <Route path="/compare" element={<ComparePage />} />)
    expect(await page.findByText('0.912')).toBeTruthy()
    expect(page.container.querySelectorAll('.sim-4').length).toBeGreaterThan(0)
    fireEvent.click(page.getByTitle('Swap A and B'))
    await waitFor(() => expect(page.getByTestId('loc').textContent).toBe('/compare?a=c%3A26%3A53&b=c%3A26%3A14'))
  })

  it('marks the word changes of the hovered pair', async () => {
    Element.prototype.scrollIntoView = vi.fn() // not in jsdom
    const calls = mockApi(true)
    const page = renderAt('/compare?a=c:26:14&b=c:26:53&marks=changes', <Route path="/compare" element={<ComparePage />} />)
    await page.findByText('0.912')
    fireEvent.mouseEnter(page.container.querySelector('.align-row')!)
    await waitFor(() => expect(page.container.querySelectorAll('.align-row .w-diff-substitution')).toHaveLength(1))
    expect(calls.some((c) => c.startsWith('/api/diff?a=1&b=2'))).toBe(true)
    expect(calls.some((c) => c.startsWith('/api/explain'))).toBe(false)
    expect(page.getByText(/50% of the words keep their lemma/)).toBeTruthy()
    fireEvent.click(page.getByRole('button', { name: 'Shared words' }))
    await waitFor(() => expect(page.getByTestId('loc').textContent).toBe('/compare?a=c%3A26%3A14&b=c%3A26%3A53'))
  })
})
