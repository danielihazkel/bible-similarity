// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ExplainResponse, SimilarResponse, UnitDetail, UnitSummary, Verse } from '../api/types'
import { UnitPage } from './UnitPage'

const unit = (id: number, label: string): UnitSummary => ({
  unit_id: `v:${id}`,
  unit_type: 'verse',
  label_en: label,
  label_he: `he ${label}`,
  book_id: 0,
  start_verse_id: id,
  end_verse_id: id,
  n_verses: 1,
  marker: null,
})
const verse = (id: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 0,
  chapter: 1,
  verse: id + 1,
  ref: `Test 1:${id + 1}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})

const SRC = verse(0, ['אָמַר', 'נָבָל', 'בְּלִבּוֹ'])
const TGT = verse(5, ['נָבָל', 'אָמַר', 'שָׁם'])
const DETAIL: UnitDetail = { unit: unit(0, 'Test 1:1'), verses: [SRC], parents: [], prev_id: null, next_id: 'v:1' }
const similar = (mode: string): SimilarResponse => ({
  unit: DETAIL.unit,
  mode: mode as SimilarResponse['mode'],
  k: 10,
  exclude: ['neighbors'],
  hits: [
    { rank: 1, score: 0.5, lex_score: null, lex_rank: 1, sem_score: null, sem_rank: null, unit: unit(5, 'Test 1:6'), verse: TGT, preview: null, link: { level: 'verse', types: ['quotation'] } },
  ],
})
const EXPLAIN: ExplainResponse = {
  a: 0,
  b: 5,
  shared: [
    {
      lemma: '559',
      he_lemma: 'אמר',
      formula: false,
      a_words: [{ idx: 0, display_idx: 0, in_formula: false }],
      b_words: [{ idx: 1, display_idx: 1, in_formula: false }],
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
      const body = u.pathname.startsWith('/api/unit/')
        ? DETAIL
        : u.pathname.startsWith('/api/similar/')
          ? similar(u.searchParams.get('mode')!)
          : u.pathname === '/api/explain'
            ? EXPLAIN
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

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/unit/:unitId" element={<UnitPage />} />
        </Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('UnitPage', () => {
  it('hides neighbours by default and highlights shared lemmas on hover', async () => {
    const calls = mockApi()
    const { container } = renderAt('/unit/v:0')
    const hit = (await screen.findByText('Test 1:6')).closest('li')!
    expect(calls.some((c) => c.includes('/api/similar/v%3A0?mode=fused&k=10&exclude=neighbors'))).toBe(true)

    fireEvent.mouseEnter(hit)
    await waitFor(() => expect(container.querySelectorAll('.w-shared')).toHaveLength(2))
    const marked = [...container.querySelectorAll('.w-shared')].map((e) => e.textContent)
    expect(marked).toEqual(['אָמַר', 'אָמַר']) // source token 0 and hit token 1
    expect(screen.getByLabelText('Shared lemmas').textContent).toContain('אמר')
  })

  it('marks Sefaria-linked hits and can hide them', async () => {
    const calls = mockApi()
    renderAt('/unit/v:0')
    const hit = (await screen.findByText('Test 1:6')).closest('li')!
    expect(hit.querySelector('.link-badge')?.getAttribute('title')).toContain('quotation')
    fireEvent.click(screen.getByLabelText('Hide Sefaria-linked'))
    await waitFor(() => expect(calls.some((c) => c.includes('exclude=neighbors%2Cknown'))).toBe(true))
  })

  it('keeps mode in the URL', async () => {
    const calls = mockApi()
    renderAt('/unit/v:0?exclude=')
    await screen.findByText('Test 1:6')
    fireEvent.click(screen.getByRole('radio', { name: 'Lexical' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?exclude=&mode=lexical'))
    await waitFor(() => expect(calls.some((c) => c.includes('mode=lexical&k=10&exclude='))).toBe(true))
  })
})
