// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Haftarah, HaftarotResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { HaftarotPage } from './HaftarotPage'

const chapter = (rank: number, id: string, en: string, he: string, haftarah = false) => ({ rank, unit_id: id, label_en: en, label_he: he, lex_rank: rank + 1, sem_rank: rank, haftarah })
const NOACH: Haftarah = {
  parasha: 'p:Noach',
  num: 2,
  label_en: 'Noach',
  label_he: 'נח',
  theme: null,
  haft: 'Isaiah 54:1-55:5',
  seph: 'Isaiah 54:1-54:10',
  chapters: ['c:13:54', 'c:13:55'],
  chapter_labels: ['Isaiah 54', 'Isaiah 55'],
  chapter_labels_he: ['ישעיה נד', 'ישעיה נה'],
  rank_lexical: 98,
  rank_semantic: 6,
  rank_fused: 17,
  pct: 0.042,
  known: true,
  top: [chapter(1, 'c:13:16', 'Isaiah 16', 'ישעיה טז'), chapter(2, 'c:13:54', 'Isaiah 54', 'ישעיה נד', true)],
}
const DEVARIM: Haftarah = { ...NOACH, parasha: 'p:Devarim', num: 44, label_en: 'Devarim', label_he: 'דברים', theme: 'admonition', haft: 'Isaiah 1:1-1:27', seph: null, rank_fused: 3, rank_lexical: 4, rank_semantic: 2, known: false, top: [] }
const DATA: HaftarotResponse = {
  candidates: 380,
  thematic: 44,
  claim_mode: 'fused',
  shuffles: 9999,
  alpha: 0.05,
  list: 10,
  thematic_pct: 0.124,
  shuffled_pct: 0.324,
  p: 0.0001,
  holds: true,
  calendar_pct: 0.325,
  difference: 0.2,
  calendar_p: 0.0042,
  calendar_holds: true,
  modes: {
    lexical: { mrr: 0.236, hits: 16, median: 25, pct: 0.15 },
    semantic: { mrr: 0.204, hits: 15, median: 30, pct: 0.13 },
    fused: { mrr: 0.199, hits: 16, median: 26, pct: 0.124 },
  },
  known: [
    { parasha: 'Noach', rank: 17, holds: false },
    { parasha: 'Vayera', rank: 3, holds: true },
  ],
  known_rank: 10,
  known_holds: false,
  parashot: [NOACH, DEVARIM],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => (missing ? new Response(JSON.stringify({ detail: 'the haftarot were not computed' }), { status: 404 }) : new Response(JSON.stringify(DATA)))),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/haftarot" element={<HaftarotPage />} />
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

describe('HaftarotPage', () => {
  it('states the three checks', async () => {
    renderAt('/haftarot')
    const claim = (await screen.findByRole('heading', { name: /ranks high among the Prophets/ })).closest('article')!
    expect(within(claim).getByText('Borne out')).toBeTruthy()
    expect(claim.textContent).toContain('The 44 haftarot chosen for their parasha stand at percentile 12% of the 380 chapters on average (0: the first), against 32%')
    const cal = screen.getByRole('heading', { name: /calendar’s haftarot rank lower/ }).closest('article')!
    expect(cal.textContent).toContain('stand at percentile 33%, against 12% for the rest (p 0.004)')
    const known = screen.getByRole('heading', { name: /Shunammite/ }).closest('article')!
    expect(within(known).getByText('Not borne out')).toBeTruthy()
    // Vayera is not among the rows here: its name falls back to Hebcal's
    expect(known.textContent).toContain('Ranked Noach 17, Vayera 3.')
  })

  it('compares the systems and lists every parasha with its haftarah', async () => {
    const { container } = renderAt('/haftarot')
    await screen.findByText('Words (TF-IDF)')
    expect([...container.querySelectorAll('table.hf-modes tbody tr')].map((r) => r.textContent)).toEqual([
      'Words (TF-IDF)0.23616 / 442515%',
      'Meaning (BEREL)0.20415 / 443013%',
      'Both (fused)0.19916 / 442612%',
    ])
    const rows = [...container.querySelectorAll('table.hf-table tbody tr')]
    expect(rows[0].textContent).toBe('2NoachIsaiah 54:1-55:5Sephardi: Isaiah 54:1-54:1017 (98 · 6)')
    expect(rows[0].className).toBe('')
    expect(rows[1].textContent).toContain('rebuke')
    expect(rows[1].className).toBe('hf-top')
  })

  it('opens a parasha’s chapters with the haftarah marked', async () => {
    const { container } = renderAt('/haftarot')
    fireEvent.click(await screen.findByRole('button', { name: 'The chapters of the Prophets for Noach' }))
    expect(screen.getByTestId('loc').textContent).toBe('/haftarot?p=p%3ANoach')
    const list = screen.getByRole('heading', { name: 'Noach: the first chapters of the Prophets' }).closest('section')!
    const items = [...list.querySelectorAll('li')]
    expect(items.map((li) => li.className)).toEqual(['', 'hf-hit'])
    expect(within(items[1] as HTMLElement).getByRole('link', { name: 'compare' }).getAttribute('href')).toBe('/compare?a=p%3ANoach&b=c%3A13%3A54')
    fireEvent.click(within(list as HTMLElement).getByRole('button', { name: 'Close' }))
    expect(container.querySelector('.hf-list')).toBeNull()
  })

  it('says when the stage did not run', async () => {
    renderAt('/haftarot', 'en', true)
    expect(await screen.findByText(/The haftarot were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/haftarot?p=p%3ANoach', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('הפטרות')
    expect(await screen.findByRole('heading', { name: 'נח: פרקי הנביאים הראשונים' })).toBeTruthy()
    expect(screen.getByText('פורענותא')).toBeTruthy()
  })
})
