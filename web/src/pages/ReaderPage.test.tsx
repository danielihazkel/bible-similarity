// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReaderResponse, StructureResponse, UnitDetail, UnitParallelism, UnitSummary, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { parseLayers, toggleLayer } from '../lib/layers'
import { ReaderPage } from './ReaderPage'

const CHAPTER: UnitSummary = {
  unit_id: 'c:0:1',
  unit_type: 'chapter',
  label_en: 'Genesis 1',
  label_he: 'בראשית א',
  book_id: 0,
  start_verse_id: 0,
  end_verse_id: 1,
  n_verses: 2,
  marker: null,
}
const verse = (id: number, n: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 0,
  chapter: 1,
  verse: n,
  ref: `Genesis 1:${n}`,
  ref_he: `בראשית א:${n}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const DETAIL: UnitDetail = {
  unit: CHAPTER,
  verses: [verse(0, 1, ['בְּרֵאשִׁית', 'בָּרָא', 'אֱלֹהִים']), verse(1, 2, ['וַיֹּאמֶר', 'אֱלֹהִים', 'יְהִי', 'אוֹר'])],
  parents: [],
  prev_id: null,
  next_id: 'c:0:2',
}
const VERSE_DETAIL: UnitDetail = {
  ...DETAIL,
  unit: { ...CHAPTER, unit_id: 'v:1', unit_type: 'verse', start_verse_id: 1, end_verse_id: 1, n_verses: 1 },
  verses: [DETAIL.verses[1]],
}
const READER: ReaderResponse = {
  unit: CHAPTER,
  rare_verses: 3,
  computed: { speech: true, phrases: true, wordplay: true, ketiv: true, gaps: true, refrains: true, mood: true, sources: true, places: true, divine: true },
  speakers: [{ lemma: '430', he: 'אלהים', divine: true, n_words: 2, to: ['אדם'] }],
  refrains: [{ refrain_id: 7, text: 'וַיֹּאמֶר אֱלֹהִים', k: 9, known: null }],
  places: [{ place_id: 5, he: 'ראשית', kind: 'region' }],
  verses: [
    {
      verse_id: 0,
      refrains: {},
      mood: { '0': 'distress' },
      source: { side: 'P', prob: 0.83, reference: 'P' },
      speech: {},
      phrases: { '0': 6 },
      rare: { '1': 1 },
      wordplay: [
        {
          display: 1,
          partner_vid: 1,
          partner_display: 3,
          partner_label: 'Genesis 1:2',
          partner_label_he: 'בראשית א:ב',
          form: 'ברא',
          partner_form: 'אור',
          kind: 'metathesis',
          q: 0.01,
        },
      ],
      ketiv: [],
      gap: null,
      gematria: [913, 203, 86],
      places: { '0': 5 }, divine: { '1': 'elohim' },
    },
    {
      verse_id: 1,
      refrains: { '0': 0, '1': 0 },
      mood: { '1': 'praise', '2': 'praise' },
      source: { side: 'P', prob: 0.6, reference: 'nonP' },
      speech: { '2': 0, '3': 0 },
      phrases: {},
      rare: {},
      wordplay: [],
      ketiv: [{ display: [3], ketiv: 'אר', qere: 'אוֹר', cls: 'vowel_letter' }],
      gap: { score: 0.98, kind: 'turn', mam: 'pe', chapter: false },
      gematria: [257, 86, 25, 207],
      places: {}, divine: {},
    },
  ],
}
const STRUCTURE = {
  unit: CHAPTER,
  verse_ids: [0, 1],
  leitworte: [{ lemma: '430', he_lemma: 'אלהים', count: 2, expected: 0.4, g2: 9, multiple_of: [], occurrences: { '0': [2], '1': [1] } }],
  root_leitworte: [
    {
      root: '1254',
      root_he: 'ברא',
      count: 1,
      expected: 0.1,
      g2: 5,
      lemmas: [],
      hidden: true,
      occurrences: { '0': [1] },
    },
  ],
} as unknown as StructureResponse
const HALVES = {
  unit: CHAPTER,
  parallel_at: 0.5,
  mean_prob: null,
  share_parallel: null,
  n_scored: 0,
  verses: [{ verse_id: 1, n_cola: 2, cola: [[0, 1], [2, 3]], clauses: [] }],
} as unknown as UnitParallelism

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', reader: ReaderResponse = READER) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = decodeURIComponent(new URL(url, 'http://x').pathname)
      const body =
        p === '/api/unit/c:0:1'
          ? DETAIL
          : p === '/api/unit/v:1'
            ? VERSE_DETAIL
            : p === '/api/reader/c:0:1'
              ? reader
              : p === '/api/structure/c:0:1'
                ? STRUCTURE
                : p === '/api/parallelism/c:0:1'
                  ? HALVES
                  : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/read/:unitId" element={<ReaderPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { ...r, calls }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('layers in the URL', () => {
  it('reads the default set, an explicit list and none', () => {
    expect([...parseLayers(null)]).toEqual(['speakers', 'leitworte', 'turns'])
    expect([...parseLayers('rare,cola,bogus')]).toEqual(['cola', 'rare'])
    expect(parseLayers('').size).toBe(0)
  })
  it('switches one layer, back to no parameter at the default set', () => {
    expect(toggleLayer(parseLayers(null), 'cola')).toBe('speakers,cola,leitworte,turns')
    expect(toggleLayer(parseLayers('speakers,cola,leitworte,turns'), 'cola')).toBeNull()
    expect(toggleLayer(parseLayers('rare'), 'rare')).toBe('')
  })
})

describe('ReaderPage', () => {
  it('paints speakers, Leitworte and turns by default', async () => {
    const { container, calls } = renderAt('/read/c%3A0%3A1')
    await waitFor(() => expect(container.querySelectorAll('.reader-text .spk-0')).toHaveLength(2))
    expect(container.querySelector('.reader-text .spk-0')?.getAttribute('title')).toBe('spoken by אלהים')
    await waitFor(() => expect(container.querySelectorAll('.reader-text .lw-0')).toHaveLength(2))
    expect(container.querySelector('.reader-text .lw-0')?.getAttribute('title')).toBe('Leitwort אלהים: 2 times here, 0.4 expected')
    expect(container.querySelector('.reader-gap.gap-turn')?.textContent).toBe('פturn')
    expect(screen.getByText(/2 words/).closest('.layer-key')?.textContent).toContain('(God)')
    expect(screen.getByText(/2 words/).closest('.layer-key')?.textContent).toContain('to אדם')
    // layers that are off are neither fetched nor painted
    expect(calls.some((c) => c.includes('/parallelism/'))).toBe(false)
    expect(container.querySelector('.ph, .wp, .w-mark')).toBeNull()
    expect(screen.getByRole('link', { name: /Next/ }).getAttribute('href')).toBe('/read/c%3A0%3A2')
  })

  it('turns layers on and off through the URL', async () => {
    const { container, calls } = renderAt('/read/c%3A0%3A1')
    await screen.findByRole('button', { name: 'Verse halves' })
    fireEvent.click(screen.getByRole('button', { name: 'Verse halves' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/read/c%3A0%3A1?layers=speakers%2Ccola%2Cleitworte%2Cturns'))
    await waitFor(() => expect(container.querySelectorAll('.colon-break')).toHaveLength(1))
    expect(calls.some((c) => c.includes('/parallelism/'))).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Speakers' }))
    await waitFor(() => expect(container.querySelector('.reader-text .spk')).toBeNull())
    expect(screen.getByRole('button', { name: 'Speakers' }).getAttribute('aria-pressed')).toBe('false')
  })

  it('marks shared phrases, rare words, ketiv and wordplay partners', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=phrases,rare,ketiv,wordplay')
    await waitFor(() => expect(container.querySelector('.ph-3')).not.toBeNull())
    expect(container.querySelector('.ph-3')?.getAttribute('title')).toBe('in a phrase shared with 6 other verses')
    const marks = [...container.querySelectorAll('.w-mark')].map((s) => s.textContent)
    expect(marks).toEqual(['1', 'ק'])
    const play = container.querySelector('.wp')!
    // a word's tooltip lists what every layer says about it
    expect(play.getAttribute('title')).toBe('sounds like אור (Genesis 1:2): Letters swapped\nnowhere else in the Bible (hapax legomenon)')
    fireEvent.click(play)
    await waitFor(() => expect(container.querySelectorAll('.wp-partner')).toHaveLength(1))
    expect(container.querySelector('.wp-partner')?.textContent).toContain('אוֹר')
    expect(container.querySelector('.wp-partner')?.getAttribute('title')).toBe('written אר, read אוֹר: A vowel letter')
  })

  it('adds each word’s letter value and each verse’s total', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=gematria')
    await waitFor(() => expect(container.querySelectorAll('.reader-text .gm-total')).toHaveLength(2))
    const marks = [...container.querySelectorAll('.w-mark')].map((s) => s.textContent)
    expect(marks).toEqual(['=913', '=203', '=86', '=257', '=86', '=25', '=207'])
    const [a] = container.querySelectorAll('.reader-text .gm-total')
    expect(a.textContent).toBe('=1202')
    expect(a.getAttribute('href')).toBe('/gematria?q=1202&view=verses')
    expect(screen.getByText(/=913 after a word: its letter value/)).toBeTruthy()
  })

  it('marks the places named and links them to the map', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=places')
    await waitFor(() => expect(container.querySelector('.reader-text .pl.pl-region')).not.toBeNull())
    expect(container.querySelector('.reader-text .pl')?.getAttribute('title')).toContain('ראשית: Region')
    expect(screen.getByRole('link', { name: 'ראשית' }).getAttribute('href')).toBe('/places?unit=c%3A0%3A1&p=5')
    expect(screen.getByRole('link', { name: 'all on the map' }).getAttribute('href')).toBe('/places?unit=c%3A0%3A1')
  })

  it('draws a line above each name of God', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=divine')
    await waitFor(() => expect(container.querySelector('.reader-text .dv.dv-elohim')).not.toBeNull())
    expect(container.querySelector('.reader-text .dv')?.getAttribute('title')).toContain('a name of God: אלהים')
    expect(container.querySelectorAll('.reader-text .dv')).toHaveLength(1)
    expect(screen.getByRole('link', { name: 'the mix of every chapter' }).getAttribute('href')).toBe('/divine')
  })

  it('marks the refrains and links to them', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=refrains')
    await waitFor(() => expect(container.querySelectorAll('.reader-text .rf')).toHaveLength(2))
    expect(container.querySelector('.reader-text .rf')?.getAttribute('title')).toBe('refrain וַיֹּאמֶר אֱלֹהִים: in 9 verses')
    expect(screen.getByRole('link', { name: 'Every refrain here' }).getAttribute('href')).toBe('/refrains?unit=c%3A0%3A1&all=1')
  })

  it('marks words of distress and praise', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=mood')
    await waitFor(() => expect(container.querySelectorAll('.reader-text .md-praise')).toHaveLength(2))
    const distress = container.querySelectorAll('.reader-text .md-distress')
    expect(distress).toHaveLength(1)
    expect(distress[0].textContent).toBe('בְּרֵאשִׁית')
    expect(distress[0].getAttribute('title')).toBe('a word of distress')
    expect(screen.getByText(/A bar under a word: solid, a word of praise/)).toBeTruthy()
  })

  it('tags each verse with its side of the P / non-P split', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=sources')
    await waitFor(() => expect(container.querySelectorAll('.reader-text .src-tag')).toHaveLength(2))
    const [a, b] = container.querySelectorAll('.reader-text .src-tag')
    expect(a.textContent).toBe('P')
    expect(a.getAttribute('title')).toBe('P-like (83% P-like); the critics: P')
    expect(b.classList.contains('src-differs')).toBe(true)
    expect(screen.getByRole('link', { name: "The split on the Pentateuch's sources page" }).getAttribute('href')).toBe('/pentateuch')
  })

  it('counts Leitworte by root on request', async () => {
    const { container } = renderAt('/read/c%3A0%3A1?layers=leitworte')
    fireEvent.click(await screen.findByRole('radio', { name: 'By root' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/read/c%3A0%3A1?layers=leitworte&lw=root'))
    await waitFor(() => expect(container.querySelector('.reader-text .lw-0')?.textContent).toBe('בָּרָא'))
  })

  it('says which layers this build did not compute', async () => {
    renderAt('/read/c%3A0%3A1?layers=speakers,turns', 'en', {
      ...READER,
      computed: { speech: false, phrases: true, wordplay: true, ketiv: true, gaps: false },
      speakers: [],
      verses: READER.verses.map((v) => ({ ...v, speech: {}, gap: null })),
    })
    expect(await screen.findByText('Speakers: not computed in this build.')).toBeTruthy()
    expect(screen.getByText('Turns: not computed in this build.')).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    const { container } = renderAt('/read/c%3A0%3A1', 'he')
    expect(await screen.findByRole('button', { name: 'מילים מנחות' })).toBeTruthy()
    await waitFor(() => expect(container.querySelector('.reader-text .spk-0')?.getAttribute('title')).toBe('בפי אלהים'))
    expect(container.querySelector('.gap-kind')?.textContent).toBe('מפנה')
  })

  it('reads a verse in its chapter', async () => {
    renderAt('/read/v%3A1?layers=rare')
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe("/read/c%3A0%3A1?layers=rare"))
  })
})
