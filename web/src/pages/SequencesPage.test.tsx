// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SequenceDetail, SequenceSummary, SequencesResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { en } from '../i18n/en'
import { he } from '../i18n/he'
import { SequencePage } from './SequencePage'
import { SequencesPage } from './SequencesPage'

const SEQ: SequenceSummary = {
  seq_id: 4,
  a_start: 10,
  a_end: 12,
  b_start: 20,
  b_end: 21,
  a_label: 'II Samuel 22:1–3',
  b_label: 'Psalms 18:1–2',
  a_label_he: 'שמואל ב כב א–ג',
  b_label_he: 'תהלים יח א–ב',
  a_book: 9,
  b_book: 26,
  same_chapter: false,
  n_pairs: 2,
  score: 1.9,
  q: 0,
  n_gold: 1,
}
const verse = (id: number, ref: string) => ({
  verse_id: id,
  book_id: 0,
  chapter: 1,
  verse: id,
  ref,
  ref_he: 'הפניה',
  text_display: 'וַיְדַבֵּר',
  display_tokens: ['וַיְדַבֵּר'],
  ketiv_note: null,
})
const DETAIL: SequenceDetail = {
  sequence: SEQ,
  rows: [
    { a: 10, b: 20, weight: 1, cosine: 0.93, gold: true, a_marks: {}, b_marks: {}, loose: false },
    { a: 11, b: null, weight: null, cosine: null, gold: false, a_marks: {}, b_marks: {}, loose: false },
    { a: 12, b: 21, weight: 0.5, cosine: 0.6, gold: false, a_marks: { '0': 'substitution' }, b_marks: { '0': 'added' }, loose: false },
  ],
  verses: { '10': verse(10, 'II Sam 22:1'), '11': verse(11, 'II Sam 22:2'), '12': verse(12, 'II Sam 22:3'), '20': verse(20, 'Ps 18:1'), '21': verse(21, 'Ps 18:2') },
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function renderAt(path: string, calls: string[], locale: Locale = 'en') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const list: SequencesResponse = {
        book: null,
        cross_book: false,
        hide_same_chapter: false,
        max_q: 0.05,
        min_pairs: 1,
        unit: null,
        total: 1,
        offset: 0,
        limit: 50,
        items: [SEQ],
      }
      const unit = { unit: { unit_id: 'c:8:22', label_en: 'II Samuel 22', label_he: 'שמואל ב כב' } }
      const body =
        p === '/api/books'
          ? []
          : p === '/api/sequences'
            ? list
            : p === '/api/sequences/4'
              ? DETAIL
              : p.startsWith('/api/unit/')
                ? unit
                : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/sequences" element={<SequencesPage />} />
            <Route path="/sequences/:seqId" element={<SequencePage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>
    </LocaleProvider>,
  )
}

describe('SequencesPage', () => {
  it('lists chains with q ≤ 0.05 by default and puts filters in the URL', async () => {
    const calls: string[] = []
    renderAt('/sequences', calls)
    expect(await screen.findByText('II Samuel 22:1–3')).toBeTruthy()
    expect(screen.getByText('q < 0.001')).toBeTruthy()
    expect(screen.getByText('Sefaria links 1/2')).toBeTruthy()
    expect(calls.some((c) => c.startsWith('/api/sequences?') && c.includes('max_q=0.05'))).toBe(true)
    fireEvent.click(screen.getByLabelText('Different books only'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/sequences?cross=1'))
    await waitFor(() => expect(calls.some((c) => c.includes('cross_book=true'))).toBe(true))
  })
})

describe('SequencesPage unit filter', () => {
  it('limits the list to one unit and can clear the filter', async () => {
    const calls: string[] = []
    renderAt('/sequences?unit=c%3A8%3A22&q=0.2', calls)
    expect(await screen.findByText('II Samuel 22', { selector: '.unit-filter a' })).toBeTruthy()
    expect(calls.some((c) => c.startsWith('/api/sequences?') && c.includes('unit=c%3A8%3A22') && c.includes('max_q=0.2'))).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Show all' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/sequences?q=0.2'))
  })
})

describe('SequencesPage order filter', () => {
  it('asks for same-order chains by default and other orders on request', async () => {
    const calls: string[] = []
    renderAt('/sequences', calls)
    await screen.findByText('II Samuel 22:1–3')
    expect(calls.some((c) => c.startsWith('/api/sequences?') && c.includes('direction=forward'))).toBe(true)
    fireEvent.change(screen.getByLabelText('Order'), { target: { value: 'reverse' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/sequences?order=reverse'))
    await waitFor(() => expect(calls.some((c) => c.includes('direction=reverse'))).toBe(true))
    fireEvent.change(screen.getByLabelText('Order'), { target: { value: 'any' } })
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/sequences?') && !c.includes('direction='))).toBe(true))
  })
})

describe('SequencePage', () => {
  it('shows aligned pairs and skipped verses as a ladder', async () => {
    const { container } = renderAt('/sequences/4', [])
    expect(await screen.findByText('Ps 18:1')).toBeTruthy()
    expect(container.querySelectorAll('.rung')).toHaveLength(3)
    expect(container.querySelectorAll('.rung.skip')).toHaveLength(1)
    expect(container.querySelector('.rung .sim-swatch')?.textContent).toBe('★')
    expect(screen.getByText(/1 verse\(s\) only on the left, 0 only on the right/)).toBeTruthy()
    expect(container.querySelectorAll('.ladder .w-diff-substitution')).toHaveLength(1)
    expect(container.querySelectorAll('.ladder .w-diff-added')).toHaveLength(1)
    fireEvent.click(screen.getByLabelText('Mark word changes'))
    expect(container.querySelectorAll('.ladder .w-diff-substitution')).toHaveLength(0)
  })
})

describe('Sequences in Hebrew', () => {
  it('lists chains with Hebrew labels and controls', async () => {
    renderAt('/sequences', [], 'he')
    expect(await screen.findByText('שמואל ב כב א–ג')).toBeTruthy()
    expect(screen.queryByText('II Samuel 22:1–3')).toBeNull()
    expect(screen.getByRole('heading', { name: 'רצפים מקבילים' })).toBeTruthy()
    expect(screen.getByText('ספריא מקשרת 1/2')).toBeTruthy()
    expect(screen.getByText(/רצף אחד · עמוד 1 מתוך 1/)).toBeTruthy()
    expect(screen.getByRole('option', { name: 'סדר הפוך' })).toBeTruthy()
  })

  it('shows the ladder with Hebrew references', async () => {
    renderAt('/sequences/4', [], 'he')
    expect(await screen.findByRole('heading', { name: 'שמואל ב כב א–ג ↔ תהלים יח א–ב' })).toBeTruthy()
    expect(screen.getAllByText('הפניה').length).toBeGreaterThan(0)
    expect(screen.getByText(/שני זוגות פסוקים באותו סדר/)).toBeTruthy()
    expect(screen.getByLabelText('סימון שינויי מילים')).toBeTruthy()
  })
})

describe('q labels', () => {
  it('formats q values', () => {
    expect(en.q(0)).toBe('q < 0.001')
    expect(en.q(0.0042)).toBe('q = 0.004')
    expect(he.q(0.25)).toBe('q = 0.25')
  })
})
