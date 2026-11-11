// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as csv from '../lib/csv'
import { BookSelect, Segmented } from './Controls'
import { GeoMap } from './GeoMap'
import { TableCsv, TableWrap } from './TableCsv'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('TableCsv', () => {
  it('wraps the table in its labelled scroll region and exports what it shows', () => {
    const save = vi.spyOn(csv, 'downloadCsv').mockImplementation(() => {})
    render(
      <TableCsv name="voices" tabIndex={0} role="region" aria-label="Speakers">
        <table>
          <thead>
            <tr>
              <th>Speaker</th>
              <th>Words</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>משה</td>
              <td>1,200</td>
            </tr>
          </tbody>
        </table>
      </TableCsv>,
    )
    const region = screen.getByRole('region', { name: 'Speakers' })
    expect(region.getAttribute('tabindex')).toBe('0')
    expect(region.className).toBe('table-wrap')
    fireEvent.click(screen.getByRole('button', { name: 'Export table (CSV)' }))
    expect(save).toHaveBeenCalledWith('voices.csv', [{ Speaker: 'משה', Words: '1,200' }])
  })
})

describe('TableWrap (M167)', () => {
  // jsdom lays nothing out: the observer reports at once, and the widths are given by the test
  function widths(scroll: number, client: number) {
    vi.stubGlobal(
      'ResizeObserver',
      class {
        cb: () => void
        constructor(cb: () => void) {
          this.cb = cb
        }
        observe() {
          this.cb()
        }
        disconnect() {}
      },
    )
    vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockReturnValue(scroll)
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(client)
  }
  const page = (wrap: React.ReactNode) => (
    <main>
      <h2>Names over time</h2>
      <section>
        <p>About the table.</p>
        {wrap}
      </section>
    </main>
  )
  const table = (
    <table>
      <tbody>
        <tr>
          <td>ירמיהו</td>
        </tr>
      </tbody>
    </table>
  )

  it('is a tab stop named after the heading above it while its table is wider than it', async () => {
    widths(900, 390)
    const { container } = render(page(<TableWrap>{table}</TableWrap>))
    const region = await screen.findByRole('region', { name: 'Names over time' })
    expect(region).toBe(container.querySelector('.table-wrap'))
    expect(region.tabIndex).toBe(0)
    vi.unstubAllGlobals()
  })

  it('adds no tab stop while the table fits', async () => {
    widths(390, 390)
    const { container } = render(page(<TableWrap>{table}</TableWrap>))
    await new Promise((r) => setTimeout(r, 20))
    expect(screen.queryByRole('region')).toBeNull()
    expect(container.querySelector('.table-wrap')?.hasAttribute('tabindex')).toBe(false)
    vi.unstubAllGlobals()
  })

  it('keeps a name the page gave it, and falls back to "Table" with no heading before it', async () => {
    widths(900, 390)
    render(
      <>
        <TableWrap>{table}</TableWrap>
        <TableCsv name="x" tabIndex={0} role="region" aria-label="Speakers">
          {table}
        </TableCsv>
      </>,
    )
    expect(await screen.findByRole('region', { name: 'Table' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Speakers' })).toBeTruthy()
    vi.unstubAllGlobals()
  })
})

describe('BookSelect and Segmented', () => {
  const books = [
    { book_id: 0, name: 'Genesis', he_name: 'בראשית' },
    { book_id: 1, name: 'Exodus', he_name: 'שמות' },
  ]

  it('BookSelect offers every book after "all" and gives null back for "all"', () => {
    const onChange = vi.fn()
    render(<BookSelect label="Book" all="All books" books={books} value={1} onChange={onChange} />)
    const select = screen.getByRole('combobox', { name: 'Book' }) as HTMLSelectElement
    expect([...select.options].map((o) => o.textContent)).toEqual(['All books', 'Genesis · בראשית', 'Exodus · שמות'])
    expect(select.value).toBe('1')
    fireEvent.change(select, { target: { value: '' } })
    expect(onChange).toHaveBeenLastCalledWith(null)
    fireEvent.change(select, { target: { value: '0' } })
    expect(onChange).toHaveBeenLastCalledWith('0')
  })

  it('Segmented is a radio group with the chosen option checked', () => {
    const onChange = vi.fn()
    render(<Segmented label="View" value="a" options={[{ value: 'a', label: 'One' }, { value: 'b', label: 'Two' }]} onChange={onChange} />)
    expect(screen.getByRole('radiogroup', { name: 'View' })).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'One' }).getAttribute('aria-checked')).toBe('true')
    fireEvent.click(screen.getByRole('radio', { name: 'Two' }))
    expect(onChange).toHaveBeenCalledWith('b')
  })

  it('Segmented has one tab stop, and the arrows, Home and End move to an option and choose it (M167)', () => {
    const onChange = vi.fn()
    const options = [
      { value: 'a', label: 'One' },
      { value: 'b', label: 'Two' },
      { value: 'c', label: 'Three' },
    ]
    const { rerender } = render(<Segmented label="View" value="b" options={options} onChange={onChange} />)
    const radio = (name: string) => screen.getByRole('radio', { name })
    expect(['One', 'Two', 'Three'].map((n) => radio(n).tabIndex)).toEqual([-1, 0, -1])
    radio('Two').focus()
    fireEvent.keyDown(radio('Two'), { key: 'ArrowRight' })
    expect(onChange).toHaveBeenLastCalledWith('c')
    expect(document.activeElement).toBe(radio('Three'))
    fireEvent.keyDown(radio('Three'), { key: 'ArrowDown' }) // past the last: round to the first
    expect(onChange).toHaveBeenLastCalledWith('a')
    fireEvent.keyDown(radio('One'), { key: 'ArrowLeft' })
    expect(onChange).toHaveBeenLastCalledWith('c')
    fireEvent.keyDown(radio('Three'), { key: 'Home' })
    expect(onChange).toHaveBeenLastCalledWith('a')
    fireEvent.keyDown(radio('One'), { key: 'End' })
    expect(onChange).toHaveBeenLastCalledWith('c')
    const n = onChange.mock.calls.length
    fireEvent.keyDown(radio('Three'), { key: 'End' }) // already there: nothing chosen again
    fireEvent.keyDown(radio('Three'), { key: 'a' })
    fireEvent.keyDown(radio('Three'), { key: 'ArrowLeft', ctrlKey: true })
    expect(onChange).toHaveBeenCalledTimes(n)
    // a value that is none of the options leaves the first as the tab stop
    rerender(<Segmented label="View" value="z" options={options} onChange={onChange} />)
    expect(['One', 'Two', 'Three'].map((name) => radio(name).tabIndex)).toEqual([0, -1, -1])
  })

  it('Segmented reads Left and Right in the direction of its group', () => {
    const onChange = vi.fn()
    render(
      <div dir="rtl" style={{ direction: 'rtl' }}>
        <Segmented label="תצוגה" value="a" options={[{ value: 'a', label: 'אחת' }, { value: 'b', label: 'שתיים' }]} onChange={onChange} />
      </div>,
    )
    fireEvent.keyDown(screen.getByRole('radio', { name: 'אחת' }), { key: 'ArrowLeft' })
    expect(onChange).toHaveBeenLastCalledWith('b')
  })
})

describe('GeoMap keys', () => {
  const points = [
    { place_id: 7, he: 'ירושלם', kind: 'town' as const, lat: 31.78, lon: 35.23, n: 10 },
    { place_id: 9, he: 'באר שבע', kind: 'town' as const, lat: 31.25, lon: 34.79, n: 4 },
  ]
  const bounds = { lon0: 34, lat0: 30, lon1: 36, lat1: 33 }

  it('steps through the places with the arrows, opens one with Enter and zooms with + and -', () => {
    const onSelect = vi.fn()
    const onBounds = vi.fn()
    render(<GeoMap basemap={undefined} points={points} bounds={bounds} onBounds={onBounds} onSelect={onSelect} label="Places" />)
    const map = screen.getByRole('img')
    fireEvent.keyDown(map, { key: 'Enter' })
    expect(onSelect).not.toHaveBeenCalled() // nothing chosen yet
    fireEvent.keyDown(map, { key: 'ArrowRight' })
    fireEvent.keyDown(map, { key: 'Enter' })
    const first = onSelect.mock.calls[0][0]
    fireEvent.keyDown(map, { key: 'ArrowRight' })
    fireEvent.keyDown(map, { key: 'Enter' })
    expect(new Set([first, onSelect.mock.calls[1][0]])).toEqual(new Set([7, 9]))
    fireEvent.keyDown(map, { key: 'ArrowLeft' })
    fireEvent.keyDown(map, { key: 'Enter' })
    expect(onSelect.mock.calls[2][0]).toBe(first) // back to the first
    fireEvent.keyDown(map, { key: '+' })
    fireEvent.keyDown(map, { key: '-' })
    const [zin, zout] = onBounds.mock.calls.map((c) => c[0].lon1 - c[0].lon0)
    expect(zin).toBeLessThan(2)
    expect(zout).toBeGreaterThan(2)
  })
})
