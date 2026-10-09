// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, SpeechBookResponse, SpeechResponse, UnitSyntax, VoiceDetail, VoicesResponse } from '../api/types'
import { SyntaxPanel } from '../components/SyntaxPanel'
import { LocaleProvider } from '../context/Locale'
import { SpeechPage } from './SpeechPage'

const BOOKS: Book[] = [{ book_id: 2, name: 'Leviticus', he_name: 'ויקרא', osis: 'Lev', section: 'Torah', n_chapters: 27 }]
const shares = { narration: 0.1, speech: 0.83, discourse: 0, divine: 0.74, attributed: 0.77, n_words: 11938 }
const GOD = { lemma: '3068', he: 'יהוה', n_words: 8000, n_explicit: 2000, divine: true }
const SPEECH: SpeechResponse = {
  meta: { speaker: { explicit: 17925, carried: 8700, enclosing: 4696, unknown: 21616 } },
  books: [{ book_id: 2, ...shares, speakers: [GOD] }],
}
const LEV: SpeechBookResponse = {
  book_id: 2,
  chapters: [{ unit_id: 'c:2:1', chapter: 1, ...shares }],
  speakers: [GOD, { lemma: '4872', he: 'משה', n_words: 300, n_explicit: 120, divine: false }],
}
const SAMUEL: Book = { book_id: 7, name: 'I Samuel', he_name: 'שמואל א', osis: '1Sam', section: 'Prophets', n_chapters: 31 }
const CHR: Book = { book_id: 37, name: 'I Chronicles', he_name: 'דברי הימים א', osis: '1Chr', section: 'Writings', n_chapters: 29 }
const speaker = (key: string, he: string | null, effect: number, q: number) => ({
  key, he, n_words: 3000, n_explicit: 1800, n_clauses: 400, main_book: 7, books: [7, 37], delta: 0.3,
  null_mean: 0.2, effect, p: q, q,
})  // prettier-ignore
const VOICES: VoicesResponse = {
  meta: {
    significant: 1,
    calibration: { significant: 0, of: 2 },
    sensitivity: { speakers: 2, rho: 0.88 },
    order: ['divine', '1732', 'narrator'],
    checks: {
      author: [
        { speaker: '1732', a: ['1Sam'], b: ['1Chr'], cross: 0.153, p_cross: 0.001, d_ab: 0.6, p_ab: 0.001, words_a: 1969, words_b: 1004, verdict: 'author' },
      ],
      distinct: [{ book: '1Sam', speaker: '1732', rank: 2, of: 2, ranking: [{ key: 'divine', effect: 9, q: 0.001 }, { key: '1732', effect: 5.3, q: 0.002 }] }],
    },
  },
  speakers: [speaker('divine', null, 9, 0.001), speaker('1732', 'דוד', 0.4, 0.3)],
  pairs: [
    { a: 'divine', b: '1732', delta: 0.4 },
    { a: 'divine', b: 'narrator', delta: 0.9 },
    { a: '1732', b: 'narrator', delta: 0.5 },
  ],
}  // prettier-ignore
const DAVID: VoiceDetail = {
  speaker: speaker('1732', 'דוד', 0.4, 0.3),
  features: [
    { side: 'over', rank: 0, feature: 'verb:h', label: 'עתיד מוארך', rate: 0.01, rate_ref: 0.004, z: 1.3 },
    { side: 'under', rank: 1, feature: 'verb:q', label: 'וקטל (עבר מהופך)', rate: 0.01, rate_ref: 0.03, z: -1.1 },
  ],
  nearest: [{ a: '1732', b: 'divine', delta: 0.4 }],
  chapters: [{ unit_id: 'c:37:17', book_id: 37, chapter: 17, n_clauses: 30 }],
}  // prettier-ignore
const SYNTAX: UnitSyntax = {
  verses: [
    {
      verse_id: 2680,
      ref: 'Leviticus 1:1',
      ref_he: 'ויקרא א:א',
      clauses: [
        {
          typ: 'Way0', kind: 'VC', txt: 'N', rela: 'NA', speech: false, speaker: null, speaker_he: null,
          speaker_source: null, divine: false,
          segments: [{ function: 'Pred', typ: 'VP', text: 'וַיִּקְרָא' }, { function: 'Cmpl', typ: 'PP', text: 'אֶל מֹשֶׁה' }],
        },
        {
          typ: 'ZIm0', kind: 'VC', txt: 'NQ', rela: 'NA', speech: true, speaker: '3068', speaker_he: 'יהוה',
          speaker_source: 'explicit', divine: true,
          segments: [{ function: 'Pred', typ: 'VP', text: 'דַּבֵּר' }],
        },
        {
          typ: 'WQt0', kind: 'VC', txt: 'NQ', rela: 'NA', speech: true, speaker: '3068', speaker_he: 'יהוה',
          speaker_source: 'explicit', divine: true,
          segments: [{ function: 'Pred', typ: 'VP', text: 'וְאָמַרְתָּ' }],
        },
      ],
    },
  ],
  neighbors: [
    {
      unit: { unit_id: 'v:2700', unit_type: 'verse', label_en: 'Leviticus 4:1', label_he: 'ויקרא ד:א', book_id: 2, start_verse_id: 2700, end_verse_id: 2700, n_verses: 1, marker: null },
      score: 9.1,
      preview: 'וַיְדַבֵּר יְהוָה אֶל מֹשֶׁה',
    },
  ],
}  // prettier-ignore

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = new URL(url, 'http://x').pathname
      const body =
        path === '/api/books' ? [...BOOKS, SAMUEL, CHR]
        : path === '/api/voices' ? VOICES
        : path === '/api/voices/1732' ? DAVID
        : path === '/api/speech' ? SPEECH
        : path === '/api/speech/book/2' ? LEV
        : path === '/api/syntax/v%3A2680' ? SYNTAX
        : null  // prettier-ignore
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(ui: React.ReactNode, path: string, locale: 'en' | 'he' = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="*" element={ui} />
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

describe('SpeechPage', () => {
  it('shows each book’s narration and speech, and a book’s speakers and chapters', async () => {
    mockApi()
    renderAt(<SpeechPage />, '/speech')
    expect(await screen.findByText(/A hand check of 50 quotations: 42 right/)).toBeTruthy()
    expect(screen.getByRole('img', { name: /God speaks 74%/ })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Leviticus/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/speech?book=2'))
    expect(await screen.findByRole('link', { name: 'משה' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Leviticus 1' }).getAttribute('href')).toBe('/unit/c%3A2%3A1?syntax=1')
  })

  it('reads in Hebrew', async () => {
    mockApi()
    renderAt(<SpeechPage />, '/speech?book=2', 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'מי מדבר' })).toBeTruthy()
    expect(await screen.findByRole('link', { name: 'ויקרא א' })).toBeTruthy()
  })
})

describe('Voices', () => {
  it('lists speakers with the checks, and opens a speaker’s profile', async () => {
    mockApi()
    renderAt(<SpeechPage />, '/speech')
    fireEvent.click(await screen.findByRole('radio', { name: 'Voices' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/speech?view=voices'))
    expect(await screen.findByText(/2 speakers profiled; 1 distinct beyond chance/)).toBeTruthy()
    expect(screen.getByText(/passes 0 of 2/)).toBeTruthy()
    expect(screen.getByText('דוד in I Samuel and in I Chronicles')).toBeTruthy()
    expect(screen.getByText(/the author's voice over the character's/)).toBeTruthy()
    expect(screen.getByText(/I Samuel: דוד is number 2 of 2 speakers/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'God (יהוה, אלהים, אדני)' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'דוד' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/speech?view=voices&voice=1732'))
    expect(await screen.findByText('עתיד מוארך')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'I Chronicles 17' }).getAttribute('href')).toBe('/unit/c%3A37%3A17?syntax=1')
    expect(screen.getByRole('img', { name: /Distance between voices/ })).toBeTruthy()
  })

  it('reads in Hebrew, and says when the stage did not run', async () => {
    mockApi()
    renderAt(<SpeechPage />, '/speech?view=voices', 'he')
    expect(await screen.findByText('דוד בשמואל א ובדברי הימים א')).toBeTruthy()
    cleanup()
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ meta: {}, speakers: [], pairs: [] }))))
    renderAt(<SpeechPage />, '/speech?view=voices')
    expect(await screen.findByText(/No speaker voices in this build/)).toBeTruthy()
  })
})

describe('SyntaxPanel', () => {
  it('shows clauses with phrase functions, the speaker once per quotation, and same-shape verses', async () => {
    mockApi()
    renderAt(<SyntaxPanel unitId="v:2680" />, '/')
    expect(await screen.findByText('wayyiqtol')).toBeTruthy()
    expect(screen.getByText('imperative first')).toBeTruthy()
    expect(screen.getAllByText('predicate')).toHaveLength(3)
    expect(screen.getAllByRole('link', { name: 'spoken by יהוה' })).toHaveLength(1)
    expect(screen.getByRole('link', { name: /^Leviticus 4:1/ }).getAttribute('href')).toBe('/unit/v%3A2700')
  })
})
