// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MeterChapter, MeterResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PoetryPage } from './PoetryPage'

const chapter = (book: number, ch: number, en: string, he: string, group: MeterChapter['group'], net: number, pct: number): MeterChapter => ({
  unit: {
    unit_id: `c:${book}:${ch}`,
    unit_type: 'chapter',
    label_en: en,
    label_he: he,
    book_id: book,
    start_verse_id: 0,
    end_verse_id: 21,
    n_verses: 22,
    marker: null,
  },
  group,
  n_lines: 66,
  fall: 0.68,
  rise: 0.08,
  net,
  share32: 0.44,
  prob: 0.16,
  pct,
})
const LAM3 = chapter(31, 3, 'Lamentations 3', 'איכה ג', 'test', 0.61, 0.994)
const LAM5 = chapter(31, 5, 'Lamentations 5', 'איכה ה', 'control', 0.27, 0.736)
const EZEK19 = chapter(13, 19, 'Ezekiel 19', 'יחזקאל יט', 'pool', 0.48, 0.96)
const RESPONSE: MeterResponse = {
  meta: {
    min_stresses: 4,
    max_stresses: 7,
    min_lines: 10,
    pool_quantile: 0.75,
    pool_prob: 0.231,
    test: { n: 4, pool_n: 174, mean: 0.388, pool_mean: 0.175, p: 0.0079 },
    test_poetic: { n: 4, pool_n: 190, mean: 0.388, pool_mean: 0.135, p: 0.0013 },
    named: { n: 12, pool_n: 170, mean: 0.202, pool_mean: 0.171, p: 0.259 },
    grid: [{ min: 3, max: 8, mean: 0.395, pool_mean: 0.186, pool_p: 0.0038, poetic_p: 0.0017 }],
    groups: { test: { chapters: 4, lines: 237, fall: 0.51, rise: 0.12, patterns: [['3:2', 82], ['2:2', 49]] } },
  },
  test_chapters: [LAM3],
  control_chapters: [LAM5],
  named_chapters: [EZEK19],
  group: null,
  book: null,
  total: 2,
  offset: 0,
  limit: 50,
  items: [LAM3, EZEK19],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', response: MeterResponse = RESPONSE) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? [] : p === '/api/meter' ? response : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/poetry" element={<PoetryPage />} />
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

describe('Poetry → Meter', () => {
  it('states the test with its control, the other lengths and the named laments', async () => {
    renderAt('/poetry?view=meter')
    expect(await screen.findByText(/Lamentations 1–4: 0\.39; other poetry under the same \(prose\) accents, 174 chapters: 0\.17 \(p 0\.008/)).toBeTruthy()
    expect(screen.getByText(/Against Psalms, Proverbs and Job, which have accents of their own: p 0\.001/)).toBeTruthy()
    expect(screen.getByText(/top 25% by their verses' probability of parallel halves \(at least 0\.23\)/)).toBeTruthy()
    const lam5 = screen.getByRole('link', { name: 'Lamentations 5' })
    expect(lam5.getAttribute('href')).toBe('/unit/c%3A31%3A5?halves=1&meter=1')
    expect(screen.getAllByRole('region', { name: 'Other line lengths' })[0].textContent).toContain('3–8')
    expect(screen.getByText(/The 12 chapters outside Lamentations that use the word קינה, tested the same way: net fall 0\.20 against 0\.17 \(p 0\.26\)/)).toBeTruthy()
    expect(screen.getByText(/3:2 ×82 · 2:2 ×49/)).toBeTruthy()
    expect(screen.getByText(/^2 chapters ·/)).toBeTruthy()
  })

  it('filters the ranking by group', async () => {
    const { calls } = renderAt('/poetry?view=meter')
    await screen.findByText(/^2 chapters ·/)
    fireEvent.change(screen.getByRole('combobox', { name: 'Group' }), { target: { value: 'pool' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/poetry?view=meter&group=pool'))
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/meter?') && c.includes('group=pool'))).toBe(true))
  })

  it('reads in Hebrew', async () => {
    renderAt('/poetry?view=meter', 'he')
    expect(await screen.findByText(/איכה א–ד: 0\.39; שירה אחרת באותה מערכת טעמים/)).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'איכה ה' }).length).toBeGreaterThan(0)
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/poetry?view=meter', 'en', { ...RESPONSE, meta: {}, test_chapters: [], control_chapters: [], named_chapters: [], total: 0, items: [] })
    expect((await screen.findAllByText(/run `bsim meter`/)).length).toBeGreaterThan(0)
  })
})
