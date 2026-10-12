// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { HiddenRootsResponse, RootFamily, RootPairsResponse, RootsResponse, UnitSummary, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { RootPage } from './RootPage'
import { RootsPage } from './RootsPage'

const chapter = (book: number, ch: number, en: string, he: string): UnitSummary => ({
  unit_id: `c:${book}:${ch}`,
  unit_type: 'chapter',
  label_en: en,
  label_he: he,
  book_id: book,
  start_verse_id: 0,
  end_verse_id: 30,
  n_verses: 31,
  marker: null,
})
const verse = (id: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 0,
  chapter: 37,
  verse: 5,
  ref: `V${id}`,
  ref_he: 'הפניה',
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const ROOTS: RootsResponse = {
  meta: {
    families: 1225,
    family_lemmas: 4442,
    window: 3,
    shuffles: 200,
    pairs: { cognate: 1677, other: 514, inf_abs: 473 },
    tests: {
      cognate: { observed: 1677, expected: 406.2, ratio: 4.13, p: 0.005 },
      other: { observed: 514, expected: 241.1, ratio: 2.13, p: 0.005 },
    },
    known_top_lemma: 6,
    known_top_root: 6,
    known_better: 3,
    top: 12,
    hidden: 896,
  },
  known: [{ unit: chapter(0, 37, 'Genesis 37', 'בראשית לז'), root: '2492', root_he: 'חָלַם', lemma_rank: 4, root_rank: 1 }],
  books: [{ book_id: 0, words: 20000, cognate: 120, expected: 30, inf_abs: 40 }],
}
const PAIRS: RootPairsResponse = {
  kind: null,
  book: null,
  unit: null,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      pair_id: 1,
      verse_id: 7,
      label: 'Genesis 37:5',
      label_he: 'בראשית לז:ה',
      kind: 'cognate',
      root: '2492',
      root_he: 'חָלַם',
      a: { lemma: '2492', he_lemma: 'חלם', n_verses: 25 },
      b: { lemma: '2472', he_lemma: 'חלום', n_verses: 50 },
      verse: verse(7, ['וַיַּחֲלֹם', 'יוֹסֵף', 'חֲלוֹם']),
      marks: { '0': 0, '2': 1 },
    },
  ],
}
const HIDDEN: HiddenRootsResponse = {
  book: null,
  unit: null,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      unit: chapter(2, 13, 'Leviticus 13', 'ויקרא יג'),
      rank: 9,
      root: '2930',
      root_he: 'טָמֵא',
      count: 23,
      g2: 113,
      n_words: 2,
      lemma_rank: 14,
      lemmas: [
        { lemma: '2931', he_lemma: 'טמא', n_verses: 80 },
        { lemma: '2930', he_lemma: 'טמא', n_verses: 150 },
      ],
    },
  ],
}
const FAMILY: RootFamily = {
  root: '2492',
  root_he: 'חָלַם',
  members: [
    { lemma: '2472', he_lemma: 'חלום', n_verses: 50 },
    { lemma: '2492', he_lemma: 'חלם', n_verses: 25 },
  ],
  links: { '2472': 'from' },
  n_verses: 70,
  by_book: [{ book_id: 0, n_verses: 30 }],
  book: null,
  total: 70,
  offset: 0,
  limit: 50,
  items: [{ verse: verse(7, ['וַיַּחֲלֹם', 'יוֹסֵף', 'חֲלוֹם']), label_en: 'Genesis 37:5', label_he: 'בראשית לז:ה', display_idxs: [0, 2] }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', roots: RootsResponse = ROOTS) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/books'
          ? []
          : p === '/api/roots'
            ? roots
            : p === '/api/roots/pairs'
              ? PAIRS
              : p === '/api/roots/hidden'
                ? HIDDEN
                : p === '/api/root/2492'
                  ? FAMILY
                  : p.startsWith('/api/unit/')
                    ? { unit: chapter(0, 37, 'Genesis 37', 'בראשית לז'), verses: [], parents: [], prev_id: null, next_id: null }
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
            <Route path="/roots" element={<RootsPage />} />
            <Route path="/root/:root" element={<RootPage />} />
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

describe('RootsPage', () => {
  it('states the side-by-side test and lists the pairs with both words marked', async () => {
    const { container } = renderAt('/roots')
    expect(await screen.findByText(/1,677 times, against 406 with the content words of each chapter shuffled \(4\.1×, p 0\.005 over 200 shuffles\)/)).toBeTruthy()
    expect(screen.getByText(/1,225 root families gather 4,442 words/)).toBeTruthy()
    expect(screen.getByText(/infinitive absolute with its own verb .* 473 times/)).toBeTruthy()
    await screen.findByRole('link', { name: /Genesis 37:5/ })
    expect(container.querySelectorAll('.root-pair .w-focus')).toHaveLength(1)
    expect(container.querySelectorAll('.root-pair .w-shared')).toHaveLength(1)
    expect(screen.getByRole('link', { name: /root חָלַם/ }).getAttribute('href')).toBe('/root/2492')
    fireEvent.change(screen.getByRole('combobox', { name: 'Kind' }), { target: { value: 'inf_abs' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/roots?kind=inf_abs'))
  })

  it('shows the Leitworte named in advance and the hidden key roots', async () => {
    renderAt('/roots?view=key')
    expect(await screen.findByText(/Counted by root, 6 of 1 Leitworte that scholars name are among their chapter's top 12; counted by word, 6. The root ranks higher for 3/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Genesis 37' }).getAttribute('href')).toBe('/unit/c%3A0%3A37?structure=1')
    expect(await screen.findByRole('link', { name: 'Leviticus 13' })).toBeTruthy()
    expect(screen.getByText(/896 chapter Leitworte among the top 12 by root/)).toBeTruthy()
  })

  it('limits the pairs to a unit from the dossier', async () => {
    const { calls } = renderAt('/roots?unit=c%3A0%3A37')
    await screen.findByRole('link', { name: /Genesis 37:5/ })
    expect(calls.some((c) => c.startsWith('/api/roots/pairs?') && c.includes('unit=c%3A0%3A37'))).toBe(true)
    expect(document.querySelector('.unit-filter')?.textContent).toContain('Genesis 37')
  })

  it('reads in Hebrew', async () => {
    renderAt('/roots', 'he')
    expect(await screen.findByText(/מושא פנימי: ויחלם חלום, זבחו זבח/)).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/roots', 'en', { meta: {}, known: [], books: [] })
    expect(await screen.findByText(/run `bsim roots`/)).toBeTruthy()
  })
})

describe('RootPage', () => {
  it('lists the family with its derivations and the verses holding any of its words', async () => {
    const { container } = renderAt('/root/2492')
    expect(await screen.findByText(/2 words of this root, in 70 verses/)).toBeTruthy()
    expect(screen.getByRole('link', { name: /חלום 50 verses \(from\)/ }).getAttribute('href')).toBe('/lemma/2472')
    expect(container.querySelectorAll('.hit-text .w-shared')).toHaveLength(2)
  })
})
