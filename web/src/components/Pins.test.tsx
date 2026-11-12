// @vitest-environment jsdom
// M169: pinned pages, recent pages and passages, the All pages index, the jump box before typing
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, UnitSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { TextModeProvider } from '../context/TextMode'
import { NAV_PAGES } from '../lib/nav'
import {
  isNavPage,
  loadPins,
  loadRecent,
  MAX_RECENT_PAGES,
  MAX_RECENT_PASSAGES,
  passageOf,
  PINS_KEY,
  RECENT_KEY,
  togglePin,
  visitPage,
  visitPassage,
} from '../lib/recent'
import { PagesPage } from '../pages/PagesPage'
import { Layout } from './Layout'

const unit = (unit_id: string, unit_type: UnitSummary['unit_type'], label_en: string, label_he: string): UnitSummary => ({
  unit_id,
  unit_type,
  label_en,
  label_he,
  book_id: 0,
  start_verse_id: 0,
  end_verse_id: 0,
  n_verses: 1,
  marker: null,
})
const UNITS: Record<string, UnitSummary> = {
  'c:0:22': unit('c:0:22', 'chapter', 'Genesis 22', 'בראשית כב'),
  'c:1:3': unit('c:1:3', 'chapter', 'Exodus 3', 'שמות ג'),
  'v:0': unit('v:0', 'verse', 'Genesis 1:1', 'בראשית א:א'),
}
const book = (book_id: number, name: string, he_name: string, osis: string, n_chapters: number): Book => ({ book_id, name, he_name, osis, section: 'torah', n_chapters })
const BOOKS: Book[] = [
  book(0, 'Genesis', 'בראשית', 'Gen', 50),
  book(1, 'Exodus', 'שמות', 'Exod', 40),
  book(7, '1 Samuel', 'שמואל א', '1Sam', 31),
  book(8, '2 Samuel', 'שמואל ב', '2Sam', 24),
  book(30, 'Ruth', 'רות', 'Ruth', 4),
]

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, { locale = 'en', personal = true }: { locale?: 'en' | 'he'; personal?: boolean } = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      const q = u.searchParams.get('q') ?? ''
      const id = decodeURIComponent(u.pathname.replace('/api/unit/', ''))
      const body: unknown =
        u.pathname === '/api/books'
          ? BOOKS
          : u.pathname === '/api/meta'
            ? { runtime: { personal } }
            : u.pathname.startsWith('/api/unit/') && UNITS[id]
              ? { unit: UNITS[id], verses: [] }
              : u.pathname === '/api/resolve'
                ? { query: q, unit: null }
                : ['/api/lemmas', '/api/places/lookup', '/api/genealogy/lookup'].includes(u.pathname)
                  ? { query: q, items: [] }
                  : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <TextModeProvider>
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route element={<Layout />}>
                <Route path="pages" element={<PagesPage />} />
                <Route path="*" element={<Location />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </TextModeProvider>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

const loc = () => screen.getByTestId('loc').textContent
const box = () => screen.getByRole('combobox', { name: /Jump to a passage|מעבר אל קטע/ })
const openJump = () => fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
const options = () => screen.getAllByRole('option').map((o) => o.textContent)

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('the pins and the recent pages (lib/recent)', () => {
  it('pins nav pages in the order they were pinned, and nothing else', () => {
    expect(loadPins()).toEqual([])
    togglePin('/phrases')
    togglePin('/map')
    togglePin('/') // the brand is the home page's link
    togglePin('/unit/v%3A0')
    togglePin('/nowhere')
    expect(loadPins()).toEqual(['/phrases', '/map'])
    togglePin('/phrases')
    expect(loadPins()).toEqual(['/map'])
    expect(JSON.parse(localStorage.getItem(PINS_KEY)!)).toEqual(['/map'])
  })

  it('keeps the pages opened last, the newest first, each once, capped', () => {
    const pages = NAV_PAGES.map((p) => p.to).filter(isNavPage)
    for (const to of pages.slice(0, MAX_RECENT_PAGES + 3)) visitPage(to)
    visitPage(pages[5])
    visitPage('/')
    visitPage('/unit/v%3A0')
    const recent = loadRecent().pages
    expect(recent).toHaveLength(MAX_RECENT_PAGES)
    expect(recent[0]).toBe(pages[5])
    expect(new Set(recent).size).toBe(recent.length)
  })

  it('keeps one entry per passage, in the view it was opened in last', () => {
    visitPassage({ to: '/unit/c%3A0%3A22', en: 'Genesis 22', he: 'בראשית כב' })
    visitPassage({ to: '/unit/c%3A1%3A3', en: 'Exodus 3', he: 'שמות ג' })
    visitPassage({ to: '/read/c%3A0%3A22', en: 'Genesis 22', he: 'בראשית כב' })
    expect(loadRecent().passages.map((p) => p.to)).toEqual(['/read/c%3A0%3A22', '/unit/c%3A1%3A3'])
    for (let i = 0; i < MAX_RECENT_PASSAGES + 4; i++) visitPassage({ to: `/unit/v%3A${i}`, en: `v ${i}`, he: `פ ${i}` })
    expect(loadRecent().passages).toHaveLength(MAX_RECENT_PASSAGES)
    expect(passageOf('/read/c%3A0%3A22')).toEqual({ view: 'read', id: 'c:0:22' })
    expect(passageOf('/unit/%E0%A4%A')).toBeUndefined()
    expect(passageOf('/phrases')).toBeUndefined()
  })

  it('reads whatever is stored without failing', () => {
    localStorage.setItem(PINS_KEY, '{not json')
    localStorage.setItem(RECENT_KEY, JSON.stringify({ pages: ['/map', 7, '/gone'], passages: [{ to: '/map', en: 'x', he: 'y' }, null, { to: '/unit/v%3A0', en: 'Genesis 1:1', he: 'בראשית א:א' }] }))
    expect(loadPins()).toEqual([])
    expect(loadRecent()).toEqual({ pages: ['/map'], passages: [{ to: '/unit/v%3A0', en: 'Genesis 1:1', he: 'בראשית א:א' }] })
    localStorage.setItem(PINS_KEY, JSON.stringify(['/map', '/map', '/unit/v%3A0', 3]))
    expect(loadPins()).toEqual(['/map'])
  })
})

describe('the pin button and the Pinned menu of the top bar', () => {
  it('pins the page on screen: the Pinned menu appears, first in the nav, with the page in it', async () => {
    const { container } = renderAt('/phrases')
    expect(screen.queryByRole('button', { name: /^Pinned/ })).toBeNull()
    const pin = screen.getByRole('button', { name: 'Pin Phrases' })
    expect(pin.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(pin)
    expect(pin.getAttribute('aria-pressed')).toBe('true')
    expect(loadPins()).toEqual(['/phrases'])
    const menu = screen.getByRole('button', { name: /^Pinned/ })
    expect(container.querySelector('#main-nav')?.firstElementChild?.contains(menu)).toBe(true)
    // from another page it is the menu and one click
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loc()).toBe('/search'))
    fireEvent.click(menu)
    fireEvent.click(within(container.querySelector('#menu-pinned')!).getByRole('link', { name: /Phrases/ }))
    await waitFor(() => expect(loc()).toBe('/phrases'))
    expect(menu.getAttribute('aria-expanded')).toBe('false')
    // the star takes the pin away, and the menu with its last page
    fireEvent.click(screen.getByRole('button', { name: 'Pin Phrases' }))
    expect(screen.queryByRole('button', { name: /^Pinned/ })).toBeNull()
    expect(loadPins()).toEqual([])
  })

  it('has no pin button on the home page or on a passage', async () => {
    renderAt('/')
    expect(screen.queryByRole('button', { name: /^Pin / })).toBeNull()
    cleanup()
    renderAt('/unit/c%3A0%3A22')
    await waitFor(() => expect(loadRecent().passages).toHaveLength(1))
    expect(screen.queryByRole('button', { name: /^Pin / })).toBeNull()
  })

  it('ends each menu with the link to every page', async () => {
    const { container } = renderAt('/')
    for (const id of ['menu-parallels', 'menu-patterns', 'menu-overview']) {
      const last = [...container.querySelectorAll(`#${id} a`)].at(-1)!
      expect(last.textContent, id).toBe('All pages')
      expect(last.getAttribute('href'), id).toBe('/pages')
    }
  })

  it('leaves your labels and notebook out of the Pinned menu where the server keeps nothing personal', async () => {
    localStorage.setItem(PINS_KEY, JSON.stringify(['/notebook', '/map']))
    const { container } = renderAt('/labels', { personal: false })
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Notebook' })).toBeNull())
    expect([...container.querySelectorAll('#menu-pinned li')].map((li) => li.textContent)).toEqual([expect.stringContaining('Map')])
    expect(screen.queryByRole('button', { name: /^Pin / })).toBeNull()
    // the pin itself is kept for the personal server
    expect(loadPins()).toEqual(['/notebook', '/map'])
  })

  it('speaks Hebrew', () => {
    localStorage.setItem(PINS_KEY, JSON.stringify(['/map']))
    renderAt('/phrases', { locale: 'he' })
    expect(screen.getByRole('button', { name: /^מוצמדים/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'הצמדת העמוד „צירופים”' })).toBeTruthy()
  })
})

describe('the visits Layout records', () => {
  it('records nav pages and, once its unit is known, a passage in its view', async () => {
    renderAt('/map')
    expect(loadRecent().pages).toEqual(['/map'])
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loadRecent().pages).toEqual(['/search', '/map']))
    cleanup()
    renderAt('/read/c%3A0%3A22')
    await waitFor(() => expect(loadRecent().passages).toEqual([{ to: '/read/c%3A0%3A22', en: 'Genesis 22', he: 'בראשית כב' }]))
    expect(loadRecent().pages).toEqual(['/search', '/map'])
  })

  it('does not record a verse opened in the reader (it is sent on to its chapter), or a passage that is not there', async () => {
    renderAt('/read/v%3A0')
    cleanup()
    renderAt('/unit/c%3A9%3A9')
    cleanup()
    renderAt('/unit/c%3A1%3A3')
    await waitFor(() => expect(loadRecent().passages.map((p) => p.to)).toEqual(['/unit/c%3A1%3A3']))
  })
})

describe('the jump box before anything is typed', () => {
  it('lists the pinned pages, the passages and pages opened last, and the index', async () => {
    togglePin('/phrases')
    visitPassage({ to: '/unit/c%3A1%3A3', en: 'Exodus 3', he: 'שמות ג' })
    visitPassage({ to: '/read/c%3A0%3A22', en: 'Genesis 22', he: 'בראשית כב' })
    visitPage('/phrases')
    visitPage('/map')
    renderAt('/search')
    openJump()
    const list = screen.getByRole('listbox')
    expect(within(list).getAllByRole('group').map((g) => g.firstElementChild?.textContent)).toEqual(['Pinned pages', 'Recent passages', 'Recent pages', 'Pages'])
    // a pinned page is not said again among the recent ones, nor the page on screen
    expect(options()).toEqual([
      expect.stringMatching(/^Phrases/),
      'Genesis 22in the reader',
      'Exodus 3',
      expect.stringMatching(/^Map/),
      'All pages',
    ])
    fireEvent.keyDown(box(), { key: 'ArrowDown' })
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/read/c%3A0%3A22'))
  })

  it('has the index alone on a first visit, and goes back to the list when the query is cleared', async () => {
    renderAt('/')
    openJump()
    expect(options()).toEqual(['All pages'])
    fireEvent.change(box(), { target: { value: 'netw' } })
    expect(await screen.findByRole('option', { name: /Network/ })).toBeTruthy()
    fireEvent.change(box(), { target: { value: '' } })
    expect(options()).toEqual(['All pages'])
    fireEvent.keyDown(box(), { key: 'Enter' })
    expect(await screen.findByRole('heading', { level: 1, name: 'All pages' })).toBeTruthy()
  })

  it('lists them in Hebrew', () => {
    visitPassage({ to: '/unit/c%3A1%3A3', en: 'Exodus 3', he: 'שמות ג' })
    renderAt('/search', { locale: 'he' })
    openJump()
    expect(options()).toEqual(['שמות ג', 'כל העמודים'])
    expect(screen.getByText('קטעים אחרונים')).toBeTruthy()
  })
})

describe('the jump box finds a book by the start of its name', () => {
  it('offers Genesis for "gen", ahead of the pages, and opens it', async () => {
    renderAt('/map')
    openJump()
    fireEvent.change(box(), { target: { value: 'gen' } })
    const genesis = await screen.findByRole('option', { name: /^Genesis/ })
    expect(genesis.textContent).toBe('Genesis\u2068בראשית\u2069 · 50 ch.')
    expect(options()[0]).toBe(genesis.textContent) // before "Family tree" (genealogy) and the search
    await waitFor(() => expect(genesis.getAttribute('aria-selected')).toBe('true'))
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/browse/0'))
  })

  it('matches a word of the name, the Hebrew name and the OSIS code', async () => {
    renderAt('/map')
    openJump()
    fireEvent.change(box(), { target: { value: 'sam' } })
    await screen.findByRole('option', { name: /^1 Samuel/ })
    expect(screen.getByRole('option', { name: /^2 Samuel/ })).toBeTruthy()
    fireEvent.change(box(), { target: { value: 'שמ' } })
    await screen.findByRole('option', { name: /^Exodus/ })
    expect(screen.getAllByRole('option', { name: /Samuel/ })).toHaveLength(2)
    fireEvent.change(box(), { target: { value: 'exod' } })
    await screen.findByRole('option', { name: /^Exodus/ })
    fireEvent.change(box(), { target: { value: 'g' } })
    await waitFor(() => expect(screen.queryByRole('option', { name: /^Genesis/ })).toBeNull())
  })

  it('names the books in Hebrew in the Hebrew interface', async () => {
    renderAt('/map', { locale: 'he' })
    openJump()
    fireEvent.change(box(), { target: { value: 'רות' } })
    const ruth = await screen.findByRole('option', { name: /^רות/ })
    expect(ruth.textContent).toBe('רות4 פר׳')
    expect(screen.getByText('ספרים')).toBeTruthy()
  })
})

describe('/pages: every page by menu', () => {
  const rows = (container: HTMLElement) => [...container.querySelectorAll('.pages-row .pages-link')].map((a) => a.textContent)

  it('lists every page of the nav under its menu and section, with its hint', () => {
    const { container } = renderAt('/pages')
    expect(screen.getByRole('heading', { level: 1, name: 'All pages' })).toBeTruthy()
    expect(rows(container)).toHaveLength(NAV_PAGES.length)
    expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual(['In the top bar', 'Parallels', 'Patterns', 'Overview'])
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(['Poetry and form', 'Words and names', 'Letters and numbers', 'Narrative'])
    const phrases = screen.getByRole('link', { name: 'Phrases' }).closest('li')!
    expect(phrases.textContent).toContain('Shared runs of words')
    expect(screen.getByText(`${NAV_PAGES.length} pages`)).toBeTruthy()
    // every page but the home page can be pinned
    expect(container.querySelectorAll('button.pages-star')).toHaveLength(NAV_PAGES.length - 1)
  })

  it('pins from a row: the page is listed under Pinned and in the bar’s menu', () => {
    const { container } = renderAt('/pages')
    fireEvent.click(screen.getByRole('button', { name: 'Pin Gematria' }))
    expect(loadPins()).toEqual(['/gematria'])
    expect(screen.getAllByRole('heading', { level: 2 })[0].textContent).toBe('Pinned')
    expect(screen.getAllByRole('button', { name: 'Pin Gematria' }).map((b) => b.getAttribute('aria-pressed'))).toEqual(['true', 'true'])
    expect(container.querySelector('#menu-pinned li')?.textContent).toContain('Gematria')
    fireEvent.click(screen.getAllByRole('button', { name: 'Pin Gematria' })[0])
    expect(loadPins()).toEqual([])
    expect(screen.getAllByRole('heading', { level: 2 })[0].textContent).toBe('In the top bar')
  })

  it('filters by name or hint, keeps the filter in the URL, and says when nothing matches', async () => {
    const { container } = renderAt('/pages?q=gematria')
    expect(rows(container)).toEqual(['Gematria', 'Equal values, related words?'])
    expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual(['Patterns'])
    expect(screen.getByText(`2 of ${NAV_PAGES.length} pages`)).toBeTruthy()
    const filter = screen.getByRole('searchbox', { name: 'Filter' })
    fireEvent.change(filter, { target: { value: 'zzz' } })
    expect(rows(container)).toEqual([])
    expect(screen.getByText(/No page matches “zzz”/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Show all' }))
    expect(rows(container)).toHaveLength(NAV_PAGES.length)
    fireEvent.change(filter, { target: { value: 'acrostic' } })
    expect(rows(container)).toEqual(['Acrostics'])
  })

  it('leaves out your labels and notebook where the server keeps nothing personal', async () => {
    const { container } = renderAt('/pages', { personal: false })
    await waitFor(() => expect(rows(container)).toHaveLength(NAV_PAGES.length - 2))
    expect(rows(container)).not.toContain('Notebook')
  })

  it('speaks Hebrew', () => {
    const { container } = renderAt('/pages?q=גימטריה', { locale: 'he' })
    expect(screen.getByRole('heading', { level: 1, name: 'כל העמודים' })).toBeTruthy()
    expect(rows(container)[0]).toBe('גימטריה')
    expect(screen.getByRole('button', { name: 'הצמדת העמוד „גימטריה”' })).toBeTruthy()
  })
})
