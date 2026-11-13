// @vitest-environment jsdom
// M174: one way to filter: the significance filter, "known only", a toolbar's choice, a list's exports
import type { UseQueryResult } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as csv from '../lib/csv'
import { flattenItem, flattenItems } from '../lib/csv'
import { parseSignificance, significanceChange } from '../lib/urlState'
import { Choice, KnownOnly, SignificanceFilter } from './Controls'
import { PagedList } from './Pager'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const q = (search: string) => new URLSearchParams(search)

describe('the significance filter in the address', () => {
  it('is q ≤ 0.05 by default, a list’s second step, or all', () => {
    expect(parseSignificance(q(''))).toEqual({ choice: '0.05', maxQ: 0.05 })
    expect(parseSignificance(q('q=all'))).toEqual({ choice: 'all', maxQ: undefined })
    expect(parseSignificance(q('q=0.2'), '0.2')).toEqual({ choice: '0.2', maxQ: 0.2 })
    // a step the list does not have, or anything else: the default
    expect(parseSignificance(q('q=0.2'), '0.5').choice).toBe('0.05')
    expect(parseSignificance(q('q=0.2')).choice).toBe('0.05')
    expect(parseSignificance(q('q=7')).choice).toBe('0.05')
  })

  it('still reads the older spellings of "all", and takes them out when it is set', () => {
    expect(parseSignificance(q('rq=all'), undefined, [['rq', 'all']]).choice).toBe('all')
    expect(parseSignificance(q('pq=all'), undefined, [['pq', 'all']]).choice).toBe('all')
    expect(parseSignificance(q('all=1'), undefined, [['all', '1']]).choice).toBe('all')
    // the new parameter wins over an older one left beside it
    expect(parseSignificance(q('all=1&q=0.05'), undefined, [['all', '1']]).choice).toBe('0.05')
    expect(significanceChange('all', [['rq', 'all']])).toEqual({ q: 'all', rq: null })
    expect(significanceChange('0.05', [['all', '1']])).toEqual({ q: null, all: null })
    expect(significanceChange('0.2')).toEqual({ q: '0.2' })
  })
})

describe('SignificanceFilter and KnownOnly', () => {
  it('is one row of the same options on every page: the cut, a second step where there is one, all', () => {
    const set = vi.fn()
    render(<SignificanceFilter value="0.05" second="0.2" onChange={set} />)
    const group = screen.getByRole('radiogroup', { name: 'Significance' })
    expect(within(group).getAllByRole('radio').map((r) => [r.textContent, r.getAttribute('aria-checked')])).toEqual([
      ['q ≤ 0.05', 'true'],
      ['q ≤ 0.2', 'false'],
      ['All', 'false'],
    ])
    fireEvent.click(screen.getByRole('radio', { name: 'All' }))
    expect(set).toHaveBeenCalledWith('all')
    cleanup()
    render(<SignificanceFilter value="all" onChange={set} />)
    expect(screen.getAllByRole('radio').map((r) => r.textContent)).toEqual(['q ≤ 0.05', 'All'])
    expect(screen.getByRole('radio', { name: 'All' }).getAttribute('aria-checked')).toBe('true')
  })

  it('names the first option after a list’s own cut where that is not a q', () => {
    render(<SignificanceFilter value="0.05" strict="Strongest of each group" strictTitle="why" onChange={() => {}} />)
    const first = screen.getByRole('radio', { name: 'Strongest of each group' })
    expect(first.getAttribute('aria-checked')).toBe('true')
    expect(first.getAttribute('title')).toBe('why')
  })

  it('KnownOnly is a checkbox with the page’s own words', () => {
    const set = vi.fn()
    render(<KnownOnly checked={false} label="Named in advance only" title="the passages listed before the run" onChange={set} />)
    const box = screen.getByRole('checkbox', { name: 'Named in advance only' })
    expect((box as HTMLInputElement).checked).toBe(false)
    expect(box.closest('label')?.getAttribute('title')).toBe('the passages listed before the run')
    fireEvent.click(box)
    expect(set).toHaveBeenCalledWith(true)
  })
})

describe('Choice: a toolbar’s one rule', () => {
  const opts = (labels: string[]) => labels.map((l) => ({ value: l.toLowerCase(), label: l }))

  it('draws up to five short options as a row of buttons, with the choice’s name before it', () => {
    const set = vi.fn()
    const { container } = render(<Choice label="Kind" value="any" options={opts(['Any', 'Verb and noun', 'Other'])} onChange={set} />)
    const group = screen.getByRole('radiogroup', { name: 'Kind' })
    expect(within(group).getAllByRole('radio')).toHaveLength(3)
    expect(container.querySelector('.choice > span[aria-hidden]')?.textContent).toBe('Kind')
    expect(screen.queryByRole('combobox')).toBeNull()
    fireEvent.click(screen.getByRole('radio', { name: 'Other' }))
    expect(set).toHaveBeenCalledWith('other')
  })

  it('draws more than five options, or long ones, as a dropdown', () => {
    const set = vi.fn()
    render(<Choice label="Group" value="a" options={opts(['A', 'B', 'C', 'D', 'E', 'F'])} onChange={set} />)
    const select = screen.getByRole('combobox', { name: 'Group' })
    expect(within(select).getAllByRole('option')).toHaveLength(6)
    expect(screen.queryByRole('radiogroup')).toBeNull()
    fireEvent.change(select, { target: { value: 'f' } })
    expect(set).toHaveBeenCalledWith('f')
    cleanup()
    // four options, but their labels are a sentence: too wide for a row
    render(<Choice label="Sort by" value="x" options={opts(['Semantic chiasm', 'Lexical chiasm', 'Semantic inclusio', 'Lexical inclusio'])} onChange={set} />)
    expect(screen.getByRole('combobox', { name: 'Sort by' })).toBeTruthy()
  })
})

describe('a list’s rows as CSV', () => {
  it('writes a unit as its label, a lemma as its Hebrew form, a verse as its reference, and no texts', () => {
    expect(
      flattenItem({
        a: { unit_id: 'v:1', label_en: 'Genesis 1:1', label_he: 'בראשית א:א' },
        lemmas: [{ lemma: '1', he_lemma: 'אב' }, { lemma: '2', he_lemma: 'אם' }],
        verse: { verse_id: 3, ref: 'Genesis 1:4', text_display: 'וַיַּרְא', display_tokens: ['וַיַּרְא'] },
        a_verse: { ref: 'Genesis 1:1', text_display: 'x' },
        counts: { same: 3, moved: 1 },
        tokens: [1, 2],
        nested: [[1, 2]],
        score: 0.5,
        text_display: 'x',
        marker: null,
      }),
    ).toEqual({ a: 'Genesis 1:1', lemmas: 'אב; אם', verse: 'Genesis 1:4', 'counts.same': 3, 'counts.moved': 1, tokens: '1; 2', score: 0.5, marker: null })
  })

  it('leaves the verse out where the item has a label of its own', () => {
    expect(flattenItem({ label: 'Genesis 1:4', n: 2, verse: { ref: 'Genesis 1:4', text_display: 'x' } })).toEqual({ label: 'Genesis 1:4', n: 2 })
  })

  it('gives every row every column', () => {
    expect(flattenItems([{ a: 1 }, { a: 2, b: 'x' }])).toEqual([
      { a: 1, b: undefined },
      { a: 2, b: 'x' },
    ])
  })
})

interface Data {
  items: { unit: { label_en: string }; score: number }[]
  total: number
  limit: number
}
function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}
function show(path: string, props: { csv?: string; pageParam?: string; params?: Record<string, string | number | undefined> }) {
  const data: Data = { items: [{ unit: { label_en: 'Genesis 1' }, score: 0.5 }], total: 30, limit: 10 }
  const res = Object.assign({ isPending: false, isError: false, error: null, data, isPlaceholderData: false } as unknown as UseQueryResult<Data>, props.params ? { params: props.params } : {})
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/list"
          element={
            <PagedList<Data> res={res} empty="Nothing." csv={props.csv} pageParam={props.pageParam} summary={(d, page, pages) => `${d.total} rows · ${page} of ${pages}`}>
              {(d) => <ul>{d.items.map((x) => <li key={x.unit.label_en}>{x.unit.label_en}</li>)}</ul>}
            </PagedList>
          }
        />
      </Routes>
      <Location />
    </MemoryRouter>,
  )
}

describe('PagedList: a list’s exports and its page', () => {
  it('exports the page as listed, and every row from the server under the list’s own filters', () => {
    const save = vi.spyOn(csv, 'downloadCsv').mockImplementation(() => {})
    show('/list?page=2', { csv: 'ketiv', params: { cls: 'swap', book: 3, unit: undefined, limit: 10, offset: 10 } })
    expect(screen.getByText('30 rows · 2 of 3')).toBeTruthy() // the summary is still its own element
    fireEvent.click(screen.getByRole('button', { name: 'Export page (CSV)' }))
    expect(save).toHaveBeenCalledWith('ketiv-p2.csv', [{ unit: 'Genesis 1', score: 0.5 }])
    // the page's own limit and offset are not the export's
    expect(screen.getByRole('link', { name: 'Export all (CSV)' }).getAttribute('href')).toBe('/api/export/ketiv.csv?cls=swap&book=3')
  })

  it('has the page export alone where the result does not carry its request, and none without a name', () => {
    show('/list', { csv: 'things' })
    expect(screen.getByRole('button', { name: 'Export page (CSV)' })).toBeTruthy()
    expect(screen.queryByRole('link', { name: 'Export all (CSV)' })).toBeNull()
    cleanup()
    show('/list', {})
    expect(screen.queryByRole('button', { name: 'Export page (CSV)' })).toBeNull()
  })

  it('keeps a second list’s page in its own parameter', () => {
    show('/list?page=3&vpage=2', { pageParam: 'vpage' })
    expect(screen.getByText('30 rows · 2 of 3')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(screen.getByTestId('loc').textContent).toBe('/list?page=3&vpage=3')
    fireEvent.click(screen.getByRole('button', { name: /previous/i }))
    fireEvent.click(screen.getByRole('button', { name: /previous/i }))
    expect(screen.getByTestId('loc').textContent).toBe('/list?page=3')
  })
})
