// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { FrameworksResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { FrameworksPage } from './FrameworksPage'

const hit = (slot: string, id: number | null) => ({ slot, verse_id: id, ref: id === null ? null : `Judges 3:${id}`, ref_he: id === null ? null : `שופטים ג:${id}` })
const SLOTS = ['evil', 'oppression', 'years', 'cry', 'deliverer', 'rest']
const REGNAL = ['age', 'mother', 'high_places', 'jeroboam', 'burial']
const VERSE = {
  verse_id: 9170,
  book_id: 10,
  chapter: 15,
  verse: 11,
  ref: 'I Kings 15:11',
  ref_he: 'מלכים א טו:יא',
  text_display: 'וַיַּעַשׂ אָסָא הַיָּשָׁר',
  display_tokens: ['וַיַּעַשׂ', 'אָסָא', 'הַיָּשָׁר'],
  ketiv_note: null,
}
const DATA: FrameworksResponse = {
  episodes: [
    { episode: 'othniel', judge: 'עתניאל', seq: 0, ref: 'Judges 3:7', ref_he: 'שופטים ג:ז', first_vid: 1, last_vid: 5, n_slots: 6, share: 1, slots: SLOTS.map((s, i) => hit(s, 7 + i)) },
    { episode: 'samson', judge: 'שמשון', seq: 1, ref: 'Judges 13:1', ref_he: 'שופטים יג:א', first_vid: 9, last_vid: 20, n_slots: 3, share: 0.5, slots: SLOTS.map((s, i) => hit(s, i < 3 ? 1 : null)) },
  ],
  slots: SLOTS,
  open: 10,
  rho: -0.971,
  cycle_p: 0.0056,
  cycle_holds: true,
  known_cycle: [
    { episode: 'othniel', expect: 'complete', missing: [], holds: true },
    { episode: 'samson', expect: 'missing cry, rest', missing: ['cry', 'deliverer', 'rest'], holds: true },
  ],
  known_cycle_holds: true,
  kings: [
    { king: 'asa', name: 'אסא', kingdom: 'judah', seq: 0, first_vid: 9168, verdict: 'good', verdict_verse: VERSE, slots: REGNAL.map((s) => hit(s, s === 'mother' ? 10 : null)) },
    { king: 'jeroboam', name: 'ירבעם', kingdom: 'israel', seq: 1, first_vid: 9150, verdict: null, verdict_verse: null, slots: REGNAL.map((s) => hit(s, null)) },
  ],
  verdicts: 34,
  good: 10,
  bad: 24,
  within: { judah: 0.286, israel: 0.391 },
  within_all: 0.326,
  between: 0.267,
  difference: 0.059,
  expected: 0,
  verdict_p: 0.0001,
  verdict_holds: true,
  known_verdicts: [
    { king: 'asa', expected: 'good', found: 'good', holds: true },
    { king: 'jeroboam', expected: 'bad', found: null, holds: false },
  ],
  known_verdicts_holds: false,
  regnal: REGNAL,
  by_kingdom: { judah: { verdict_vid: 0.95, age: 0.85, mother: 0.85, high_places: 0.45, jeroboam: 0, burial: 0.7 }, israel: { verdict_vid: 0.79, age: 0, mother: 0, high_places: 0, jeroboam: 0.63, burial: 0.26 } },
  shuffles: 9999,
  alpha: 0.05,
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path = '/frameworks', locale: 'en' | 'he' = 'en', missing = false) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => (missing ? new Response(JSON.stringify({ detail: 'the frameworks were not computed' }), { status: 404 }) : new Response(JSON.stringify(DATA)))),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/frameworks" element={<FrameworksPage />} />
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

describe('FrameworksPage', () => {
  it('states the four checks', async () => {
    renderAt()
    const cycle = (await screen.findByRole('heading', { name: /cycle breaks down/ })).closest('article')!
    expect(cycle.textContent).toContain('Spearman’s rho with the book’s order -0.97, against every order of the 2 episodes (p 0.006)')
    const known = screen.getByRole('heading', { name: /Othniel whole/ }).closest('article')!
    expect(known.textContent).toContain('(missing: nothing); Samson’s has no cry and no rest (missing: Cried out, A deliverer raised, The land at rest)')
    const words = screen.getByRole('heading', { name: /own wording/ }).closest('article')!
    expect(words.textContent).toContain('verdicts of one kingdom 0.33 alike on average, of different kingdoms 0.27')
    const kv = screen.getByRole('heading', { name: /read right/ }).closest('article')!
    expect(within(kv).getByText('Not borne out')).toBeTruthy()
    expect(kv.textContent).toContain('1 of 2 verdicts named in advance read as expected: ⁨אסא⁩ right, ⁨ירבעם⁩ none found (not evil).')
  })

  it('shows the cycle slot by slot', async () => {
    const { container } = renderAt()
    await screen.findByText('The judges’ cycle')
    const rows = [...container.querySelectorAll('table.fw-cycle tbody tr')]
    expect(rows).toHaveLength(2)
    expect(rows[0].querySelectorAll('a.fw-hit')).toHaveLength(6)
    expect(rows[1].querySelectorAll('a.fw-hit')).toHaveLength(3)
    expect(rows[1].lastElementChild!.textContent).toBe('3 / 6')
    expect(screen.getByRole('link', { name: 'Did evil: found in Judges 3:7' }).getAttribute('href')).toBe('/unit/v%3A7')
  })

  it('lists the kings and opens a verdict', async () => {
    const { container } = renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'The account of אסא' }))
    expect(screen.getByTestId('loc').textContent).toBe('/frameworks?k=asa')
    const panel = container.querySelector('.fw-panel')!
    expect(panel.textContent).toContain('I Kings 15:11')
    expect(panel.querySelector('.type-tag.fw-good')!.textContent).toBe('right')
    const rows = [...container.querySelectorAll('table.fw-kings tbody tr')]
    expect(rows[0].className).toBe('fw-judah selected')
    expect(rows[1].textContent).toContain('none found')
    expect([...container.querySelectorAll('table.fw-by-kingdom tbody tr')].map((r) => r.textContent)).toContain('Mother85%0%')
  })

  it('says when the stage did not run', async () => {
    renderAt('/frameworks', 'en', true)
    expect(await screen.findByText(/The frameworks were not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/frameworks?k=jeroboam', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('המסגרות של הסיפור')
    expect(await screen.findByRole('heading', { name: '⁨ירבעם⁩: ההערכה' })).toBeTruthy()
    expect(screen.getAllByText('לא נמצאה').length).toBeGreaterThan(0)
  })
})
