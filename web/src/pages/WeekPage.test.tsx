// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { UnitSummary, WeekResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { isIsoDate, localToday, longDate } from '../lib/week'
import { BooksPage } from './BooksPage'
import { WeekPage } from './WeekPage'

const unit = (name: string, he: string, i: number): UnitSummary => ({
  unit_id: `p:${name}`,
  unit_type: 'parasha',
  label_en: name,
  label_he: he,
  book_id: 3,
  start_verse_id: i,
  end_verse_id: i + 10,
  n_verses: 11,
  marker: null,
})
const WEEK: WeekResponse = {
  date: '2019-08-01',
  israel: false,
  shabbat: '2019-08-03',
  hebrew_he: 'ב׳ אב תשע״ט',
  hebrew_en: '2 Av 5779',
  festival: false,
  reading_shabbat: '2019-08-03',
  parashot: [
    { unit: unit('Matot', 'מטות', 100), haftarah: { haft: 'Jeremiah 1:1-2:3', seph: null, theme: 'admonition', chapters: ['c:12:1'], rank_fused: 40 } },
    { unit: unit('Masei', 'מסעי', 200), haftarah: null },
  ],
  prev: '2019-07-27',
  next: '2019-08-10',
}
const FESTIVAL: WeekResponse = { ...WEEK, date: '2019-04-24', shabbat: '2019-04-27', festival: true, reading_shabbat: '2019-05-04', parashot: [{ unit: unit('Achrei Mot', 'אחרי מות', 50), haftarah: null }] }

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

const calls: string[] = []

function renderAt(path: string, body: (u: URL) => unknown = (u) => (u.searchParams.get('date') === '2019-04-24' ? FESTIVAL : WEEK), locale: 'en' | 'he' = 'en') {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      if (u.pathname.startsWith('/api/dossier')) return new Response(JSON.stringify({ unit_id: 'p:Matot', entries: [] }))
      if (u.pathname === '/api/books') return new Response(JSON.stringify([]))
      return new Response(JSON.stringify(body(u)))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/week" element={<WeekPage />} />
            <Route path="/" element={<BooksPage />} />
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

describe('week dates', () => {
  it('reads the viewer’s own date and writes a Shabbat in each language', () => {
    expect(localToday(new Date(2026, 10, 3, 23, 30))).toBe('2026-11-03')
    expect(isIsoDate('2026-11-07') && !isIsoDate('7.11.2026') && !isIsoDate(null)).toBe(true)
    expect(longDate('2026-11-07', 'en')).toBe('7 November 2026')
    expect(longDate('2026-11-07', 'he')).toContain('2026')
  })
})

describe('WeekPage', () => {
  it('shows the Shabbat, the portions read together and each haftarah', async () => {
    const { container } = renderAt('/week?date=2019-08-01')
    expect(await screen.findByText('Shabbat, 3 August 2019 · 2 Av 5779')).toBeTruthy()
    expect(screen.getByText('Two portions are read together this week.')).toBeTruthy()
    expect([...container.querySelectorAll('.wk-parasha h3')].map((h) => h.textContent)).toEqual(['מטות Matot', 'מסעי Masei'])
    const haft = screen.getByRole('link', { name: 'The haftarah: Jeremiah 1:1-2:3' })
    expect(haft.getAttribute('href')).toBe('/read/c%3A12%3A1')
    expect(screen.getByText('one of the three of admonition, fixed by the calendar')).toBeTruthy()
    expect(screen.getByText('The haftarot were not computed in this build.')).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Read it' })[0].getAttribute('href')).toBe('/read/p%3AMatot')
    expect(calls.some((c) => c.includes('/api/week?date=2019-08-01'))).toBe(true)
  })

  it('moves by week and reads for Israel, in the URL', async () => {
    renderAt('/week?date=2019-08-01')
    await screen.findByText(/3 August 2019/)
    fireEvent.click(screen.getByRole('button', { name: /Next Shabbat/ }))
    expect(screen.getByTestId('loc').textContent).toBe('/week?date=2019-08-10')
    fireEvent.click(screen.getByRole('radio', { name: 'In Israel' }))
    expect(screen.getByTestId('loc').textContent).toBe('/week?date=2019-08-10&israel=1')
    await waitFor(() => expect(calls.some((c) => c.includes('israel=true'))).toBe(true))
  })

  it('says when a festival replaces the weekly portion', async () => {
    renderAt('/week?date=2019-04-24')
    expect(await screen.findByText(/a festival’s reading replaces the weekly portion. The next weekly portion is read on Shabbat, 4 May 2019/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/week?date=2019-08-01', undefined, 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('פרשת השבוע')
    expect(await screen.findByText(/ב׳ אב תשע״ט/)).toBeTruthy()
  })
})

describe('the home page’s week line', () => {
  it('links to this week’s parasha', async () => {
    renderAt('/')
    const link = await screen.findByRole('link', { name: 'Matot–Masei, read on Shabbat 3 August 2019' })
    expect(link.getAttribute('href')).toBe('/week')
  })

  it('shows nothing when the build has no parashot', async () => {
    renderAt('/', () => ({ detail: 'the parasha units are not in this build' }))
    await waitFor(() => expect(calls.some((c) => c.includes('/api/week'))).toBe(true))
    expect(document.querySelector('.wk-home')).toBeNull()
  })
})
