// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NeighbourhoodResponse, UnitSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { NeighbourhoodPage } from './NeighbourhoodPage'

const unit = (id: number, label: string): UnitSummary => ({
  unit_id: `v:${id}`,
  unit_type: 'verse',
  label_en: label,
  label_he: `he ${label}`,
  book_id: 0,
  start_verse_id: id,
  end_verse_id: id,
  n_verses: 1,
  marker: null,
})

const DATA: NeighbourhoodResponse = {
  unit: unit(0, 'Genesis 1:1'),
  k: 6,
  hops: 2,
  truncated: false,
  nodes: [
    { unit: unit(0, 'Genesis 1:1'), hop: 0, x: 0.5, y: 0.5 },
    { unit: unit(5, 'Genesis 1:6'), hop: 1, x: 0.2, y: 0.3 },
    { unit: unit(9, 'Genesis 2:4'), hop: 2, x: 0.8, y: 0.7 },
  ],
  edges: [
    { a: 'v:0', b: 'v:5', kinds: ['known', 'lexical', 'fused'], score: 0.4 },
    { a: 'v:5', b: 'v:9', kinds: ['semantic', 'fused'], score: 0.2 },
    { a: 'v:0', b: 'v:9', kinds: ['citation'], score: null },
  ],
}

const calls: string[] = []
function mockApi(data: NeighbourhoodResponse = DATA) {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      calls.push(u.pathname + u.search)
      return new Response(JSON.stringify(u.pathname.startsWith('/api/neighbourhood/') ? data : null), { status: 200 })
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
            <Route path="/neighbourhood/:unitId" element={<NeighbourhoodPage />} />
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

describe('NeighbourhoodPage (DESIGN.md §11.1, D149)', () => {
  it('draws each passage and each link in the colour of its first kind', async () => {
    mockApi()
    const { container } = renderAt('/neighbourhood/v%3A0')
    expect(await screen.findByRole('heading', { level: 1, name: 'The neighbourhood of Genesis 1:1' })).toBeTruthy()
    expect(calls).toContain('/api/neighbourhood/v%3A0')
    expect(container.querySelectorAll('.nbh-graph circle')).toHaveLength(3)
    expect(container.querySelector('.nbh-node.centre')).not.toBeNull()
    const lines = [...container.querySelectorAll('.nbh-edge')].map((l) => l.getAttribute('class'))
    expect(lines).toEqual(['nbh-edge nbh-known', 'nbh-edge nbh-semantic', 'nbh-edge nbh-citation'])
    // the legend lists only the kinds there are, as toggles
    const boxes = screen.getAllByRole('checkbox').map((b) => b.parentElement?.textContent)
    expect(boxes).toEqual(['A citation', 'A parallel already recorded', 'Shared wording', 'Shared meaning', 'Only on the combined list'])
    // the table: every passage, its link to the middle, a link to put it there
    const rows = screen.getAllByRole('row').slice(1).map((r) => r.textContent)
    expect(rows[0]).toContain('In the middle')
    expect(rows[1]).toContain('A parallel already recorded · Shared wording · Only on the combined list')
    expect(screen.getAllByRole('link', { name: 'Put in the middle' })[0].getAttribute('href')).toBe('/neighbourhood/v%3A5')
  })

  it('switches a kind off through the address: its links take their next kind or go', async () => {
    mockApi()
    const { container } = renderAt('/neighbourhood/v%3A0')
    fireEvent.click(await screen.findByRole('checkbox', { name: 'A parallel already recorded' }))
    expect(screen.getByTestId('loc').textContent).toBe('/neighbourhood/v%3A0?off=known')
    fireEvent.click(screen.getByRole('checkbox', { name: 'A citation' }))
    const lines = [...container.querySelectorAll('.nbh-edge')].map((l) => l.getAttribute('class'))
    expect(lines).toEqual(['nbh-edge nbh-lexical', 'nbh-edge nbh-semantic'])
    // the settings go along when a passage is put in the middle
    expect(screen.getAllByRole('link', { name: 'Put in the middle' })[0].getAttribute('href')).toBe('/neighbourhood/v%3A5?off=known%2Ccitation')
  })

  it('asks for other settings, and says when the walk stopped', async () => {
    mockApi({ ...DATA, truncated: true })
    renderAt('/neighbourhood/v%3A0?k=10&hops=1')
    expect(await screen.findByText(/^Only the first 3 passages are drawn/)).toBeTruthy()
    expect(calls).toContain('/api/neighbourhood/v%3A0?k=10&hops=1')
  })

  it('runs in the Hebrew interface', async () => {
    mockApi()
    renderAt('/neighbourhood/v%3A0', 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'השכנים של he Genesis 1:1' })).toBeTruthy()
    expect(screen.getByRole('checkbox', { name: 'ציטוט' })).toBeTruthy()
  })
})
