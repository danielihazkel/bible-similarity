// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, CheckResponse, ContrastResponse, NotebookResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { WorkbenchPage } from './WorkbenchPage'

const BOOKS: Book[] = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 26, name: 'Psalms', he_name: 'תהלים', osis: 'Ps', section: 'Writings', n_chapters: 150 },
]
const NOTEBOOK: NotebookResponse = {
  writable: true,
  hidden: 0,
  entries: [],
  collections: [{ collection_id: 3, name: 'Laments', description: '', created_at: 't', updated_at: 't', n_entries: 2 }],
}
const row = (key: string, label: string | null, a: number, b: number, logRatio: number, q: number) => ({
  key,
  label,
  a,
  b,
  rate_a: a / 5.879,
  rate_b: b / 12.6,
  log_ratio: logRatio,
  g2: 222.31,
  p: q / 10,
  q,
  examples: [{ verse_id: 15000, label: 'Psalms 42:2', label_he: 'תהלים מב:ב' }],
})
const CONTRAST: ContrastResponse = {
  feature: 'lemma',
  error: null,
  a: { spec: 'chapters:26:42-83', verses: 740, words: 5879, books: [26], filtered: false },
  b: { spec: 'book:26', verses: 1787, words: 12600, books: [26], filtered: false },
  overlap: 5879,
  total_a: 5879,
  total_b: 12600,
  tested: 671,
  min_count: 5,
  alpha: 0.05,
  significant_a: 7,
  significant_b: 20,
  over_a: [row('430', 'אלהים', 245, 117, 2.17, 9.6e-48), row('5542', 'סלה', 39, 32, 1.2, 0.0014)],
  over_b: [row('3068', 'יהוה', 40, 647, -2.9, 1.2e-55)],
}
const CHECK: CheckResponse = {
  q: '[lemma=430]',
  within: 'book',
  draws: 999,
  error: null,
  pattern_error: null,
  set: { spec: 'chapters:26:42-83', verses: 740, words: 5879, books: [26], filtered: false },
  testable: true,
  matches: 245,
  words: 5879,
  rate: 41.67,
  rest_matches: 117,
  rest_words: 12600,
  rest_rate: 9.29,
  null_mean: 18.5,
  null_low: 15.2,
  null_high: 21.9,
  p_high: 0.001,
  p_low: 1,
  groups: 1,
  fixed_verses: 0,
  books: [{ book_id: 26, matches: 245, words: 5879 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{decodeURIComponent(l.search.replaceAll('+', ' '))}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', bodies: Record<string, unknown> = {}) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const routes: Record<string, unknown> = {
        '/api/books': BOOKS,
        '/api/notebook': NOTEBOOK,
        '/api/workbench/contrast': CONTRAST,
        '/api/workbench/check': CHECK,
        ...bodies,
      }
      const body = routes[u.pathname]
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/workbench" element={<WorkbenchPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { ...r, calls }
}

const loc = () => screen.getByTestId('loc').textContent ?? ''

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('WorkbenchPage: contrast', () => {
  it('asks for set A before it asks the server', () => {
    const { calls } = renderAt('/workbench')
    expect(screen.getByText(/Build set A to begin/)).toBeTruthy()
    expect(calls.some((c) => c.includes('/workbench/'))).toBe(false)
  })

  it('shows both sets as chips and the values commoner on each side', async () => {
    const { calls } = renderAt('/workbench?a=chapters:26:42-83&b=book:26')
    expect(await screen.findByText('Psalms 42–83')).toBeTruthy()
    const call = calls.find((c) => c.includes('/workbench/contrast'))!
    const u = new URL(call, 'http://x')
    expect([u.searchParams.get('a'), u.searchParams.get('b'), u.searchParams.get('feature')]).toEqual(['chapters:26:42-83', 'book:26', 'lemma'])
    const a = await screen.findByRole('region', { name: 'Commoner in A' })
    const elohim = within(a).getByRole('link', { name: 'אלהים' })
    expect(elohim.getAttribute('href')).toBe('/lemma/430')
    expect(within(a).getAllByRole('link', { name: 'Search' })[0].getAttribute('href')).toBe(`/query?q=${encodeURIComponent('[lemma=430]')}`)
    expect(within(a).getByText('×4.5')).toBeTruthy()
    expect(within(a).getByText('9.6e-48')).toBeTruthy()
    expect(within(a).getAllByRole('link', { name: 'Psalms 42:2' })[0].getAttribute('href')).toBe('/unit/v%3A15000')
    const b = screen.getByRole('region', { name: 'Commoner in B' })
    expect(within(b).getByRole('link', { name: 'יהוה' })).toBeTruthy()
    expect(within(b).getByText('×7.46')).toBeTruthy() // B's side shows B over A
    expect(screen.getByText(/671 values scored; 7 commoner in A and 20 commoner in B/)).toBeTruthy()
    expect(screen.getByText(/5,879 words are in both sets/)).toBeTruthy()
  })

  it('adds and removes items, and switches the feature, through the URL', async () => {
    renderAt('/workbench?a=book:0')
    const setA = (await screen.findAllByRole('group', { name: 'Set A' }))[0]
    await waitFor(() => expect(within(setA).getByRole('list').textContent).toContain('Genesis'))
    const add = within(setA).getByRole('form', { name: 'Add to the set: Set A' })
    fireEvent.change(within(add).getByLabelText('Add to the set'), { target: { value: 'section' } })
    fireEvent.change(within(add).getByLabelText('A section'), { target: { value: 'prophets' } })
    fireEvent.click(within(add).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(loc()).toContain('a=book:0; section:prophets'))
    fireEvent.change(within(add).getByLabelText('Add to the set'), { target: { value: 'collection' } })
    await within(add).findByRole('option', { name: 'Laments' })
    fireEvent.click(within(add).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(loc()).toContain('a=book:0; section:prophets; collection:3'))
    expect(await within(setA).findByText('Collection “Laments”')).toBeTruthy()
    fireEvent.click(within(setA).getByRole('button', { name: 'Remove book:0' }))
    await waitFor(() => expect(loc()).toContain('a=section:prophets; collection:3'))
    fireEvent.change(screen.getByLabelText('Compare by'), { target: { value: 'domain' } })
    await waitFor(() => expect(loc()).toContain('feature=domain'))
  })

  it('refuses chapters that run backwards and writes ranges', async () => {
    renderAt('/workbench')
    const setA = (await screen.findAllByRole('group', { name: 'Set A' }))[0]
    const add = within(setA).getByRole('form', { name: 'Add to the set: Set A' })
    fireEvent.change(within(add).getByLabelText('Add to the set'), { target: { value: 'chapters' } })
    await within(add).findByRole('option', { name: 'Psalms' })
    fireEvent.change(within(add).getByLabelText('Book'), { target: { value: '26' } })
    fireEvent.change(within(add).getByLabelText('From chapter'), { target: { value: '83' } })
    fireEvent.change(within(add).getByLabelText('to chapter'), { target: { value: '42' } })
    expect((within(add).getByRole('button', { name: 'Add' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(within(add).getByLabelText('From chapter'), { target: { value: '42' } })
    fireEvent.change(within(add).getByLabelText('to chapter'), { target: { value: '83' } })
    fireEvent.click(within(add).getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(loc()).toContain('a=chapters:26:42-83'))
  })

  it("names the set and item at fault, and a pattern item's own problem", async () => {
    const bad: ContrastResponse = {
      ...CONTRAST,
      error: { set: 'b', code: 'pattern', item: 0, token: '[lemma=430', pattern: { code: 'unclosed', at: 0, token: '[lemma=430' } },
      a: null,
      b: null,
      over_a: [],
      over_b: [],
    }
    renderAt('/workbench?a=book:0&b=pattern:[lemma=430', 'en', { '/api/workbench/contrast': bad })
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('Set B: The pattern “[lemma=430” cannot run.')
    expect(alert.textContent).toContain('This bracket is not closed')
  })
})

describe('WorkbenchPage: check', () => {
  it('checks a pattern on a set and reads the verdict', async () => {
    const { calls } = renderAt('/workbench?tab=check&q=[lemma=430]&set=chapters:26:42-83')
    expect(await screen.findByText('Denser than chance: p = 0.001.')).toBeTruthy()
    expect(screen.getByText(/245 matches in the set's 740 verses \(5,879 words\): 41.7 per 1,000 words/)).toBeTruthy()
    expect(screen.getByText(/drawn again at random within each book, 999 times: 18.5 per 1,000/)).toBeTruthy()
    const call = new URL(calls.find((c) => c.includes('/workbench/check'))!, 'http://x')
    expect(call.searchParams.get('within')).toBe('book')
    fireEvent.click(screen.getByRole('radio', { name: 'each chapter' }))
    await waitFor(() => expect(loc()).toContain('within=chapter'))
  })

  it('says when there is nothing to draw against', async () => {
    renderAt('/workbench?tab=check&q=[lemma=430]&set=book:26', 'en', {
      '/api/workbench/check': { ...CHECK, testable: false, groups: 0, fixed_verses: 2527 },
    })
    expect(await screen.findByText(/nothing to draw it against/)).toBeTruthy()
  })

  it('shows the query problem from pattern search', async () => {
    renderAt('/workbench?tab=check&q=[colour=red]&set=book:26', 'en', {
      '/api/workbench/check': { ...CHECK, pattern_error: { code: 'unknown_key', at: 1, token: 'colour' } },
    })
    expect((await screen.findByRole('alert')).textContent).toContain('There is no key “colour”')
  })
})

describe('WorkbenchPage in Hebrew', () => {
  it('runs in the Hebrew interface', async () => {
    renderAt('/workbench?a=chapters:26:42-83', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('שולחן עבודה')
    expect(await screen.findByText('תהלים 42–83')).toBeTruthy()
    expect(await screen.findByRole('region', { name: 'שכיח יותר ב־א' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'בדיקת תבנית' })).toBeTruthy()
  })
})
