// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { FormsListsResponse, FormsResponse, FormsSayingsResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { FormsPage } from './FormsPage'

const verse = (id: number, ref: string, refHe: string, tokens: string[]): Verse => ({
  verse_id: id,
  book_id: 27,
  chapter: 6,
  verse: 16,
  ref,
  ref_he: refHe,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const label = (id: number, en: string, he: string) => ({ verse_id: id, label_en: en, label_he: he })
const DATA: FormsResponse = {
  meta: {
    window: 8,
    alpha: 0.05,
    shuffles: 999,
    numbers: 7026,
    free: 2931,
    sayings: 91,
    graded_pairs: 105,
    steps: { '1 / 2': 57, '3 / 4': 14 },
    chance: { pairs: 1286, observed: 105, expected: 96.2, p: 0.196, without: ['1 / 2'], without_observed: 48, without_expected: 37.0, without_p: 0.037 },
    parallel: { sayings: 91, others: 511, saying_prob: 0.19, other_prob: 0.15, saying_parallel: 0.12, other_parallel: 0.05, p: 0.026 },
    known_found: 18,
    known_share: 0.67,
    lists: {
      threshold: 0.73,
      like_verses: 1300,
      observed: 69,
      expected: 0.7,
      verses: 900,
      kinds: { names: 36, other: 23, genealogy: 5 },
      known_found: 8,
      known_share: 0.67,
      shuffles: 20,
      min_verses: 5,
      quantile: 0.99,
    },
  },
  known: [
    { name: 'שש … ושבע (Prov 6:16)', first: label(1, 'Proverbs 6:16', 'משלי ו:טז'), n_verses: 1, hits: 1, found: true },
    { name: 'שלשה … ארבעה (Amos 1–2)', first: label(2, 'Amos 1:3', 'עמוס א:ג'), n_verses: 8, hits: 8, found: true },
    { name: 'אחד … ושנים (Deut 32:30)', first: label(3, 'Deuteronomy 32:30', 'דברים לב:ל'), n_verses: 1, hits: 0, found: false },
  ],
  known_lists: [
    { name: 'Adam to Noah', first: label(4, 'Genesis 5:6', 'בראשית ה:ו'), last_verse: label(5, 'Genesis 5:31', 'בראשית ה:לא'), n_verses: 26, covered: 25, found: true },
    { name: "the chieftains' offerings", first: label(6, 'Numbers 7:12', 'במדבר ז:יב'), last_verse: label(7, 'Numbers 7:83', 'במדבר ז:פג'), n_verses: 72, covered: 0, found: false },
  ],
  books: [{ book_id: 27, numbers: 40, free: 30, sayings: 6, lists: 0, list_verses: 0 }],
}
const SAYINGS: FormsSayingsResponse = {
  book: null,
  unit: null,
  known: false,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      unit_id: 'c:27:6',
      n_pairs: 1,
      steps: '6 / 7',
      prob: 0.81,
      known: 'שש … ושבע (Prov 6:16)',
      pairs: [{ a_tok: 0, b_tok: 4, a_value: 6, b_value: 7 }],
      verse: verse(1, 'Proverbs 6:16', 'משלי ו:טז', ['שֶׁשׁ־הֵנָּה', 'שָׂנֵא', 'יְהוָה', 'וְשֶׁבַע', 'תּוֹעֲבוֹת']),
    },
  ],
}
const LISTS: FormsListsResponse = {
  book: null,
  unit: null,
  kind: null,
  total: 1,
  offset: 0,
  limit: 20,
  items: [
    {
      list_id: 1,
      book_id: 0,
      unit_id: 'c:0:5',
      first: label(4, 'Genesis 5:4', 'בראשית ה:ד'),
      last_verse: label(5, 'Genesis 5:30', 'בראשית ה:ל'),
      n_verses: 27,
      n_like: 24,
      likeness: 0.86,
      kind: 'genealogy',
      known: 'Adam to Noah',
      verses: [verse(4, 'Genesis 5:4', 'בראשית ה:ד', ['וַיִּהְיוּ']), verse(8, 'Genesis 5:5', 'בראשית ה:ה', ['וַיִּהְיוּ'])],
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: FormsResponse = DATA) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/books'
          ? []
          : p === '/api/forms'
            ? data
            : p === '/api/forms/sayings'
              ? SAYINGS
              : p === '/api/forms/lists'
                ? LISTS
                : p.startsWith('/api/unit/')
                  ? { unit: { unit_id: 'c:0:5', unit_type: 'chapter', label_en: 'Genesis 5', label_he: 'בראשית ה', book_id: 0, start_verse_id: 0, end_verse_id: 31, n_verses: 32, marker: null }, verses: [], parents: [], prev_id: null, next_id: null }
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
            <Route path="/forms" element={<FormsPage />} />
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

describe('FormsPage', () => {
  it('states the three checks on the sayings with their verdicts', async () => {
    const { container } = renderAt('/forms')
    expect(await screen.findByText(/7,026 number words; 2,931 stand alone/)).toBeTruthy()
    expect(screen.getByText(/found: 18 of 3\. A known answer/)).toBeTruthy()
    expect(screen.getByText(/105 against 96\.2 .* p 0\.20\)/)).toBeTruthy()
    expect(screen.getByText(/without 1 \/ 2, 48 graded pairs against 37\.0 \(p 0\.04\)/)).toBeTruthy()
    expect(screen.getByText(/12% of 91 against 5% of 511 .* p 0\.03\)/)).toBeTruthy()
    expect([...container.querySelectorAll('.dlg-verdict')].map((v) => v.textContent)).toEqual(['holds', 'does not hold', 'holds'])
    expect(screen.getByText('Steps: 1 / 2: 57 · 3 / 4: 14')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Deuteronomy 32:30' }).getAttribute('href')).toBe('/unit/v%3A3')
    expect(screen.getByText('8 of 8 verses')).toBeTruthy()
    expect(screen.getByText('not found')).toBeTruthy()
  })

  it('lists the sayings with both numbers marked', async () => {
    const { container } = renderAt('/forms')
    await screen.findByText('6 / 7')
    expect(container.querySelectorAll('.saying .hit-text .w-shared')).toHaveLength(2)
    expect(container.querySelector('.saying .hit-head .muted')?.textContent).toBe('parallel halves 0.81 · named in advance: שש … ושבע (Prov 6:16)')
    fireEvent.click(screen.getByLabelText('Named in advance only'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/forms?known=1'))
  })

  it('shows the lists, their check and a list with its first verses', async () => {
    const { container, calls } = renderAt('/forms?view=lists&unit=c%3A0%3A5')
    expect(await screen.findByText(/69 lists of at least 5 verses, 900 verses in all, against 0\.7/)).toBeTruthy()
    expect(screen.getByText(/8 of 2; 69 lists against 0\.7/)).toBeTruthy()
    expect(container.querySelector('.dlg-verdict')?.textContent).toBe('holds')
    expect(screen.getByText('0 of 72')).toBeTruthy()
    expect(screen.getByText('genealogy 5 · names 36 · other 23')).toBeTruthy()
    await screen.findByText('genealogy')
    expect(container.querySelectorAll('.list .hit-text')).toHaveLength(2)
    expect(screen.getByText('+ 25 more verses')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Read the chapter' }).getAttribute('href')).toBe('/unit/c%3A0%3A5')
    expect(calls.some((c) => c.startsWith('/api/forms/lists?') && c.includes('unit=c%3A0%3A5'))).toBe(true)
    fireEvent.change(screen.getByLabelText('Kind'), { target: { value: 'names' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/forms?view=lists&unit=c%3A0%3A5&kind=names'))
    fireEvent.click(screen.getByRole('radio', { name: 'Numerical sayings' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/forms'))
  })

  it('reads in Hebrew', async () => {
    renderAt('/forms?view=lists', 'he')
    expect(await screen.findByRole('heading', { name: 'מספרים ורשימות', level: 1 })).toBeTruthy()
    expect(await screen.findByText('יחס')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'בראשית ה:ו – בראשית ה:לא' })).toBeTruthy()
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/forms', 'en', { meta: { lists: {} }, known: [], known_lists: [], books: [] })
    expect(await screen.findByText(/run `bsim forms`/)).toBeTruthy()
  })
})
