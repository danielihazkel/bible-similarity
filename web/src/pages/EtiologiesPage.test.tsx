// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EtiologiesResponse, Naming } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { EtiologiesPage } from './EtiologiesPage'

const verse = (id: number, ref: string, refHe: string, text: string) => ({
  verse_id: id,
  book_id: 0,
  chapter: 29,
  verse: 32,
  ref,
  ref_he: refHe,
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const naming = (over: Partial<Naming>): Naming => ({
  naming: 0,
  unit_id: 'c:0:29',
  verse: verse(800, 'Genesis 29:32', 'בראשית כט:לב', 'ותקרא שמו ראובן כי ראה יהוה'),
  name: 'ראובן',
  kind: 'person',
  name_first: 2,
  name_last: 2,
  echo_word: 'ראה',
  echo_disp: 4,
  words: 1,
  score: 0.4,
  chance: 0.2,
  rank_p: 0.13,
  p: 0.2,
  q: 0.5,
  known: true,
  ...over,
})
const DATA: EtiologiesResponse = {
  namings: [
    naming({}),
    naming({
      naming: 1,
      verse: verse(810, 'Genesis 30:8', 'בראשית ל:ח', 'נפתולי אלהים נפתלתי ותקרא שמו נפתלי'),
      name: 'נפתלי',
      name_first: 5,
      name_last: 5,
      echo_word: 'נפתולי',
      echo_disp: 0,
      score: 1,
      p: 0.0002,
      q: 0.01,
      known: false,
    }),
    naming({ naming: 2, name: 'חוה', echo_word: null, echo_disp: null, score: 0, p: 1, q: 1, known: false, kind: 'place' }),
  ],
  places: 1,
  explained: 2,
  mean_own: 0.51,
  mean_null: 0.26,
  p: 0.0001,
  shuffles: 9999,
  alpha: 0.05,
  holds: true,
  leads: 1,
  known: [
    { ref: 'Genesis 29:32', name: 'ראובן', found: true, naming: 0, score: 0.4, rank_p: 0.13, echoes: false },
    { ref: 'Genesis 35:7', name: 'בית אל', found: false, naming: null, score: null, rank_p: null, echoes: false },
  ],
  known_found: 1,
  known_echo: 0,
  known_rank: 0.1,
  known_share: 0.75,
  known_holds: false,
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      missing
        ? new Response(JSON.stringify({ detail: 'the naming etiologies were not computed' }), { status: 404 })
        : new Response(JSON.stringify(DATA), { status: 200 }),
    ),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/etiologies" element={<EtiologiesPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

const plain = (s: string | null | undefined) => (s ?? '').replace(/[⁨⁩]/g, '')

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('EtiologiesPage', () => {
  it('states both checks with their verdicts', async () => {
    renderAt('/etiologies')
    const echo = (await screen.findByRole('heading', { name: /A name echoes its own explanation/ })).closest('article')!
    expect(within(echo).getByText('Borne out')).toBeTruthy()
    expect(echo.textContent).toContain('On average 51% of a name’s consonants stand in order in one word of its own verse, against 26%')
    const known = screen.getByRole('heading', { name: /everyone agrees on/ }).closest('article')!
    expect(within(known).getByText('Not borne out')).toBeTruthy()
    expect(plain(known.textContent)).toContain('The formula finds 1 of the 2 named in advance')
    expect(known.textContent).toContain('Not found: Genesis 35:7.')
  })

  it('lists every naming with its name and echo marked in the verse', async () => {
    const { container } = renderAt('/etiologies')
    await screen.findAllByText('נפתולי')
    const items = [...container.querySelectorAll('li.ety-naming')]
    expect(items).toHaveLength(3)
    const reuben = items[0]
    expect(reuben.querySelector('.w-focus')?.textContent).toBe('ראובן')
    expect(reuben.querySelector('.w-shared')?.textContent).toBe('ראה')
    expect(reuben.textContent).toContain('40% of its letters')
    expect(reuben.textContent).toContain('named in advance')
    const ref = reuben.querySelector('a.verse-ref')!
    expect(ref.textContent).toContain('29:32')
    expect(ref.getAttribute('href')).toBe('/unit/v%3A800')
    // a naming beyond chance carries the lead bar; one without an echo says so
    expect(items[1].className).toContain('ety-lead')
    expect(items[2].textContent).toContain('no word of the verse echoes it')
    expect(items[2].textContent).toContain('place')
  })

  it('filters and orders the namings', async () => {
    const { container } = renderAt('/etiologies')
    fireEvent.click(await screen.findByRole('radio', { name: 'Beyond chance (1)' }))
    expect(screen.getByTestId('loc').textContent).toBe('/etiologies?show=leads')
    expect([...container.querySelectorAll('li.ety-naming b.he')].map((b) => b.textContent)).toEqual(['נפתלי', 'נפתולי'])
    fireEvent.click(screen.getByRole('radio', { name: 'Named in advance (1)' }))
    expect(container.querySelectorAll('li.ety-naming')).toHaveLength(1)
    fireEvent.click(screen.getByRole('radio', { name: 'All (3)' }))
    fireEvent.click(screen.getByRole('radio', { name: 'Strongest first' }))
    expect(screen.getByTestId('loc').textContent).toBe('/etiologies?order=strongest')
    expect([...container.querySelectorAll('li.ety-naming > .hit-head > b.he:first-of-type')].map((b) => b.textContent)).toEqual(['נפתלי', 'ראובן', 'חוה'])
  })

  it('says when the stage did not run', async () => {
    renderAt('/etiologies', 'en', true)
    expect(await screen.findByText(/The naming etiologies were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/etiologies', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('מדרשי שמות')
    expect(await screen.findByText('מתאשר')).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'מעבר למקרה (1)' })).toBeTruthy()
  })
})
