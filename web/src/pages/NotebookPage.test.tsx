// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NotebookCollection, NotebookEntry, NotebookResponse, UnitSummary, Verse } from '../api/types'
import { NotebookPanel } from '../components/NotebookPanel'
import { Toaster } from '../components/Toaster'
import { LocaleProvider } from '../context/Locale'
import { clearToasts } from '../lib/toast'
import { filterEntries, notebookMarkdown } from '../lib/notebook'
import { NotebookPage } from './NotebookPage'

const unit = (id: string, type: UnitSummary['unit_type'], en: string, he: string, start: number): UnitSummary => ({
  unit_id: id,
  unit_type: type,
  label_en: en,
  label_he: he,
  book_id: 0,
  start_verse_id: start,
  end_verse_id: start,
  n_verses: 1,
  marker: null,
})
const UNITS: Record<string, UnitSummary> = {
  'c:0:1': unit('c:0:1', 'chapter', 'Genesis 1', 'בראשית א', 0),
  'v:0': unit('v:0', 'verse', 'Genesis 1:1', 'בראשית א:א', 0),
  'v:27': unit('v:27', 'verse', 'Genesis 1:28', 'בראשית א:כח', 27),
}
const verse = (id: number, text: string): Verse => ({
  verse_id: id,
  book_id: 0,
  chapter: 1,
  verse: id + 1,
  ref: `Genesis 1:${id + 1}`,
  ref_he: 'בראשית',
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})

/** The notebook API, in memory: what the tests change, the page reads back. */
function fakeServer(writable = true) {
  const entries = new Map<string, { note: string; collections: number[] }>()
  const cols = new Map<number, { name: string; description: string }>()
  let next = 1
  const entry = (id: string): NotebookEntry => ({
    unit: UNITS[id],
    note: entries.get(id)!.note,
    collections: entries.get(id)!.collections,
    created_at: '2026-10-13T00:00:00+00:00',
    updated_at: '2026-10-13T00:00:00+00:00',
    verse: UNITS[id].unit_type === 'verse' ? verse(UNITS[id].start_verse_id, 'בְּרֵאשִׁית בָּרָא') : null,
  })
  const collection = (id: number): NotebookCollection => ({
    collection_id: id,
    ...cols.get(id)!,
    n_entries: [...entries.values()].filter((e) => e.collections.includes(id)).length,
    created_at: '',
    updated_at: '',
  })
  const json = (body: unknown, status = 200) => new Response(body === null ? null : JSON.stringify(body), { status })
  const calls: string[] = []
  // while on, every change is refused
  const failing = { on: false }
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const path = decodeURIComponent(new URL(url, 'http://x').pathname)
    calls.push(`${method} ${path}`)
    if (failing.on && method !== 'GET') return json({ detail: 'disk full' }, 500)
    const body = init?.body ? JSON.parse(String(init.body)) : {}
    let m: RegExpMatchArray | null
    if (path === '/api/notebook' && method === 'GET') {
      const order = [...entries.keys()].sort((a, b) => UNITS[a].start_verse_id - UNITS[b].start_verse_id || (UNITS[a].unit_type === 'chapter' ? -1 : 1))
      const res: NotebookResponse = { writable, entries: order.map(entry), collections: [...cols.keys()].map(collection), hidden: 0 }
      return json(res)
    }
    if ((m = path.match(/^\/api\/notebook\/entries\/(.+)$/))) {
      if (method === 'PUT') {
        const old = entries.get(m[1])
        entries.set(m[1], { note: body.note ?? old?.note ?? '', collections: old?.collections ?? [] })
        return json(entry(m[1]))
      }
      entries.delete(m[1])
      return json(null, 204)
    }
    if (path === '/api/notebook/collections' && method === 'POST') {
      if ([...cols.values()].some((c) => c.name === body.name)) return json({ detail: 'exists' }, 409)
      cols.set(next, { name: body.name, description: body.description })
      return json(collection(next++), 201)
    }
    if ((m = path.match(/^\/api\/notebook\/collections\/(\d+)\/entries\/(.+)$/))) {
      const id = Number(m[1])
      const old = entries.get(m[2]) ?? { note: '', collections: [] }
      entries.set(m[2], { ...old, collections: method === 'PUT' ? [...new Set([...old.collections, id])] : old.collections.filter((c) => c !== id) })
      return method === 'PUT' ? json(entry(m[2])) : json(null, 204)
    }
    if ((m = path.match(/^\/api\/notebook\/collections\/(\d+)$/))) {
      const id = Number(m[1])
      if (method === 'DELETE') {
        cols.delete(id)
        for (const e of entries.values()) e.collections = e.collections.filter((c) => c !== id)
        return json(null, 204)
      }
      cols.set(id, { name: body.name, description: body.description })
      return json(collection(id))
    }
    return json({ detail: 'nope' }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { entries, cols, calls, failing }
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
            <Route path="/notebook" element={<NotebookPage />} />
            <Route path="/unit/:unitId" element={<UnitPanel />} />
          </Routes>
          <Location />
        </MemoryRouter>
        <Toaster />
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

function UnitPanel() {
  return <NotebookPanel unitId={useLocation().pathname.split('/').pop()!} />
}

afterEach(() => {
  cleanup()
  clearToasts()
  vi.unstubAllGlobals()
})

describe('NotebookPanel', () => {
  it('keeps a unit, saves a note, puts it in a new collection and removes it again', async () => {
    const s = fakeServer()
    renderAt('/unit/v:0')
    fireEvent.click(await screen.findByRole('button', { name: /Keep in notebook/ }))
    expect(await screen.findByText('In your notebook')).toBeTruthy()
    const box = screen.getByPlaceholderText('Your note (plain text)')
    fireEvent.change(box, { target: { value: 'the first word' } })
    expect(screen.getByText('Not saved yet')).toBeTruthy()
    fireEvent.blur(box) // leaving the box saves it (M177)
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('the first word'))
    expect(await screen.findByText('Saved')).toBeTruthy()
    fireEvent.change(screen.getByRole('combobox', { name: 'Add to a collection…' }), { target: { value: '__new__' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Name of the new collection' }), { target: { value: 'Openings' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create and add' }))
    expect(await screen.findByRole('button', { name: 'Take it out of “Openings”' })).toBeTruthy()
    expect(s.entries.get('v:0')?.collections).toEqual([1])
    fireEvent.click(screen.getByRole('button', { name: 'Take it out of “Openings”' }))
    await waitFor(() => expect(s.entries.get('v:0')?.collections).toEqual([]))
    fireEvent.click(screen.getByRole('button', { name: 'Remove from notebook' }))
    fireEvent.click(within(screen.getByRole('group', { name: 'Remove it and its note?' })).getByRole('button', { name: 'Remove' }))
    expect(await screen.findByRole('button', { name: /Keep in notebook/ })).toBeTruthy()
    expect(s.entries.has('v:0')).toBe(false)
  })

  it('names a collection already taken', async () => {
    const s = fakeServer()
    s.cols.set(1, { name: 'Openings', description: '' })
    s.entries.set('v:0', { note: '', collections: [] })
    renderAt('/unit/v:0')
    fireEvent.change(await screen.findByRole('combobox', { name: 'Add to a collection…' }), { target: { value: '__new__' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Name of the new collection' }), { target: { value: 'Openings' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create and add' }))
    expect(await screen.findByText('A collection of that name exists.')).toBeTruthy()
  })

  it('shows the note without controls when the server is read-only, and nothing for a unit not kept', async () => {
    const s = fakeServer(false)
    s.entries.set('v:0', { note: 'read me', collections: [] })
    renderAt('/unit/v:0')
    expect(await screen.findByText('read me')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Remove from notebook/ })).toBeNull()
    cleanup()
    renderAt('/unit/v:27')
    await waitFor(() => expect(s.calls).toContain('GET /api/notebook'))
    expect(screen.queryByRole('button', { name: /Keep in notebook/ })).toBeNull()
  })
})

describe('NotebookPage', () => {
  it('lists the entries in canon order, filters them by collection and by text', async () => {
    const s = fakeServer()
    s.cols.set(1, { name: 'Blessings', description: 'who blesses whom' })
    s.entries.set('v:27', { note: 'ויברך אתם', collections: [1] })
    s.entries.set('v:0', { note: 'the first word', collections: [] })
    s.entries.set('c:0:1', { note: '', collections: [] })
    const { container } = renderAt('/notebook')
    await screen.findByText('3 entries')
    expect([...container.querySelectorAll('.notebook-entry .verse-ref')].map((a) => a.textContent)).toEqual([
      'Genesis 1בראשית א',
      'Genesis 1:1בראשית א:א',
      'Genesis 1:28בראשית א:כח',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Blessings (1)' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/notebook?c=1'))
    expect(screen.getByText('who blesses whom')).toBeTruthy()
    expect(container.querySelectorAll('.notebook-entry')).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'All entries (3)' }))
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search your notes' }), { target: { value: 'FIRST' } })
    expect(screen.getByText('1 of 3 entries')).toBeTruthy()
  })

  it('creates, renames and deletes a collection; its entries stay', async () => {
    const s = fakeServer()
    s.entries.set('v:0', { note: '', collections: [] })
    renderAt('/notebook')
    expect(await screen.findByText('No collections yet.')).toBeTruthy()
    fireEvent.change(screen.getByRole('textbox', { name: 'New collection' }), { target: { value: 'Openings' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Openings (0)' }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Rename' }), { target: { value: 'Beginnings' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('button', { name: 'Beginnings (0)' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Delete collection' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(await screen.findByText('No collections yet.')).toBeTruthy()
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/notebook'))
    expect(s.entries.has('v:0')).toBe(true)
  })

  it('reads in Hebrew, and says how to start when empty', async () => {
    fakeServer()
    renderAt('/notebook', 'he')
    expect(await screen.findByRole('heading', { name: 'המחברת שלכם', level: 1 })).toBeTruthy()
    // the heading is there before the notebook has come (M176)
    expect(await screen.findByText(/עדיין לא נשמר דבר/)).toBeTruthy()
  })
})

describe('saving feedback in the notebook (M177)', () => {
  const box = () => screen.findByPlaceholderText('Your note (plain text)') as Promise<HTMLTextAreaElement>
  const puts = (s: ReturnType<typeof fakeServer>) => s.calls.filter((c) => c === 'PUT /api/notebook/entries/v:0').length

  it('saves a note by itself a moment after the writing stops, and says so', async () => {
    const s = fakeServer()
    s.entries.set('v:0', { note: '', collections: [] })
    renderAt('/unit/v:0')
    fireEvent.change(await box(), { target: { value: 'the first word' } })
    expect(screen.getByText('Not saved yet')).toBeTruthy()
    expect(puts(s)).toBe(0)
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('the first word'), { timeout: 4000 })
    expect(await screen.findByText('Saved')).toBeTruthy()
    expect(puts(s)).toBe(1)
    expect(screen.queryByRole('button', { name: 'Save note' })).toBeNull()
  })

  it('saves at once on Ctrl+Enter, and not at all when nothing changed', async () => {
    const s = fakeServer()
    s.entries.set('v:0', { note: 'kept', collections: [] })
    renderAt('/unit/v:0')
    const note = await box()
    fireEvent.blur(note)
    fireEvent.keyDown(note, { key: 'Enter', ctrlKey: true })
    expect(puts(s)).toBe(0)
    fireEvent.change(note, { target: { value: 'kept, and more' } })
    fireEvent.keyDown(note, { key: 'Enter' }) // a new line, not a save
    expect(puts(s)).toBe(0)
    fireEvent.keyDown(note, { key: 'Enter', ctrlKey: true })
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('kept, and more'))
    expect(puts(s)).toBe(1)
  })

  it('does not wipe out what is written while a save is on its way', async () => {
    const s = fakeServer()
    s.entries.set('v:0', { note: '', collections: [] })
    renderAt('/unit/v:0')
    const note = await box()
    fireEvent.change(note, { target: { value: 'In the beginning' } })
    fireEvent.blur(note)
    fireEvent.change(note, { target: { value: 'In the beginning God' } })
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('In the beginning'))
    await waitFor(() => expect(s.calls.filter((c) => c === 'GET /api/notebook').length).toBeGreaterThan(1))
    expect(note.value).toBe('In the beginning God')
    // and the rest follows by itself
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('In the beginning God'), { timeout: 4000 })
    expect(note.value).toBe('In the beginning God')
  })

  it('says that a note could not be saved, keeps the writing, and saves it on "Try again"', async () => {
    const s = fakeServer()
    s.entries.set('v:0', { note: '', collections: [] })
    s.failing.on = true
    renderAt('/unit/v:0')
    const note = await box()
    fireEvent.change(note, { target: { value: 'not lost' } })
    fireEvent.blur(note)
    expect((await screen.findByRole('alert')).textContent).toContain('Could not save: 500: disk full')
    expect(await screen.findByText('Could not save the note')).toBeTruthy()
    expect(note.value).toBe('not lost')
    // not sent again by itself
    const sent = puts(s)
    await new Promise((r) => setTimeout(r, 1500))
    expect(puts(s)).toBe(sent)
    s.failing.on = false
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('not lost'))
    expect(await screen.findByText('Saved')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
  })

  it('asks before the page is left with a note unsaved, and saves it when the editor goes', async () => {
    const s = fakeServer()
    s.entries.set('v:0', { note: '', collections: [] })
    const leaving = () => {
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    renderAt('/unit/v:0')
    const note = await box()
    expect(leaving()).toBe(false)
    fireEvent.change(note, { target: { value: 'half a thought' } })
    expect(leaving()).toBe(true)
    // another page of the viewer: the editor goes, the note is saved on the way out
    cleanup()
    await waitFor(() => expect(s.entries.get('v:0')?.note).toBe('half a thought'))
    expect(leaving()).toBe(false)
  })

  it('offers to put a passage back into the collection it was taken out of', async () => {
    const s = fakeServer()
    s.cols.set(1, { name: 'Openings', description: '' })
    s.entries.set('v:0', { note: '', collections: [1] })
    renderAt('/unit/v:0')
    fireEvent.click(await screen.findByRole('button', { name: 'Take it out of “Openings”' }))
    expect(await screen.findByText('Taken out of “Openings”')).toBeTruthy()
    expect(s.entries.get('v:0')?.collections).toEqual([])
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Take it out of “Openings”' })).toBeNull())
    fireEvent.click(screen.getByRole('button', { name: 'Undo' }))
    expect(await screen.findByRole('button', { name: 'Take it out of “Openings”' })).toBeTruthy()
    expect(s.entries.get('v:0')?.collections).toEqual([1])
    expect(screen.queryByText('Taken out of “Openings”')).toBeNull()
  })

  it('says that keeping a passage failed (the button had no way to before)', async () => {
    const s = fakeServer()
    s.failing.on = true
    renderAt('/unit/v:0')
    fireEvent.click(await screen.findByRole('button', { name: /Keep in notebook/ }))
    expect((await screen.findByRole('alert')).textContent).toContain('Could not save: 500: disk full')
    expect(s.entries.has('v:0')).toBe(false)
  })

  it('keeps the words searched for in the address', async () => {
    const s = fakeServer()
    s.entries.set('v:27', { note: 'ויברך אתם', collections: [] })
    s.entries.set('v:0', { note: 'the first word', collections: [] })
    const { container } = renderAt('/notebook?f=FIRST')
    expect(await screen.findByText('1 of 2 entries')).toBeTruthy()
    const search = screen.getByRole('searchbox', { name: 'Search your notes' }) as HTMLInputElement
    expect(search.value).toBe('FIRST')
    fireEvent.change(search, { target: { value: 'ויברך' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe(`/notebook?f=${encodeURIComponent('ויברך')}`))
    expect([...container.querySelectorAll('.notebook-entry .verse-ref')].map((a) => a.textContent)).toEqual(['Genesis 1:28בראשית א:כח'])
    fireEvent.change(search, { target: { value: '' } })
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/notebook'))
    expect(screen.getByText('2 entries')).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    const s = fakeServer()
    s.cols.set(1, { name: 'פתיחות', description: '' })
    s.entries.set('v:0', { note: '', collections: [1] })
    renderAt('/unit/v:0', 'he')
    const note = await screen.findByPlaceholderText('ההערה שלכם (טקסט פשוט)')
    fireEvent.change(note, { target: { value: 'בראשית' } })
    expect(screen.getByText('עדיין לא נשמרה')).toBeTruthy()
    fireEvent.blur(note)
    expect(await screen.findByText('נשמרה')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'הוצאה מ”פתיחות“' }))
    expect(await screen.findByText('הקטע הוצא מ”פתיחות“')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'ביטול הפעולה' })).toBeTruthy()
  })
})

describe('the Markdown file', () => {
  it('has a section per entry, a verse quoted, the note and its collections', () => {
    const e = (id: string, note: string, collections: number[], v: Verse | null): NotebookEntry => ({
      unit: UNITS[id],
      note,
      collections,
      created_at: '',
      updated_at: '',
      verse: v,
    })
    const entries = [e('c:0:1', '', [], null), e('v:0', ' first \n', [1], verse(0, 'בְּרֵאשִׁית בָּרָא'))]
    const cols: NotebookCollection[] = [{ collection_id: 1, name: 'Openings', description: '', n_entries: 1, created_at: '', updated_at: '' }]
    const t = { title: 'Notebook', exported: (d: string) => `Exported ${d}.`, collections: 'Collections' }
    expect(notebookMarkdown(entries, cols, 'Openings', t, 'en', '2026-10-13')).toBe(
      [
        '# Notebook: Openings',
        '',
        'Exported 2026-10-13.',
        '',
        '## Genesis 1 · בראשית א',
        '',
        '## Genesis 1:1 · בראשית א:א',
        '',
        '> בְּרֵאשִׁית בָּרָא',
        '',
        'first',
        '',
        '*Collections: Openings*',
        '',
      ].join('\n'),
    )
    expect(notebookMarkdown(entries, cols, null, t, 'he', 'x').split('\n')[4]).toBe('## בראשית א')
    expect(filterEntries(entries, 'בראשית א:א').map((x) => x.unit.unit_id)).toEqual(['v:0'])
    expect(filterEntries(entries, '  ')).toHaveLength(2)
  })
})
