// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { KetivResponse, KqPairsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { KetivPage } from './KetivPage'

const KETIV: KetivResponse = {
  meta: {
    pairs: 1260,
    classes: { vowel_letter: 583, swap: 457, division: 25 },
    grammar: { spelling: 470, form: 545, word: 230 },
    euphemisms: 14,
    features: [['number s>p', 142], ['prefix ->c', 32]],
    checks: {
      lookalike: {
        all: { n: 457, lookalike: 323, share: 0.707, expected: 0.039, p: 0 },
        without_wy: { n: 152, lookalike: 18, share: 0.118, expected: 0.0125, p: 1.2e-12 },
      },
      late_fuller: { late: 0.82, late_n: 114, other: 0.4, other_n: 469, diff: 0.42, p: 0.0058, books: 36 },
      parallel: { qere: 57, ketiv: 11, neither: 29, p: 1.3e-8 },
      plural_suffix: { plural: 142, waw_yw: 82 },
      books: { chi2: 878, p: 1e-160 },
    },
  },
  books: [{ book_id: 34, n: 116, words: 5919, rate: 19.6, vowel_letter: 50, ketiv_fuller: 0.64, swap: 40, division: 2, other_cls: 3, form: 30, word: 10 }],
  letters: [{ pair: 'וי', n: 304, expected: 12.2, ratio: 24.9, p: 0, q: 0, lookalike: true }],
}
const PAIRS: KqPairsResponse = {
  cls: null,
  grammar: null,
  parallel: null,
  euphemism: null,
  book: null,
  unit: null,
  total: 1,
  offset: 0,
  limit: 25,
  items: [
    {
      kq_id: 7,
      verse_id: 8535,
      book_id: 8,
      label: 'II Samuel 22:23',
      label_he: 'שמואל ב כב:כג',
      ketiv: 'משפטו',
      qere: 'מִשְׁפָּטָ֖יו',
      cls: 'vowel_letter',
      fuller: 'qere',
      letters: null,
      grammar: 'form',
      features: ['number s>p'],
      euphemism: false,
      parallel: 'qere',
      partner_vid: 15351,
      partner_label: 'Psalms 18:23',
      partner_label_he: 'תהלים יח:כג',
      partner_form: 'משפטיו',
      verse: {
        verse_id: 8535,
        book_id: 8,
        chapter: 22,
        verse: 23,
        ref: 'II Samuel 22:23',
        ref_he: 'שמואל ב כב:כג',
        text_display: 'כִּ֥י כָל־מִשְׁפָּטָ֖יו לְנֶגְדִּ֑י',
        display_tokens: ['כִּ֥י', 'כָל־', 'מִשְׁפָּטָ֖יו', 'לְנֶגְדִּ֑י'],
        ketiv_note: null,
      },
      display: [2],
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', ketiv: KetivResponse = KETIV) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const body =
        u.pathname === '/api/books'
          ? [{ book_id: 34, name: 'Daniel', he_name: 'דניאל', osis: 'Dan', section: 'Writings', n_chapters: 12 }]
          : u.pathname === '/api/ketiv'
            ? ketiv
            : u.pathname === '/api/ketiv/pairs'
              ? PAIRS
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
            <Route path="/ketiv" element={<KetivPage />} />
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

describe('KetivPage', () => {
  it('states the findings and lists the pairs with their parallel', async () => {
    const { container, calls } = renderAt('/ketiv')
    expect(await screen.findByText(/71% of the one-letter differences/)).toBeTruthy()
    expect(screen.getByText(/82% of the pairs in the Late Biblical Hebrew books/)).toBeTruthy()
    expect(screen.getByText(/writes the reading \(qere\) 57 times and the written form \(ketiv\) 11 times/)).toBeTruthy()
    expect(screen.getByText('number: singular → plural')).toBeTruthy()
    expect(screen.getByText('prefix: none → ו')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Daniel' }).getAttribute('href')).toBe('/ketiv?book=34#ketiv-list')
    const partner = await screen.findByRole('link', { name: /Psalms 18:23 writes משפטיו: the qere/ })
    expect(partner.getAttribute('href')).toBe('/unit/v%3A15351')
    expect([...container.querySelectorAll('.kq-item .w-focus')].map((e) => e.textContent)).toEqual(['מִשְׁפָּטָ֖יו'])
    expect(calls).toContain('/api/ketiv/pairs?limit=25&offset=0')
    fireEvent.change(screen.getByLabelText('Kind'), { target: { value: 'swap' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/ketiv?cls=swap'))
    await waitFor(() => expect(calls).toContain('/api/ketiv/pairs?cls=swap&limit=25&offset=0'))
    fireEvent.click(screen.getByLabelText('Euphemisms only'))
    await waitFor(() => expect(calls).toContain('/api/ketiv/pairs?cls=swap&euphemism=true&limit=25&offset=0'))
  })

  it('filters by unit, in Hebrew', async () => {
    const { calls } = renderAt('/ketiv?unit=v:8535', 'he')
    expect(await screen.findByRole('heading', { name: 'כתיב וקרי', level: 1 })).toBeTruthy()
    await screen.findByRole('link', { name: 'שמואל ב כב:כג' })
    expect(calls).toContain('/api/ketiv/pairs?unit=v%3A8535&limit=25&offset=0')
    expect(screen.getByText('מספר: יחיד → רבים', { selector: '.kq-features-line' })).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/ketiv', 'en', { meta: {}, books: [], letters: [] })
    expect(await screen.findByText(/run `bsim ketiv`/)).toBeTruthy()
  })
})
