// @vitest-environment jsdom
// M170: the start page (`/`): the jump field, Continue, the pinned pages, the notebook's latest, the books
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, NotebookEntry, UnitSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { togglePin, visitPage, visitPassage } from '../lib/recent'
import { BooksPage } from './BooksPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const unit = (unit_id: string, label_en: string, label_he: string): UnitSummary => ({
  unit_id,
  unit_type: 'chapter',
  label_en,
  label_he,
  book_id: 0,
  start_verse_id: 0,
  end_verse_id: 0,
  n_verses: 1,
  marker: null,
})
const entry = (u: UnitSummary, note: string, updated_at: string): NotebookEntry => ({ unit: u, note, collections: [], created_at: '2026-01-01T00:00:00', updated_at, verse: null })
const NOTES: NotebookEntry[] = [
  entry(unit('c:0:1', 'Genesis 1', 'בראשית א'), 'the oldest note', '2026-10-01T08:00:00'),
  entry(unit('c:0:22', 'Genesis 22', 'בראשית כב'), 'the binding\nits second line', '2026-11-10T08:00:00'),
  entry(unit('c:26:23', 'Psalms 23', 'תהלים כג'), '', '2026-11-12T08:00:00'),
  entry(unit('c:26:14', 'Psalms 14', 'תהלים יד'), 'beside Psalm 53', '2026-11-11T08:00:00'),
]

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderHome({ locale = 'en', personal = true, notes = [] as NotebookEntry[], books = true }: { locale?: 'en' | 'he'; personal?: boolean; notes?: NotebookEntry[]; books?: boolean } = {}) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      calls.push(u.pathname)
      const q = u.searchParams.get('q') ?? ''
      const body: unknown =
        u.pathname === '/api/books'
          ? books && BOOKS
          : u.pathname === '/api/meta'
            ? { runtime: { personal } }
            : u.pathname === '/api/notebook'
              ? { writable: true, entries: notes, collections: [], hidden: 0 }
              : u.pathname === '/api/resolve'
                ? { query: q, unit: null }
                : ['/api/lemmas', '/api/places/lookup', '/api/genealogy/lookup'].includes(u.pathname)
                  ? { query: q, items: [] }
                  : null
      return new Response(JSON.stringify(body || { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const view = render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<BooksPage />} />
            <Route path="*" element={<Location />} />
          </Routes>
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { ...view, calls }
}

const headings = () => screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
const field = () => screen.getByRole('combobox', { name: /Jump to a passage|מעבר אל קטע/ })

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('the start page on a first visit', () => {
  it('has the guided tours where the recent passages will be, then the books', async () => {
    renderHome()
    expect(await screen.findByRole('heading', { level: 3, name: /Torah/ })).toBeTruthy()
    expect(headings()).toEqual(['New here?', 'The books'])
    expect(screen.getAllByRole('link', { name: /^Start: / })).toHaveLength(4)
    expect(screen.getByRole('link', { name: /^תהלים\s*Psalms/ }).getAttribute('href')).toBe('/browse/26')
    // the findings, and the index that took the Explore panel's place
    expect(screen.getByRole('link', { name: /What the analyses found/ }).getAttribute('href')).toBe('/findings')
    expect(screen.getByRole('link', { name: /^All pages/ }).getAttribute('href')).toBe('/pages')
    expect(screen.queryByRole('heading', { name: 'Explore' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Take a guided tour' })).toBeNull()
  })

  it('keeps the rest of the page when the books cannot be loaded', async () => {
    renderHome({ books: false })
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(headings()).toEqual(['New here?', 'The books'])
    expect(field()).toBeTruthy()
  })
})

describe('the start page with something to go back to', () => {
  it('offers the passages opened last, each in the view it was left in, and the pages', async () => {
    visitPassage({ to: '/unit/c%3A26%3A23', en: 'Psalms 23', he: 'תהלים כג' })
    visitPassage({ to: '/read/c%3A0%3A22', en: 'Genesis 22', he: 'בראשית כב' })
    visitPage('/acrostics')
    visitPage('/map')
    renderHome()
    await screen.findByRole('heading', { level: 3, name: /Torah/ })
    expect(headings()).toEqual(['Continue', 'The books'])
    const passages = within(screen.getByRole('list', { name: 'Recent passages' })).getAllByRole('link')
    expect(passages.map((a) => a.getAttribute('href'))).toEqual(['/read/c%3A0%3A22', '/unit/c%3A26%3A23'])
    expect(passages[0].textContent).toBe('בראשית כבGenesis 22in the reader')
    expect(passages[1].textContent).toBe('תהלים כגPsalms 23')
    const pages = within(screen.getByRole('list', { name: 'Recent pages' })).getAllByRole('link')
    expect(pages.map((a) => a.textContent)).toEqual(['Map', 'Acrostics'])
    expect(pages[1].getAttribute('title')).toBe('Lines through the alphabet')
    // the tours are a line now
    expect(screen.queryByRole('link', { name: /^Start: / })).toBeNull()
    expect(screen.getByRole('link', { name: 'Take a guided tour' }).getAttribute('href')).toBe('/tours')
  })

  it('lists the pinned pages in a row of their own, not again among the recent ones', async () => {
    togglePin('/gematria')
    togglePin('/map')
    visitPage('/map')
    visitPage('/phrases')
    renderHome()
    expect(headings()).toEqual(['Continue', 'Pinned', 'The books'])
    expect(within(screen.getByRole('list', { name: 'Pinned' })).getAllByRole('link').map((a) => a.textContent)).toEqual(['Gematria', 'Map'])
    expect(within(screen.getByRole('list', { name: 'Recent pages' })).getAllByRole('link').map((a) => a.textContent)).toEqual(['Phrases'])
    cleanup()
    // pins alone: no Continue, and no tours either
    localStorage.clear()
    togglePin('/gematria')
    renderHome()
    expect(headings()).toEqual(['Pinned', 'The books'])
  })

  it('speaks Hebrew: the Hebrew reference alone on a card', async () => {
    visitPassage({ to: '/read/c%3A0%3A22', en: 'Genesis 22', he: 'בראשית כב' })
    togglePin('/gematria')
    renderHome({ locale: 'he' })
    await screen.findByRole('heading', { level: 3, name: 'תורה' })
    expect(headings()).toEqual(['המשיכו מכאן', 'נעוצים', 'הספרים'])
    expect(within(screen.getByRole('list', { name: 'קטעים אחרונים' })).getByRole('link').textContent).toBe('בראשית כבבקורא')
    expect(screen.queryByText('Genesis 22')).toBeNull()
    expect(screen.getByRole('link', { name: 'צאו לסיור מודרך' })).toBeTruthy()
  })
})

describe('the notebook on the start page', () => {
  it('shows the three entries changed last, each with the first line of its note', async () => {
    renderHome({ notes: NOTES })
    const section = (await screen.findByRole('heading', { level: 2, name: 'Notebook' })).closest('section')!
    const rows = [...section.querySelectorAll('li')].map((li) => li.textContent)
    expect(rows).toEqual(['Psalms 23', 'Psalms 14beside Psalm 53', 'Genesis 22the binding'])
    expect(within(section).getByRole('link', { name: 'Genesis 22' }).getAttribute('href')).toBe('/unit/c%3A0%3A22')
    expect(within(section).getByRole('link', { name: /The whole notebook/ }).getAttribute('href')).toBe('/notebook')
  })

  it('is left out while the notebook is empty', async () => {
    const { calls } = renderHome()
    await waitFor(() => expect(calls).toContain('/api/notebook'))
    await screen.findByRole('heading', { level: 3, name: /Torah/ })
    expect(screen.queryByRole('heading', { name: 'Notebook' })).toBeNull()
  })

  it('is not asked for or shown where the server keeps nothing personal, nor a pin of it', async () => {
    togglePin('/notebook')
    togglePin('/map')
    const { calls } = renderHome({ personal: false, notes: NOTES })
    await screen.findByRole('heading', { level: 3, name: /Torah/ })
    await waitFor(() => expect(within(screen.getByRole('list', { name: 'Pinned' })).getAllByRole('link').map((a) => a.textContent)).toEqual(['Map']))
    expect(screen.queryByRole('heading', { name: 'Notebook' })).toBeNull()
    expect(calls).not.toContain('/api/notebook')
  })
})

describe('the jump field of the start page', () => {
  it('lists nothing until something is typed, then finds a book and opens it', async () => {
    visitPage('/map')
    renderHome()
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(field().getAttribute('aria-expanded')).toBe('false')
    fireEvent.focus(field())
    expect(screen.queryByRole('listbox')).toBeNull() // the page itself lists the recent ones
    fireEvent.change(field(), { target: { value: 'gen' } })
    const genesis = await screen.findByRole('option', { name: /^Genesis/ })
    expect(field().getAttribute('aria-expanded')).toBe('true')
    expect(field().getAttribute('aria-controls')).toBe(screen.getByRole('listbox').id)
    await waitFor(() => expect(genesis.getAttribute('aria-selected')).toBe('true'))
    fireEvent.keyDown(field(), { key: 'Enter' })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/browse/0'))
  })

  it('clears on Escape, closes when the focus leaves, and lets Tab move on', async () => {
    renderHome()
    fireEvent.focus(field())
    fireEvent.change(field(), { target: { value: 'netw' } })
    expect(await screen.findByRole('option', { name: /Network/ })).toBeTruthy()
    expect(fireEvent.keyDown(field(), { key: 'Tab' })).toBe(true) // not prevented, as it is in the box
    fireEvent.blur(field())
    expect(screen.queryByRole('listbox')).toBeNull()
    fireEvent.focus(field())
    expect(screen.getByRole('listbox')).toBeTruthy()
    fireEvent.keyDown(field(), { key: 'Escape' })
    expect((field() as HTMLInputElement).value).toBe('')
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('opens the choice clicked', async () => {
    renderHome()
    fireEvent.change(field(), { target: { value: 'netw' } })
    fireEvent.click(await screen.findByRole('option', { name: /Network/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/network'))
  })
})
