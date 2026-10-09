// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CitationListResponse, CitationsResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { CitationsPage } from './CitationsPage'

const fam = (verses: number, resolved: number, share: number, nul: number, p: number) => ({
  verses,
  resolved,
  share,
  null_share: nul,
  p,
  pct_median: 0.6,
})
const META: CitationsResponse = {
  meta: {
    citations: 116,
    resolved: 41,
    families: { written: fam(36, 4, 0.11, 0.08, 0.36), word: fam(31, 10, 0.32, 0.27, 0.32), command: fam(49, 27, 0.55, 0.32, 0.0008) },
    gold: { named: 20, found: 20, missing: [], top1: 15, top_k: 17, k: 5, resolved: 10, resolved_right: 10 },
    word_lag_median: 636.5,
    book_pairs: 17,
  },
  books: [
    { book_id: 10, target_book: 9, n: 2 },
    { book_id: 10, target_book: 4, n: 1 },
  ],
}
const verse = (id: number, book: number, text: string): Verse => ({
  verse_id: id,
  book_id: book,
  chapter: 1,
  verse: 1,
  ref: `B${id}`,
  ref_he: 'הפניה',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const LIST: CitationListResponse = {
  family: null,
  resolved: null,
  book: null,
  unit: null,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      cite_id: 3,
      family: 'written',
      verse_id: 9813,
      book_id: 10,
      label: 'II Kings 14:6',
      label_he: 'מלכים ב יד:ו',
      formula: 'ככתוב',
      verse: verse(9813, 10, 'כַּכָּתוּב בְּסֵפֶר תּוֹרַת־מֹשֶׁה'),
      target: verse(5552, 4, 'לֹא־יוּמְתוּ אָבוֹת עַל־בָּנִים'),
      target_label: 'Deuteronomy 24:16',
      target_label_he: 'דברים כד:טז',
      score: 17.2,
      pct: 0.99,
      resolved: true,
      candidates: [
        { verse_id: 5552, label: 'Deuteronomy 24:16', label_he: 'דברים כד:טז', score: 17.2 },
        { verse_id: 4396, label: 'Numbers 27:3', label_he: 'במדבר כז:ג', score: 9.1 },
      ],
      gold_rank: 1,
      named: true,
    },
  ],
}
const BOOKS = [
  { book_id: 4, name: 'Deuteronomy', he_name: 'דברים', osis: 'Deut', section: 'Torah', n_chapters: 34 },
  { book_id: 9, name: 'I Kings', he_name: 'מלכים א', osis: '1Kgs', section: 'Prophets', n_chapters: 22 },
  { book_id: 10, name: 'II Kings', he_name: 'מלכים ב', osis: '2Kgs', section: 'Prophets', n_chapters: 25 },
]

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', meta: CitationsResponse = META) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? BOOKS : p === '/api/citations' ? meta : p === '/api/citations/list' ? LIST : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/citations" element={<CitationsPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return calls
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('CitationsPage', () => {
  it('measures each formula against random verses and shows a citation with its source', async () => {
    const calls = renderAt('/citations')
    expect(await screen.findByText(/As commanded: 27 of 49 resolved \(55%\), against 32%/)).toBeTruthy()
    expect(screen.getByText(/20 citations whose source scholarship names, 15 find it first/)).toBeTruthy()
    expect(screen.getByText(/10 of the 10 resolved ones are right/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'II Kings → I Kings: 2' }).getAttribute('href')).toBe('/citations?book=10&resolved=1#citation-list')
    expect((await screen.findByRole('link', { name: 'Deuteronomy 24:16' })).getAttribute('href')).toBe('/unit/v%3A5552')
    expect(screen.getByText('named source found')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Compare' }).getAttribute('href')).toContain('v%3A9813')
    expect(screen.getByRole('link', { name: 'Numbers 27:3' })).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'The word fulfilled' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/citations?family=word'))
    await waitFor(() => expect(calls).toContain('/api/citations/list?family=word&limit=20&offset=0'))
    fireEvent.click(screen.getByLabelText('Resolved only'))
    await waitFor(() => expect(calls).toContain('/api/citations/list?family=word&resolved=true&limit=20&offset=0'))
  })

  it('filters by unit, in Hebrew', async () => {
    const calls = renderAt('/citations?unit=v:5552', 'he')
    expect(await screen.findByRole('heading', { name: 'הפניות', level: 1 })).toBeTruthy()
    await screen.findByRole('link', { name: 'דברים כד:טז' })
    expect(calls).toContain('/api/citations/list?unit=v%3A5552&limit=20&offset=0')
    expect(screen.getByText(/כאשר צוה: 27 מתוך 49 זוהו/)).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/citations', 'en', { meta: {}, books: [] })
    expect(await screen.findByText(/run `bsim citations`/)).toBeTruthy()
  })
})
