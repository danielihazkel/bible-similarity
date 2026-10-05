// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, DomainInfo, DomainResponse, UnitDomains, Verse } from '../api/types'
import { ThemesPanel } from '../components/ThemesPanel'
import { LocaleProvider } from '../context/Locale'
import { DomainsPage } from './DomainsPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהילים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const dom = (code: string, label_en: string, n_verses: number): DomainInfo => ({
  code,
  level: code.length / 3,
  parent: code.length > 3 ? code.slice(0, -3) : null,
  label_en,
  n_verses,
  weight: n_verses * 1.5,
})
const DOMAINS = [
  dom('002', 'Events', 900),
  dom('002002', 'Position', 400),
  dom('002002001', 'Move', 120),
  dom('002002001001', 'Fly', 12),
]
const VERSE: Verse = {
  verse_id: 0,
  book_id: 0,
  chapter: 1,
  verse: 20,
  ref: 'Genesis 1:20',
  ref_he: 'בראשית א:כ',
  text_display: 'וְעוֹף יְעוֹפֵף',
  display_tokens: ['וְעוֹף', 'יְעוֹפֵף'],
  ketiv_note: null,
}
const detail = (book: string | null): DomainResponse => ({
  domain: DOMAINS[2],
  path: DOMAINS.slice(0, 2),
  children: [DOMAINS[3]],
  by_book: [
    { book_id: 0, n_verses: 8 },
    { book_id: 26, n_verses: 4 },
  ],
  book: book === null ? null : Number(book),
  total: book === null ? 120 : 4,
  offset: 0,
  limit: 50,
  items: [{ verse: VERSE, label_en: 'Genesis 1:20', label_he: 'בראשית א:כ', display_idxs: [1], weight: 1 }],
})
const THEMES: UnitDomains = {
  unit: {
    unit_id: 'c:0:1',
    unit_type: 'chapter',
    label_en: 'Genesis 1',
    label_he: 'בראשית א',
    book_id: 0,
    start_verse_id: 0,
    end_verse_id: 30,
    n_verses: 31,
    marker: null,
  },
  total: 368,
  themes: [{ domain: DOMAINS[2], weight: 13, expected: 0.3, lift: 37.9, g2: 80 }],
  broad: [],
}

function mockApi() {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const path = decodeURIComponent(u.pathname)
      const body =
        path === '/api/books'
          ? BOOKS
          : path === '/api/domains'
            ? DOMAINS
            : path === '/api/domain/002002001'
              ? detail(u.searchParams.get('book'))
              : path === '/api/unit-domains/c:0:1'
                ? THEMES
                : null
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    }),
  )
  return calls
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/domains" element={<DomainsPage />} />
            <Route path="/domains/:code" element={<DomainsPage />} />
            <Route path="/unit/:id" element={<ThemesPanel unitId="c:0:1" />} />
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

describe('DomainsPage', () => {
  it('lists the two top levels and the third as chips', async () => {
    mockApi()
    renderAt('/domains')
    expect(await screen.findByRole('heading', { level: 2, name: /Events/ })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 3, name: /Position/ })).toBeTruthy()
    const move = screen.getByRole('link', { name: /Move/ })
    expect(move.getAttribute('href')).toBe('/domains/002002001')
    expect(screen.queryByText('Fly')).toBeNull() // fourth level: on Move's page
  })

  it('shows a domain with its path, subdomains and highlighted verses, and filters by book', async () => {
    const calls = mockApi()
    const { container } = renderAt('/domains/002002001')
    expect(await screen.findByRole('heading', { level: 1, name: 'Move' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Position' }).getAttribute('href')).toBe('/domains/002002')
    expect(screen.getByRole('link', { name: /Fly/ })).toBeTruthy()
    // the word in the domain (יְעוֹפֵף) is highlighted, the other not
    expect([...container.querySelectorAll('.hit-text .w-shared')].map((e) => e.textContent)).toEqual(['יְעוֹפֵף'])
    fireEvent.click(screen.getByRole('button', { name: /Psalms/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/domains/002002001?book=26'))
    await waitFor(() => expect(calls.some((c) => c.includes('/api/domain/002002001?book=26'))).toBe(true))
  })

  it('names the top levels in Hebrew and keeps deeper SDBH names in English', async () => {
    mockApi()
    renderAt('/domains/002002001', 'he')
    expect(await screen.findByRole('link', { name: 'מקום ותנועה' })).toBeTruthy()
    const title = await screen.findByRole('heading', { level: 1 })
    expect(title.textContent).toBe('Move')
    expect(title.querySelector('bdi')?.getAttribute('dir')).toBe('ltr')
  })
})

describe('ThemesPanel', () => {
  it('lists the over-represented domains with their lift', async () => {
    mockApi()
    renderAt('/unit/c:0:1')
    const chip = await screen.findByRole('link', { name: /Move/ })
    expect(chip.textContent).toContain('×37.9')
    expect(chip.getAttribute('href')).toBe('/domains/002002001')
  })
})
