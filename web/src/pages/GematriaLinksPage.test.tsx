// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { GematriaLinksResponse, GematriaPairsResponse, LinkTest } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { GematriaLinksPage } from './GematriaLinksPage'

const test_ = (observed: number, null_mean: number, p: number): LinkTest => ({ n: 100, observed, null_mean, null_q05: null_mean - 0.01, null_q95: null_mean + 0.01, p, unmatched: 0 })
const label = (verse_id: number, en: string, he: string) => ({ verse_id, label_en: en, label_he: he })
const LINKS: GematriaLinksResponse = {
  meta: { system: 'standard', draws: 999, alpha: 0.05, lemmas: 3373, pairs: 14751, same_letters: 3423, tested: 11328, root_pairs: 2183 },
  equal: { domains: test_(0.0085, 0.0097, 0.957), root: test_(0.0001, 0.0004, 0.991), vector: test_(0.6018, 0.6006, 0.058) },
  root_family: { domains: test_(0.2566, 0.0132, 0.001), vector: test_(0.673, 0.5959, 0.001) },
  equivalences: [
    {
      a_text: 'נחש',
      b_text: 'משיח',
      found: true,
      a: { lemma: '5175', he: 'נָחָשׁ', n_words: 31 },
      b: { lemma: '4899', he: 'מָשִׁיחַ', n_words: 39 },
      value: 358,
      equal: true,
      domains: 0,
      root: 0,
      vector: 0.6663,
      domains_rank: 0,
      root_rank: 0,
      vector_rank: 0.7422,
    },
    { a_text: 'שלום', b_text: 'אין', found: false, a: null, b: null, value: null, equal: null, domains: null, root: null, vector: null, domains_rank: null, root_rank: null, vector_rank: null },
  ],
  verse: {
    verse: label(0, 'Genesis 1:1', 'בראשית א:א'),
    value: 2701,
    words: 7,
    letters: 28,
    largest_prime: 73,
    n_verses: 23206,
    all: 1,
    expected_all: 0.0052,
    unique_here: false,
    unique_share: 0.6289,
    twins: [label(15800, 'Psalms 44:5', 'תהלים מד:ה'), label(17850, 'Proverbs 7:7', 'משלי ז:ז')],
    properties: [
      { key: 'words7', kind: 'words', n: 7, holds_here: true, verses: 1875 },
      { key: 'multiple37', kind: 'multiple', n: 37, holds_here: true, verses: 675 },
      { key: 'triangular', kind: 'triangular', n: null, holds_here: true, verses: 305 },
    ],
  },
}
const PAIRS: GematriaPairsResponse = {
  value: null,
  sort: 'vector',
  same_letters: false,
  total: 1,
  offset: 0,
  limit: 25,
  items: [{ a: { lemma: '3257', he: 'יָעֶה', n_words: 9 }, b: { lemma: '4207b', he: 'מַזְלֵג', n_words: 7 }, value: 80, same_letters: false, domains: 1, root: false, vector: 0.8976 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', links: GematriaLinksResponse = LINKS) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/gematria-links' ? links : p === '/api/gematria-links/pairs' ? PAIRS : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/gematria-links" element={<GematriaLinksPage />} />
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

describe('GematriaLinksPage', () => {
  it('sets equal-value pairs against matched pairs, with the check of the measures', async () => {
    const { container } = renderAt('/gematria-links')
    expect(await screen.findByText(/3,373 words .* make 14,751 pairs of equal standard value; 3,423 of them are spelled with the same letters/)).toBeTruthy()
    const tables = container.querySelectorAll('.gl-tests')
    expect(tables).toHaveLength(2)
    const rows = tables[0].querySelectorAll('tbody tr')
    expect([...rows].map((r) => r.querySelector('td')?.textContent)).toEqual(['Same semantic domains', 'Same root family', 'Used alike (BEREL)'])
    expect(rows[1].textContent).toContain('0.01%')
    expect(rows[2].textContent).toContain('0.602')
    expect(rows[2].textContent).toContain('0.058')
    const verdicts = [...container.querySelectorAll('.dlg-verdict')].map((x) => x.textContent)
    expect(verdicts.slice(0, 2)).toEqual(['does not hold', 'holds'])
  })

  it('ranks the tradition’s equivalences and counts Genesis 1:1’s numbers', async () => {
    const { container } = renderAt('/gematria-links')
    await screen.findByRole('heading', { name: 'The tradition’s equivalences' })
    const rows = container.querySelectorAll('.gl-eq tbody tr')
    expect(rows[0].textContent).toContain('358')
    expect(rows[0].textContent).toContain('closer than 74%')
    expect(rows[0].querySelector('a')?.getAttribute('href')).toBe('/lemma/5175')
    expect(rows[1].textContent).toContain('not among the words tested')
    expect(container.querySelectorAll('.gl-props tbody tr')).toHaveLength(3)
    expect(screen.getByText(/Only Genesis 1:1 has all of them; 0.005 would/)).toBeTruthy()
    expect(screen.getByText(/it shares its description with 2 other verses, while 63% of all verses/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Psalms 44:5' }).getAttribute('href')).toBe('/unit/v%3A15800')
  })

  it('lists the pairs, sorted and filtered', async () => {
    const { container, calls } = renderAt('/gematria-links')
    await waitFor(() => expect(container.querySelectorAll('.gl-pairs li')).toHaveLength(1))
    expect(container.querySelector('.gl-pairs li')?.textContent).toContain('used alike 0.90 · domains 100%')
    fireEvent.click(screen.getByRole('radio', { name: 'By value' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/gematria-links?sort=value'))
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Value' }), { target: { value: '80' } })
    await waitFor(() => expect(calls.some((c) => c.includes('value=80') && c.includes('sort=value'))).toBe(true))
    fireEvent.click(screen.getByRole('checkbox', { name: 'With pairs spelled alike' }))
    await waitFor(() => expect(calls.some((c) => c.includes('same_letters=true'))).toBe(true))
  })

  it('reads in Hebrew', async () => {
    renderAt('/gematria-links', 'he')
    expect(await screen.findByRole('heading', { name: 'שווים במספר, קרובים במשמעות?' })).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'המספרים של בראשית א:א' })).toBeTruthy()
    expect(screen.getByText(/הוא חולק את תיאורו עם שני פסוקים נוספים/)).toBeTruthy()
  })

  it('says when the build has no test', async () => {
    renderAt('/gematria-links', 'en', { meta: {}, equal: {}, root_family: {}, equivalences: [], verse: null })
    expect(await screen.findByText(/Not computed in this build: run `bsim gematria-links`/)).toBeTruthy()
  })
})
