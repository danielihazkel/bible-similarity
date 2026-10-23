// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RetoldPage as Page, RetoldPair, RetoldResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { RetoldPage } from './RetoldPage'

const verse = (id: number, ref: string, refHe: string, text: string) => ({
  verse_id: id,
  book_id: 0,
  chapter: 3,
  verse: 2,
  ref,
  ref_he: refHe,
  text_display: text,
  display_tokens: text.split(' '),
  ketiv_note: null,
})
const EVE: RetoldPair = {
  pair: 11,
  book_id: 0,
  group: 'retold',
  source: {
    kind: 'speech',
    teller: { key: 'divine', he: null, rank: 2 },
    verses: [verse(46, 'Genesis 2:16', 'בראשית ב:טז', 'מכל עץ הגן אכל תאכל'), verse(47, 'Genesis 2:17', 'בראשית ב:יז', 'ומעץ הדעת לא תאכל ממנו')],
    marks: [{ 0: 'omitted' }, {}],
  },
  retelling: {
    kind: 'speech',
    teller: { key: '802', he: 'אשה', rank: 0 },
    verses: [verse(56, 'Genesis 3:2', 'בראשית ג:ב', 'מפרי עץ הגן נאכל')],
    marks: [{ 0: 'added', 3: 'form' }],
  },
  unit_id: 'c:0:3',
  n_ops: 13,
  n_changed: 6,
  rate: 0.4615,
  ops: { same: 5, substitution: 4, added: 2 },
  score: 18,
  known: true,
}
const CARRIED: RetoldPair = {
  ...EVE,
  pair: 12,
  group: 'carried',
  known: false,
  rate: 0.1,
  retelling: { kind: 'narration', teller: null, verses: [verse(60, 'Genesis 3:6', 'בראשית ג:ו', 'ותקח מפריו ותאכל')], marks: [{}] },
}
const DATA: RetoldResponse = {
  pairs: 1330,
  groups: { retold: 109, repeated: 197, carried: 232, told: 126, narrated: 420, unclear: 246 },
  rates: { retold: 0.29, repeated: 0.249, carried: 0.3, told: 0.311, narrated: 0.293, unclear: 0.267 },
  claim: ['retold', 'carried'],
  difference: -0.01,
  p: 0.6567,
  shuffles: 9999,
  bins: 4,
  alpha: 0.05,
  holds: false,
  known: [
    { source: 'Genesis 2:16-17', retelling: 'Genesis 3:2-3', found: true, pairs: [11], group: 'retold', rate: 0.4615 },
    { source: 'Genesis 24:2-8', retelling: 'Genesis 24:37-41', found: false, pairs: [], group: null, rate: null },
  ],
  known_found: 1,
  known_holds: false,
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

const calls: string[] = []

function renderAt(path: string, locale: 'en' | 'he' = 'en', missing = false) {
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const u = new URL(url, 'http://x')
      calls.push(u.pathname + u.search)
      if (missing) return new Response(JSON.stringify({ detail: 'the retold speech was not computed' }), { status: 404 })
      if (u.pathname === '/api/retold') return new Response(JSON.stringify(DATA))
      const group = u.searchParams.get('group')
      const items = group === 'carried' ? [CARRIED] : group ? [] : [EVE, CARRIED]
      const page: Page = { group: (group as Page['group']) ?? null, book: null, order: (u.searchParams.get('order') ?? 'canon') as Page['order'], known: false, total: items.length, offset: 0, limit: 20, items }
      return new Response(JSON.stringify(page))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/retold" element={<RetoldPage />} />
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

describe('RetoldPage', () => {
  it('states both checks with their verdicts and the groups', async () => {
    renderAt('/retold')
    const claim = (await screen.findByRole('heading', { name: /changes more than speech carried out/ })).closest('article')!
    expect(within(claim).getByText('Not borne out')).toBeTruthy()
    expect(claim.textContent).toContain('109 retellings by another speaker change 29% of their words')
    expect(claim.textContent).toContain('232 speeches told again by the narrator as done change 30%. Compared within the same lengths: p 0.66.')
    const known = screen.getByRole('heading', { name: /read side by side/ }).closest('article')!
    expect([...known.querySelectorAll('li')].map((li) => li.textContent)).toEqual(['Genesis 2:16-17 → Genesis 3:2-3: found, 46% changed', 'Genesis 24:2-8 → Genesis 24:37-41: not found'])
    const rows = [...document.querySelectorAll('table.rt-groups tbody tr')]
    expect(rows.map((r) => r.textContent)).toEqual([
      'Retold by another speaker10929%',
      'Repeated by the same speaker19725%',
      'Carried out by the narrator23230%',
      'Narration told in a speech12631%',
      'Narration told again42029%',
      'A speaker not known24627%',
    ])
    expect(rows.filter((r) => r.className === 'rt-claim')).toHaveLength(2)
  })

  it('sets the two passages side by side with their changes marked and their tellers', async () => {
    const { container } = renderAt('/retold')
    await screen.findByText('2 passages · page 1 of 1')
    const eve = container.querySelector('li.rt-pair')!
    expect(eve.textContent).toContain('46% of 13 words changed')
    expect(eve.textContent).toContain('named in advance')
    const tellers = [...eve.querySelectorAll('.rt-teller')].map((p) => p.textContent)
    expect(tellers).toEqual(['First told by God', 'Told again by אשה'])
    expect(eve.querySelectorAll('.hit-text')).toHaveLength(3)
    expect(eve.querySelector('.w-diff-omitted')?.textContent).toBe('מכל')
    expect(eve.querySelector('.w-diff-added')?.textContent).toBe('מפרי')
    expect(eve.querySelector('.w-diff-form')?.textContent).toBe('נאכל')
    expect(within(eve as HTMLElement).getByRole('link', { name: 'compare the first verses' }).getAttribute('href')).toBe('/compare?a=v%3A46&b=v%3A56&marks=changes')
    const carried = container.querySelectorAll('li.rt-pair')[1]
    expect([...carried.querySelectorAll('.rt-teller')].map((p) => p.textContent)).toEqual(['First told by God', 'Told again by the narrator'])
  })

  it('filters by group, order and the known through the address and the API', async () => {
    const { container } = renderAt('/retold')
    fireEvent.click(await screen.findByRole('radio', { name: 'Carried out by the narrator' }))
    expect(screen.getByTestId('loc').textContent).toBe('/retold?group=carried')
    await screen.findByText('1 passage · page 1 of 1')
    expect(container.querySelectorAll('li.rt-pair')).toHaveLength(1)
    fireEvent.click(screen.getByRole('radio', { name: 'Most changed' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Named in advance only' }))
    expect(screen.getByTestId('loc').textContent).toBe('/retold?group=carried&order=most&known=1')
    await vi.waitFor(() => expect(calls).toContain('/api/retold/items?group=carried&known=true&order=most&limit=20&offset=0'))
  })

  it('says when the stage did not run', async () => {
    renderAt('/retold', 'en', true)
    expect(await screen.findByText(/The retold speech was not computed/)).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/retold', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('דיבור שמסופר שוב')
    expect(await screen.findByText('לא מתאשר', { selector: '.dv-check:first-child .dv-verdict' })).toBeTruthy()
    expect(await screen.findAllByText('לראשונה בפי האל')).toHaveLength(2)
  })
})
