// @vitest-environment jsdom
// The views inside Poetry (fixed word pairs) and Wordplay (alliteration, rhyme), and the About page.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AlliterationResponse, Book, RhymesResponse, Verse, WordPairsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { AboutPage } from './AboutPage'
import { PoetryPage } from './PoetryPage'
import { WordplayPage } from './WordplayPage'

const BOOKS: Book[] = [{ book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 }]
const verse = (id: number, ref: string, refHe: string, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 26,
  chapter: 1,
  verse: id,
  ref,
  ref_he: refHe,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const PAIRS: WordPairsResponse = {
  total: 1,
  offset: 0,
  limit: 50,
  max_q: 0.05,
  lemma: null,
  items: [
    {
      a: { lemma: '8064', he_lemma: 'שָׁמַיִם' },
      b: { lemma: '776', he_lemma: 'אֶרֶץ' },
      n: 12,
      expected: 1.5,
      g2: 31.4,
      q: 0.001,
      reverse: 2,
      examples: [{ verse_id: 7, label_en: 'Psalms 69:35', label_he: 'תהלים סט לה' }],
    },
  ],
}
const ALLIT: AlliterationResponse = {
  total: 1,
  offset: 0,
  limit: 50,
  book: null,
  unit: null,
  items: [
    {
      verse: verse(3, 'Psalms 122:6', 'תהלים קכב ו', ['שַׁאֲלוּ', 'שְׁלוֹם', 'יְרוּשָׁלָ͏ִם', 'יִשְׁלָיוּ']),
      label: 'Psalms 122:6',
      label_he: 'תהלים קכב ו',
      colon: 0,
      sound: 'ש',
      count: 4,
      n_words: 4,
      words: [0, 1, 2, 3],
      p: 0.0004,
      q: 0.02,
    },
  ],
}
const RHYMES: RhymesResponse = {
  total: 1,
  offset: 0,
  limit: 50,
  book: null,
  max_q: 0.05,
  unit: null,
  items: [
    {
      start_vid: 5,
      end_vid: 5,
      label: 'Psalms 2:3',
      label_he: 'תהלים ב ג',
      n_cola: 2,
      ending: 'מו',
      members: [
        [5, 1],
        [5, 3],
      ],
      verses: [verse(5, 'Psalms 2:3', 'תהלים ב ג', ['נְנַתְּקָה', 'אֶת־', 'מוֹסְרוֹתֵימוֹ', 'עֲבֹתֵימוֹ'])],
      p: 0.003,
      q: 0.04,
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

const calls: string[] = []

function renderAt(path: string, route: string, page: ReactElement, locale: 'en' | 'he' = 'en') {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string) => {
      const url = String(input)
      calls.push(url)
      const body = url.startsWith('/api/books')
        ? BOOKS
        : url.startsWith('/api/word-pairs')
          ? PAIRS
          : url.startsWith('/api/alliteration')
            ? ALLIT
            : url.startsWith('/api/rhymes')
              ? RHYMES
              : { total: 0, offset: 0, limit: 50, items: [] }
      return new Response(JSON.stringify(body))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path={route} element={page} />
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

describe('fixed word pairs (Poetry)', () => {
  it('lists each pair with its lemmas, counts and an example, and includes all q on request', async () => {
    renderAt('/poetry?view=pairs', '/poetry', <PoetryPage />)
    expect(await screen.findByRole('link', { name: 'שָׁמַיִם' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'אֶרֶץ' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Psalms 69:35/ })).toBeTruthy()
    expect(calls.some((c) => c.startsWith('/api/word-pairs') && c.includes('max_q=0.05'))).toBe(true)
    fireEvent.click(screen.getByRole('radio', { name: 'All' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/poetry?view=pairs&q=all'))
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/word-pairs') && c.includes('max_q=1&'))).toBe(true))
  })
})

describe('sound (Wordplay)', () => {
  it('shows an alliterating colon with its sound and words marked', async () => {
    const { container } = renderAt('/wordplay?view=alliteration', '/wordplay', <WordplayPage />)
    expect(await screen.findByRole('link', { name: /Psalms 122:6/ })).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('[class*="focus"]').length).toBe(4)) // the four words in ש
    expect(calls.some((c) => c.startsWith('/api/alliteration'))).toBe(true)
  })

  it('shows a rhyme with its ending and its verse', async () => {
    renderAt('/wordplay?view=rhyme', '/wordplay', <WordplayPage />)
    expect(await screen.findByRole('link', { name: /Psalms 2:3/ })).toBeTruthy()
    expect(screen.getAllByText(/מו/).length).toBeGreaterThan(0)
    expect(calls.some((c) => c.startsWith('/api/rhymes'))).toBe(true)
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/wordplay?view=rhyme', '/wordplay', <WordplayPage />, 'he')
    expect(await screen.findByRole('link', { name: /תהלים ב ג/ })).toBeTruthy()
    expect(screen.queryByText('Psalms 2:3')).toBeNull()
  })
})

describe('About', () => {
  it('names the modes and the sources with their licences, in both languages', async () => {
    renderAt('/about', '/about', <AboutPage />)
    expect(screen.getByRole('heading', { level: 1, name: 'About' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Sources and licenses' })).toBeTruthy()
    expect(screen.getByText(/Miqra according to the Masorah/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Psalms 14:1' }).getAttribute('href')).toBe('/unit/v:15291')
    cleanup()
    renderAt('/about', '/about', <AboutPage />, 'he')
    expect(screen.queryByRole('heading', { name: 'About' })).toBeNull()
    expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(/[א-ת]/)
  })
})
