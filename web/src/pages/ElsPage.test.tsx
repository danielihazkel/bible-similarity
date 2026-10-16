// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ElsResponse, ElsScope } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { ElsPage } from './ElsPage'

const control = (p: number, values: number[]) => ({ n: values.length, mean: -0.011, q05: -0.049, q95: 0.026, p, values })
const scope = (key: string, letters: number, r: number, holds = true): ElsScope => ({
  key,
  label_en: key === 'torah' ? 'Genesis 1:1 – Deuteronomy 34:12' : 'Genesis 1:1 – 50:26',
  label_he: key === 'torah' ? 'בראשית א:א – דברים לד:יב' : 'בראשית א:א–נ:כו',
  letters,
  verses: 5846,
  hits: 1428731,
  expected: 1429940,
  r,
  holds,
  controls: { letters: control(0.62, [-0.05, 0.01, 0.02]), verses: control(holds ? 0.57 : 0.01, [-0.03, 0.0]), blocks: control(0.33, [-0.03, -0.05]) },
  blocks: [{ block: 1, label_en: 'Joshua 1:1 – Isaiah 3:1', label_he: 'יהושע א:א – ישעיהו ג:א', first_vid: 5846, r: -0.0303 }],
  terms: [
    { term: 'משה', length: 3, forward: 118445, backward: 117597, hits: 236042, expected: 235306.13, log_ratio: 0.00312, letters_mean: 235300, letters_q05: 234500, letters_q95: 236100, letters_p: 0.08, verses_mean: 235366.12, blocks_log_ratio: 0.00428 },
    { term: 'יחזקאל', length: 6, forward: 0, backward: 1, hits: 1, expected: 1.03, log_ratio: -0.0188, letters_mean: 1.1, letters_q05: 0, letters_q95: 3, letters_p: 0.64, verses_mean: 1.01, blocks_log_ratio: null },
  ],
})
const DATA: ElsResponse = {
  meta: { text: 'ketiv', min_skip: 2, max_skip: 1000, shuffles: 199, alpha: 0.05, smooth: 0.5, terms: 27, holds: true },
  scopes: [scope('torah', 304801, -0.0113), scope('genesis', 78063, -0.0094, false)],
  known: [{ verse: { verse_id: 0, label_en: 'Genesis 1:1', label_he: 'בראשית א:א' }, term: 'תורה', skip: 50, found: true, offset: 5, in_torah: 19, expected: 9.8 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: ElsResponse = DATA) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/els' ? data : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/els" element={<ElsPage />} />
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

describe('ElsPage', () => {
  it('counts the Torah’s hits against its controls', async () => {
    const { container } = renderAt('/els')
    expect(await screen.findByText(/27 names at skips of 2 to 1,000 letters, forwards and backwards: 1,428,731 hits in 304,801 letters, against 1,429,940 expected/)).toBeTruthy()
    expect(screen.getByText(/run at −0.011 on a log scale/)).toBeTruthy()
    const rows = container.querySelectorAll('.els-table')[0].querySelectorAll('tbody tr')
    expect([...rows].map((r) => r.querySelector('td')?.textContent)).toEqual(['The same letters, shuffled', 'The same verses, shuffled', 'Stretches of the other books, as long'])
    expect(rows[0].textContent).toContain('0.62')
    expect(container.querySelectorAll('.els-dot')).toHaveLength(7)
    expect(container.querySelector('.els-blocks a')?.textContent).toBe('Joshua 1:1 – Isaiah 3:1: R −0.030')
  })

  it('lists the names and the tradition’s sequences', async () => {
    const { container } = renderAt('/els')
    await screen.findByRole('heading', { name: 'Name by name' })
    const terms = container.querySelectorAll('.els-terms tbody tr')
    expect(terms[0].textContent).toContain('236,042')
    expect(terms[0].textContent).toContain('×1.00')
    expect(terms[1].textContent).toContain('–')
    const known = container.querySelector('#known tbody tr')!
    expect(known.textContent).toContain('from letter 6 of the verse')
    expect(known.textContent).toContain('19 times (10 expected by chance)')
    expect(known.querySelector('a')?.getAttribute('href')).toBe('/unit/v%3A0')
  })

  it('switches to Genesis, where a control fails', async () => {
    const { container } = renderAt('/els')
    await screen.findByRole('heading', { name: 'Against the controls' })
    fireEvent.click(screen.getByRole('radio', { name: 'Genesis' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/els?scope=genesis'))
    expect(screen.getByText(/78,063 letters/)).toBeTruthy()
    const verdicts = [...container.querySelectorAll('.els-table')[0].querySelectorAll('.dlg-verdict')].map((v) => v.textContent)
    expect(verdicts).toEqual(['holds', 'does not hold', 'holds'])
  })

  it('reads in Hebrew', async () => {
    renderAt('/els', 'he')
    expect(await screen.findByRole('heading', { name: 'אותיות בדילוג שווה' })).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'מה שקראה המסורת' })).toBeTruthy()
    expect(screen.getByText(/19 פעמים/)).toBeTruthy()
  })

  it('says when the build has no count', async () => {
    renderAt('/els', 'en', { meta: {}, scopes: [], known: [] })
    expect(await screen.findByText(/Not computed in this build: run `bsim els`/)).toBeTruthy()
  })
})
