// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { FindingsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { FindingsPage } from './FindingsPage'

const FINDINGS: FindingsResponse = {
  alpha: 0.05,
  items: [
    { key: 'dating', verdict: 'holds', values: { later: 26, pairs: 26, p: 3e-8, auc: 0.9476 } },
    { key: 'sevens', verdict: 'fails', values: { ratio7: 1.159, ratio10: 1.407, smallest: 7, largest: 12 } },
    { key: 'chiasm', verdict: 'fails', values: { verses_chiastic: 2099, verses_parallel: 2790, share: 0.4287, p: 4.9e-23 } },
    { key: 'allusions', verdict: 'lead', values: { pairs: 176, known: 171, strong: 3, strong_known: 3, best_new_q: 0.8154 } },
  ],
}

function renderAt(locale: 'en' | 'he' = 'en', body: FindingsResponse = FINDINGS) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const p = new URL(url, 'http://x').pathname
      return p === '/api/findings'
        ? new Response(JSON.stringify(body), { status: 200 })
        : new Response(JSON.stringify({ detail: 'nope' }), { status: 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={['/findings']}>
          <Routes>
            <Route path="/findings" element={<FindingsPage />} />
          </Routes>
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('FindingsPage', () => {
  it('groups the claims by verdict, states their numbers and links to the evidence', async () => {
    renderAt()
    const holds = await screen.findByRole('region', { name: 'Borne out' })
    expect(within(holds).getByText(/Chronicles side later in 26 of 26 parallel passages \(p < 0.001\)/)).toBeTruthy()
    expect(within(holds).getByRole('link', { name: 'A late-language profile: Language' }).getAttribute('href')).toBe('/language')
    const fails = screen.getByRole('region', { name: 'Not borne out' })
    expect(within(fails).getByText(/multiples of 7 1.16 times .* 12\), and 7 the least\. Nothing singles out 7/)).toBeTruthy()
    expect(within(fails).getByText(/same order more often than mirrored: 2,790 verses against 2,099 \(43% of pairs mirrored/)).toBeTruthy()
    const leads = screen.getByRole('region', { name: 'Leads, not findings' })
    expect(within(leads).getByText(/176 pairs of passages .* 171 are known parallels, and the best new one has q 0.82/)).toBeTruthy()
    expect(screen.getByText(/passes at p ≤ 0.05/)).toBeTruthy()
  })

  it('words a claim by the direction the numbers take, in Hebrew', async () => {
    renderAt('he', {
      alpha: 0.05,
      items: [{ key: 'chiasm', verdict: 'holds', values: { verses_chiastic: 30, verses_parallel: 10, share: 0.7, p: 0.001 } }],
    })
    expect(await screen.findByRole('region', { name: 'עומדות במבחן' })).toBeTruthy()
    expect(screen.getByText(/שבות במהופך יותר מאשר באותו סדר: 30 פסוקים לעומת 10/)).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'אינן עומדות במבחן' })).toBeNull()
  })

  it('says how to compute them when no stage ran', async () => {
    renderAt('en', { alpha: 0.05, items: [] })
    expect(await screen.findByText(/run `bsim all`/)).toBeTruthy()
  })
})
