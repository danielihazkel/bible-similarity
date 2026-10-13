// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, DialogueBookResponse, DialogueExchangesResponse, DialogueParty, DialogueResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { SpeechPage } from './SpeechPage'

const BOOKS: Book[] = [{ book_id: 2, name: 'Leviticus', he_name: 'ויקרא', osis: 'Lev', section: 'Torah', n_chapters: 27 }]
const GOD: DialogueParty = { key: 'divine', he: null, rank: 2 }
const MOSES: DialogueParty = { key: '4872', he: 'משה', rank: 0 }
const AARON: DialogueParty = { key: '175', he: 'אהרן', rank: 0 }
const DIALOGUE: DialogueResponse = {
  meta: {
    quotations: 5489,
    with_addressee: 2901,
    addressee: { explicit: 1264, vocative: 494, pronoun: 622, turn: 521 },
    reliable: ['explicit', 'vocative'],
    hand_check: { explicit: [21, 21], vocative: [11, 11], pronoun: [4, 9], turn: [6, 9] },
    tests: {
      deference: {
        observed: 11.58, null: 1.14, p: 0.001, holds: true,
        up: { rate: 13.12, count: 99, of: 7548, quotations: 229 }, rest: { rate: 1.54, count: 108, of: 70124, quotations: 974 },
      },
      particle: {
        observed: 0.098, null: 0.002, p: 0.003, holds: true,
        up: { rate: 0.1405, count: 26, of: 185, quotations: 229 }, rest: { rate: 0.0428, count: 86, of: 2008, quotations: 974 },
      },
      last_word: { observed: 96, expected: 89.42, exchanges: 170, p: 0.166, holds: false },
    },
    sensitivity: {
      deference: { observed: 10.37, null: 0.44, p: 0.001, up: { rate: 11.9, count: 113, of: 9507, quotations: 381 }, rest: { rate: 1.5, count: 125, of: 82452, quotations: 1733 } },
      particle: { observed: 0.081, null: -0.01, p: 0.001, up: { rate: 0.13, count: 30, of: 231, quotations: 381 }, rest: { rate: 0.049, count: 117, of: 2382, quotations: 1733 } },
    },
    opener: { observed: 84, expected: 89.42, exchanges: 170, p: 0.82 },
    lengths: { longer: 75, shorter: 90, median_higher: 11.7, median_lower: 11, p: 0.28 },
  },
  books: [{ book_id: 2, n_quotes: 40, n_pairs: 3, n_exchanges: 1 }],
}  // prettier-ignore
const LEV: DialogueBookResponse = {
  book_id: 2,
  pairs: [
    { speaker: GOD, addressee: MOSES, n_quotes: 30, n_words: 9000, n_reliable: 28 },
    { speaker: MOSES, addressee: AARON, n_quotes: 5, n_words: 120, n_reliable: 4 },
    { speaker: MOSES, addressee: GOD, n_quotes: 3, n_words: 40, n_reliable: 1 },
  ],
}
const EXCHANGES: DialogueExchangesResponse = {
  book: 2,
  party: null,
  unequal: false,
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      exchange: 4, book_id: 2, unit_id: 'c:2:10',
      first: { verse_id: 2916, label_en: 'Leviticus 10:16', label_he: 'ויקרא י:טז' },
      last_verse: { verse_id: 2920, label_en: 'Leviticus 10:20', label_he: 'ויקרא י:כ' },
      a: MOSES, b: AARON, turns: 2, a_turns: 1, a_words: 50, b_words: 30, last: '175',
    },
  ],
}  // prettier-ignore

function mockApi(dialogue: DialogueResponse = DIALOGUE) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const path = new URL(url, 'http://x').pathname
      const body =
        path === '/api/books' ? BOOKS
        : path === '/api/dialogue' ? dialogue
        : path === '/api/dialogue/book/2' ? LEV
        : path === '/api/dialogue/exchanges' ? EXCHANGES
        : path === '/api/speech' ? { meta: {}, books: [] }
        : null  // prettier-ignore
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  return calls
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
            <Route path="*" element={<SpeechPage />} />
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

describe('To whom', () => {
  it('opens from the tab and states the addressees, the hand check and the three checks', async () => {
    mockApi()
    renderAt('/speech')
    fireEvent.click(await screen.findByRole('radio', { name: 'To whom' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/speech?view=dialogue'))
    expect(await screen.findByText(/5,489 quotations; an addressee found for 2,901: named in the introduction 1,264/)).toBeTruthy()
    expect(screen.getByText(/named 21 \/ 21, called by name 11 \/ 11, “to him” 4 \/ 9, an answer 6 \/ 9/)).toBeTruthy()
    expect(screen.getByText(/13\.1 times per 1,000 words \(99 in 7,548 words\), against 1\.5 .* \(p 0\.001\)/)).toBeTruthy()
    expect(screen.getByText(/14% of the commands to God or a king \(26 of 185\), against 4% of the others \(p 0\.003\)/)).toBeTruthy()
    expect(screen.getByText(/In 170 exchanges .* the higher one speaks last in 96, against 89\.4/)).toBeTruthy()
    expect(screen.getAllByText('holds')).toHaveLength(2)
    expect(screen.getAllByText('does not hold')).toHaveLength(1)
    expect(screen.getByText(/the higher party opens 84 of the 170 exchanges/)).toBeTruthy()
  })

  it('draws a book’s conversations, lists its pairs and filters the exchanges by a party', async () => {
    const calls = mockApi()
    const { container } = renderAt('/speech?view=dialogue')
    expect(await screen.findByRole('img', { name: /The 3 most active speakers of Leviticus/ })).toBeTruthy()
    expect(container.querySelectorAll('.dlg-edge')).toHaveLength(3)
    expect(container.querySelector('.dlg-node.rank-2 text')?.textContent).toBe('God')
    const rows = [...container.querySelectorAll('.dlg-pairs tbody tr')].map((r) => r.textContent)
    expect(rows[0]).toBe('Godמשה30900028')
    const link = await screen.findByRole('link', { name: 'Leviticus 10:16 – Leviticus 10:20' })
    expect(link.getAttribute('href')).toBe('/read/c%3A2%3A10?layers=speakers')
    expect(screen.getByText(/2 turns: משה 1, אהרן 1 · last word: אהרן/)).toBeTruthy()
    fireEvent.click(screen.getAllByRole('button', { name: 'אהרן' })[0])
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/speech?view=dialogue&party=175'))
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/dialogue/exchanges?') && c.includes('party=175'))).toBe(true))
    expect(await screen.findByRole('button', { name: 'With אהרן ×' })).toBeTruthy()
    fireEvent.click(screen.getByRole('checkbox', { name: /Only God or a king/ }))
    await waitFor(() => expect(calls.some((c) => c.includes('unequal=true'))).toBe(true))
  })

  it('reads in Hebrew', async () => {
    mockApi()
    renderAt('/speech?view=dialogue', 'he')
    expect(await screen.findByRole('radio', { name: 'אל מי' })).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'בדיקות שנקבעו מראש' })).toBeTruthy()
    expect(screen.getAllByText('מתקיימת')).toHaveLength(2)
    expect(await screen.findByRole('link', { name: 'ויקרא י:טז – ויקרא י:כ' })).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    mockApi({ meta: {}, books: [] })
    renderAt('/speech?view=dialogue')
    expect(await screen.findByText(/run `bsim syntax`, `bsim dialogue`/)).toBeTruthy()
  })
})
