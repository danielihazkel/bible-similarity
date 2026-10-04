// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, ResolveResponse } from '../api/types'
import { UnitPicker } from './UnitPicker'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
]
const GEN1 = {
  unit_id: 'c:0:1',
  unit_type: 'chapter' as const,
  book_id: 0,
  start_verse_id: 0,
  end_verse_id: 30,
  n_verses: 31,
  label_en: 'Genesis 1',
  label_he: 'בראשית א',
  marker: null,
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function renderPicker(fetchImpl: (path: string, url: URL) => unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      const body = fetchImpl(u.pathname, u)
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body === undefined ? 500 : 200 })
    }),
  )
  const onChange = vi.fn()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <UnitPicker label="A" value={undefined} onChange={onChange} />
    </QueryClientProvider>,
  )
  return onChange
}

describe('UnitPicker', () => {
  it('resolves a typed reference', async () => {
    const onChange = renderPicker((p, u) => {
      if (p === '/api/books') return BOOKS
      if (p === '/api/resolve') {
        const r: ResolveResponse = { query: u.searchParams.get('q')!, unit: u.searchParams.get('q') === 'Gen 1' ? GEN1 : null }
        return r
      }
    })
    const input = screen.getByLabelText('A reference')
    fireEvent.change(input, { target: { value: 'Gen 1' } })
    fireEvent.submit(input.closest('form')!)
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('c:0:1'))

    fireEvent.change(input, { target: { value: 'xyz' } })
    fireEvent.submit(input.closest('form')!)
    expect(await screen.findByText('Not a reference: xyz')).toBeTruthy()
  })

  it('shows an error when books fail to load', async () => {
    renderPicker(() => undefined)
    expect((await screen.findByRole('alert')).textContent).toBe('Could not load books')
  })
})
