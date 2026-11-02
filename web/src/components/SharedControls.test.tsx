// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as csv from '../lib/csv'
import { BookSelect, Segmented } from './Controls'
import { GeoMap } from './GeoMap'
import { TableCsv } from './TableCsv'

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
