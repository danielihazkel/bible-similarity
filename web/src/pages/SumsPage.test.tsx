// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SumsItemsResponse, SumsList, SumsParallelsResponse, SumsResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { SumsPage } from './SumsPage'

const verse = (id: number, ref: string, refHe: string): Verse => ({
  verse_id: id,
  book_id: 3,
  chapter: 1,
  verse: id,
  ref,
  ref_he: refHe,
  text_display: 'שִׁשָּׁה וְאַרְבָּעִים אֶלֶף',
  display_tokens: ['שִׁשָּׁה', 'וְאַרְבָּעִים', 'אֶלֶף'],
  ketiv_note: null,
})
const list = (key: string, sum: number, total: number, holds = true): SumsList => ({
  key,
  total,
  sum,
  n_items: 12,
  adds_up: sum === total,
  expected: holds ? sum === total : sum !== total,
  holds,
  total_verse: verse(46, 'Numbers 1:46', 'במדבר א:מו'),
  total_tok_first: 0,
  total_tok_last: 2,
  first_verse: verse(20, 'Numbers 1:20', 'במדבר א:כ'),
  last_verse: verse(43, 'Numbers 1:43', 'במדבר א:מג'),
})
const test = { numbers: 770, same: 358, tested: 309, one_step: 105, share: 0.3398, expected: 0.1647, p: 0.001 }
const DATA: SumsResponse = {
  lists: [list('num1', 603550, 603550), list('ezra2', 29818, 42360)],
  lists_adding_up: 1,
  lists_holds: true,
  min_value: 2,
  pairs: 23204,
  pairs_used: 2549,
  numbers: 3640,
  numbers_same: 1557,
  numbers_differ: 2083,
  across: test,
  every: { ...test, tested: 1589, share: 0.2656, expected: 0.1629 },
  step_holds: true,
  known_parallels: [
    {
      a: verse(1, 'II Samuel 24:9', 'שמואל ב כד:ט'),
      b: verse(2, 'I Chronicles 21:5', 'דברי הימים א כא:ה'),
      a_value: 800000,
      b_value: 1100000,
      found: true,
      one_step: false,
      expected: false,
      holds: true,
    },
  ],
  known_holds: true,
  min_shared: 2,
  min_big: 10,
  shuffles: 999,
  alpha: 0.05,
}
const ITEMS: SumsItemsResponse = {
  key: 'num1',
  items: [
    { verse: verse(21, 'Numbers 1:21', 'במדבר א:כא'), value: 46500, tok_first: 0, tok_last: 2 },
    { verse: verse(23, 'Numbers 1:23', 'במדבר א:כג'), value: 59300, tok_first: 0, tok_last: 2 },
  ],
}
const PARALLELS: SumsParallelsResponse = {
  across: true,
  differ: true,
  one_step: null,
  book: null,
  total: 1,
  offset: 0,
  limit: 25,
  items: [
    {
      a: verse(5, 'I Kings 5:6', 'מלכים א ה:ו'),
      b: verse(6, 'II Chronicles 9:25', 'דברי הימים ב ט:כה'),
      unit: 'count',
      a_value: 40000,
      b_value: 4000,
      same: false,
      one_step: true,
      a_tok_first: 0,
      a_tok_last: 1,
      b_tok_first: 0,
      b_tok_last: 1,
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

const calls: string[] = []

function renderAt(path = '/sums', locale: 'en' | 'he' = 'en', missing = false) {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(String(url))
      if (missing) return new Response(JSON.stringify({ detail: { code: 'stage_missing', stage: 'sums', message: 'not computed in this build' } }), { status: 503 })
      const u = String(url)
      if (u.includes('/books')) return new Response(JSON.stringify([]))
      return new Response(JSON.stringify(u.includes('/sums/items') ? ITEMS : u.includes('/sums/parallels') ? PARALLELS : DATA))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/sums" element={<SumsPage />} />
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

describe('SumsPage', () => {
  it('states the checks', async () => {
    renderAt()
    const lists = (await screen.findByRole('heading', { name: /Each list adds up/ })).closest('article')!
    expect(within(lists).getByText('Borne out')).toBeTruthy()
    expect(lists.textContent).toContain('1 of the 2 lists add up')
    const step = screen.getByRole('heading', { name: /differ by one step/ }).closest('article')!
    expect(step.textContent).toContain('Of the 309 numbers that differ between parallel verses in different books, 105 (34%) are one step apart')
    expect(step.textContent).toContain('at random, 16% would be (p 0.001)')
    expect(step.textContent).toContain('pairs inside one book too (mostly repeated formulae): 27% against 16%')
    const known = screen.getByRole('heading', { name: /David’s census/ }).closest('article')!
    expect(known.textContent).toContain('800,000 / 1,100,000 (not one step)')
  })

  it('lists the sums and opens a list', async () => {
    const { container } = renderAt()
    await screen.findByText('The census at Sinai')
    const rows = [...container.querySelectorAll('table.sm-table tbody tr')]
    expect(rows.map((r) => r.querySelector('td button')!.textContent)).toEqual(['The census at Sinai', 'The returnees (Ezra)'])
    expect(rows[1].className).toBe('sm-off')
    expect([...rows[1].querySelectorAll('td.num')].map((c) => c.textContent)).toEqual(['12', '29,818', '42,360', '12,542'])
    fireEvent.click(screen.getByRole('button', { name: 'The counts of The census at Sinai' }))
    expect(screen.getByTestId('loc').textContent).toBe('/sums?list=num1')
    await screen.findByText('46,500')
    const panel = container.querySelector('.sm-panel')!
    expect(panel.querySelectorAll('li.hit')).toHaveLength(3) // two counts and the total
  })

  it('lists the parallels and filters them in the URL', async () => {
    renderAt()
    expect(await screen.findByText('40,000 / 4,000')).toBeTruthy()
    expect(screen.getByText('1 differing numbers · page 1 of 1')).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'One step apart' }))
    expect(screen.getByTestId('loc').textContent).toBe('/sums?step=yes')
    await vi.waitFor(() => expect(calls.some((u) => u.includes('/sums/parallels') && u.includes('one_step=true'))).toBe(true))
    fireEvent.click(screen.getByRole('radio', { name: 'Every pair' }))
    await vi.waitFor(() => expect(calls.some((u) => u.includes('across=false'))).toBe(true))
  })

  it('says when the stage did not run', async () => {
    renderAt('/sums', 'en', true)
    expect(await screen.findByText(/The sums were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/sums', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('האם החשבון מסתדר?')
    expect(await screen.findByText('המפקד בסיני')).toBeTruthy()
  })
})
