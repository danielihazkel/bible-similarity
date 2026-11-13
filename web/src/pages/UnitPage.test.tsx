// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
  Dossier,
  DossierEntry,
  ExplainResponse,
  SimilarResponse,
  UnitDetail,
  UnitMeter,
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
    { rank: 1, score: 0.5, lex_score: null, lex_rank: 1, sem_score: null, sem_rank: null, phr_score: null, phr_rank: null, unit: unit(5, 'Test 1:6'), verse: TGT, preview: null, link: { level: 'verse', types: ['quotation'] }, phrase: { score: 20, n_tokens: 4 } },
  ],
  phrases: false,
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
    roots: [{ lemma: '559', root: '559', root_he: 'אָמַר' }],
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

const METER: UnitMeter = {
  unit_id: 'v:0',
  min_stresses: 4,
  max_stresses: 7,
  chapter: {
    unit: unit(0, 'Test 1'),
    group: 'test',
    n_lines: 40,
    fall: 0.68,
    rise: 0.08,
    net: 0.61,
    share32: 0.44,
    prob: 0.2,
    pct: 0.994,
  },
  verses: [{ verse_id: 0, lines: [{ first: 0, last: 1, stresses: 2, a: 1, b: 1 }, { first: 2, last: 2, stresses: 1, a: null, b: null }] }],
}

const EMPTY_PAGE = { total: 0, offset: 0, limit: 5, items: [] }
const entry = (e: Partial<DossierEntry> & Pick<DossierEntry, 'kind'>): DossierEntry => ({
  scope: 'unit', computed: true, count: 0, total: null, value: null, key: null, label: null, target_unit: null, ...e,
})  // prettier-ignore
const DOSSIER: Dossier = {
  unit_id: 'v:0',
  entries: [
    entry({ kind: 'phrases', count: 1 }),
    entry({ kind: 'sequences', count: 0 }),
    entry({ kind: 'wordplay', count: 0 }),
    entry({ kind: 'changes', count: 3 }),
    entry({ kind: 'borrowing', computed: false }),
    entry({ kind: 'acrostic', scope: 'chapter', target_unit: 'c:25:118', value: 0.0004, count: 1 }),
    entry({ kind: 'structure', scope: 'chapter', target_unit: 'c:25:118', value: 0.4, count: 0 }),
    entry({ kind: 'speech', count: 2, key: '1732', label: 'דוד' }),
    entry({ kind: 'voices', count: 1, key: '1732', label: 'דוד' }),
    entry({ kind: 'divisions', count: 1, key: 'cut', value: 0.09 }),
    entry({ kind: 'ketiv', count: 2 }),
    entry({ kind: 'citations', count: 1 }),
    entry({ kind: 'allusions', count: 2 }),
    entry({ kind: 'mirrors', count: 1 }),
    entry({ kind: 'echoes', count: 2 }),
    entry({ kind: 'meter', scope: 'chapter', target_unit: 'c:25:118', value: 0.61, count: 1 }),
    entry({ kind: 'roots', count: 2 }),
    entry({ kind: 'places', count: 2, key: '1', label: 'ירושלם' }),
    entry({ kind: 'people', count: 3, key: '17', label: 'דוד' }),
    entry({ kind: 'ciphers', count: 1, key: 'ששך', label: 'בבל' }),
    entry({ kind: 'gematria', count: 1, label: 'אליעזר', value: 2701, total: 4 }),
  ],
}

function mockApi(failing: string[] = []) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      if (failing.includes(u.pathname)) return new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
      const body = u.pathname.startsWith('/api/dossier/')
        ? DOSSIER
        : u.pathname.startsWith('/api/unit/')
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
                  : u.pathname.startsWith('/api/meter/')
                  ? METER
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

  it('lists what the analyses found and skips the panels with nothing to show', async () => {
    const calls = mockApi()
    renderAt('/unit/v:0')
    const bar = await screen.findByRole('navigation', { name: 'What the analyses found here' })
    const link = (name: string | RegExp) => screen.getByRole('link', { name }).getAttribute('href')
    // every finding: a family shows its first four until "more"
    fireEvent.click(within(bar).getByRole('button', { name: '+1 more' }))
    expect(link('1 shared phrase')).toBe('/phrases?unit=v%3A0')
    expect(link('3 word changes in parallels')).toBe('/changes?unit=v%3A0')
    expect(link('acrostic, q < 0.001 (chapter)')).toBe('/unit/c%3A25%3A118?acrostic=1')
    expect(link('2 quotation clauses, mostly דוד')).toBe('/unit/v%3A0?syntax=1')
    expect(link('the voice of דוד')).toBe('/speech?view=voices&voice=1732')
    expect(link('a chapter start inside running text')).toBe('/divisions?book=0&unit=v%3A0')
    expect(link('2 words written one way and read another')).toBe('/ketiv?unit=v%3A0')
    expect(link('1 explicit citation')).toBe('/citations?unit=v%3A0')
    expect(link('2 passages sharing rare words')).toBe('/phrases?view=spread&unit=v%3A0')
    expect(link('1 mirrored order')).toBe('/structure?view=small&unit=v%3A0')
    expect(link('2 directed echoes with other books')).toBe('/network?view=directions&unit=v%3A0')
    expect(link('lines fall like a lament (net 0.61) (chapter)')).toBe('/unit/c%3A25%3A118?halves=1&meter=1')
    expect(link('2 pairs of words of one root')).toBe('/roots?unit=v%3A0')
    expect(link('2 places on the map, most named ירושלם')).toBe('/places?unit=v%3A0')
    expect(link('3 people in the family tree, most named דוד')).toBe('/genealogy?p=17')
    expect(link('1 name read through atbash or albam (ששך read as בבל)')).toBe('/ciphers?unit=v%3A0')
    expect(link("letter value 2,701, as in 4 other verses · the tradition's values: אליעזר")).toBe('/gematria?q=2701&view=verses')
    expect(bar.textContent).toContain('Nothing found: parallel runs · wordplay · inclusio / chiasm')
    expect(bar.textContent).toContain('Not computed in this build: who borrowed')
    await screen.findByLabelText('Shared phrases')
    expect(calls.some((c) => c.includes('/api/wordplay') || c.includes('/api/sequences'))).toBe(false)
  })

  it('shows the dossier in Hebrew', async () => {
    mockApi()
    renderAt('/unit/v:0', 'he')
    const bar = await screen.findByRole('navigation', { name: 'מה מצאו הניתוחים כאן' })
    expect(screen.getByRole('link', { name: 'צירוף משותף אחד' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'תחילת פרק בתוך טקסט רציף' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'שני מקומות במפה, הנזכר ביותר ירושלם' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'ערך האותיות 2,701, כמו ב־4 פסוקים אחרים · ערכי המסורת: אליעזר' })).toBeTruthy()
    expect(bar.textContent).toContain('לא חושב בבנייה זו: כיוון השאילה')
  })

  it('says when an optional panel fails instead of hiding it', async () => {
    // without a dossier every panel is fetched, as before it existed
    mockApi(['/api/phrases/0', '/api/wordplay', '/api/dossier/v%3A0'])
    renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    // the server's detail is its own (bidi-isolated) element: match the alert's whole text
    await waitFor(() =>
      expect(screen.getAllByRole('alert').map((a) => a.textContent)).toEqual(
        expect.arrayContaining([
          'Could not load shared phrases (500: boom).',
          'Could not load wordplay (500: boom).',
          'Could not load what the analyses found here (500: boom).',
        ]),
      ),
    )
    expect(screen.queryByText(/Could not load parallel sequences/)).toBeNull()
  })

  it('marks Sefaria-linked hits and can hide them', async () => {
    const calls = mockApi()
    renderAt('/unit/v:0')
    const hit = (await screen.findByText('Test 1:6')).closest('li')!
    expect(hit.querySelector('.link-badge')?.getAttribute('title')).toContain('quotation')
    fireEvent.click(screen.getByRole('button', { name: /^Hide/ }))
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
    expect(within(panel).getByRole('link', { name: 'root אָמַר' }).getAttribute('href')).toBe('/root/559')
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByLabelText('Word analysis')).toBeNull()
  })

  it('splits the verse at its accent pause and marks parallel halves', async () => {
    const calls = mockApi()
    const { container } = renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    expect(container.querySelector('.colon-break')).toBeNull()
    // the layered reader reads the verse in its chapter
    expect(screen.getByRole('link', { name: 'Read with layers' }).getAttribute('href')).toBe('/read/v%3A0')
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

  it('shows the stresses of each line with the chapter it is in', async () => {
    const calls = mockApi()
    const { container } = renderAt('/unit/v:0?halves=1')
    await screen.findByText('Test 1:6')
    fireEvent.click(await screen.findByLabelText('Stresses'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?halves=1&meter=1'))
    await waitFor(() => expect(container.querySelector('.source .meter-badge')?.textContent).toBe('1:1 · 1'))
    expect(screen.getByText(/This chapter's lines: net fall 0\.61, above 99% of the poetry pool \(Lamentations 1–4\)/)).toBeTruthy()
    expect(calls.some((c) => c.startsWith('/api/meter/v%3A0'))).toBe(true)
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

  it('groups the findings under the nav’s families, the first few of each and the rest behind "more"', async () => {
    mockApi()
    const { container } = renderAt('/unit/v:0')
    const bar = await screen.findByRole('navigation', { name: 'What the analyses found here' })
    const groups = () => [...bar.querySelectorAll('.dossier-family')].map((f) => [f.querySelector('dt')!.textContent, f.querySelectorAll('.dossier-chip').length])
    // the nav's order: Parallels, the four sections of Patterns, Overview
    expect(groups()).toEqual([
      ['Parallels', 4],
      ['Poetry and form', 4],
      ['Words and names', 2],
      ['Letters and numbers', 2],
      ['Overview', 4],
    ])
    expect(within(bar).queryByRole('link', { name: /3 people in the family tree/ })).toBeNull()
    const more = within(bar).getByRole('button', { name: '+1 more' })
    expect(more.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(more)
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?found=all'))
    expect(groups().at(-1)).toEqual(['Overview', 5])
    expect(within(bar).queryByRole('button', { name: /more$/ })).toBeNull()
    fireEvent.click(within(bar).getByRole('button', { name: 'Show fewer' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0'))
    expect(groups().at(-1)).toEqual(['Overview', 4])
    // the analyses that found nothing are folded away, and open in the URL
    const rest = container.querySelector('details.dossier-rest') as HTMLDetailsElement
    expect(rest.open).toBe(false)
    expect(rest.querySelector('summary')?.textContent).toBe('Nothing found by 3 other analyses; 1 not computed in this build')
    rest.open = true
    fireEvent(rest, new Event('toggle'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?open=nothing'))
  })

  it('lists the page’s sections that are drawn in a strip, marks one, and jumps to a section on a click', async () => {
    const into = vi.fn()
    Element.prototype.scrollIntoView = into
    mockApi()
    renderAt('/unit/v:0')
    await screen.findByLabelText('Shared phrases')
    const strip = screen.getByRole('navigation', { name: 'On this page' })
    // a verse has no structure panel, and wordplay and runs found nothing here
    await waitFor(() => expect(within(strip).getAllByRole('link').map((a) => a.textContent)).toEqual(['Text', 'Clauses and speakers', 'Similar verses', 'Shared phrases']))
    expect(within(strip).getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'true')).toHaveLength(1)
    fireEvent.click(within(strip).getByRole('link', { name: 'Similar verses' }))
    const similar = document.getElementById('unit-similar')!
    expect(into).toHaveBeenCalledWith({ block: 'start' })
    expect(into.mock.instances.at(-1)).toBe(similar)
    expect(document.activeElement).toBe(similar)
    expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0') // the address does not change
  })

  it('keeps the list’s filters behind one Hide button, with the number switched on', async () => {
    const calls = mockApi()
    renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    const hide = screen.getByRole('button', { name: /^Hide/ })
    expect(hide.textContent).toContain('1') // neighbours ±2, the default of a verse
    expect(hide.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByLabelText('Hide same book')).toBeNull()
    fireEvent.click(hide)
    expect((screen.getByLabelText('Hide neighbours ±2') as HTMLInputElement).checked).toBe(true)
    fireEvent.click(screen.getByLabelText('Hide same book'))
    await waitFor(() => expect(calls.some((c) => c.includes('exclude=neighbors%2Cbook'))).toBe(true))
    expect(screen.getByRole('button', { name: /^Hide/ }).textContent).toContain('2')
    // Escape closes it and gives the focus back; so does a click outside
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByLabelText('Hide same book')).toBeNull()
    expect(document.activeElement).toBe(hide)
    fireEvent.click(hide)
    fireEvent.mouseDown(document.body)
    expect(screen.queryByLabelText('Hide same book')).toBeNull()
  })

  it('offers Reset once the list is not the default one, and goes back to it', async () => {
    mockApi()
    renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    expect(screen.queryByRole('button', { name: 'Reset' })).toBeNull()
    fireEvent.click(screen.getByRole('radio', { name: 'Lexical' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?mode=lexical'))
    fireEvent.click(screen.getByRole('radio', { name: 'Changes' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0?mode=lexical&marks=changes'))
    fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/unit/v:0'))
    expect(screen.queryByRole('button', { name: 'Reset' })).toBeNull()
    expect(screen.getByRole('radio', { name: 'Fused' }).getAttribute('aria-checked')).toBe('true')
  })

  it('puts the text’s options under one group, and the ways out of the page under the heading', async () => {
    mockApi()
    const { container } = renderAt('/unit/v:0')
    await screen.findByText('Test 1:6')
    const group = screen.getByRole('group', { name: 'Show in the text:' })
    expect(within(group).getByLabelText("Verse halves (te'amim)")).toBeTruthy()
    const actions = container.querySelector('.head-actions')!
    expect([...actions.querySelectorAll('a, button')].map((x) => x.textContent)).toEqual(['Read with layers', 'Its neighbourhood as a graph', 'Copy reference', 'Copy text'])
  })

  it('names the families and the controls in Hebrew', async () => {
    mockApi()
    renderAt('/unit/v:0', 'he')
    const bar = await screen.findByRole('navigation', { name: 'מה מצאו הניתוחים כאן' })
    expect([...bar.querySelectorAll('.dossier-family dt')].map((d) => d.textContent)).toEqual(['מקבילות', 'שירה וצורה', 'מילים ושמות', 'אותיות ומספרים', 'מבט־על'])
    expect(within(bar).getByRole('button', { name: 'ועוד 1' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'בעמוד הזה' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /^הסתרה/ })).toBeTruthy()
    expect(screen.getByRole('group', { name: 'להציג בטקסט:' })).toBeTruthy()
  })
})
