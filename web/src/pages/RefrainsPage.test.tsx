// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RefrainsListResponse, RefrainsResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { RefrainsPage } from './RefrainsPage'

const verse = (id: number, n: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 16,
  chapter: 4,
  verse: n,
  ref: `Amos 4:${n}`,
  ref_he: `עמוס ד:${n}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const REFRAIN = ['וְלֹא־שַׁבְתֶּם', 'עָדַי', 'נְאֻם־יְהוָה׃']
const DATA: RefrainsResponse = {
  meta: {
    min_tokens: 3,
    min_count: 3,
    max_gap: 20,
    alpha: 0.05,
    shuffles: 20,
    detect: { observed: 925, expected: 45.5 },
    refrains: 925,
    distinct: 551,
    known_found: 8,
    regular: { testable: 179, regular: 27, share: 0.151, p: 3e-7 },
    turns: { n: 2270, observed: 0.679, expected: 0.65, p: 0.001 },
  },
  known: [
    { name: 'ולא שבתם עדי', first_vid: 6, label: 'Amos 4:6', label_he: 'עמוס ד:ו', n_verses: 5, refrain_id: 1, text: 'וְלֹא־שַׁבְתֶּם עָדַי נְאֻם־יְהוָה׃', k: 5, q: 0.001 },
    { name: 'השבעתי אתכם בנות ירושלם', first_vid: 20, label: 'Song of Songs 2:7', label_he: 'שיר השירים ב:ז', n_verses: 3, refrain_id: null, text: null, k: null, q: null },
  ],
  books: [{ book_id: 16, refrains: 3, strongest: 2 }],
}
const LIST: RefrainsListResponse = {
  book: null,
  unit: null,
  strongest: true,
  known: false,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      refrain_id: 1,
      book_id: 16,
      k: 5,
      n_tokens: 5,
      p: 1e-6,
      q: 0.001,
      cv: 0.3,
      regular_p: null,
      turn: 0.7,
      strongest: true,
      known: 'ולא שבתם עדי',
      text: 'וְלֹא־שַׁבְתֶּם עָדַי נְאֻם־יְהוָה׃',
      lemmas: '3808 7725 5704 5002 3068',
      occurrences: [6, 8, 9, 10, 11].map((n) => ({ verse_id: n, label: `Amos 4:${n}`, label_he: `עמוס ד:${n}`, first: 1, last: 3 })),
      verses: [verse(6, 6, ['בְּכָל־מְקוֹמֹתֵיכֶם', ...REFRAIN]), verse(8, 8, ['וְלֹא', ...REFRAIN]), verse(9, 9, ['הִכֵּיתִי', ...REFRAIN])],
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: RefrainsResponse = DATA) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/books'
          ? []
          : p === '/api/refrains'
            ? data
            : p === '/api/refrains/list'
              ? LIST
              : p.startsWith('/api/unit/')
                ? { unit: { unit_id: 'c:16:4', unit_type: 'chapter', label_en: 'Amos 4', label_he: 'עמוס ד', book_id: 16, start_verse_id: 0, end_verse_id: 12, n_verses: 13, marker: null }, verses: [], parents: [], prev_id: null, next_id: null }
                : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/refrains" element={<RefrainsPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { ...r, calls }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('RefrainsPage', () => {
  it('states the three tests', async () => {
    renderAt('/refrains')
    expect(await screen.findByText(/925 refrains, against 46 runs as strong with the verses of each book shuffled \(20 shuffles\); 551 once/)).toBeTruthy()
    expect(screen.getByText(/8 of 2 found/)).toBeTruthy()
    expect(screen.getByText(/27 of 179 refrains that can be tested .* \(15% against 5%, p < 0\.001\)/)).toBeTruthy()
    expect(screen.getByText(/scores 0\.68 against 0\.65 .* p 0\.001 over 2,270 verses/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Amos 4:6' }).getAttribute('href')).toBe('/read/v%3A6?layers=refrains')
    expect(screen.getByText('not found')).toBeTruthy()
  })

  it('lists each refrain with its verses marked and the rest as references', async () => {
    const { container } = renderAt('/refrains')
    await screen.findByText('5 verses')
    expect(container.querySelectorAll('.refrain .hit-text')).toHaveLength(3)
    expect(container.querySelectorAll('.refrain .hit-text .w-shared')).toHaveLength(9)
    expect(screen.getByText(/\+ 2 more verses/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Amos 4:11' }).getAttribute('href')).toBe('/unit/v%3A11')
    expect(screen.getByRole('link', { name: 'Read in the passage' }).getAttribute('href')).toBe('/read/v%3A6?layers=refrains')
    expect(container.querySelector('.refrain .hit-head .muted')?.textContent).toBe('Amos 4:6 – Amos 4:11 · q 0.001 · turn 0.70 · named in advance: ולא שבתם עדי')
  })

  it('filters through the URL and shows every refrain of a unit from the dossier', async () => {
    const { calls } = renderAt('/refrains?unit=c%3A16%3A4&all=1')
    await screen.findByText('5 verses')
    expect(calls.some((c) => c.startsWith('/api/refrains/list?') && c.includes('unit=c%3A16%3A4') && c.includes('strongest=0'))).toBe(true)
    fireEvent.click(screen.getByLabelText('Named in advance only'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/refrains?unit=c%3A16%3A4&all=1&known=1'))
    fireEvent.click(screen.getByLabelText('Strongest of each group'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/refrains?unit=c%3A16%3A4&known=1'))
  })

  it('reads in Hebrew', async () => {
    renderAt('/refrains', 'he')
    expect(await screen.findByRole('heading', { name: 'פזמונים חוזרים', level: 1 })).toBeTruthy()
    expect(await screen.findByText(/נמצאו 8 מתוך 2/)).toBeTruthy()
    expect(await screen.findByRole('link', { name: 'עמוס ד:ו' })).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/refrains', 'en', { meta: {}, known: [], books: [] })
    expect(await screen.findByText(/run `bsim refrains`/)).toBeTruthy()
  })
})
