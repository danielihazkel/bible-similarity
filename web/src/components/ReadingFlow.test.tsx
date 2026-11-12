// @vitest-environment jsdom
// M171: the reading flow: Back keeps your place, an address's hash, Read and copy on a hit, a search
// result's actions
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Hit, NotebookEntry, SearchResponse, UnitSummary, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { TextModeProvider } from '../context/TextMode'
import { resetScrollMemory, SCROLL_KEY } from '../lib/scroll'
import { useQueryParams } from '../lib/urlState'
import { SearchPage } from '../pages/SearchPage'
import { CopyButton, CopyPassage } from './CopyButton'
import { HitCard } from './HitCard'
import { Layout } from './Layout'

const VERSE: Verse = {
  verse_id: 569,
  book_id: 0,
  chapter: 22,
  verse: 2,
  ref: 'Genesis 22:2',
  ref_he: 'בראשית כב:ב',
  text_display: 'וַיֹּ֡אמֶר קַח־נָ֠א',
  display_tokens: ['וַיֹּ֡אמֶר', 'קַח־', 'נָ֠א'],
  ketiv_note: null,
}
const unit = (unit_id: string, unit_type: UnitSummary['unit_type'], label_en: string, label_he: string): UnitSummary => ({
  unit_id,
  unit_type,
  label_en,
  label_he,
  book_id: 0,
  start_verse_id: 569,
  end_verse_id: 569,
  n_verses: 1,
  marker: null,
})

// a window that scrolls: jsdom has neither a layout nor `scrollTo`
let y = 0
let height = 5000
const written: string[] = []
beforeEach(() => {
  y = 0
  height = 5000
  written.length = 0
  Object.defineProperty(window, 'scrollY', { configurable: true, get: () => y })
  Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, get: () => height })
  window.scrollTo = vi.fn((_x: number, top: number) => {
    y = top
    window.dispatchEvent(new Event('scroll'))
  }) as unknown as typeof window.scrollTo
  Element.prototype.scrollIntoView = vi.fn()
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn(async (s: string) => void written.push(s)) } })
  sessionStorage.clear()
  localStorage.clear()
  resetScrollMemory()
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const scrollBy = (top: number) => {
  y = top
  window.dispatchEvent(new Event('scroll'))
}

function Page() {
  const l = useLocation()
  const navigate = useNavigate()
  const [, update] = useQueryParams()
  return (
    <div>
      <output data-testid="loc">{l.pathname + l.search + l.hash}</output>
      <button type="button" onClick={() => navigate(-1)}>
        back
      </button>
      <button type="button" onClick={() => update({ pin: '1' })}>
        toggle
      </button>
      <button type="button" onClick={() => update({ page: '2' }, false)}>
        next page
      </button>
      <p id="spot">here</p>
    </div>
  )
}

type Api = (url: string, init?: RequestInit) => Promise<Response>
const nothing: Api = async () => new Response(JSON.stringify({ detail: 'nope' }), { status: 404 })

function inApp(ui: ReactNode, path: string, locale: 'en' | 'he' = 'en', api: Api = nothing) {
  vi.stubGlobal('fetch', vi.fn(api))
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <LocaleProvider initial={locale}>
        <TextModeProvider>
          <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
        </TextModeProvider>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}
const app = (path: string) =>
  inApp(
    <Routes>
      <Route element={<Layout />}>
        <Route path="*" element={<Page />} />
      </Route>
    </Routes>,
    path,
  )
const loc = () => screen.getByTestId('loc').textContent
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }))

describe('where a navigation leaves the window', () => {
  it('starts a new page at the top, and Back returns to where the page was left', async () => {
    app('/phrases')
    scrollBy(700)
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loc()).toBe('/search'))
    expect(window.scrollTo).toHaveBeenLastCalledWith(0, 0)
    expect(y).toBe(0)
    click('back')
    await waitFor(() => expect(loc()).toBe('/phrases'))
    await waitFor(() => expect(y).toBe(700))
  })

  it('waits for the page to be as tall as it was', async () => {
    app('/phrases')
    scrollBy(700)
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loc()).toBe('/search'))
    height = 900 // the list is not back yet: the window cannot go further than 132px
    click('back')
    await waitFor(() => expect(loc()).toBe('/phrases'))
    await waitFor(() => expect(y).toBe(900 - window.innerHeight))
    height = 5000
    await waitFor(() => expect(y).toBe(700))
  })

  it('gives up the wait when the viewer scrolls first', async () => {
    app('/phrases')
    scrollBy(700)
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loc()).toBe('/search'))
    height = 900
    click('back')
    await waitFor(() => expect(y).toBe(900 - window.innerHeight))
    window.dispatchEvent(new Event('wheel'))
    height = 5000
    await new Promise((r) => setTimeout(r, 80))
    expect(y).toBe(900 - window.innerHeight)
  })

  it('keeps the place through a toggle on the page, and a new page of a list keeps the one before it', async () => {
    app('/phrases')
    scrollBy(700)
    click('toggle') // the entry is replaced: its place goes with it
    await waitFor(() => expect(loc()).toBe('/phrases?pin=1'))
    click('next page')
    await waitFor(() => expect(loc()).toBe('/phrases?pin=1&page=2'))
    expect(window.scrollTo).not.toHaveBeenCalled() // the same page: no jump to the top
    scrollBy(120)
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loc()).toBe('/search'))
    click('back')
    await waitFor(() => expect(y).toBe(120))
    click('back')
    await waitFor(() => expect(loc()).toBe('/phrases?pin=1'))
    await waitFor(() => expect(y).toBe(700))
  })

  it('returns to the top of an entry that was left at its top', async () => {
    app('/phrases')
    fireEvent.click(screen.getByRole('link', { name: 'Search' }))
    await waitFor(() => expect(loc()).toBe('/search'))
    scrollBy(400)
    click('back')
    await waitFor(() => expect(loc()).toBe('/phrases'))
    expect(y).toBe(0)
  })

  it('keeps the place over a reload, by the address', async () => {
    sessionStorage.setItem(SCROLL_KEY, JSON.stringify([['default', 420, '/phrases']]))
    app('/phrases')
    await waitFor(() => expect(y).toBe(420))
    cleanup()
    // the first entry of another load has the same key: its place is not this page's
    y = 0
    resetScrollMemory()
    app('/map')
    await new Promise((r) => setTimeout(r, 50))
    expect(y).toBe(0)
  })

  it('brings the element a hash names into view, and a query change keeps the hash', async () => {
    app('/phrases#spot')
    await waitFor(() => expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ block: 'center' }))
    expect(vi.mocked(Element.prototype.scrollIntoView).mock.instances[0]).toBe(document.getElementById('spot'))
    expect(window.scrollTo).not.toHaveBeenCalled()
    click('toggle')
    await waitFor(() => expect(loc()).toBe('/phrases?pin=1#spot'))
  })
})

describe('copying', () => {
  it('copies a text and says so', async () => {
    inApp(<CopyButton text={() => 'the text'} label="Copy it" />, '/')
    click('Copy it')
    await screen.findByRole('button', { name: 'Copied' })
    expect(written).toEqual(['the text'])
  })

  it('copies a passage’s reference in the interface language, and its text as the text display shows it', async () => {
    inApp(<CopyPassage en="Genesis 22:2" he="בראשית כב:ב" verses={[VERSE, { ...VERSE, display_tokens: ['שֵׁנִי'] }]} />, '/')
    click('Copy reference')
    click('Copy text')
    await waitFor(() => expect(written).toHaveLength(2))
    expect(written).toEqual(['Genesis 22:2', 'וַיֹּ֡אמֶר קַח־נָ֠א\nשֵׁנִי'])
    cleanup()
    written.length = 0
    localStorage.setItem('bsim.textMode', 'consonants')
    inApp(<CopyPassage en="Genesis 22:2" he="בראשית כב:ב" verses={[VERSE]} />, '/', 'he')
    click('העתקת ההפניה')
    click('העתקת הטקסט')
    await waitFor(() => expect(written).toHaveLength(2))
    expect(written).toEqual(['בראשית כב:ב', 'ויאמר קח־נא'])
  })

  it('offers the reference alone where the verses are not at hand', () => {
    inApp(<CopyPassage en="Genesis 22" he="בראשית כב" />, '/')
    expect(screen.getByRole('button', { name: 'Copy reference' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Copy text' })).toBeNull()
  })
})

describe('a hit card', () => {
  const hit = (u: UnitSummary, verse: Verse | null): Hit =>
    ({ rank: 1, score: 0.5, lex_score: 1, lex_rank: 1, sem_score: null, sem_rank: null, phr_score: null, phr_rank: null, unit: u, verse, preview: verse ? null : 'ויהי', link: null, phrase: null }) as unknown as Hit

  it('reads a verse in the reader and copies its reference and text', async () => {
    inApp(
      <ol>
        <HitCard hit={hit(unit('v:569', 'verse', 'Genesis 22:2', 'בראשית כב:ב'), VERSE)} mode="lexical" source={unit('v:0', 'verse', 'Genesis 1:1', 'בראשית א:א')} />
      </ol>,
      '/',
    )
    const card = within(screen.getByRole('listitem'))
    expect(card.getByRole('link', { name: 'Read' }).getAttribute('href')).toBe('/read/v%3A569')
    fireEvent.click(card.getByRole('button', { name: 'Copy reference' }))
    fireEvent.click(card.getByRole('button', { name: 'Copy text' }))
    await waitFor(() => expect(written).toEqual(['Genesis 22:2', 'וַיֹּ֡אמֶר קַח־נָ֠א']))
  })

  it('offers a chapter its reference alone', () => {
    inApp(
      <ol>
        <HitCard hit={hit(unit('c:0:22', 'chapter', 'Genesis 22', 'בראשית כב'), null)} mode="lexical" source={unit('c:0:1', 'chapter', 'Genesis 1', 'בראשית א')} />
      </ol>,
      '/',
    )
    expect(screen.getByRole('link', { name: 'Read' }).getAttribute('href')).toBe('/read/c%3A0%3A22')
    expect(screen.getByRole('button', { name: 'Copy reference' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Copy text' })).toBeNull()
  })
})

describe('a search result’s actions', () => {
  const SEARCH = {
    book: null,
    query: 'קח',
    normalized: 'קח',
    tokens: ['קח'],
    mode: 'lexical',
    k: 10,
    hits: [{ rank: 1, score: 3, lex_score: 3, lex_rank: 1, sem_score: null, sem_rank: null, phr_score: null, phr_rank: null, verse: VERSE, label_en: 'Genesis 22:2', label_he: 'בראשית כב:ב' }],
  } as unknown as SearchResponse

  function search({ personal = true, writable = true, kept = false } = {}) {
    const entries: NotebookEntry[] = kept ? [{ unit: unit('v:569', 'verse', 'Genesis 22:2', 'בראשית כב:ב'), note: '', collections: [], created_at: '', updated_at: '', verse: null }] : []
    const sent: string[] = []
    const view = inApp(
      <Routes>
        <Route path="/search" element={<SearchPage />} />
      </Routes>,
      '/search?q=%D7%A7%D7%97&mode=lexical',
      'en',
      async (url: string, init?: RequestInit) => {
        const p = new URL(url, 'http://x').pathname
        if (init?.method === 'PUT') {
          sent.push(`PUT ${p}`)
          entries.push({ unit: unit('v:569', 'verse', 'Genesis 22:2', 'בראשית כב:ב'), note: '', collections: [], created_at: '', updated_at: '', verse: null })
          return new Response(JSON.stringify(entries[0]), { status: 200 })
        }
        const body: unknown =
          p === '/api/search'
            ? SEARCH
            : p === '/api/meta'
              ? { runtime: { personal, encoder_on: false } }
              : p === '/api/notebook'
                ? { writable, entries, collections: [], hidden: 0 }
                : p === '/api/books'
                  ? []
                  : p === '/api/resolve'
                    ? { query: 'קח', unit: null }
                    : null
        return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
      },
    )
    return { ...view, sent }
  }

  it('reads the verse in the reader, keeps it in the notebook with one click, and copies it', async () => {
    const { sent } = search()
    const row = within(await screen.findByRole('listitem'))
    expect(row.getByRole('link', { name: 'Read' }).getAttribute('href')).toBe('/read/v%3A569')
    fireEvent.click(await row.findByRole('button', { name: /Keep in notebook/ }))
    const kept = await row.findByRole('link', { name: /In your notebook/ })
    expect(kept.getAttribute('href')).toBe('/unit/v%3A569')
    expect(sent).toEqual(['PUT /api/notebook/entries/v%3A569'])
    expect(row.queryByRole('button', { name: /Keep in notebook/ })).toBeNull()
    fireEvent.click(row.getByRole('button', { name: 'Copy text' }))
    await waitFor(() => expect(written).toEqual(['וַיֹּ֡אמֶר קַח־נָ֠א']))
  })

  it('has no keep button without a notebook, or on a read-only one that does not hold the verse', async () => {
    search({ personal: false })
    const row = within(await screen.findByRole('listitem'))
    expect(row.getByRole('link', { name: 'Read' })).toBeTruthy()
    await new Promise((r) => setTimeout(r, 30))
    expect(row.queryByRole('button', { name: /Keep in notebook/ })).toBeNull()
    cleanup()
    search({ writable: false })
    await screen.findByRole('listitem')
    await new Promise((r) => setTimeout(r, 30))
    expect(screen.queryByRole('button', { name: /Keep in notebook/ })).toBeNull()
    cleanup()
    search({ writable: false, kept: true })
    expect(await screen.findByRole('link', { name: /In your notebook/ })).toBeTruthy()
  })
})
