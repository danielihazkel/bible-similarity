// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Verse } from '../api/types'
import { PoetryPage } from './PoetryPage'
import { TypeScenesPage } from './TypeScenesPage'
import { WordplayPage } from './WordplayPage'

const verse = (id: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 22,
  chapter: 24,
  verse: id,
  ref: `Isa 24:${id}`,
  ref_he: 'הפניה',
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const unit = (id: string, label: string) => ({
  unit_id: id,
  unit_type: 'pericope' as const,
  label_en: label,
  label_he: label,
  book_id: 26,
  start_verse_id: 0,
  end_verse_id: 1,
  n_verses: 2,
  marker: null,
})
const page = <T,>(items: T[], extra: object = {}) => ({ total: items.length, offset: 0, limit: 50, items, ...extra })

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function mount(path: string, route: string, element: ReactNode, bodies: Record<string, unknown>) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? [] : bodies[p]
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={route} element={element} />
        </Routes>
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { calls, ...r }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('TypeScenesPage', () => {
  it('lists aligned action sequences and hides textual parallels by default', async () => {
    const { calls } = mount('/typescenes', '/typescenes', <TypeScenesPage />, {
      '/api/typescenes': page(
        [
          {
            a: unit('s:1', 'Daniel 3:1–18'),
            b: unit('s:2', 'Daniel 6:16–29'),
            score: 55,
            n_matches: 2,
            aligned: [
              { a_vid: 1, b_vid: 2, lemma: 'x', he_lemma: 'רמה' },
              { a_vid: 3, b_vid: 4, lemma: 'y', he_lemma: 'שיזב' },
            ],
            parallel_text: false,
            q: 0.008,
          },
        ],
        { book: null, max_q: 0.05, hide_textual: true, unit: null },
      ),
    })
    expect(await screen.findByText('2 actions in order')).toBeTruthy()
    expect(screen.getByText('שיזב')).toBeTruthy()
    expect(calls.some((c) => c.includes('hide_textual=true') && c.includes('max_q=0.05'))).toBe(true)
    fireEvent.click(screen.getByLabelText('Include textual parallels'))
    await waitFor(() => expect(calls.some((c) => c.includes('hide_textual=false'))).toBe(true))
  })
})

describe('WordplayPage sound views', () => {
  it('shows alliteration and rhyme with their words marked', async () => {
    const { container } = mount('/wordplay?view=alliteration', '/wordplay', <WordplayPage />, {
      '/api/alliteration': page(
        [{ verse: verse(17, ['פַּחַד', 'וָפַחַת', 'וָפָח', 'עָלֶיךָ']), label: 'Isaiah 24:17', colon: 0, sound: 'פ', count: 3, n_words: 3, words: [0, 1, 2], p: 0.007, q: 0.55 }],
        { book: null, unit: null },
      ),
      '/api/rhymes': page(
        [{ start_vid: 8, end_vid: 8, label: 'Job 10:8', n_cola: 3, ending: 'נִי', members: [[8, 1], [8, 3]], verses: [verse(8, ['יָדֶיךָ', 'עֲצָּבוּנִי', 'וַיַּעֲשׂוּנִי', 'וַתְּבַלְּעֵנִי'])], p: 1e-8, q: 1e-7 }],
        { book: null, max_q: 0.05 },
      ),
    })
    expect(await screen.findByText('פ ×3')).toBeTruthy()
    expect(container.querySelectorAll('.disc .w-focus')).toHaveLength(3)
    fireEvent.click(screen.getByRole('radio', { name: 'Rhyme' }))
    expect(await screen.findByText('‑נִי ×3')).toBeTruthy()
    await waitFor(() => expect(container.querySelectorAll('.disc .w-focus')).toHaveLength(2))
  })
})

describe('PoetryPage word pairs', () => {
  it('lists fixed word pairs across parallel halves', async () => {
    mount('/poetry?view=pairs', '/poetry', <PoetryPage />, {
      '/api/word-pairs': page(
        [
          {
            a: { lemma: '6662', he_lemma: 'צדיק' },
            b: { lemma: '7563', he_lemma: 'רשע' },
            n: 28,
            expected: 1.2,
            g2: 90,
            q: 1e-9,
            reverse: 14,
            examples: [{ verse_id: 5, label_en: 'Proverbs 10:3', label_he: 'משלי י ג' }],
          },
        ],
        { max_q: 0.05, lemma: null },
      ),
    })
    expect(await screen.findByRole('link', { name: 'צדיק' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Proverbs 10:3' }).getAttribute('href')).toBe('/unit/v%3A5?halves=1')
    expect(screen.getByText('14')).toBeTruthy()
  })
})
