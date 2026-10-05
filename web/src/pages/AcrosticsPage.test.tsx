// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AcrosticsResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { AcrosticsPage } from './AcrosticsPage'

const unit = { unit_type: 'chapter' as const, book_id: 31, start_verse_id: 0, end_verse_id: 21, n_verses: 22, marker: null }
const RES: AcrosticsResponse = {
  max_q: 0.05,
  book: null,
  known_recall: 0.929,
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      unit: { ...unit, unit_id: 'c:31:2', label_en: 'Lamentations 2', label_he: 'איכה ב' },
      granularity: 'verse',
      order_name: 'pe-ayin',
      score: 21,
      n_letters: 21,
      missing: 1,
      first_letter: 'א',
      last_letter: 'ת',
      n_lines: 22,
      p: 0.0001,
      q: 0.0077,
      chain: [],
    },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('AcrosticsPage', () => {
  it('lists significant acrostics with their chain and filters by q', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? [] : p === '/api/acrostics' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/acrostics']}>
          <Routes>
            <Route path="/acrostics" element={<AcrosticsPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const link = await screen.findByRole('link', { name: /Lamentations 2/ })
    expect(link.getAttribute('href')).toBe('/unit/c%3A31%3A2?acrostic=1')
    expect(screen.getByText('21 letters, 1 skipped')).toBeTruthy()
    expect(screen.getByText(/פ before ע/)).toBeTruthy()
    expect(screen.getByText(/93% of the acrostics scholars list/)).toBeTruthy()
    // the chain shows the alphabet in the pe-ayin order
    const letters = [...container.querySelectorAll('.acrostic-chain span')].map((e) => e.textContent).join('')
    expect(letters).toBe('אבגדהוזחטיכלמנספעצקרשת')
    expect(calls.some((c) => c.startsWith('/api/acrostics?max_q=0.05'))).toBe(true)
    fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'all' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/acrostics?q=all'))
    await waitFor(() => expect(calls.some((c) => c.startsWith('/api/acrostics?max_q=1&'))).toBe(true))
  })

  it('speaks Hebrew in the Hebrew interface', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? [] : p === '/api/acrostics' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <LocaleProvider initial="he">
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={['/acrostics']}>
            <Routes>
              <Route path="/acrostics" element={<AcrosticsPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </LocaleProvider>,
    )
    const link = await screen.findByRole('link', { name: 'איכה ב' })
    expect(link.getAttribute('href')).toBe('/unit/c%3A31%3A2?acrostic=1')
    expect(screen.getByRole('heading', { name: 'אקרוסטיכונים' })).toBeTruthy()
    expect(screen.getByText('21 אותיות, 1 חסרות')).toBeTruthy()
    expect(screen.getByText('פסוק אחר פסוק · פ לפני ע')).toBeTruthy()
    expect(screen.getByText(/פרק אחד · עמוד 1 מתוך 1/)).toBeTruthy()
    expect(screen.getByLabelText('הצגה')).toBeTruthy()
    expect(screen.queryByText(/Lamentations/)).toBeNull()
    expect(screen.queryByText(/letters/)).toBeNull()
  })
})
