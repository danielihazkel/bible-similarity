// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Acrostic, StructureRankingResponse, StructureResponse, UnitDetail, UnitSummary, Verse } from '../api/types'
import { StructurePage } from './StructurePage'
import { UnitPage } from './UnitPage'

const CHAPTER: UnitSummary = {
  unit_id: 'c:26:8',
  unit_type: 'chapter',
  label_en: 'Psalms 8',
  label_he: 'תהילים ח',
  book_id: 26,
  start_verse_id: 10,
  end_verse_id: 12,
  n_verses: 3,
  marker: null,
}
const verse = (id: number, n: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 26,
  chapter: 8,
  verse: n,
  ref: `Psalms 8:${n}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const VERSES = [verse(10, 2, ['יְהוָה', 'אֲדֹנֵינוּ']), verse(11, 3, ['מִפִּי', 'עוֹלְלִים']), verse(12, 10, ['יְהוָה', 'אֲדֹנֵינוּ'])]
const DETAIL: UnitDetail = { unit: CHAPTER, verses: VERSES, parents: [], prev_id: null, next_id: null }
const basis = {
  matrix: [
    [1, 0.2, 0.9],
    [0.2, 1, 0.3],
    [0.9, 0.3, 1],
  ],
  inclusio: { value: 0.9, pct: 1, z: null, pair: [10, 12] as [number, number] },
  chiasm: null,
  echoes: [{ a: 10, b: 12, sim: 0.9 }],
}
const STRUCTURE: StructureResponse = {
  unit: CHAPTER,
  verse_ids: [10, 11, 12],
  semantic: basis,
  lexical: basis,
  leitworte: [
    { lemma: '113', he_lemma: 'אדון', count: 2, expected: 0.1, g2: 12, multiple_of: [], occurrences: { '10': [1], '12': [1] } },
  ],
}
const RANKING: StructureRankingResponse = {
  unit_type: 'chapter',
  by: 'semantic_chiasm',
  min_verses: 8,
  leitwort_numbers: {
    leitworte: 9241,
    lemma_counts: 21805,
    '7': { multiples: 776, expected: 669.5, share: 0.084, p: 5e-6 },
    '10': { multiples: 309, expected: 219.6, share: 0.033, p: 1e-10 },
  },
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      unit: { ...CHAPTER, n_verses: 10 },
      semantic_inclusio: 0.9,
      semantic_inclusio_pct: 1,
      semantic_chiasm: 0.5,
      semantic_chiasm_pct: 0.97,
      semantic_chiasm_z: 2.1,
      lexical_inclusio: null,
      lexical_inclusio_pct: null,
      lexical_chiasm: 0.4,
      lexical_chiasm_pct: 0.5,
      lexical_chiasm_z: 0.1,
      semantic_chiasm_q: 0.3,
    },
  ],
}
const ACROSTIC: Acrostic = {
  unit: CHAPTER,
  granularity: 'verse',
  order_name: 'standard',
  score: 3,
  n_letters: 3,
  missing: 0,
  first_letter: 'א',
  last_letter: 'ג',
  n_lines: 3,
  p: 0.0001,
  q: 0.0008,
  chain: [
    { verse_id: 10, display_idx: 0, letter: 'א' },
    { verse_id: 11, display_idx: 0, letter: 'ב' },
    { verse_id: 12, display_idx: 0, letter: 'ג' },
  ],
}

let calls: string[] = []
beforeEach(() => {
  calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const p = decodeURIComponent(u.pathname)
      const body =
        p === '/api/unit/c:26:8'
          ? DETAIL
          : p === '/api/similar/c:26:8'
            ? { unit: CHAPTER, mode: 'fused', k: 10, exclude: [], hits: [] }
            : p === '/api/structure/c:26:8'
              ? STRUCTURE
              : p === '/api/structure'
                ? RANKING
                : p === '/api/acrostics/c:26:8'
                  ? ACROSTIC
                  : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/unit/:unitId" element={<UnitPage />} />
          <Route path="/structure" element={<StructurePage />} />
        </Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('structure panel', () => {
  it('loads only when opened and highlights a Leitwort in the text', async () => {
    const { container } = renderAt('/unit/c:26:8')
    await screen.findByText('Structure: inclusio, chiasm, Leitworte')
    expect(calls.some((c) => c.startsWith('/api/structure'))).toBe(false)
    renderAt('/unit/c:26:8?structure=1')
    expect(await screen.findByText(/100th percentile/)).toBeTruthy()
    expect(screen.getByText(/8:2 ↔ 8:10, 0.90/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /אדון/ }))
    await waitFor(() => expect(container.ownerDocument.querySelectorAll('.source .w-focus')).toHaveLength(2))
  })
})

describe('acrostic bar', () => {
  it('names a significant acrostic and marks its letters on request', async () => {
    const { container } = renderAt('/unit/c:26:8')
    expect(await screen.findByText(/3 letters in alphabetical order, א–ג/)).toBeTruthy()
    expect(container.querySelectorAll('.source .w-acrostic')).toHaveLength(0)
    fireEvent.click(screen.getByLabelText('Mark the letters'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/c:26:8?acrostic=1'))
    await waitFor(() => expect(container.querySelectorAll('.source .w-acrostic')).toHaveLength(3))
  })
})

describe('StructurePage', () => {
  it('ranks units and links to their structure view', async () => {
    renderAt('/structure')
    const link = await screen.findByRole('link', { name: 'Psalms 8' })
    expect(link.getAttribute('href')).toBe('/unit/c%3A26%3A8?structure=1')
    expect(calls).toContain('/api/structure?unit_type=chapter&by=semantic_chiasm&min_verses=8&limit=50&offset=0')
    expect(screen.getByText('q = 0.30')).toBeTruthy()
    expect(screen.getByText(/776 occur a multiple of 7\s+times against 669.5 expected/)).toBeTruthy()
    expect(screen.getByText(/so nothing singles out 7/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'lexical_inclusio' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/structure?by=lexical_inclusio'))
  })
})
