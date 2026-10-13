// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PsalmsListResponse, PsalmsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { PsalmsPage } from './PsalmsPage'

const FEATS = ['first_singular', 'first_plural', 'second', 'imperative', 'imperative_plural', 'question', 'distress', 'praise']
const profile = (x: number) => Object.fromEntries(FEATS.map((f) => [f, x]))
const DATA: PsalmsResponse = {
  meta: {
    psalms: 150,
    labelled: 119,
    genres: { hymn: 31, lament_individual: 37 },
    features: FEATS,
    k: 2,
    alpha: 0.05,
    title_words: 320,
    genre_test: { nmi: 0.262, null: 0.082, p: 0.001 },
    crosstab: [
      { genre: 'hymn', cluster: 2, n: 24 },
      { genre: 'lament_individual', cluster: 1, n: 26 },
      { genre: 'lament_individual', cluster: 2, n: 2 },
    ],
    checks: [
      { genre: 'lament_individual', feature: 'first_singular', direction: 'higher', mean: 0.241, rest: 0.075, p: 0.001, q: 0.0012 },
      { genre: 'hymn', feature: 'first_singular', direction: 'lower', mean: 0.013, rest: 0.143, p: 0.2, q: 0.2 },
    ],
    checks_held: 1,
    cluster_profiles: { '1': profile(0.2), '2': profile(0.05) },
    known_turns: { found: 7, n: 12, expected: 3.36, p: 0.016 },
    laments_vs_hymns: { laments: 7, n_laments: 37, hymns: 2, n_hymns: 30, p: 0.135 },
    tolerance: 1,
    min_side: 2,
    robustness: {
      titles_kept: { nmi: 0.282, known: 8, laments_vs_hymns_p: 0.25 },
      form_only: { nmi: 0.294, null: 0.083, p: 0.001 },
      domains_only: { nmi: 0.142, null: 0.081, p: 0.001 },
      tolerance: { '0': { found: 4, expected: 1.0, p: 0.011 }, '1': { found: 7, expected: 3.36, p: 0.016 }, '2': { found: 7, expected: 5.58, p: 0.24 } },
    },
  },
  known: [
    { verse_id: 100, label: 'Psalms 13:6', label_he: 'תהלים יג:ו', turn_vid: 99, turn_label: 'Psalms 13:5', turn_label_he: 'תהלים יג:ה', p: 0.49, found: true, chance: 0.5 },
    { verse_id: 200, label: 'Psalms 140:13', label_he: 'תהלים קמ:יג', turn_vid: null, turn_label: null, turn_label_he: null, p: null, found: null, chance: null },
  ],
}
const LIST: PsalmsListResponse = {
  genre: null,
  cluster: null,
  turned: false,
  unit: null,
  sort: 'chapter',
  total: 2,
  offset: 0,
  limit: 20,
  items: [
    {
      unit_id: 'c:26:13',
      label: 'Psalms 13',
      label_he: 'תהלים יג',
      chapter: 13,
      genre: 'lament_individual',
      cluster: 1,
      words: 50,
      features: profile(0.1),
      turn: { verse_id: 99, verse: 5, label: 'Psalms 13:5', label_he: 'תהלים יג:ה', stat: 0.3, p: 0.02, before: -0.1, after: 0.2 },
      mood: [1, 2, 3, 4, 5, 6].map((v) => ({ verse: v, words: 8, distress: v < 5 ? 1 : 0, praise: v < 5 ? 0 : 2 })),
    },
    { unit_id: 'c:26:14', label: 'Psalms 14', label_he: 'תהלים יד', chapter: 14, genre: null, cluster: 2, words: 40, features: profile(0.05), turn: null, mood: [] },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: PsalmsResponse = DATA) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/psalms'
          ? data
          : p === '/api/psalms/list'
            ? LIST
            : p.startsWith('/api/unit/')
              ? { unit: { unit_id: 'c:26:13', unit_type: 'chapter', label_en: 'Psalms 13', label_he: 'תהלים יג', book_id: 26, start_verse_id: 95, end_verse_id: 100, n_verses: 6, marker: null }, verses: [], parents: [], prev_id: null, next_id: null }
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
            <Route path="/psalms" element={<PsalmsPage />} />
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

describe('PsalmsPage', () => {
  it('states the genre test, its checks and the turns', async () => {
    const { container } = renderAt('/psalms')
    expect(await screen.findByText(/normalized mutual information 0\.262, against 0\.082 .* \(p 0\.001\)/)).toBeTruthy()
    expect(screen.getByText(/The form alone .* gives 0\.294/)).toBeTruthy()
    // genres by cluster: a row per genre, a column per cluster
    const cross = container.querySelector('.psalm-crosstab')!
    expect([...cross.querySelectorAll('tbody tr')].map((r) => r.textContent)).toEqual(['Hymn024', 'Individual lament262'])
    expect(screen.getByText('1 of 2 hold: each genre’s mean against the other labelled psalms, with the genres shuffled (one-sided, Benjamini–Hochberg q).'.replace('’', "'"))).toBeTruthy()
    expect(container.querySelectorAll('td.on')).toHaveLength(1)
    expect(screen.getByText(/7 of 12 found within 1 verse, against 3\.4 for a split drawn at random \(p 0\.02\)/)).toBeTruthy()
    expect(screen.getByText(/the result rests on the tolerance/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Psalms 13:6' }).getAttribute('href')).toBe('/read/v%3A100?layers=mood')
    expect(screen.getByText('too short')).toBeTruthy()
    expect(screen.getByText(/7 of 37 individual laments have a turn above chance, against 2 of 30 hymns \(Fisher, p 0\.14\)/)).toBeTruthy()
  })

  it('lists each psalm with its form, turn and mood', async () => {
    const { container } = renderAt('/psalms')
    expect(await screen.findByRole('link', { name: 'Psalms 13' })).toBeTruthy()
    expect(screen.getByText('turns at Psalms 13:5 (p 0.02; mood -0.10 → 0.20 per word)')).toBeTruthy()
    expect(screen.getByText('too short to turn')).toBeTruthy()
    expect(screen.getByText('mixed or disputed')).toBeTruthy()
    const strip = screen.getByRole('img', { name: 'Mood of Psalms 13, verse by verse' })
    expect(strip.querySelectorAll('.mood-praise')).toHaveLength(6)
    expect(strip.querySelector('.mood-turn')).not.toBeNull()
    expect(strip.querySelector('title')?.textContent).toBe('verse 1: 0 praise, 1 distress')
    expect(container.querySelectorAll('.mood-strip')).toHaveLength(1)
    expect(screen.getAllByRole('link', { name: 'Read with its mood' })[0].getAttribute('href')).toBe('/read/c%3A26%3A13?layers=mood')
  })

  it('filters through the URL and from the dossier', async () => {
    const { calls } = renderAt('/psalms?unit=c%3A26%3A13')
    await screen.findByRole('link', { name: 'Psalms 13' })
    expect(calls.some((c) => c.startsWith('/api/psalms/list?') && c.includes('unit=c%3A26%3A13'))).toBe(true)
    fireEvent.change(screen.getByLabelText('Genre'), { target: { value: 'hymn' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/psalms?unit=c%3A26%3A13&genre=hymn'))
    fireEvent.click(screen.getByLabelText('Turn above chance only'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/psalms?unit=c%3A26%3A13&genre=hymn&turned=1'))
    fireEvent.change(screen.getByLabelText('Order'), { target: { value: 'turn' } })
    await waitFor(() => expect(calls.some((c) => c.includes('sort=turn') && c.includes('turned=1'))).toBe(true))
  })

  it('reads in Hebrew', async () => {
    renderAt('/psalms', 'he')
    expect(await screen.findByRole('heading', { name: 'תהלים', level: 1 })).toBeTruthy()
    expect(await screen.findByRole('link', { name: 'תהלים יג' })).toBeTruthy()
    expect(screen.getAllByText('קינת יחיד').length).toBeGreaterThan(0)
  })

  it('says how to compute it when the stage did not run', async () => {
    renderAt('/psalms', 'en', { meta: {}, known: [] })
    expect(await screen.findByText(/run `bsim psalms`/)).toBeTruthy()
  })
})
