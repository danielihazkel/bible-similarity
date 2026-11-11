// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DetectorPrecisionResponse, PrecisionRow } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { PrecisionNote, PrecisionTable } from './PrecisionNote'

const row = (set: string, right: number, wrong: number, population: number | null, precision: number): PrecisionRow => ({
  set,
  population,
  judged: right + wrong,
  right,
  wrong,
  unsure: 0,
  precision,
  lo: 0.4,
  hi: 0.9,
})

const data: DetectorPrecisionResponse = {
  runs: [
    { run: 'llm_audit', population: 'strongest', model: 'claude-sonnet-5-5', collected_at: '2026-11-05T12:00:00+00:00', places_right: '45 / 50', known_right: '127 / 138' },
    { run: 'llm_audit_pages', population: 'pages', model: 'claude-sonnet-5-5', collected_at: '2026-11-10T12:00:00+00:00', places_right: '46 / 50', known_right: '87 / 91' },
  ],
  detectors: {
    etiologies: [row('strongest', 29, 18, null, 0.617), row('marked', 7, 0, 8, 1), row('shown', 26, 18, 111, 0.591)],
    acrostics: [row('strongest', 4, 46, null, 0.08)],
  },
}

function mockApi(personal = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      const body =
        u.pathname === '/api/meta'
          ? { runtime: { personal, encoder_on: true, embeddings_shape: [1, 1] } }
          : u.pathname === '/api/detector-precision' && personal
            ? data
            : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
}

function renderIt(el: React.ReactNode, locale: Locale = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter>{el}</MemoryRouter>
      </QueryClientProvider>
    </LocaleProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('PrecisionNote (DESIGN.md §16.86, D147)', () => {
  it("leads with the share right of what the page lists, then each population and the runs", async () => {
    mockApi()
    renderIt(<PrecisionNote detector="etiologies" />)
    const summary = await screen.findByText(/59% right \[0.40, 0.90\] of what this page lists/)
    fireEvent.click(summary)
    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toMatch(/^44 drawn from the 111 listed here: 26 right, 18 wrong: precision 0.59/)
    expect(items[1]).toMatch(/^7 drawn from the 8 marked strong: 7 right, 0 wrong/)
    expect(items[2]).toMatch(/^47 drawn from its strongest findings/)
    expect(screen.getByText(/2026-11-10\. Its calibration: .* 46 \/ 50 right, the known answers 87 \/ 91/)).toBeTruthy()
  })

  it('names the run alone when only the strongest were judged, and nothing for a detector not audited', async () => {
    mockApi()
    const { container } = renderIt(
      <>
        <PrecisionNote detector="acrostics" />
        <PrecisionNote detector="gematria" />
      </>,
    )
    expect(await screen.findByText('How often it is right, by Claude’s reading')).toBeTruthy()
    expect(container.querySelectorAll('.precision-note')).toHaveLength(1)
  })

  it('is in Hebrew with the Hebrew interface', async () => {
    mockApi()
    renderIt(<PrecisionNote detector="etiologies" />, 'he')
    expect(await screen.findByText(/59% נכונים \[0.40, 0.90\] ממה שהעמוד הזה מציג/)).toBeTruthy()
  })

  it('shows nothing on a public server', async () => {
    mockApi(false)
    const { container } = renderIt(
      <>
        <PrecisionNote detector="etiologies" />
        <PrecisionTable />
      </>,
    )
    await new Promise((r) => setTimeout(r, 50))
    expect(container.textContent).toBe('')
  })
})

describe('PrecisionTable', () => {
  it('lists each detector judged on its page, linked, with its marked share', async () => {
    mockApi()
    renderIt(<PrecisionTable />)
    const link = await screen.findByRole('link', { name: 'Naming etiologies' })
    expect(link.getAttribute('href')).toBe('/etiologies')
    const cells = screen.getAllByRole('cell').map((c) => c.textContent)
    expect(cells).toEqual(['Naming etiologies', '111', '59% [0.40, 0.90] (44 judged)', '100% [0.40, 0.90] (7 judged)'])
    expect(screen.queryByText('Acrostics')).toBeNull() // only M152's run: not on the table
  })
})
