// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { LemmaLookup, PersonLookup, PersonMatch, PlaceLookup, PlaceMatch, ResolveResponse, UnitSummary } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { TextModeProvider } from '../context/TextMode'
import { Layout } from './Layout'

const GEN: UnitSummary = {
  unit_id: 'v:0',
  unit_type: 'verse',
  label_en: 'Genesis 1:1',
  label_he: 'בראשית א:א',
  book_id: 0,
  start_verse_id: 0,
  end_verse_id: 0,
  n_verses: 1,
  marker: null,
}

const place = (place_id: number, he: string, lemma: string, n_verses: number, exact = true): PlaceMatch => ({
  place_id,
  he,
  kind: 'town',
  lat: 31.5,
  lon: 35.1,
  score: 900,
  coord_source: 'openbible',
  runner_up: null,
  n_identifications: 1,
  n_verses,
  n_here: null,
  first_vid: 300,
  lemmas: [lemma],
  exact,
  first_label: 'Genesis 13:18',
  first_label_he: 'בראשית יג:יח',
})
// חברון the town and its name; עין the town, and עין the eye, commoner
const PLACES: Record<string, PlaceMatch[]> = { חברון: [place(31, 'חברון', '2275', 54)], עין: [place(80, 'עין', '5871', 5)] }
// יפתח: Jephthah son of Gilead
const person = (person_id: number, of_he: string | null, first_label: string, first_label_he: string): PersonMatch => ({
  person_id,
  he: 'יפתח',
  sex: 'm',
  kind: 'person',
  placement: 'tree',
  first_vid: 600,
  n_verses: 25,
  exact: true,
  relation: of_he ? 'child' : null,
  of_he,
  first_label,
  first_label_he,
})
const PEOPLE: Record<string, PersonMatch[]> = { יפתח: [person(1700, 'גלעד', 'Judges 11:1', 'שופטים יא:א')] }
const LEMMAS: Record<string, LemmaLookup['items']> = {
  שלום: [{ lemma: '7965', he_lemma: 'שלום', n_verses: 209 }],
  חברון: [{ lemma: '2275', he_lemma: 'חברון', n_verses: 62 }],
  עין: [
    { lemma: '5869', he_lemma: 'עין', n_verses: 800 },
    { lemma: '5871', he_lemma: 'עין', n_verses: 5 },
  ],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en') {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const q = u.searchParams.get('q') ?? ''
      const body: ResolveResponse | LemmaLookup | PlaceLookup | PersonLookup | null =
        u.pathname === '/api/resolve'
          ? { query: q, unit: /^(gen 1:1|בראשית א א)$/i.test(q) ? GEN : null }
          : u.pathname === '/api/lemmas'
            ? { query: q, items: LEMMAS[q] ?? [] }
            : u.pathname === '/api/places/lookup'
              ? { query: q, items: PLACES[q] ?? [] }
              : u.pathname === '/api/genealogy/lookup'
                ? { query: q, items: PEOPLE[q] ?? [] }
                : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <TextModeProvider>
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route element={<Layout />}>
                <Route path="*" element={<Location />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </TextModeProvider>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return calls
}

const box = () => screen.getByRole('combobox', { name: /Jump to a passage|מעבר אל קטע/ })
const loc = () => screen.getByTestId('loc').textContent

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('JumpBox', () => {
  it('opens on Ctrl+K and goes to the passage a reference names', async () => {
    renderAt('/map')
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(document.activeElement).toBe(box())
    fireEvent.change(box(), { target: { value: 'Gen 1:1' } })
    const option = await screen.findByRole('option', { name: 'Genesis 1:1' })
    expect(option.getAttribute('aria-selected')).toBe('true')
    expect(box().getAttribute('aria-activedescendant')).toBe(option.id)
    // the text search is always the last choice
    expect(screen.getAllByRole('option').at(-1)?.textContent).toBe('Search the text for “Gen 1:1”')
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/unit/v%3A0'))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('finds words and pages, moves with the arrows and closes on Escape', async () => {
    renderAt('/')
    const opener = screen.getByRole('button', { name: /Jump to/ })
    opener.focus() // a click focuses the button in a browser, not in jsdom
    fireEvent.click(opener)
    fireEvent.change(box(), { target: { value: 'שלום' } })
    expect(await screen.findByRole('option', { name: /שלום.*7965 · 209 verses/ })).toBeTruthy()
    fireEvent.change(box(), { target: { value: 'netw' } })
    const page = await screen.findByRole('option', { name: /Network/ })
    expect(page.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(box(), { key: 'ArrowDown' })
    expect(screen.getByRole('option', { name: /Search the text/ }).getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(box(), { key: 'ArrowDown' }) // wraps around
    expect(page.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(box(), { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(opener)
    expect(loc()).toBe('/')
  })

  it('opens the letter value of `= …`', async () => {
    renderAt('/')
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
    fireEvent.change(box(), { target: { value: '= 318' } })
    const option = await screen.findByRole('option', { name: 'Letter value: 318' })
    expect(option.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/gematria?q=318'))
  })

  it('opens the map at a place its name names, before the words', async () => {
    renderAt('/')
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
    fireEvent.change(box(), { target: { value: 'חברון' } })
    const option = await screen.findByRole('option', { name: /חברון.*Town · 54 verses · first in Genesis 13:18/ })
    expect(option.getAttribute('aria-selected')).toBe('true')
    const groups = screen.getAllByRole('group').map((g) => g.getAttribute('aria-labelledby'))
    expect(groups.map((id) => document.getElementById(id!)?.textContent)).toEqual(['Places on the map', 'Words', 'Search the text'])
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/places?p=31'))
  })

  it('puts a commoner word before a place of the same name', async () => {
    renderAt('/')
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
    fireEvent.change(box(), { target: { value: 'עין' } })
    await screen.findByRole('option', { name: /עין.*Town/ })
    expect(screen.getAllByRole('option')[0].textContent).toContain('5869 · 800 verses')
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/lemma/5869'))
  })

  it('opens the place at once when Enter beats the typing pause', async () => {
    renderAt('/')
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
    fireEvent.change(box(), { target: { value: 'חברון' } })
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/places?p=31'))
  })

  it('looks the query up at once when Enter beats the typing pause', async () => {
    const calls = renderAt('/')
    fireEvent.keyDown(document, { key: 'K', metaKey: true })
    fireEvent.change(box(), { target: { value: 'nothing at all' } })
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/search?q=nothing%20at%20all'))
    expect(calls.some((c) => c.startsWith('/api/resolve?q=nothing'))).toBe(true)
  })

  it('opens the family tree at a person, told apart by parent and first verse', async () => {
    renderAt('/')
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
    fireEvent.change(box(), { target: { value: 'יפתח' } })
    const option = await screen.findByRole('option', { name: /יפתח.*son of גלעד · first in Judges 11:1/ })
    const groups = screen.getAllByRole('group').map((g) => g.getAttribute('aria-labelledby'))
    expect(groups.map((id) => document.getElementById(id!)?.textContent)).toEqual(['People in the family tree', 'Search the text'])
    expect(option.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(box(), { key: 'Enter' })
    await waitFor(() => expect(loc()).toBe('/genealogy?p=1700'))
  })

  it('works in Hebrew', async () => {
    renderAt('/', 'he')
    fireEvent.click(screen.getByRole('button', { name: /מעבר אל/ }))
    fireEvent.change(box(), { target: { value: 'בראשית א א' } })
    fireEvent.click(await screen.findByRole('option', { name: 'בראשית א:א' }))
    await waitFor(() => expect(loc()).toBe('/unit/v%3A0'))
    fireEvent.click(screen.getByRole('button', { name: /מעבר אל/ }))
    fireEvent.change(box(), { target: { value: 'חברון' } })
    expect(await screen.findByRole('option', { name: /חברון.*עיר · 54 פסוקים · לראשונה ב־בראשית יג:יח/ })).toBeTruthy()
    expect(screen.getByText('מקומות במפה')).toBeTruthy()
    fireEvent.change(box(), { target: { value: 'יפתח' } })
    expect(await screen.findByRole('option', { name: /יפתח.*לראשונה ב.*שופטים יא:א/ })).toBeTruthy()
    expect(screen.getByText('אנשים באילן היוחסין')).toBeTruthy()
  })
})
