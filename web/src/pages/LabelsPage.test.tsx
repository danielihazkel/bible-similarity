// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Label, LabelQueue, LabelsEval, LabelsResponse, UnitSummary, Verse } from '../api/types'
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

const verse = (id: number, ref: string, text: string): Verse => ({
  verse_id: id,
  book_id: 0,
  chapter: 1,
  verse: id,
  ref,
  ref_he: `ה${ref}`,
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const QUEUE: LabelQueue = {
  writable: true,
  split: 'train',
  k: 50,
  pool: 79,
  labelled: 4,
  train_real: 3,
  min_train: 30,
  total: 75,
  items: [
    {
      a: verse(7, 'Genesis 1:8', 'וַיִּקְרָא אֱלֹהִים'),
      b: verse(900, 'Psalms 19:2', 'הַשָּׁמַיִם מְסַפְּרִים'),
      a_id: 'v:7',
      b_id: 'v:900',
      lex_rank: null,
      sem_rank: 1,
      disagreement: 50,
      side: 'semantic',
      score: 0.016,
      suggestion: { verdict: 'real', p_real: 0.8, kind: 'allusion', rationale: 'השמים in both, as the witnesses of creation' },
    },
  ],
  llm: { model: 'claude-sonnet-5-5', rationale: 'english', collected_at: '2026-11-04T12:00:00+00:00', auc: 0.91, min_auc: 0.75, holds: true, pairs: 500 },
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
    const body =
      path === '/api/labels' ? labels : path === '/api/labels/eval' ? EVAL : path === '/api/labels/queue' ? { ...QUEUE, writable } : null
    return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderAt(ui: React.ReactNode, locale: 'en' | 'he' = 'en', path = '/labels') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
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
    expect(await screen.findByText('השרת הזה מציג סימונים לקריאה בלבד.')).toBeTruthy()
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})

describe('The label queue', () => {
  it('shows the pairs the modes rank apart, and labels one as from the queue', async () => {
    const fetchMock = mockApi()
    renderAt(<LabelsPage />, 'en', '/labels?tab=queue')
    expect(await screen.findByText('75 pairs to judge · 4 of 79 judged')).toBeTruthy()
    expect(screen.getByText(/lexical rank beyond 50 · semantic rank 1/)).toBeTruthy()
    expect(screen.getByText(/You have 3 real pairs between training books/)).toBeTruthy()
    // Claude's suggestion beside the buttons, and the run it comes from
    expect(screen.getByText('Claude suggests: Real (p 0.80, allusion).')).toBeTruthy()
    expect(screen.getByText('השמים in both, as the witnesses of creation').getAttribute('lang')).toBe('en')
    expect(screen.getByText(/AUC 0\.91 \(shown from 0\.75\)/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Psalms 19:2' }).getAttribute('href')).toBe('/unit/v%3A900')
    fireEvent.click(await screen.findByRole('button', { name: 'Real' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(true))
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT')!
    expect(JSON.parse(String(put[1]!.body))).toMatchObject({ a_id: 'v:7', b_id: 'v:900', label: 'real', mode: 'queue', score: 0.016 })
    // ranked higher by meaning only
    fireEvent.click(screen.getByRole('radio', { name: 'Semantic' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/api/labels/queue') && String(u).includes('side=semantic'))).toBe(true),
    )
    // only the pairs Claude read
    fireEvent.click((await screen.findByRole('checkbox', { name: 'Only pairs with a suggestion' })))
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).includes('suggested=true'))).toBe(true))
  })

  it('switches between the two views, and reads in Hebrew', async () => {
    mockApi()
    renderAt(<LabelsPage />, 'he')
    fireEvent.click(await screen.findByRole('radio', { name: 'מה לשפוט עכשיו' }))
    expect(await screen.findByText(/זוגות לשיפוט/)).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'מה לשפוט עכשיו' })).toBeTruthy()
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
