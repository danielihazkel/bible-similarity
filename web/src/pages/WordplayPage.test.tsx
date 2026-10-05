// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { WordplayResponse } from '../api/types'
import { WordplayPage } from './WordplayPage'

const verse = (id: number, tokens: string[]) => ({
  verse_id: id,
  book_id: 22,
  chapter: 5,
  verse: 7,
  ref: `Isa 5:${id}`,
  ref_he: 'הפניה',
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const RES: WordplayResponse = {
  book: null,
  kind: null,
  unit: null,
  total: 400,
  expected_by_chance: 279,
  offset: 0,
  limit: 50,
  items: [
    {
      a_vid: 7,
      b_vid: 7,
      a_display: 1,
      b_display: 3,
      a_form: 'משפט',
      b_form: 'משפח',
      a_he: 'משפט',
      b_he: 'משפח',
      kind: 'substitution',
      gap: 1,
      score: 7.05,
      q: 0.25,
      a_label: 'Isaiah 5:7',
      b_label: 'Isaiah 5:7',
      verses: [verse(7, ['וַיְקַו', 'לְמִשְׁפָּט', 'וְהִנֵּה', 'מִשְׂפָּח'])],
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

describe('WordplayPage', () => {
  it('lists sound-alike pairs with both words highlighted and the chance baseline', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const p = new URL(url, 'http://x').pathname
        const body = p === '/api/books' ? [] : p === '/api/wordplay' ? RES : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/wordplay']}>
          <Routes>
            <Route path="/wordplay" element={<WordplayPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('משפט ~ משפח')).toBeTruthy()
    expect(container.querySelectorAll('.disc .w-focus')).toHaveLength(2)
    expect(screen.getByText(/roughly\s+121\s+are more than chance/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Kind'), { target: { value: 'metathesis' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/wordplay?kind=metathesis'))
    await waitFor(() => expect(calls.some((c) => c.includes('kind=metathesis'))).toBe(true))
  })
})
