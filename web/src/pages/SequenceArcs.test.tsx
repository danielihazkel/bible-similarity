// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SequenceArcsResponse, SequenceSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { SequencesPage } from './SequencesPage'

const seq = (id: number, a: [number, number, number], b: [number, number, number], n: number, sameChapter = false): SequenceSummary => ({
  seq_id: id,
  a_start: a[1],
  a_end: a[2],
  b_start: b[1],
  b_end: b[2],
  direction: 'forward',
  a_label: `A${id}`,
  b_label: `B${id}`,
  a_label_he: `א${id}`,
  b_label_he: `ב${id}`,
  a_book: a[0],
  b_book: b[0],
  same_chapter: sameChapter,
  n_pairs: n,
  score: n,
  q: 0,
  n_gold: 0,
})
const BOOKS = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
  { book_id: 2, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const ARCS: SequenceArcsResponse = {
  max_q: 0.05,
  direction: 'forward',
  total: 5,
  books: [
    { book_id: 0, start: 0, end: 499 },
    { book_id: 1, start: 500, end: 799 },
    { book_id: 2, start: 800, end: 999 },
  ],
  items: [seq(1, [0, 10, 20], [2, 900, 910], 11), seq(2, [0, 100, 110], [1, 600, 605], 6), seq(3, [1, 700, 701], [1, 702, 703], 2, true)],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en') {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? BOOKS : p === '/api/sequences/arcs' ? ARCS : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const out = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/sequences" element={<SequencesPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { calls, container: out.container }
}

const startX = (el: Element) => Number(el.querySelector('path')!.getAttribute('d')!.split(' ')[1])

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('SequenceArcs', () => {
  it('draws every chain as an arc linking to it, and fetches no page of the list', async () => {
    const { calls, container } = renderAt('/sequences?view=arcs')
    const arc = await screen.findByRole('link', { name: 'A1 ↔ B1, 11 verse pairs' })
    expect(arc.getAttribute('href')).toBe('/sequences/1')
    expect(container.querySelectorAll('.arc')).toHaveLength(3)
    expect(container.querySelectorAll('path.arc-cross')).toHaveLength(2)
    expect(screen.getByText(/3 chains, 2 of them between books \(the 3 strongest of 5\)/)).toBeTruthy()
    expect(calls).toContain('/api/sequences/arcs?max_q=0.05&direction=forward')
    expect(calls.some((c) => c.startsWith('/api/sequences?'))).toBe(false)
    // the thickest arc is drawn last, on top
    expect([...container.querySelectorAll('.arc')].at(-1)?.getAttribute('aria-label')).toMatch(/^A1/)
    // book labels where they fit
    expect([...container.querySelectorAll('.arc-book-label')].map((e) => e.textContent)).toEqual(['Gen', 'Exod', 'Ps'])
  })

  it('applies the list filters and brings out a book', async () => {
    const { calls, container } = renderAt('/sequences?view=arcs&cross=1&book=1&q=all&order=any')
    await screen.findByRole('link', { name: /A2/ })
    expect(calls).toContain('/api/sequences/arcs')
    expect(container.querySelectorAll('.arc')).toHaveLength(2) // the within-book chain left out
    expect(container.querySelectorAll('.arc.faded')).toHaveLength(1) // A1: Genesis–Psalms
    expect(container.querySelector('.arc-book.on rect title')?.textContent).toBe('Exodus')
    fireEvent.click(screen.getByRole('radio', { name: 'List' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).not.toContain('view=arcs'))
  })

  it('runs right to left in Hebrew', async () => {
    const { container } = renderAt('/sequences?view=arcs', 'he')
    const arc = await screen.findByRole('link', { name: 'א1 ↔ ב1, 11 זוגות פסוקים' })
    const genesis = container.querySelector('.arc-book rect')!
    expect(Number(genesis.getAttribute('x'))).toBeGreaterThan(400) // Genesis on the right
    expect(startX(arc)).toBeLessThan(Number(genesis.getAttribute('x')))
  })
})
