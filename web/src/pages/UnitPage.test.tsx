// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
  ExplainResponse,
  SimilarResponse,
  UnitDetail,
  UnitParallelism,
  UnitSummary,
  PhrasePair,
  Verse,
  WordDetail,
} from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
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
  ref_he: 'הפניה',
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
    { rank: 1, score: 0.5, lex_score: null, lex_rank: 1, sem_score: null, sem_rank: null, unit: unit(5, 'Test 1:6'), verse: TGT, preview: null, link: { level: 'verse', types: ['quotation'] }, phrase: { score: 20, n_tokens: 4 } },
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

const WORDS: WordDetail[] = [
  {
    idx: 0,
    display_idx: 0,
    surface: 'אָמַר',
    lemma: '559',
    morph: 'HVqp3ms',
    morph_he: ['פועל · קל · עבר · גוף שלישי · זכר · יחיד'],
    in_formula: false,
    lemmas: [{ lemma: '559', he_lemma: 'אמר', n_verses: 4300 }],
    domains: ['002003001'],
  },
]

const PHRASES: PhrasePair[] = [
  {
    score: 20,
    n_tokens: 4,
    spread: 2,
    a: unit(0, 'Test 1:1'),
    b: unit(5, 'Phrase partner'),
    a_verse: SRC,
    b_verse: TGT,
    a_display: [0, 1],
    b_display: [0, 1],
    link: null,
  },
]

const HALVES: UnitParallelism = {
  unit: unit(0, 'Test 1:1'),
  parallel_at: 0.5,
  mean_prob: 0.8,
  share_parallel: 1,
  n_scored: 1,
  verses: [
    {
      verse_id: 0,
      n_cola: 2,
      cola: [[0, 0], [1, 2]],
      pauses: ['etnahta'],
      cos: 0.7,
      shared: 0,
      shape: 0.5,
      balance: 0.5,
      prob: 0.8,
      clauses: [[0, 0], [1, 1], [2, 2]],
      next_prob: null,
      relation: 'antithetic',
      relation_pairs: [{ a: '6662', b: '7563', kind: 'antonym', a_he: 'צדיק', b_he: 'רשע' }],
    },
  ],
}

const EMPTY_PAGE = { total: 0, offset: 0, limit: 5, items: [] }

function mockApi(failing: string[] = []) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      if (failing.includes(u.pathname)) return new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
      const body = u.pathname.startsWith('/api/unit/')
        ? DETAIL
        : u.pathname.startsWith('/api/similar/')
          ? similar(u.searchParams.get('mode')!)
          : u.pathname === '/api/explain'
            ? EXPLAIN
            : u.pathname === '/api/words/0'
              ? WORDS
              : u.pathname === '/api/phrases/0'
                ? PHRASES
                : u.pathname === '/api/diff'
                  ? { a: 0, b: 5, a_marks: { '2': 'omitted' }, b_marks: { '2': 'added' }, counts: {}, shared: 0.6, loose: false }
                  : u.pathname.startsWith('/api/parallelism/')
                  ? HALVES
                  : u.pathname === '/api/wordplay' || u.pathname === '/api/sequences'
                    ? EMPTY_PAGE
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

function renderAt(path: string, locale: Locale = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/unit/:unitId" element={<UnitPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>
    </LocaleProvider>,
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
    await waitFor(() => expect(container.querySelectorAll('.source .w-shared, .hits .w-shared')).toHaveLength(2))
    const marked = [...container.querySelectorAll('.source .w-shared, .hits .w-shared')].map((e) => e.textContent)
    expect(marked).toEqual(['אָמַר', 'אָמַר']) // source token 0 and hit token 1
    expect(screen.getByLabelText('Shared lemmas').textContent).toContain('אמר')
  })

  it('speaks Hebrew in the Hebrew interface', async () => {
    mockApi()
    const { container } = renderAt('/unit/v:0', 'he')
    const hit = (await screen.findByText('he Test 1:6')).closest('li')!
    expect(screen.queryByText('Test 1:6')).toBeNull()
    expect(screen.getByRole('heading', { name: 'פסוקים דומים' })).toBeTruthy()
    expect(hit.querySelector('.phrase-tag')?.textContent).toBe('צירוף · 4')
    expect(container.querySelector('.type-tag')?.textContent).toBe('פסוק')
    expect(screen.getByRole('radio', { name: 'משולב' }).getAttribute('aria-checked')).toBe('true')
    fireEvent.mouseEnter(hit)
    expect((await screen.findByLabelText('ערכים משותפים')).textContent).toContain('אמר')
  })

  it('shows the phrase badge and the shared-phrases section', async () => {
    mockApi()
    const { container } = renderAt('/unit/v:0')
    const hit = (await screen.findByText('Test 1:6')).closest('li')!
    expect(hit.querySelector('.phrase-tag')?.textContent).toBe('phrase · 4')
    const section = await screen.findByLabelText('Shared phrases')
    expect(section.textContent).toContain('4 lemmas')
    expect(section.querySelectorAll('.w-shared')).toHaveLength(4)
    expect(container.querySelector('h2')).toBeTruthy()
  })

  it('says when an optional panel fails instead of hiding it', async () => {
    mockApi(['/api/phrases/0', '/api/wordplay'])
    renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    // the server's detail is its own (bidi-isolated) element: match the alert's whole text
    await waitFor(() =>
      expect(screen.getAllByRole('alert').map((a) => a.textContent)).toEqual(
        expect.arrayContaining(['Could not load shared phrases (500: boom).', 'Could not load wordplay (500: boom).']),
      ),
    )
    expect(screen.queryByText(/Could not load parallel sequences/)).toBeNull()
  })

  it('marks Sefaria-linked hits and can hide them', async () => {
    const calls = mockApi()
    renderAt('/unit/v:0')
    const hit = (await screen.findByText('Test 1:6')).closest('li')!
    expect(hit.querySelector('.link-badge')?.getAttribute('title')).toContain('quotation')
    fireEvent.click(screen.getByLabelText('Hide Sefaria-linked'))
    await waitFor(() => expect(calls.some((c) => c.includes('exclude=neighbors%2Cknown'))).toBe(true))
  })

  it('shows the morphology and a concordance link for a clicked word', async () => {
    mockApi()
    renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    const source = screen.getByLabelText('Source text')
    fireEvent.click(source.querySelector('[role="button"]')!)
    const panel = await screen.findByLabelText('Word analysis')
    await waitFor(() => expect(panel.textContent).toContain('פועל · קל · עבר'))
    expect(panel.querySelector('a')?.getAttribute('href')).toBe('/lemma/559')
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByLabelText('Word analysis')).toBeNull()
  })

  it('splits the verse at its accent pause and marks parallel halves', async () => {
    const calls = mockApi()
    const { container } = renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    expect(container.querySelector('.colon-break')).toBeNull()
    fireEvent.click(screen.getByLabelText("Verse halves (te'amim)"))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?halves=1'))
    await waitFor(() => expect(container.querySelectorAll('.source .colon-break')).toHaveLength(1))
    // typed antithetic (SDBH antonyms across the halves): marked, with the pair in the tooltip
    const badge = container.querySelector('.source .parallel-badge')
    expect(badge?.textContent).toBe('∥≠')
    expect(badge?.getAttribute('title')).toContain('antithetic: צדיק / רשע (antonyms)')
    expect(calls.some((c) => c.startsWith('/api/parallelism/'))).toBe(true)
    // the weaker pause inside the second half shows on request
    expect(container.querySelector('.source .clause-break')).toBeNull()
    fireEvent.click(screen.getByLabelText('Finer clauses'))
    await waitFor(() => expect(container.querySelectorAll('.source .clause-break')).toHaveLength(1))
  })

  it('marks word changes instead of shared words, and j pins the next hit', async () => {
    Element.prototype.scrollIntoView = vi.fn() // not in jsdom
    const calls = mockApi()
    const { container } = renderAt('/unit/v:0?marks=changes')
    await screen.findByText('Test 1:6')
    fireEvent.keyDown(document.body, { key: 'j' })
    await waitFor(() => expect(container.querySelectorAll('.hits .hit-text .w-diff-added')).toHaveLength(1))
    expect(container.querySelectorAll('.source .w-diff-omitted').length).toBeGreaterThan(0)
    expect(calls.some((c) => c.startsWith('/api/diff?a=0&b=5'))).toBe(true)
    expect(calls.some((c) => c.startsWith('/api/explain'))).toBe(false)
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
