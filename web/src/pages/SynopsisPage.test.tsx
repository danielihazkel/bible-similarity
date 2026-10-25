// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SequenceDetail, SynopsesResponse, SynopsisDetail, SynopsisSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { SequencePage } from './SequencePage'
import { SynopsesPage } from './SynopsesPage'
import { SynopsisPage } from './SynopsisPage'

const SUMMARY: SynopsisSummary = {
  syn_id: 13,
  seq_ids: [13, 45, 56],
  columns: [
    { book_id: 12, label: 'Jeremiah 52:1–27', label_he: 'ירמיהו נב א–כז' },
    { book_id: 12, label: 'Jeremiah 39:1–11', label_he: 'ירמיהו לט א–יא' },
    { book_id: 10, label: 'II Kings 24:18–25:21', label_he: 'מלכים ב כד יח–כה כא' },
  ],
  n_rows: 3,
  n_aligned: 2,
  breaks: 0,
  dropped: 3,
}
const verse = (id: number, ref: string) => ({
  verse_id: id,
  book_id: 0,
  chapter: 1,
  verse: id,
  ref,
  ref_he: `ה${ref}`,
  text_display: 'וַיְהִי בַּשָּׁנָה',
  display_tokens: ['וַיְהִי', 'בַּשָּׁנָה'],
  ketiv_note: null,
})
const cell = (v: number | null, extra: object = {}) => ({ verse: v, marks: {}, loose: false, reordered: false, ...extra })
const DETAIL: SynopsisDetail = {
  synopsis: SUMMARY,
  base: 0,
  rows: [
    [cell(1, { marks: { '1': 'substitution' } }), cell(null), cell(21, { marks: { '1': 'substitution' } })],
    [cell(2), cell(11, { loose: true }), cell(22)],
    [cell(3), cell(10, { reordered: true }), cell(null)],
  ],
  verses: {
    '1': verse(1, 'Jer 52:1'),
    '2': verse(2, 'Jer 52:2'),
    '3': verse(3, 'Jer 52:3'),
    '10': verse(10, 'Jer 39:1'),
    '11': verse(11, 'Jer 39:2'),
    '21': verse(21, '2 Kgs 24:18'),
    '22': verse(22, '2 Kgs 24:19'),
  },
}
const LIST: SynopsesResponse = { max_q: 0.05, items: [SUMMARY] }

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function renderAt(path: string, calls: string[], locale: Locale = 'en', extra: Record<string, unknown> = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/synopses' ? LIST : p === '/api/synopses/13' ? DETAIL : (extra[p] ?? null)
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/synopses" element={<SynopsesPage />} />
            <Route path="/synopses/:synId" element={<SynopsisPage />} />
            <Route path="/sequences/:seqId" element={<SequencePage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>
    </LocaleProvider>,
  )
}

describe('SynopsesPage', () => {
  it('lists every synopsis with its passages', async () => {
    renderAt('/synopses', [])
    const link = await screen.findByRole('link', { name: /Jeremiah 52:1–27/ })
    expect(link.getAttribute('href')).toBe('/synopses/13')
    expect(link.textContent).toContain('II Kings 24:18–25:21')
    expect(screen.getByText('One synopsis')).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    renderAt('/synopses', [], 'he')
    expect(await screen.findByRole('link', { name: /ירמיהו נב א–כז/ })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'סינופסיס' })).toBeTruthy()
    expect(screen.getByText('סינופסיס אחד')).toBeTruthy()
  })
})

describe('SynopsisPage', () => {
  it('shows the passages in columns, marked against the first', async () => {
    const { container } = renderAt('/synopses/13', [])
    expect(await screen.findByRole('heading', { name: /Jeremiah 52:1–27 · Jeremiah 39:1–11 · II Kings/ })).toBeTruthy()
    expect(container.querySelectorAll('.syn-row')).toHaveLength(3)
    expect(container.querySelectorAll('.syn-cell.empty')).toHaveLength(2)
    expect(container.querySelectorAll('.syn-cell.base')).toHaveLength(3)
    expect(container.querySelectorAll('.synopsis .w-diff-substitution')).toHaveLength(2)
    expect(screen.getByRole('img', { name: /goes back in its book/ })).toBeTruthy()
    expect(screen.getByRole('img', { name: /Too different/ })).toBeTruthy()
    expect(screen.getByText(/3 aligned pair\(s\) left out/)).toBeTruthy()
    expect(screen.getByRole('link', { name: '#45' }).getAttribute('href')).toBe('/sequences/45')
    fireEvent.click(screen.getByLabelText('Mark word changes'))
    expect(container.querySelectorAll('.synopsis .w-diff-substitution')).toHaveLength(0)
    expect(screen.queryByRole('img', { name: /Too different/ })).toBeNull()
  })

  it('puts the column marked against in the URL', async () => {
    const calls: string[] = []
    renderAt('/synopses/13', calls)
    await screen.findByRole('heading', { name: /Jeremiah 52/ })
    fireEvent.change(screen.getByLabelText('Mark against'), { target: { value: '2' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/synopses/13?base=2'))
    await waitFor(() => expect(calls.some((c) => c.includes('/api/synopses/13') && c.includes('base=2'))).toBe(true))
  })

  it('reads in Hebrew', async () => {
    renderAt('/synopses/13', [], 'he')
    expect(await screen.findByText('הJer 52:1')).toBeTruthy()
    expect(screen.getByLabelText('סימון לעומת')).toBeTruthy()
    expect(screen.getByText(/3 שורות, 2 מהן/)).toBeTruthy()
  })

  it('says when the id is not a number', () => {
    renderAt('/synopses/x', [])
    expect(screen.getByText('Not a synopsis id.')).toBeTruthy()
  })
})

describe('SequencePage', () => {
  it('links a chain to the synopsis it is part of', async () => {
    const seq: SequenceDetail = {
      sequence: {
        seq_id: 45,
        a_start: 10,
        a_end: 11,
        b_start: 1,
        b_end: 2,
        direction: 'forward',
        a_label: 'Jeremiah 39:1–2',
        b_label: 'Jeremiah 52:4–5',
        a_label_he: 'ירמיהו לט א–ב',
        b_label_he: 'ירמיהו נב ד–ה',
        a_book: 12,
        b_book: 12,
        same_chapter: false,
        n_pairs: 2,
        score: 2,
        q: 0,
        n_gold: 0,
      },
      rows: [],
      verses: {},
    }
    renderAt('/sequences/45', [], 'en', { '/api/sequences/45': seq })
    const link = await screen.findByRole('link', { name: 'Part of a synopsis of 3 passages' })
    expect(link.getAttribute('href')).toBe('/synopses/13')
  })
})
