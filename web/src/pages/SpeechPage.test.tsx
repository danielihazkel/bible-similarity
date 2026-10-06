// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, SpeechBookResponse, SpeechResponse, UnitSyntax } from '../api/types'
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
        path === '/api/books' ? BOOKS
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
