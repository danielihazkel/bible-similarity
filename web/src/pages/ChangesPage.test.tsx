// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ChangesResponse } from '../api/types'
import { ChangesPage } from './ChangesPage'

const RES: ChangesResponse = {
  op: 'substitution',
  a_book: null,
  b_book: null,
  totals: { substitution: 1963, added: 1632 },
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      a_key: '3068',
      b_key: '430',
      a_form: null,
      b_form: null,
      a_he: 'יהוה',
      b_he: 'אלהים',
      count: 31,
      n_sequences: 9,
      examples: [{ seq_id: 7, a: 15292, b: 15956, a_label: 'Psalms 14:2', b_label: 'Psalms 53:3' }],
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

describe('ChangesPage', () => {
  it('lists grouped changes with totals per kind and links to the sequence', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? [] : p === '/api/changes' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/changes']}>
          <Routes>
            <Route path="/changes" element={<ChangesPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('אלהים')).toBeTruthy()
    expect(screen.getByText('Substituted 1,963')).toBeTruthy()
    const example = screen.getByText('Psalms 14:2 → Psalms 53:3')
    expect(example.getAttribute('href')).toBe('/sequences/7')
    fireEvent.click(screen.getByText('Added 1,632'))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/changes?op=added'))
    await waitFor(() => expect(calls.some((c) => c.includes('op=added'))).toBe(true))
  })
})
