// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ProphItems, PropheticResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { PropheticPage } from './PropheticPage'

const DATA: PropheticResponse = {
  counts: { messenger: 801, woe: 38, nations: 70, lawsuit: 62, call: 12 },
  items: 983,
  known: {
    nations: { refs: [{ ref: 'Isaiah 13-23', found: true, cover: 0.593, item: 843 }], found: 1, holds: true },
    call: {
      refs: [
        { ref: 'Isaiah 6', found: true, cover: 0.385, item: 975 },
        { ref: 'Ezekiel 1-3', found: false, cover: 0, item: null },
      ],
      found: 1,
      holds: false,
    },
  },
  known_found: 2,
  known_total: 3,
  known_holds: false,
  known_cover: 0.5,
  known_overlap: ['lawsuit', 'call'],
  books: [{ book_id: 11, counts: { messenger: 67, woe: 20 } }],
}
const verse = (id: number, text: string) => ({
  verse_id: id,
  book_id: 11,
  chapter: 5,
  verse: 8,
  ref: 'Isaiah 5:8',
  ref_he: 'ישעיהו ה:ח',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const ITEMS: ProphItems = {
  total: 1,
  offset: 0,
  limit: 25,
  form: null,
  book: null,
  items: [
    {
      item_id: 803,
      form: 'woe',
      unit_id: 's:900',
      book_id: 11,
      first_vid: 10256,
      last_vid: 10258,
      first_label: 'Isaiah 5:8',
      last_label: 'Isaiah 5:10',
      first_label_he: 'ישעיהו ה:ח',
      last_label_he: 'ישעיהו ה:י',
      detail: { kind: null, next: '5060', names: null, heading: null, paragraphs: null, dispute: null, witnesses: null, objection: null, reassurance: null },
      known: true,
      verses: [verse(10256, 'הוֹי מַגִּיעֵי בַיִת בְּבַיִת')],
      marks: { '10256': [0, 1] },
    },
  ],
}

const calls: string[] = []
function mockApi() {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      calls.push(u.pathname + u.search)
      const body = u.pathname === '/api/prophetic' ? DATA : u.pathname === '/api/prophetic/items' ? ITEMS : u.pathname === '/api/books' ? [] : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
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
            <Route path="/prophetic" element={<PropheticPage />} />
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

describe('PropheticPage (DESIGN.md §16.92, D154)', () => {
  it('counts the forms, lists the passages named in advance, the books and the findings', async () => {
    mockApi()
    const { container } = renderAt('/prophetic')
    expect(await screen.findByText('Woe saying: 38 findings')).toBeTruthy()
    expect(screen.getByText('983 findings in all.')).toBeTruthy()
    expect(screen.getByText('Ezekiel 1-3: not found (0% of its verses covered)')).toBeTruthy()
    expect(screen.getByText('Isaiah 13-23: found (59% of its verses covered)')).toBeTruthy()
    expect(screen.getAllByText('Not all found')).toHaveLength(1)
    expect(await screen.findByText('Isaiah 5:8 – Isaiah 5:10')).toBeTruthy()
    expect(screen.getByText('Woe saying · named in advance')).toBeTruthy()
    expect(container.querySelectorAll('.pf-item .w-focus')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'read it with the layer' }).getAttribute('href')).toBe('/read/s%3A900?layers=prophetic')
    expect(screen.getByText('and 2 more verses')).toBeTruthy()
  })

  it('asks for one form and the known passages through the address', async () => {
    mockApi()
    renderAt('/prophetic')
    // six forms with "all": a dropdown, by the toolbar's rule
    fireEvent.change(await screen.findByRole('combobox', { name: 'Form' }), { target: { value: 'lawsuit' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Only those in a passage named in advance' }))
    expect(screen.getByTestId('loc').textContent).toBe('/prophetic?form=lawsuit&known=1')
    await vi.waitFor(() => expect(calls).toContain('/api/prophetic/items?form=lawsuit&known=true&limit=25&offset=0'))
  })

  it('runs in the Hebrew interface', async () => {
    mockApi()
    renderAt('/prophetic', 'he')
    expect(await screen.findByRole('heading', { level: 1, name: 'צורות הדיבור הנבואי' })).toBeTruthy()
    expect(await screen.findByText('דבר ה„הוי”: 38 ממצאים')).toBeTruthy()
  })
})
