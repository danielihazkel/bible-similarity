// @vitest-environment jsdom
import type { UseQueryResult } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it } from 'vitest'
import { PagedList } from './Pager'

interface Data {
  items: string[]
  total: number
  limit: number
}
const result = (r: Partial<UseQueryResult<Data>>) => r as UseQueryResult<Data>
const ok = (data: Data, stale = false) =>
  result({ isPending: false, isError: false, error: null, data, isPlaceholderData: stale })

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function show(res: UseQueryResult<Data>, path = '/list') {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/list"
          element={
            <PagedList res={res} empty="Nothing here." summary={(d, page, pages) => `${d.total} rows · ${page} of ${pages}`}>
              {(d, stale) => (
                <ul className={`rows ${stale}`}>
                  {d.items.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )}
            </PagedList>
          }
        />
      </Routes>
      <Location />
    </MemoryRouter>,
  )
}

afterEach(cleanup)

describe('PagedList', () => {
  it('shows loading, then an error', () => {
    show(result({ isPending: true }))
    expect(screen.getByText(/Loading/)).toBeTruthy()
    cleanup()
    show(result({ isPending: false, isError: true, error: new Error('boom') }))
    expect(screen.getByText(/boom/)).toBeTruthy()
  })

  it('says when the list is empty, and offers the last page past the end', () => {
    show(ok({ items: [], total: 0, limit: 10 }))
    expect(screen.getByText('Nothing here.')).toBeTruthy()
    cleanup()
    show(ok({ items: [], total: 25, limit: 10 }), '/list?page=9')
    fireEvent.click(screen.getByRole('button', { name: /last page/i }))
    expect(screen.getByTestId('loc').textContent).toBe('/list?page=3')
  })

  it('draws the summary, the list (stale while the next page loads) and the pager', () => {
    show(ok({ items: ['a', 'b'], total: 25, limit: 10 }, true), '/list?page=2')
    expect(screen.getByText('25 rows · 2 of 3')).toBeTruthy()
    expect(screen.getByRole('list').className).toBe('rows stale')
    fireEvent.click(screen.getByRole('button', { name: /previous/i }))
    expect(screen.getByTestId('loc').textContent).toBe('/list')
  })

  it('leaves out the pager for a single page', () => {
    show(ok({ items: ['a'], total: 1, limit: 10 }))
    expect(screen.queryByRole('navigation')).toBeNull()
    expect(screen.getByRole('list').className).toBe('rows ')
  })
})
