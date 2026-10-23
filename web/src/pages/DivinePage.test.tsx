// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, DivinePairsResponse, DivineResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { shareStep } from '../lib/divine'
import { DivinePage } from './DivinePage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const chapter = (book: number, ch: number, y: number, e: number, part: number | null = null) => ({
  unit_id: `c:${book}:${ch}`,
  book_id: book,
  chapter: ch,
  words: 100,
  counts: { ...(y ? { yhwh: y } : {}), ...(e ? { elohim: e } : {}) },
  share: y + e ? y / (y + e) : null,
  part,
})
const DIVINE: DivineResponse = {
  names: ['yhwh', 'elohim', 'adonai', 'el', 'eloah', 'shaddai', 'yah', 'elyon', 'tsevaot'],
  measure: ['yhwh', 'elohim'],
  totals: { yhwh: 6827, elohim: 2599 },
  alpha: 0.05,
  shuffles: 999,
  min_segment: 3,
  elohistic: { book_id: 26, named: [42, 83], tolerance: 2, first: 42, last: 84, shares: [0.85, 0.17, 0.85], gain: 227, p: 0.001, found: true, holds: true },
  doubled: {
    pairs: [{ pair: 0, e: 'Psalms 53:1-7', y: 'Psalms 14:1-7', e_ward: 4, y_ward: 0, same: 4, other: 0 }],
    missing: [],
    e_ward: 6,
    y_ward: 1,
    p: 0.0625,
    holds: false,
  },
  books: [
    { book_id: 0, chapters: 2, words: 200, counts: { yhwh: 3, elohim: 5 }, share: 0.375, split: false, cut1: null, cut2: null, shares: [], gain: null, p: null, q: null },
    { book_id: 26, chapters: 3, words: 300, counts: { yhwh: 9, elohim: 4 }, share: 0.69, split: true, cut1: 2, cut2: 3, shares: [1, 0, 1], gain: 30, p: 0.001, q: 0.02 },
  ],
  chapters: [chapter(0, 1, 0, 5), chapter(0, 2, 3, 0), chapter(26, 1, 5, 0, 1), chapter(26, 2, 0, 4, 2), chapter(26, 3, 0, 0, 3)],
}
const PAIRS: DivinePairsResponse = {
  pairs: [
    {
      pair: 0,
      e: 'Psalms 53:1-7',
      y: 'Psalms 14:1-7',
      e_ward: 4,
      y_ward: 0,
      same: 4,
      other: 0,
      places: [
        { kind: 'e_ward', e_vid: 15100, e_label: 'Psalms 53:3', e_label_he: 'תהלים נג:ג', e_word: 'אלהים', e_name: 'elohim', y_vid: 14000, y_label: 'Psalms 14:2', y_label_he: 'תהלים יד:ב', y_word: 'יהוה', y_name: 'yhwh' },
        { kind: 'same', e_vid: 15100, e_label: 'Psalms 53:3', e_label_he: 'תהלים נג:ג', e_word: 'אלהים', e_name: 'elohim', y_vid: null, y_label: null, y_label_he: null, y_word: null, y_name: null },
      ],
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      const body = u.pathname === '/api/books' ? BOOKS : u.pathname === '/api/divine' && !missing ? DIVINE : u.pathname === '/api/divine/pairs' ? PAIRS : null
      return new Response(JSON.stringify(body ?? { detail: 'the divine names were not computed' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/divine" element={<DivinePage />} />
            <Route path="/read/:unit" element={<p>reader</p>} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

const plain = (s: string | null | undefined) => (s ?? '').replace(/[⁨⁩]/g, '')

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('shareStep', () => {
  it('puts a share on two arms around a neutral middle', () => {
    expect([1, 0.9, 0.7, 0.5, 0.3, 0.05, 0].map(shareStep)).toEqual(['y2', 'y2', 'y1', 'mid', 'e1', 'e2', 'e2'])
    expect(shareStep(null)).toBe('none')
  })
})

describe('DivinePage', () => {
  it('states both checks with their verdicts', async () => {
    renderAt('/divine')
    const elo = (await screen.findByRole('heading', { name: /The Elohistic Psalter/ })).closest('article')!
    expect(within(elo).getByText('Borne out')).toBeTruthy()
    expect(plain(elo.textContent)).toContain('Psalms falls into 1–41, 42–84 and 85–150, with יהוה 85%, 17%, 85% of the two')
    const dbl = screen.getByRole('heading', { name: /doubled psalms\s*Not borne out/ }).closest('article')!
    expect(within(dbl).getByText('Not borne out')).toBeTruthy()
    expect(plain(dbl.textContent)).toContain('has אלהים where the other has יהוה 6 times, and the reverse 1 time (sign test, p 0.06)')
  })

  it('draws every chapter by its mix, marks the cuts beyond chance and opens a chapter in the reader', async () => {
    const { container } = renderAt('/divine')
    await screen.findByRole('img', { name: 'Psalms: chapters by the mix of the names' })
    const cells = [...container.querySelectorAll('rect.dv-cell')]
    expect(cells.map((c) => c.getAttribute('class'))).toEqual(['dv-cell dv-e2', 'dv-cell dv-y2', 'dv-cell dv-y2', 'dv-cell dv-e2', 'dv-cell dv-none'])
    expect(plain(cells[1].querySelector('title')?.textContent)).toBe('Genesis 2: יהוה 3, אלהים 0')
    // Psalms is cut beyond chance (q 0.02) at its chapters 2 and 3; Genesis is not split
    expect(container.querySelectorAll('rect.dv-cut')).toHaveLength(2)
    fireEvent.click(cells[3])
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/read/c%3A26%3A2?layers=divine'))
  })

  it('lists the books and a book’s chapters', async () => {
    renderAt('/divine')
    const table = await screen.findByRole('region', { name: 'Books' })
    const psalms = await within(table).findByRole('button', { name: 'Psalms' })
    const row = psalms.closest('tr')!
    expect(row.className).toBe('dv-sig')
    expect([...row.querySelectorAll('td')].map((td) => td.textContent)).toEqual(['Psalms', '3', '9', '4', '0', '69%', '2, 3', '100% · 0% · 100%', '0.001', '0.02'])
    fireEvent.click(psalms)
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/divine?book=26'))
    const chapters = screen.getByRole('region', { name: 'Psalms, chapter by chapter' })
    expect(within(chapters).getByRole('link', { name: '2' }).getAttribute('href')).toBe('/read/c%3A26%3A2?layers=divine')
    expect(within(chapters).getAllByRole('row')).toHaveLength(4)
  })

  it('aligns the doubled psalms name by name', async () => {
    renderAt('/divine')
    const pair = await screen.findByRole('region', { name: 'Psalms 53:1-7 and Psalms 14:1-7' })
    const rows = within(pair).getAllByRole('row').slice(1)
    expect(plain(rows[0].textContent)).toContain('אלהים for יהוה')
    expect(rows[0].className).toBe('dv-kind-e_ward')
    expect(within(rows[0]).getByRole('link', { name: 'Psalms 14:2' }).getAttribute('href')).toBe('/unit/v%3A14000')
    expect(rows[1].textContent).toContain('(no word)')
  })

  it('says when the stage did not run', async () => {
    renderAt('/divine', 'en', true)
    expect(await screen.findByText(/The divine names were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/divine', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('שמות האל')
    expect(await screen.findByText('מתאשר')).toBeTruthy()
    expect(await screen.findByRole('img', { name: 'תהלים: הפרקים לפי תמהיל השמות' })).toBeTruthy()
  })
})
