// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Label, LabelsEval, LabelsResponse, UnitSummary } from '../api/types'
import { LabelButtons } from '../components/LabelButtons'
import { LocaleProvider } from '../context/Locale'
import { LabelsPage } from './LabelsPage'

const unit = (id: number, en: string, he: string): UnitSummary => ({
  unit_id: `v:${id}`,
  unit_type: 'verse',
  label_en: en,
  label_he: he,
  book_id: 0,
  start_verse_id: id,
  end_verse_id: id,
  n_verses: 1,
  marker: null,
})
const LABEL: Label = {
  unit_type: 'verse',
  a: unit(0, 'Genesis 1:1', 'בראשית א:א'),
  b: unit(3, 'Genesis 2:1', 'בראשית ב:א'),
  label: 'real',
  note: 'creation',
  mode: 'semantic',
  score: 0.91,
  labeled_at: '2026-10-06T10:00:00+00:00',
}
const EVAL: LabelsEval = {
  k: 10,
  min_pairs: 5,
  rows: [
    { unit_type: 'verse', mode: 'semantic', n_real: 6, n_not: 5, found_real: 6, found_not: 2, recall: 1, precision: 0.75, auc: 0.83 },
  ],
}

function mockApi(writable = true) {
  let labels: LabelsResponse = { writable, counts: { real: 1, not: 0, unsure: 0 }, items: [LABEL] }
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url, 'http://x').pathname
    if (init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      const item = { ...LABEL, label: body.label, note: body.note }
      labels = { ...labels, counts: { real: 0, not: 1, unsure: 0 }, items: [item] }
      return new Response(JSON.stringify(item), { status: 200 })
    }
    if (init?.method === 'DELETE') {
      labels = { ...labels, counts: { real: 0, not: 0, unsure: 0 }, items: [] }
      return new Response(null, { status: 204 })
    }
    const body = path === '/api/labels' ? labels : path === '/api/labels/eval' ? EVAL : null
    return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderAt(ui: React.ReactNode, locale: 'en' | 'he' = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={['/labels']}>
          <Routes>
            <Route path="/labels" element={ui} />
          </Routes>
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('LabelsPage', () => {
  it('lists the labels with how each mode separates them', async () => {
    mockApi()
    renderAt(<LabelsPage />)
    expect(await screen.findByText('1 real · 0 not · 0 unsure')).toBeTruthy()
    expect(screen.getByRole('link', { name: /^Genesis 2:1/ }).getAttribute('href')).toBe('/unit/v%3A3')
    expect(screen.getByText(/judged in Semantic \(score 0\.91/)).toBeTruthy()
    expect(await screen.findByText('0.75')).toBeTruthy()
    expect(screen.getByText('0.83')).toBeTruthy()
    expect((screen.getByRole('textbox', { name: 'Note' }) as HTMLInputElement).value).toBe('creation')
  })

  it('reads in Hebrew, read-only', async () => {
    mockApi(false)
    renderAt(<LabelsPage />, 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'הסימונים שלך' })).toBeTruthy()
    expect(screen.getByText('השרת הזה מציג סימונים לקריאה בלבד.')).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})

describe('LabelButtons', () => {
  it('labels a pair, relabels it and clears it', async () => {
    const fetchMock = mockApi()
    renderAt(<LabelButtons a="v:3" b="v:0" mode="fused" score={0.5} />)
    const real = await screen.findByRole('button', { name: 'Real' })
    expect(real.getAttribute('aria-pressed')).toBe('true') // found in either order
    fireEvent.click(screen.getByRole('button', { name: 'Not' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Not' }).getAttribute('aria-pressed')).toBe('true'))
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')!
    expect(JSON.parse(String(put[1]!.body))).toEqual({ a_id: 'v:3', b_id: 'v:0', label: 'not', note: 'creation', mode: 'fused', score: 0.5 })
    fireEvent.click(screen.getByRole('button', { name: 'Not' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Not' }).getAttribute('aria-pressed')).toBe('false'))
    expect(fetchMock.mock.calls.some(([u, init]) => init?.method === 'DELETE' && u === '/api/labels/v%3A3/v%3A0')).toBe(true)
  })
})
