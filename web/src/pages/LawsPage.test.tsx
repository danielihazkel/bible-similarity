// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Law, LawList, LawPairs, LawsResponse, LawSynopsis } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { LawsPage } from './LawsPage'

const DATA: LawsResponse = {
  laws: 257,
  pairs: 344,
  linked: 1556,
  top_k: 20,
  min_links: 2,
  forms: { casuistic: 107, apodictic: 109, other: 41 },
  known: [
    { group: 'slave release', members: [{ a: 'Exodus 21:2-11', b: 'Deuteronomy 15:12-18', found: true, strict: true, pairs: [7] }], found: 1, of: 1 },
    { group: "the kid in its mother's milk", members: [{ a: 'Exodus 23:19', b: 'Deuteronomy 14:21', found: false, strict: false, pairs: [] }], found: 0, of: 1 },
  ],
  known_found: 1,
  known_total: 2,
  known_holds: true,
  known_strict: 1,
  kept_mean: 0.11,
  codes: [{ code: 'covenant', laws: 32, verses: 102, casuistic: 21, apodictic: 11, other: 0, v2ms: 8, v2mp: 0, v3: 22, mixed: 2 }],
}
const law = (id: number, code: Law['code'], first: string): Law => ({
  law_id: id,
  code,
  unit_id: `s:${id}`,
  book_id: 1,
  first_vid: id,
  last_vid: id + 4,
  first_label: first,
  last_label: first.replace(/:\d+$/, ':6'),
  first_label_he: 'שמות כא:ב',
  last_label_he: 'שמות כא:ו',
  n_verses: 5,
  form: 'casuistic',
  casuistic: true,
  apodictic: false,
  address: '3',
  pairs: 2,
})
const PAIR = {
  pair_id: 7,
  a: law(10, 'covenant', 'Exodus 21:2'),
  b: law(20, 'deuteronomic', 'Deuteronomy 15:12'),
  links: 15,
  score: 0.0474,
  a_first: 10,
  a_last: 11,
  b_first: 20,
  b_last: 22,
  a_span: 'Exodus 21:2 – Exodus 21:3',
  b_span: 'Deuteronomy 15:12 – Deuteronomy 15:14',
  a_span_he: 'שמות כא:ב – שמות כא:ג',
  b_span_he: 'דברים טו:יב – דברים טו:יד',
  ops: { same: 5, spelling: 0, form: 2, substitution: 3, omitted: 1, added: 4, moved: 0 },
  kept: 0.146,
  known: 'slave release',
}
const PAIRS: LawPairs = { total: 1, offset: 0, limit: 25, order: 'score', code: null, items: [PAIR] }
const LIST: LawList = { total: 1, offset: 0, limit: 25, code: null, form: null, items: [law(10, 'covenant', 'Exodus 21:2')] }
const verse = (id: number, ref: string, text: string) => ({
  verse_id: id,
  book_id: 1,
  chapter: 21,
  verse: 2,
  ref,
  ref_he: 'שמות כא:ב',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const SYN: LawSynopsis = {
  pair: PAIR,
  a: [{ verse: verse(10, 'Exodus 21:2', 'כִּי תִקְנֶה עֶבֶד עִבְרִי'), marks: { '1': 'substitution' } }],
  b: [{ verse: verse(20, 'Deuteronomy 15:12', 'כִּי יִמָּכֵר לְךָ אָחִיךָ'), marks: { '1': 'substitution', '2': 'added' } }],
}

const calls: string[] = []
function mockApi() {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      calls.push(u.pathname + u.search)
      const body =
        u.pathname === '/api/laws'
          ? DATA
          : u.pathname === '/api/laws/pairs'
            ? PAIRS
            : u.pathname === '/api/laws/list'
              ? LIST
              : u.pathname === '/api/laws/pair/7'
                ? SYN
                : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
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
            <Route path="/laws" element={<LawsPage />} />
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

describe('LawsPage (DESIGN.md §16.93, D155)', () => {
  it('profiles the codes, lists the known pairs and the matched pairs', async () => {
    mockApi()
    renderAt('/laws')
    expect(await screen.findByText('257 laws in five codes; 344 matched pairs across them.')).toBeTruthy()
    expect(screen.getByRole('rowheader', { name: 'Covenant Code' })).toBeTruthy()
    expect(screen.getByRole('cell', { name: '21 (66%)' })).toBeTruthy()
    expect(screen.getByRole('cell', { name: 'third person' })).toBeTruthy()
    expect(screen.getByText('1 of 2 pairs of passages found.')).toBeTruthy()
    expect(screen.getByText('By the aligned verses themselves, not their whole paragraphs: 1 of 2.')).toBeTruthy()
    expect(screen.getByText('Exodus 23:19 and Deuteronomy 14:21: not found')).toBeTruthy()
    expect(screen.getByText('The kid in its mother’s milk')).toBeTruthy()
    expect(await screen.findByText('Covenant Code, Exodus 21:2 – Exodus 21:6')).toBeTruthy()
    expect(screen.getByText(/15 links · 15% of the words aligned keep their lemma · named in advance: The release of a slave/)).toBeTruthy()
  })

  it('opens a pair side by side through the address, its changes marked', async () => {
    mockApi()
    const { container } = renderAt('/laws')
    fireEvent.click((await screen.findAllByRole('button', { name: 'side by side' }))[0])
    expect(screen.getByTestId('loc').textContent).toBe('/laws?pair=7')
    expect(await screen.findByRole('heading', { name: 'Covenant Code beside Deuteronomic Code' })).toBeTruthy()
    expect(screen.getByRole('group', { name: 'Deuteronomic Code, Deuteronomy 15:12 – Deuteronomy 15:14' })).toBeTruthy()
    expect(container.querySelectorAll('.lw-side .w-diff-substitution')).toHaveLength(2)
    expect(container.querySelectorAll('.lw-side .w-diff-added')).toHaveLength(1)
    expect(screen.getByText('and 1 more verse')).toBeTruthy() // each side cut short: a 2 verses, b 3, one shown
    expect(screen.getByText('and 2 more verses')).toBeTruthy()
  })

  it('switches to the laws and filters them by code and form through the address', async () => {
    mockApi()
    renderAt('/laws?view=laws')
    fireEvent.change(await screen.findByRole('combobox', { name: 'Code' }), { target: { value: 'holiness' } })
    fireEvent.click(screen.getByRole('radio', { name: 'Apodictic' }))
    expect(screen.getByTestId('loc').textContent).toBe('/laws?view=laws&code=holiness&form=apodictic')
    await vi.waitFor(() => expect(calls).toContain('/api/laws/list?code=holiness&form=apodictic&limit=25&offset=0'))
  })

  it('runs in the Hebrew interface', async () => {
    mockApi()
    renderAt('/laws', 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'קובצי החוקים זה בצד זה' })).toBeTruthy()
    expect(await screen.findByText('שחרור העבד')).toBeTruthy()
  })
})
