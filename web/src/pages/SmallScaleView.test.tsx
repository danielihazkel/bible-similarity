// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MirrorClausesResponse, MirrorsResponse, MirrorVersesResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { StructurePage } from './StructurePage'

const side = (c: number, p: number, share: number, verses: number) => ({
  verses_chiastic: c,
  verses_parallel: p,
  pairs_chiastic: 0,
  pairs_parallel: 0,
  share,
  p: 4.9e-23,
  verses,
  bigrams: 0,
  interval: [0.416, 0.441] as [number, number],
})
const META: MirrorsResponse = {
  meta: {
    words: { all: side(2099, 2790, 0.429, 6853), poetry: side(47, 75, 0.386, 231), prose: side(2052, 2715, 0.429, 6622) },
    clauses: {
      poetry: 0.235,
      poetry_n: 506,
      prose: 0.167,
      prose_n: 2670,
      diff: 0.068,
      p: 0.0003,
      pairs: 3176,
      by_pair: [{ pair: 'Objc-Pred', n: 944, poetry: 0.294, poetry_n: 187, prose: 0.186, prose_n: 757 }],
    },
    full_mirrors: 94,
    full_mirrors_q: 0,
    min_words: 3,
  },
}
const verse = (id: number, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 26,
  chapter: 1,
  verse: 1,
  ref: `V${id}`,
  ref_he: 'הפניה',
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const CLAUSES: MirrorClausesResponse = {
  pair: null,
  mirrored: null,
  poetic: null,
  book: null,
  unit: null,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      pair_id: 1,
      verse_id: 7,
      label: 'Psalms 1:2',
      label_he: 'תהלים א:ב',
      poetic: true,
      pair: 'Objc-Pred',
      first: 'Pred',
      second: 'Objc',
      mirrored: true,
      verse: verse(7, ['חֶפְצוֹ', 'יֶהְגֶּה', 'תוֹרָתוֹ', 'יֶהְגֶּה']),
      marks: { '0': 1, '1': 0, '2': 1, '3': 0 },
    },
  ],
}
const VERSES: MirrorVersesResponse = {
  book: null,
  unit: null,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      verse_id: 9,
      label: 'Exodus 32:16',
      label_he: 'שמות לב:טז',
      poetic: false,
      n_pairs: 3,
      n_words: 3,
      p: 0.051,
      q: 0.083,
      verse: verse(9, ['הַלֻּחֹת', 'מַעֲשֵׂה', 'אֱלֹהִים', 'אֱלֹהִים', 'מַעֲשֵׂה', 'הַלֻּחֹת']),
      marks: { '0': 0, '1': 1, '2': 2, '3': 2, '4': 1, '5': 0 },
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', meta: MirrorsResponse = META) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/books' ? [] : p === '/api/mirrors' ? meta : p === '/api/mirrors/clauses' ? CLAUSES : p === '/api/mirrors/verses' ? VERSES : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/structure" element={<StructurePage />} />
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

describe('Structure → Small scale', () => {
  it('states both order tests and lists clause pairs with their parts marked', async () => {
    const { container, calls } = renderAt('/structure?view=small')
    expect(await screen.findByText(/mirrored \(x y … y x\) in 2,099 verses and repeated \(x y … x y\) in 2,790/)).toBeTruthy()
    expect(screen.getByText(/in 24% of the pairs in poetry \(506\) and 17% in prose \(2,670\)/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'object + verb' }).getAttribute('href')).toBe('/structure?view=small&list=clauses&pair=Objc-Pred&mirrored=1#mirror-lists')
    await screen.findByRole('link', { name: 'Psalms 1:2' })
    expect(screen.getByText('verb – object | object – verb')).toBeTruthy()
    expect(container.querySelectorAll('.mirror-item .w-focus')).toHaveLength(2)
    expect(container.querySelectorAll('.mirror-item .w-shared')).toHaveLength(2)
    expect(calls.some((c) => c.startsWith('/api/structure?'))).toBe(false)
    fireEvent.click(screen.getByRole('radio', { name: 'Full mirrors' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/structure?view=small&list=verses'))
    await screen.findByRole('link', { name: 'Exodus 32:16' })
    expect(screen.getByText(/94 verses where 3 or more words used twice all nest/)).toBeTruthy()
    expect(container.querySelectorAll('.mirror-item .w-acrostic')).toHaveLength(2)
  })

  it('reads in Hebrew and returns to the whole passages', async () => {
    const { calls } = renderAt('/structure?view=small', 'he')
    expect(await screen.findByText(/הופכות את סדרם ב־24% מהזוגות בשירה/)).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'קטעים שלמים' }))
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/structure?'))).toBe(true))
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/structure?view=small', 'en', { meta: {} })
    expect(await screen.findByText(/run `bsim mirrors`/)).toBeTruthy()
  })
})
