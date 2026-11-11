// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MainlinePauses, MainlineResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { MainlinePage } from './MainlinePage'

const DATA: MainlineResponse = {
  clauses: 27167,
  main: 14625,
  background: 12542,
  pauses: 1250,
  min_run: 2,
  max_run: 30,
  opening: 3,
  claim: { excess: -0.0093, null_mean: 0.0287, p: 1, holds: false, paragraphs: 1554 },
  shuffles: 999,
  alpha: 0.05,
  known: [
    { ref: 'Genesis 3:1', found: true, pause: 724 },
    { ref: 'I Samuel 3:1-3', found: false, pause: null },
  ],
  known_found: 1,
  books: [{ book_id: 0, main: 2087, background: 724, share: 0.7424, pauses: 146 }],
}
const verse = (id: number, text: string) => ({
  verse_id: id,
  book_id: 0,
  chapter: 3,
  verse: 1,
  ref: 'Genesis 3:1',
  ref_he: 'בראשית ג:א',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const PAUSES: MainlinePauses = {
  total: 1,
  offset: 0,
  limit: 25,
  order: 'longest',
  book: null,
  items: [
    {
      pause_id: 724,
      unit_id: 's:5',
      book_id: 0,
      first_vid: 55,
      last_vid: 56,
      first_label: 'Genesis 2:25',
      last_label: 'Genesis 3:1',
      first_label_he: 'בראשית ב:כה',
      last_label_he: 'בראשית ג:א',
      n_clauses: 2,
      types: ['WxY0', 'WXQt'],
      known: true,
      verses: [verse(55, 'וְלֹא יִתְבֹּשָׁשׁוּ'), verse(56, 'וְהַנָּחָשׁ הָיָה עָרוּם')],
    },
  ],
}

const calls: string[] = []
function mockApi() {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      calls.push(u.pathname + u.search)
      const body = u.pathname === '/api/mainline' ? DATA : u.pathname === '/api/mainline/pauses' ? PAUSES : u.pathname === '/api/books' ? [] : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: Locale = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/mainline" element={<MainlinePage />} />
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

describe('MainlinePage (DESIGN.md §16.91, D153)', () => {
  it('states the claim and its note, the known pauses, the books and the pauses', async () => {
    mockApi()
    renderAt('/mainline')
    expect(await screen.findByText('Not borne out')).toBeTruthy()
    expect(screen.getByText(/It is -0\.9 points more common there, against 2\.9 with the clauses shuffled/)).toBeTruthy()
    expect(screen.getByText(/mostly open on the main line/)).toBeTruthy()
    expect(screen.getByText('The pauses the commentaries point to are found: 1 of 2.')).toBeTruthy()
    expect(screen.getByText('I Samuel 3:1-3: not found')).toBeTruthy()
    expect(await screen.findByText('Genesis 2:25 – Genesis 3:1')).toBeTruthy()
    expect(screen.getByText('2 background clauses · ו + x-yiqtol, ו + x-qatal · named in advance')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'read it with the layer' }).getAttribute('href')).toBe('/read/s%3A5?layers=mainline')
    expect(screen.getByRole('cell', { name: '74%' })).toBeTruthy()
  })

  it('asks for the canon order and the known pauses through the address', async () => {
    mockApi()
    renderAt('/mainline')
    fireEvent.click(await screen.findByRole('radio', { name: 'Canon order' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Only those named in advance' }))
    expect(screen.getByTestId('loc').textContent).toBe('/mainline?order=canon&known=1')
    await vi.waitFor(() => expect(calls).toContain('/api/mainline/pauses?order=canon&known=true&limit=25&offset=0'))
  })

  it('runs in the Hebrew interface', async () => {
    mockApi()
    renderAt('/mainline', 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'הקו העלילתי של הסיפור' })).toBeTruthy()
    expect(await screen.findByText('לא מתאשר')).toBeTruthy()
  })
})
