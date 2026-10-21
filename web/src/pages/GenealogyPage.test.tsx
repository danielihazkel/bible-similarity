// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { FamilyLink, PersonDetail, PersonLookup, PersonRef, SkeletonResponse, TreeNode, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { GenealogyPage } from './GenealogyPage'

const node = (person_id: number, he: string, parent: number | null, extra: Partial<TreeNode> = {}): TreeNode => ({
  person_id,
  he,
  sex: 'm',
  kind: 'person',
  placement: parent === null ? 'root' : 'tree',
  parent,
  role: parent === null ? null : 'father',
  link_kind: parent === null ? null : 'son',
  seq: null,
  mother: null,
  book_id: null,
  reviewed: true,
  doubt: false,
  conflict: false,
  spouses: [],
  ...extra,
})

// Adam (Eve beside him) -> Cain, Seth; Seth -> Enosh (a conflict); Cain -> Lamech (a descendant)
// -> Jabal (by Adah), Tubal (by Zillah), an unnamed daughter; Balaam under "unattached", Exodus
const SK: SkeletonResponse = {
  meta: { persons: 13, parent_links: 12, proved: 6, reviewed_links: 3 },
  nodes: [
    node(1, 'אדם', null, { spouses: [2] }),
    node(3, 'קין', 1, { seq: 0, mother: 2 }),
    node(4, 'שת', 1, { seq: 1, mother: 2, reviewed: false }),
    node(5, 'למך', 3, { link_kind: 'descendant', spouses: [6, 7] }),
    node(8, 'יבל', 5, { seq: 0, mother: 6 }),
    node(9, 'תובל', 5, { seq: 1, mother: 7 }),
    node(10, 'אנוש', 4, { conflict: true }),
    node(11, '', 5, { sex: 'f', kind: 'anon', seq: 2, doubt: true }),
    node(14, '', null, { kind: 'virtual', placement: 'virtual', reviewed: false }),
    node(15, '', 14, { kind: 'virtual', placement: 'virtual', role: 'unstated', link_kind: 'unstated', book_id: 1, reviewed: false }),
    node(13, 'בלעם', 15, { placement: 'unattached', role: 'unstated', link_kind: 'unstated' }),
  ],
  spouses: [
    { person_id: 2, he: 'חוה', sex: 'f', kind: 'person', reviewed: true },
    { person_id: 6, he: 'עדה', sex: 'f', kind: 'person', reviewed: true },
    { person_id: 7, he: 'צלה', sex: 'f', kind: 'person', reviewed: true },
  ],
  cross: [{ parent: 3, child: 10, role: 'father', kind: 'son' }],
}

const verse = (verse_id: number, text: string): Verse => ({
  verse_id,
  book_id: 0,
  chapter: 4,
  verse: verse_id,
  ref: `Genesis 4:${verse_id}`,
  ref_he: `בראשית ד:${verse_id}`,
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const ref = (person_id: number, he: string, placement: PersonRef['placement'] = 'tree'): PersonRef => ({ person_id, he, sex: 'm', kind: 'person', placement })
const link = (link_id: number, person: PersonRef, extra: Partial<FamilyLink> = {}): FamilyLink => ({
  link_id,
  person,
  role: 'father',
  kind: 'son',
  drawn: true,
  doubt: false,
  marker: '',
  status: 'tipnr',
  source: 'tipnr',
  cue: null,
  n_candidates: 0,
  conflict_id: null,
  proofs: [],
  ...extra,
})
const ENOSH: PersonDetail = {
  person: { person_id: 10, he: 'אנוש', sex: 'm', kind: 'person', placement: 'tree', first_vid: 26, n_verses: 1, reviewed: true, book_id: null },
  first_label: 'Genesis 4:26',
  first_label_he: 'בראשית ד:כו',
  parents: [
    link(14, ref(4, 'שת'), { status: 'reading', cue: 'construct', proofs: [{ verse: verse(26, 'וּלְשֵׁת גַּם־הוּא יֻלַּד־בֵּן'), tokens: [0], cue: 'construct', source: 'curated' }] }),
    link(15, ref(3, 'קין'), { drawn: false, status: 'reading', cue: 'together', proofs: [{ verse: verse(25, 'קַיִן וְאֱנוֹשׁ'), tokens: [0, 1], cue: 'together', source: 'curated' }] }),
  ],
  attached: null,
  spouses: [],
  children: [],
  siblings: [],
  members: [],
  conflicts: [{ conflict_id: 1, kind: 'bible', block: 'b01-gen-1-11', readings: [], note_en: 'Two passages differ.', note_he: 'שני כתובים חלוקים.' }],
}
ENOSH.conflicts[0].readings = ENOSH.parents
const LAMECH: PersonDetail = {
  ...ENOSH,
  person: { ...ENOSH.person, person_id: 5, he: 'למך', reviewed: false },
  parents: [link(6, ref(3, 'קין'), { kind: 'descendant', marker: 'a' })],
  spouses: [link(7, ref(6, 'עדה', 'spouse'), { role: 'spouse', kind: 'spouse', drawn: false })],
  children: [
    { other: { ...ref(6, 'עדה', 'spouse'), sex: 'f' }, children: [link(9, ref(8, 'יבל'), { cue: 'sons_of', proofs: [{ verse: verse(20, 'יָבָל הוּא'), tokens: [0], cue: 'sons_of', source: 'auto' }] })] },
    { other: null, children: [link(13, { ...ref(11, ''), sex: 'f', kind: 'anon' }, { doubt: true })] },
  ],
  conflicts: [],
}
const LOOKUP: PersonLookup = {
  query: 'אנוש',
  items: [{ person_id: 10, he: 'אנוש', sex: 'm', kind: 'person', placement: 'tree', first_vid: 26, n_verses: 1, exact: true, relation: 'child', of_he: 'שת', first_label: 'Genesis 4:26', first_label_he: 'בראשית ד:כו' }],
}
const BOOKS = [
  { book_id: 0, name: 'Genesis', he_name: 'בראשית', osis: 'Gen', section: 'Torah', n_chapters: 50 },
  { book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 },
]

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', skeleton: SkeletonResponse = SK) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const p = new URL(url, 'http://x').pathname
      const body =
        p === '/api/genealogy/skeleton'
          ? skeleton
          : p === '/api/genealogy/person/10'
            ? ENOSH
            : p === '/api/genealogy/person/5'
              ? LAMECH
              : p === '/api/genealogy/lookup'
                ? LOOKUP
                : p === '/api/books'
                  ? BOOKS
                  : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/genealogy" element={<GenealogyPage />} />
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

const names = (c: HTMLElement) => [...c.querySelectorAll('.gt-node .gt-name')].map((b) => b.querySelector('.he, bdi')?.textContent)

describe('GenealogyPage', () => {
  it('opens on Adam’s first generations, with spouses beside, the markers and the legend', async () => {
    const { container } = renderAt('/genealogy')
    expect(await screen.findByText(/13 people and 12 parent links, 6 of them with a verse naming both; 3 checked/)).toBeTruthy()
    await waitFor(() => expect(names(container)).toContain('אנוש'))
    // three generations open, so four shown; the unattached closed
    expect(names(container)).toContain('יבל')
    expect(names(container)).toContain('Unattached')
    const lamech = [...container.querySelectorAll('.gt-node')].find((n) => n.textContent?.includes('למך'))
    expect(lamech?.querySelector('.gt-spouses')?.textContent).toContain('עדה')
    expect(container.querySelector('.gt-node.conflict')?.textContent).toContain('אנוש')
    expect(container.querySelector('.gt-node.unreviewed')?.textContent).toContain('שת')
    expect(container.querySelector('.gt-edges .gt-edge.desc')).toBeTruthy()
    expect(container.querySelector('.gt-edges .gt-cross')).toBeTruthy()
    expect(screen.getByRole('list', { name: 'Legend' }).querySelectorAll('li')).toHaveLength(8)
  })

  it('opens and closes a branch: children under their mothers', async () => {
    const { container } = renderAt('/genealogy')
    await waitFor(() => expect(names(container)).toContain('יבל'))
    expect(names(container)).toContain('daughter of למך') // unnamed: what she is to her father
    expect([...container.querySelectorAll('.gt-header')].map((h) => h.textContent)).toEqual(['by עדה', 'by צלה', 'mother not named'])
    fireEvent.click(screen.getAllByRole('button', { name: 'Hide those below' }).find((b) => b.closest('.gt-node')?.textContent?.includes('למך'))!)
    await waitFor(() => expect(names(container)).not.toContain('יבל'))
    expect(container.querySelectorAll('.gt-header')).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Show 3 people below' }))
    await waitFor(() => expect(names(container)).toContain('יבל'))
    // the unattached, by book
    fireEvent.click(screen.getByRole('button', { name: 'Show 2 people below' }))
    await waitFor(() => expect(names(container)).toContain('Exodus'))
  })

  it('opens a person: the panel with verses, the conflict’s readings', async () => {
    const { container } = renderAt('/genealogy')
    await waitFor(() => expect(names(container)).toContain('אנוש'))
    fireEvent.click(screen.getByRole('button', { name: /אנוש/ }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/genealogy?p=10'))
    const panel = await screen.findByRole('region', { name: 'Person' })
    expect(within(panel).getByText('Where the text disagrees')).toBeTruthy()
    expect(panel.querySelector('.gt-conflict')?.textContent).toContain('Two passages give different parents · Two passages differ.')
    expect(within(panel).getAllByText('the reading the tree draws')).toHaveLength(1)
    expect(within(panel).getAllByText('“son of”').length).toBeGreaterThan(0)
    expect(panel.querySelectorAll('.w-focus').length).toBeGreaterThan(0)
    expect(within(panel).getAllByRole('link', { name: 'Genesis 4:26' })[0].getAttribute('href')).toBe('/unit/v%3A26')
    fireEvent.click(within(panel).getByRole('button', { name: 'Close' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/genealogy'))
  })

  it('opens the line down to a person given in the address, children by mother in the panel', async () => {
    const { container } = renderAt('/genealogy?p=5')
    const panel = await screen.findByRole('region', { name: 'Person' })
    expect(await within(panel).findByText('a descendant, not a child')).toBeTruthy()
    expect(within(panel).getByText('an ancestor, not the parent')).toBeTruthy()
    expect(within(panel).getByText('Mother not named')).toBeTruthy()
    expect(panel.querySelector('.gt-child-group h4')?.textContent).toBe('By עדה')
    expect(container.querySelector('.gt-node.selected')?.textContent).toContain('למך')
    fireEvent.click(within(panel).getByRole('button', { name: 'Open all below' }))
    await waitFor(() => expect(names(container)).toContain('תובל'))
  })

  it('finds a person by name', async () => {
    renderAt('/genealogy')
    fireEvent.change(await screen.findByRole('searchbox'), { target: { value: 'אנוש' } })
    const hit = await screen.findByRole('button', { name: 'אנוש' }, { timeout: 2000 })
    expect(hit.closest('li')?.textContent).toContain('son of שת · first in Genesis 4:26')
    fireEvent.click(hit)
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/genealogy?p=10'))
  })

  it('reads in Hebrew', async () => {
    const { container } = renderAt('/genealogy?p=5', 'he')
    expect(await screen.findByRole('heading', { name: 'אילן היוחסין' })).toBeTruthy()
    await waitFor(() => expect(names(container)).toContain('בלי קשר'))
    const panel = await screen.findByRole('region', { name: 'אדם' })
    expect(await within(panel).findByText('צאצא ולא בן')).toBeTruthy()
    expect(panel.querySelector('.gt-child-group h4')?.textContent).toBe('ילדי עדה')
  })

  it('says when the tree was not built', async () => {
    renderAt('/genealogy', 'en', { meta: {}, nodes: [], spouses: [], cross: [] })
    expect(await screen.findByText(/Not computed in this build/)).toBeTruthy()
  })
})
