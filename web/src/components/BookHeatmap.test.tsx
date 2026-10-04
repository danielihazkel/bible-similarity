// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book } from '../api/types'
import { BookHeatmap } from './BookHeatmap'

const BOOKS: Book[] = ['Genesis', 'Exodus', 'Leviticus'].map((name, book_id) => ({
  book_id,
  name,
  he_name: name,
  osis: name,
  section: 'Torah',
  n_chapters: 1,
}))

afterEach(cleanup)

describe('BookHeatmap', () => {
  it('moves a keyboard cursor over the off-diagonal cells and selects with Enter', () => {
    const onSelect = vi.fn()
    render(
      <BookHeatmap
        books={BOOKS}
        order={[0, 1, 2]}
        value={() => 0.5}
        title={(a, b) => `${a}→${b}`}
        selected={null}
        onSelect={onSelect}
        label="Test map"
      />,
    )
    const svg = screen.getByRole('img')
    fireEvent.keyDown(svg, { key: 'ArrowRight' }) // first cell: row 0, column 1
    expect(screen.getByText('0→1', { selector: 'p' })).toBeTruthy()
    fireEvent.keyDown(svg, { key: 'ArrowDown' }) // (1, 1) is the diagonal: skipped to (2, 1)
    expect(screen.getByText('2→1', { selector: 'p' })).toBeTruthy()
    fireEvent.keyDown(svg, { key: 'Enter' })
    expect(onSelect).toHaveBeenCalledWith('2-1')
  })
})
