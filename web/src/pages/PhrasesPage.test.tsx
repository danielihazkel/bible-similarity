// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PhrasesResponse, UnitSummary, Verse } from '../api/types'
import { PhrasesPage } from './PhrasesPage'

const unit = (id: number, label: string): UnitSummary => ({
  unit_id: `v:${id}`,
  unit_type: 'verse',
  label_en: label,
  label_he: `he ${label}`,
  book_id: id,
  start_verse_id: id,
  end_verse_id: id,
  n_verses: 1,
  marker: null,
})
const verse = (id: number): Verse => ({
  verse_id: id,
  book_id: id,
  chapter: 1,
  verse: 1,
  ref: `B${id}`,
  ref_he: 'הפניה',
  text_display: 'כְּדֹב שַׁכּוּל',
  display_tokens: ['כְּדֹב', 'שַׁכּוּל'],
  ketiv_note: null,
})
const RESPONSE: PhrasesResponse = {
  book: null,
  unit: null,
  cross_book: false,
  min_tokens: 3,
  max_spread: 3,
  total: 1,
  offset: 0,
  limit: 50,
  items: [
    {
      score: 23.2,
      n_tokens: 3,
      spread: 5,
      a: unit(1, 'Hosea 13:8'),
      b: unit(2, 'Proverbs 17:12'),
      a_verse: verse(1),
      b_verse: verse(2),
      a_display: [0, 1],
      b_display: [1],
      link: null,
    },
  ],
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('PhrasesPage', () => {
  it('hides recurring phrases by default and highlights the matched words', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const body = url.startsWith('/api/phrases') ? RESPONSE : url.startsWith('/api/books') ? [] : null
        return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/phrases']}>
          <Routes>
            <Route path="/phrases" element={<PhrasesPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const card = (await screen.findByText('Hosea 13:8')).closest('li')!
    expect(card.textContent).toContain('recurs in 5 verses')
    expect(container.querySelectorAll('.w-shared')).toHaveLength(3)
    expect(calls).toContain('/api/phrases?min_tokens=3&max_spread=3&limit=50&offset=0')
    fireEvent.click(screen.getByLabelText('Include recurring phrases'))
    await waitFor(() => expect(calls).toContain('/api/phrases?min_tokens=3&limit=50&offset=0'))
  })

  it('lists every phrase of one unit (from the dossier) and can go back to all', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(url)
        const body = url.startsWith('/api/phrases')
          ? { ...RESPONSE, unit: 'v:1' }
          : url.startsWith('/api/unit/')
            ? { unit: unit(1, 'Hosea 13:8'), verses: [], parents: [], prev_id: null, next_id: null }
            : url.startsWith('/api/books')
              ? []
              : null
        return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/phrases?unit=v:1']}>
          <Routes>
            <Route path="/phrases" element={<PhrasesPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByRole('status')).toBeTruthy()
    // recurring idioms are not hidden for one unit: its count matches the dossier's
    expect(calls).toContain('/api/phrases?min_tokens=3&unit=v%3A1&limit=50&offset=0')
    fireEvent.click(screen.getByRole('button', { name: /Show all/ }))
    await waitFor(() => expect(calls).toContain('/api/phrases?min_tokens=3&max_spread=3&limit=50&offset=0'))
  })
})
