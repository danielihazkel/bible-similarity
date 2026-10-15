// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CipherHitsResponse, CiphersResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { CiphersPage } from './CiphersPage'

const label = (id: number, en: string, he: string) => ({ verse_id: id, label_en: en, label_he: he })
const DATA: CiphersResponse = {
  meta: {
    min_letters: 3,
    rare_form: 2,
    shuffles: 999,
    alpha: 0.05,
    names: 2120,
    spans: 268699,
    single_spans: 30000,
    n_chapters: 929,
    random_hits: 104.6,
    known_found: 3,
    tests: {
      jeremiah: { observed: 3, expected: 0.64, p: 0.036 },
      elsewhere: { observed: 78, expected: 104.0, p: 0.761 },
      albam: { observed: 94, expected: 104.6, p: 0.528 },
    },
  },
  known: [
    { verse: label(12068, 'Jeremiah 25:26', 'ירמיהו כה:כו'), cipher: 'atbash', text: 'ששך', name: 'בבל', found: true },
    { verse: label(12721, 'Jeremiah 51:1', 'ירמיהו נא:א'), cipher: 'atbash', text: 'לב קמי', name: 'כשדים', found: true },
    { verse: label(12761, 'Jeremiah 51:41', 'ירמיהו נא:מא'), cipher: 'atbash', text: 'ששך', name: 'בבל', found: true },
  ],
  chapters: [
    { cipher: 'albam', unit_id: 'c:28:37', label_en: 'Job 37', label_he: 'איוב לז', hits: 2, expected: 0.12, p: 0.009, q: 1 },
    { cipher: 'atbash', unit_id: 'c:12:51', label_en: 'Jeremiah 51', label_he: 'ירמיהו נא', hits: 2, expected: 0.39, p: 0.066, q: 1 },
  ],
}
const verse: Verse = {
  verse_id: 12721,
  book_id: 12,
  chapter: 51,
  verse: 1,
  ref: 'Jeremiah 51:1',
  ref_he: 'ירמיהו נא:א',
  text_display: 'יֹשְׁבֵי לֵב קָמָי',
  display_tokens: ['יֹשְׁבֵי', 'לֵב', 'קָמָי'],
  ketiv_note: null,
}
const HITS: CipherHitsResponse = {
  cipher: null,
  book: null,
  unit: null,
  known: false,
  total: 1,
  offset: 0,
  limit: 25,
  items: [{ hit_id: 1, cipher: 'atbash', unit_id: 'c:12:51', verse, first_tok: 1, last_tok: 2, span: 'לב קמי', reads: 'כשדים', name_lemma: '3778', known: 'Jeremiah 51:1' }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: CiphersResponse = DATA) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? [] : p === '/api/ciphers' ? data : p === '/api/ciphers/hits' ? HITS : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/ciphers" element={<CiphersPage />} />
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

describe('CiphersPage', () => {
  it('states the checks with their verdicts and the places named in advance', async () => {
    const { container } = renderAt('/ciphers')
    expect(await screen.findByText(/2,120 names; 268,699 places a cipher could hide/)).toBeTruthy()
    expect(screen.getByText(/The places named in advance are found: 3 of 3\./)).toBeTruthy()
    expect(screen.getByText(/In Jeremiah 25 and Jeremiah 51, atbash reads 3 names against 0\.64 for a random swap \(p 0\.04\)/)).toBeTruthy()
    expect(screen.getByText(/In the rest of the Bible, atbash reads 78 names against 104\.0/)).toBeTruthy()
    expect([...container.querySelectorAll('.dlg-verdict')].map((v) => v.textContent)).toEqual(['holds', 'holds', 'does not hold', 'does not hold'])
    expect(screen.getAllByRole('link', { name: 'Jeremiah 51:1' })[0].getAttribute('href')).toBe('/unit/v%3A12721')
  })

  it('lists the names read through a swap, with the words that hide them marked', async () => {
    const { container, calls } = renderAt('/ciphers')
    await waitFor(() => expect(container.querySelector('.cipher-hit')).not.toBeNull())
    expect(container.querySelectorAll('.cipher-hit .w-shared')).toHaveLength(2)
    expect(container.querySelector('.cipher-hit')?.textContent).toContain('named in advance')
    fireEvent.click(screen.getByRole('radio', { name: 'Albam' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/ciphers?cipher=albam'))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Only those named in advance' }))
    await waitFor(() => expect(calls.some((c) => c.includes('cipher=albam') && c.includes('known=true'))).toBe(true))
  })

  it('ranks the chapters against random swaps and filters by one', async () => {
    renderAt('/ciphers')
    const job = await screen.findByRole('link', { name: /Job 37/ })
    expect(job.getAttribute('href')).toBe('/ciphers?unit=c%3A28%3A37&cipher=albam')
    expect(screen.getByText(/q corrects for the 929 chapters/)).toBeTruthy()
  })

  it('says when the build has no ciphers', async () => {
    renderAt('/ciphers', 'en', { meta: {}, known: [], chapters: [] })
    expect(await screen.findByText(/Not computed in this build: run `bsim ciphers`/)).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    renderAt('/ciphers', 'he')
    expect(await screen.findByRole('heading', { name: 'את״ב״ש ואל״ב״ם' })).toBeTruthy()
    expect(await screen.findByText(/בירמיהו כה וירמיהו נא, את״ב״ש קורא 3 שמות/)).toBeTruthy()
  })
})
