// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LemmaSensesResponse, LemmaShift, ShiftsResponse } from '../api/types'
import { SensesPanel } from '../components/SensesPanel'
import { LocaleProvider } from '../context/Locale'
import { ShiftsPage } from './ShiftsPage'

const ORDER = ['torah', 'latter_prophets', 'poetry']
const SHIFT: LemmaShift = {
  lemma: '1350a',
  he_lemma: 'גאל',
  n: 103,
  groups: { torah: 35, latter_prophets: 27, poetry: 14 },
  k: 3,
  silhouette: 0.1,
  use_excess: 0.8,
  use_q: 0.006,
  n_senses: 3,
  sense_excess: 0.68,
  sense_q: 0.0004,
  nmi: 0.67,
  nmi_null: 0.02,
}
const shifts = (by: string, maxQ: string | null): ShiftsResponse => ({
  by: by as 'sense' | 'use',
  max_q: maxQ === null ? null : Number(maxQ),
  group_order: ORDER,
  nmi_mean: 0.2,
  nmi_null_mean: 0.03,
  total: 1,
  offset: 0,
  limit: 50,
  items: [SHIFT],
})
const verse = {
  verse_id: 7,
  book_id: 11,
  chapter: 43,
  verse: 14,
  ref: 'Isaiah 43:14',
  ref_he: 'ישעיהו מג:יד',
  text_display: 'כֹּה־אָמַר יְהוָה גֹּאַלְכֶם',
  display_tokens: ['כֹּה־', 'אָמַר', 'יְהוָה', 'גֹּאַלְכֶם'],
  ketiv_note: null,
}
const SENSES: LemmaSensesResponse = {
  lemma: '1350a',
  he_lemma: 'גאל',
  group_order: ORDER,
  shift: SHIFT,
  uses: [
    {
      kind: 'use',
      sense: '0',
      n: 32,
      groups: { torah: 10, poetry: 1 },
      collocates: [{ lemma: '1818', he_lemma: 'דם' }],
      examples: [],
      domains: [],
    },
    {
      kind: 'use',
      sense: '1',
      n: 44,
      groups: { torah: 3, latter_prophets: 27, poetry: 13 },
      collocates: [{ lemma: '6918', he_lemma: 'קדוש' }],
      examples: [{ verse, label_en: 'Isaiah 43:14', label_he: 'ישעיהו מג:יד', display_idx: 3 }],
      domains: [],
    },
  ],
  senses: [
    {
      kind: 'sdbh',
      sense: 'x',
      n: 60,
      groups: { torah: 30, latter_prophets: 20 },
      collocates: [],
      examples: [],
      domains: ['002003001'],
    },
  ],
}

function mockApi() {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const path = decodeURIComponent(u.pathname)
      const body =
        path === '/api/shifts'
          ? shifts(u.searchParams.get('by') ?? 'sense', u.searchParams.get('max_q'))
          : path === '/api/lemma/1350a/senses'
            ? SENSES
            : path === '/api/domains'
              ? [{ code: '002003001', level: 3, parent: '002003', label_en: 'Attachment', n_verses: 9, weight: 9 }]
              : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
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
            <Route path="/shifts" element={<ShiftsPage />} />
            <Route path="/lemma/:lemma" element={<SensesPanel lemma="1350a" />} />
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

describe('ShiftsPage', () => {
  it('ranks words by the shift of their senses and switches to uses and all q', async () => {
    const calls = mockApi()
    renderAt('/shifts')
    const link = await screen.findByRole('link', { name: 'גאל' })
    expect(link.getAttribute('href')).toBe('/lemma/1350a#senses')
    expect(screen.getByText('0.68')).toBeTruthy()
    expect(calls.some((c) => c.includes('by=sense') && c.includes('max_q=0.05'))).toBe(true)
    fireEvent.click(screen.getByRole('radio', { name: 'Uses in context' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/shifts?by=use'))
    expect(await screen.findByText('0.80')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Include q > 0.05'))
    await waitFor(() => expect(calls.some((c) => c.includes('max_q=1'))).toBe(true))
  })
})

describe('SensesPanel', () => {
  it('shows each sense by group with its domains, collocates and highlighted examples', async () => {
    mockApi()
    const { container } = renderAt('/lemma/1350a')
    const table = (await screen.findByText('Uses in context (clusters of its BEREL vectors)')).nextElementSibling!
    const rows = within(table as HTMLElement).getAllByRole('row')
    expect(rows).toHaveLength(3) // header + two uses
    // use 2 holds all of the Latter Prophets' occurrences among the uses
    expect(within(rows[2]).getAllByRole('cell')[1].textContent).toBe('100%')
    expect(within(rows[2]).getByRole('link', { name: 'קדוש' }).getAttribute('href')).toBe('/lemma/6918')
    expect(container.querySelector('.sense-examples .w-shared')?.textContent).toBe('גֹּאַלְכֶם')
    expect(await screen.findByRole('link', { name: 'Attachment' })).toBeTruthy()
  })

  it('names the groups in Hebrew', async () => {
    mockApi()
    renderAt('/lemma/1350a', 'he')
    expect((await screen.findAllByText('נביאים אחרונים')).length).toBeGreaterThan(0)
  })
})
